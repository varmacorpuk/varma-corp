from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    EMPLOYEE_HEADERS,
    LONDON_CASH_CLOSE,
    QUANT_HEADERS,
    RISK_HEADERS,
    SESSION_OPEN,
    TECH_HEADERS,
    TRADER_HEADERS,
)
from varma.controls.addendum_c import FLATTEN_AT, FLATTEN_NOT_AT
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_i import PAPER_EXECUTION_CLOSED_REASON
from varma.controls.addendum_k import (
    ADDENDUM_K_LABEL,
    ADDENDUM_K_LSE_SYMBOLS,
    INVENTED_US_LISTINGS,
    LSE_AFTER_LONDON_CASH_CLOSE_REASON,
    LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE,
    LSE_SESSION_RULE_KEY,
    addendum_k_public,
)
from varma.controls.engine import ControlEngine
from varma.controls.lse_session import (
    LSE_HOLD_SYMBOLS,
    LSE_SESSION_RULE_REASON,
    lse_hold_blocks,
    lse_session_rule_is_unset,
)
from varma.db.models import ControlSetting, ControlState, Employee, PaperFill, Permission
from varma.db.seed import MI_SLUG
from varma.observability.board import BoardObservability
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED

US_NAMES = tuple(s for s in ADDENDUM_E_SYMBOLS if not s.endswith(".L"))
from varma.clock import now_london
from varma.db.models import AllowListInstrument
EMPLOYEE_SETS = (
    EMPLOYEE_HEADERS,
    CEO_HEADERS,
    RISK_HEADERS,
    TRADER_HEADERS,
    QUANT_HEADERS,
    TECH_HEADERS,
)


def _grant_place(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    return emp


def _add_lse_to_allow_list(session):
    """Test-only: add SHEL.L/AZN.L/ULVR.L so Addendum K can be exercised."""
    now = now_london()
    for sym in ADDENDUM_K_LSE_SYMBOLS:
        if session.query(AllowListInstrument).filter_by(symbol=sym).one_or_none() is None:
            session.add(AllowListInstrument(symbol=sym, venue="LSE", approved_by="test-only", approved_at=now))
    session.commit()


def test_addendum_k_is_board_set_not_unset(session):
    row = session.get(ControlSetting, LSE_SESSION_RULE_KEY)
    assert row.value == LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE
    assert row.source == ADDENDUM_K_LABEL
    assert lse_session_rule_is_unset(session) is False
    pub = addendum_k_public()
    assert pub["label"] == ADDENDUM_K_LABEL
    assert pub["hari_explicit_yes"] is True
    assert pub["letter_exists_outside_repo"] is True
    assert pub["chat_is_not_the_record"] is True
    assert pub["flatten_at"] == FLATTEN_AT == "US_REGULAR_CASH_CLOSE"
    assert pub["flatten_not_at"] == FLATTEN_NOT_AT == "LONDON_CASH_CLOSE"
    assert pub["london_cash_close_is_not_flatten"] is True
    assert pub["paper_execution_stays"] == "OPEN_OR_CLOSED_BY_ADDENDUM_I"
    assert pub["not_grand_opening"] is False
    assert pub["trading_mode_stays"] == "LIVE_BLOCKED"
    snap = ControlEngine(session).snapshot()
    assert snap["addendum_k"]["label"] == ADDENDUM_K_LABEL
    assert snap["lse_session"]["session_rule"] == LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE
    assert snap["lse_session"]["session_rule_unset"] is False
    assert snap["addendum_c"]["flatten_at_london_cash_close"] is False
    gate = BoardObservability(session).snapshot()["paper_gate"]
    assert gate["lse_session_rule_unset"] is False
    assert gate["addendum_k"] == ADDENDUM_K_LABEL
    assert gate["paper_execution_closed"] is False
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_london_open_uk_names_may_fill_when_paper_open(session):
    """Mocked London-open session: UK names are not denied by K while London cash is open."""
    _add_lse_to_allow_list(session)
    emp = _grant_place(session)
    engine = ControlEngine(session)
    assert engine.paper_execution_closed() is False
    for symbol in ADDENDUM_K_LSE_SYMBOLS:
        assert lse_hold_blocks(session, symbol, at=SESSION_OPEN) is False
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": symbol, "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
            at=SESSION_OPEN,
        )
        assert d.allowed is True
        assert d.reason == "PAPER_FILL_SIMULATED"
        assert d.reason != LSE_AFTER_LONDON_CASH_CLOSE_REASON
        assert d.reason != LSE_SESSION_RULE_REASON
    assert session.query(PaperFill).count() == 3


def test_after_london_shut_session_rule_unit_denies_lse_three_ignoring_closed(session):
    """(2) Session-rule unit after London cash close, even ignoring CLOSED.

    CLOSED stays on in the database and in integration. This unit does not
    consult the CLOSED flag; it only asks whether K would deny the LSE three.
    """
    assert ControlEngine(session).paper_execution_closed() is False
    for symbol in ADDENDUM_K_LSE_SYMBOLS:
        assert lse_hold_blocks(session, symbol, at=LONDON_CASH_CLOSE) is True
        assert lse_hold_blocks(session, symbol, at=SESSION_OPEN) is False
    _add_lse_to_allow_list(session)
    emp = _grant_place(session)
    engine = ControlEngine(session)
    for symbol in ADDENDUM_K_LSE_SYMBOLS:
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": symbol, "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
            at=LONDON_CASH_CLOSE,
        )
        assert d.allowed is False
        assert d.reason == LSE_AFTER_LONDON_CASH_CLOSE_REASON
        assert d.reason != PAPER_EXECUTION_CLOSED_REASON
        assert d.details["addendum_k"] == ADDENDUM_K_LABEL
        assert d.details["london_cash_close_is_not_flatten"] is True
        assert d.details["paper_execution_closed"] is False
    assert session.query(PaperFill).count() == 0
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_us_names_not_denied_by_k_after_london_shut(session):
    """US names are not denied by K after London shut; they may fill while desk is open."""
    emp = _grant_place(session)
    engine = ControlEngine(session)
    assert engine.paper_execution_closed() is False
    for symbol in ("AAPL", "MSFT", "NVDA"):
        assert lse_hold_blocks(session, symbol, at=LONDON_CASH_CLOSE) is False
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": symbol, "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
            at=LONDON_CASH_CLOSE,
        )
        assert d.allowed is True
        assert d.reason == "PAPER_FILL_SIMULATED"
        assert d.reason != LSE_AFTER_LONDON_CASH_CLOSE_REASON
        assert d.reason != LSE_SESSION_RULE_REASON
    assert session.query(PaperFill).count() == 3


def test_k_survives_hypothetical_paper_open_after_london_shut(session):
    _add_lse_to_allow_list(session)
    emp = _grant_place(session)
    paper = session.get(ControlSetting, "paper_execution")
    paper.value = "OPEN"
    session.commit()
    engine = ControlEngine(session)
    assert engine.paper_execution_closed() is False
    d = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=LONDON_CASH_CLOSE,
    )
    assert d.allowed is False
    assert d.reason == LSE_AFTER_LONDON_CASH_CLOSE_REASON
    assert session.query(PaperFill).count() == 0


def test_no_invented_us_listings_and_addendum_c_unrewritten(session):
    allow = set(ControlEngine(session).allow_list_symbols())
    # After Addendum L the default list is US-only; LSE names removed.
    # K logic stays in code for when LSE names return.
    for fake in INVENTED_US_LISTINGS:
        assert fake not in allow
    assert allow == set(ADDENDUM_E_SYMBOLS)
    snap = ControlEngine(session).snapshot()
    assert snap["addendum_c"]["flatten_at"] == FLATTEN_AT == "US_REGULAR_CASH_CLOSE"
    assert snap["addendum_c"]["flatten_not_at"] == FLATTEN_NOT_AT == "LONDON_CASH_CLOSE"
    assert snap["addendum_c"]["flatten_at_london_cash_close"] is False
    assert snap["lse_session"]["split_flatten_clocks"] is True
    assert snap["split_flatten_clocks"] is True
    assert snap["risk_02f"]["bound"] is True
    assert snap["risk_02f"]["id"] == "02F"
    assert snap["lse_session"]["invented_us_listings"] is False
    assert snap["addendum_k"]["invented_us_listings"] is False


def test_missing_session_rule_still_fail_closed_unset(session):
    _add_lse_to_allow_list(session)
    emp = _grant_place(session)
    row = session.get(ControlSetting, LSE_SESSION_RULE_KEY)
    session.delete(row)
    session.commit()
    assert lse_session_rule_is_unset(session) is True
    assert lse_hold_blocks(session, "SHEL.L", at=SESSION_OPEN) is True
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == LSE_SESSION_RULE_REASON
    assert d.reason != PAPER_EXECUTION_CLOSED_REASON
    assert session.query(PaperFill).count() == 0


def test_employees_cannot_write_addendum_k(client, monkeypatch):
    monkeypatch.setattr("varma.controls.engine.now_london", lambda: SESSION_OPEN)
    for headers in EMPLOYEE_SETS:
        r = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "lse_session_rule", "value": "UNSET"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
        k = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "addendum_k", "value": "open"},
        )
        assert k.status_code == 403
        flatten = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "paper_flatten_at", "value": "LONDON_CASH_CLOSE"},
        )
        assert flatten.status_code == 403
    board = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "lse_session_rule", "value": "UNSET"},
    )
    assert board.status_code == 403
    setting = client.get("/controls").json()
    assert setting["lse_session"]["session_rule"] == LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE
    assert setting["addendum_k"]["label"] == ADDENDUM_K_LABEL
    assert setting["trading_mode"] == "LIVE_BLOCKED"
    trader = client.post(
        "/execution/place-order",
        headers=TRADER_HEADERS,
        json={"symbol": "AZN.L", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert trader.status_code == 403
    assert trader.json()["detail"]["reason"] == "LIVE_BLOCKED"
    us = client.post(
        "/execution/place-order",
        headers=TRADER_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "BROKER_PAPER"},
    )
    assert us.status_code == 403
    assert us.json()["detail"]["reason"] == "BROKER_PAPER_NOT_LOADED"
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
