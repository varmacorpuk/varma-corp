from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    EMPLOYEE_HEADERS,
    QUANT_HEADERS,
    RISK_HEADERS,
    SESSION_OPEN,
    TECH_HEADERS,
    TRADER_HEADERS,
)
from varma.controls.addendum_c import FLATTEN_AT, FLATTEN_NOT_AT
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_i import PAPER_EXECUTION_CLOSED_REASON
from varma.controls.engine import ControlEngine
from varma.controls.lse_session import (
    INVENTED_US_LISTINGS,
    LSE_HOLD_SYMBOLS,
    LSE_SESSION_RULE_KEY,
    LSE_SESSION_RULE_REASON,
    LSE_SESSION_RULE_UNSET,
)
from varma.db.models import ControlSetting, ControlState, Employee, PaperFill, Permission
from varma.db.seed import MI_SLUG
from varma.observability.board import BoardObservability
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED

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


def test_lse_three_deny_while_closed_with_distinct_hold(session):
    emp = _grant_place(session)
    engine = ControlEngine(session)
    assert session.get(ControlSetting, LSE_SESSION_RULE_KEY).value == LSE_SESSION_RULE_UNSET
    assert engine.paper_execution_closed() is True
    for symbol in LSE_HOLD_SYMBOLS:
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": symbol, "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
            at=SESSION_OPEN,
        )
        assert d.allowed is False
        assert d.reason == LSE_SESSION_RULE_REASON
        assert d.reason != PAPER_EXECUTION_CLOSED_REASON
        assert d.details["fail_closed"] is True
        assert d.details["cannot_silently_fill_at_grand_opening"] is True
        assert d.details["addendum_c_not_rewritten"] is True
        assert d.details["split_flatten_clocks"] is False
        assert d.details["invented_us_listings"] is False
        assert d.details["paper_execution_closed"] is True
    aapl = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert aapl.allowed is False
    assert aapl.reason == PAPER_EXECUTION_CLOSED_REASON
    assert session.query(PaperFill).count() == 0
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_lse_hold_survives_hypothetical_paper_open(session):
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
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == LSE_SESSION_RULE_REASON
    assert d.details["cannot_silently_fill_at_grand_opening"] is True
    assert session.query(PaperFill).count() == 0


def test_no_invented_us_listings_and_addendum_c_unrewritten(session):
    allow = set(ControlEngine(session).allow_list_symbols())
    assert set(LSE_HOLD_SYMBOLS) <= allow
    for fake in INVENTED_US_LISTINGS:
        assert fake not in allow
    assert allow == set(ADDENDUM_E_SYMBOLS)
    snap = ControlEngine(session).snapshot()
    assert snap["addendum_c"]["flatten_at"] == FLATTEN_AT == "US_REGULAR_CASH_CLOSE"
    assert snap["addendum_c"]["flatten_not_at"] == FLATTEN_NOT_AT == "LONDON_CASH_CLOSE"
    assert snap["addendum_c"]["flatten_at_london_cash_close"] is False
    assert snap["lse_session"]["session_rule_unset"] is True
    assert snap["lse_session"]["split_flatten_clocks"] is False
    assert snap["lse_session"]["invented_us_listings"] is False
    gate = BoardObservability(session).snapshot()["paper_gate"]
    assert gate["lse_session_rule_unset"] is True
    assert gate["split_flatten_clocks"] is False
    assert gate["paper_execution_closed"] is True


def test_employees_cannot_write_lse_session_rule(client):
    for headers in EMPLOYEE_SETS:
        r = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "lse_session_rule", "value": "US_REGULAR_CASH_CLOSE"},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
        flatten = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "paper_flatten_at", "value": "LONDON_CASH_CLOSE"},
        )
        assert flatten.status_code == 403
    board = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "lse_session_rule", "value": "LONDON_CASH_CLOSE"},
    )
    assert board.status_code == 403
    setting = client.get("/controls").json()
    assert setting["lse_session"]["session_rule"] == LSE_SESSION_RULE_UNSET
    assert setting["trading_mode"] == "LIVE_BLOCKED"
    trader = client.post(
        "/execution/place-order",
        headers=TRADER_HEADERS,
        json={"symbol": "AZN.L", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert trader.status_code == 403
    assert trader.json()["detail"]["reason"] == LSE_SESSION_RULE_REASON
    us = client.post(
        "/execution/place-order",
        headers=TRADER_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert us.status_code == 403
    assert us.json()["detail"]["reason"] == PAPER_EXECUTION_CLOSED_REASON
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
