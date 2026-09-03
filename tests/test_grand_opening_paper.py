"""Grand Opening PAPER (Hari explicit yes, 3 Sep 2026).

Practice / paper only. LIVE stays blocked. Addendum I remains the
two-opening rule. Opening is a Board-only control write.
"""

from __future__ import annotations

from tests.conftest import (
    BEFORE_UK_OPEN,
    BOARD_HEADERS,
    CEO_HEADERS,
    EMPLOYEE_HEADERS,
    LONDON_CASH_CLOSE,
    SESSION_OPEN,
    TECH_HEADERS,
    TRADER_HEADERS,
    WEEKEND,
    close_paper,
)
from varma.controls.addendum_a import MAX_ORDERS_PER_DAY, MAX_POSITION, SIMULATED_CAPITAL
from varma.controls.addendum_c import us_regular_cash_close_london
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_f import TRADER_SLUG
from varma.controls.addendum_i import (
    GRAND_OPENING_LIVE_NOT_IMPLEMENTED_REASON,
    GRAND_OPENING_PAPER_REASON,
    PAPER_EXECUTION_CLOSED_REASON,
    addendum_i_public,
    paper_execution_is_closed,
)
from varma.controls.addendum_k import LSE_AFTER_LONDON_CASH_CLOSE_REASON
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.controls.kill_switch import trip_kill_switch
from varma.db.models import ControlSetting, ControlState, Employee, PaperFill, PaperPosition
from varma.employees.runtime import EmployeeRuntime
from varma.observability.board import BoardObservability
from varma.paper.flatten import flatten_all_paper
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.routines.run_paper_trade_path import run_paper_trade_path
from varma.skills.propose_paper_ticket import LEGAL_PAPER_TICKET

EMPLOYEE_SETS = (EMPLOYEE_HEADERS, CEO_HEADERS, TRADER_HEADERS, TECH_HEADERS)


def _trader(session) -> Employee:
    return session.query(Employee).filter_by(slug=TRADER_SLUG).one()


def test_fresh_seed_paper_open_live_blocked(session):
    engine = ControlEngine(session)
    assert paper_execution_is_closed(session) is False
    assert session.get(ControlSetting, "paper_execution").value == "OPEN"
    assert session.get(ControlSetting, "grand_opening_paper").value == "yes"
    assert session.get(ControlSetting, "grand_opening_live").value == "not"
    snap = engine.snapshot()
    assert snap["paper_execution"] == "OPEN"
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert snap["addendum_i"]["two_opening_rule_still_exists"] is True
    assert snap["addendum_i"]["grand_opening_paper_done"] is True
    assert snap["addendum_i"]["grand_opening_live_done"] is False
    assert snap["addendum_i"]["simulated_capital_status"] == "PAPER_STARTING_BOOK"
    assert set(engine.allow_list_symbols()) == set(ADDENDUM_E_SYMBOLS)
    assert engine.limit_value("simulated_capital") == SIMULATED_CAPITAL
    assert engine.limit_value("max_position") == MAX_POSITION
    assert engine.limit_value("max_daily_loss") == 50.0
    assert engine.limit_value("max_orders_per_day") == float(MAX_ORDERS_PER_DAY)
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
    pub = addendum_i_public(session)
    assert pub["employees_cannot_open_the_firm"] is True
    assert pub["employees_cannot_close_the_firm"] is True


def test_live_still_impossible(session, client):
    trader = _trader(session)
    live = EmployeeRuntime(session, trader).propose_paper_ticket(
        order={
            "symbol": "AAPL",
            "side": "buy",
            "notional_gbp": 50,
            "execution_port": "LIVE",
        },
        at=SESSION_OPEN,
    )
    assert live["allowed"] is False
    assert live["reason"] == "LIVE_BLOCKED"
    assert live["filled"] is False
    broker = EmployeeRuntime(session, trader).propose_paper_ticket(
        order={
            "symbol": "AAPL",
            "side": "buy",
            "notional_gbp": 50,
            "execution_port": "BROKER_PAPER",
        },
        at=SESSION_OPEN,
    )
    assert broker["allowed"] is False
    assert broker["reason"] == "BROKER_PAPER_NOT_LOADED"
    http_live = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert http_live.status_code == 403
    assert http_live.json()["detail"]["reason"] in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}
    board_live = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "grand_opening_live", "value": "yes"},
    )
    assert board_live.status_code == 403
    assert board_live.json()["detail"] == GRAND_OPENING_LIVE_NOT_IMPLEMENTED_REASON
    mode = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert mode.status_code == 403
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
    assert session.query(PaperFill).count() == 0


def test_legal_aapl_paper_buy_fills_when_open_in_session(session):
    assert LEGAL_PAPER_TICKET["symbol"] == "AAPL"
    result = EmployeeRuntime(session, _trader(session)).propose_paper_ticket(at=SESSION_OPEN)
    assert result["proposed"] is True
    assert result["allowed"] is True
    assert result["filled"] is True
    assert result["paper_fills"] is True
    assert result["live_fills"] is False
    assert result["reason"] == "PAPER_FILL_SIMULATED"
    assert result["paper_execution"] == "OPEN"
    assert result["trading_mode"] == "LIVE_BLOCKED"
    assert result["ai_called"] is False
    assert result["path"]["reached"] == "internal_simulator"
    assert session.query(PaperFill).count() == 1
    assert session.query(PaperPosition).filter_by(symbol="AAPL").count() == 1
    path = run_paper_trade_path(session, started_by="board-member", at=SESSION_OPEN)
    assert path["ai_called"] is False
    assert path["live_fills"] is False
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_employees_cannot_open_or_close_or_write_locks(client, session):
    for headers in EMPLOYEE_SETS:
        for field, value in (
            ("paper_execution", "CLOSED"),
            ("paper_execution", "OPEN"),
            ("grand_opening_paper", "yes"),
            ("grand_opening_live", "yes"),
            ("firm_open", True),
            ("open_firm", False),
            ("trading_mode", "LIVE"),
            ("allow_list", ["FAKE"]),
            ("lse_session_rule", "UNSET"),
        ):
            r = client.post(
                "/controls/write",
                headers=headers,
                json={"field": field, "value": value},
            )
            assert r.status_code == 403
            assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
    after = client.get("/controls").json()
    assert after["paper_execution"] == "OPEN"
    assert after["trading_mode"] == "LIVE_BLOCKED"
    assert after["addendum_i"]["two_opening_rule_still_exists"] is True


def test_board_member_can_open_paper_from_closed_fixture(client, session):
    close_paper(session)
    assert paper_execution_is_closed(session) is True
    denied = EmployeeRuntime(session, _trader(session)).propose_paper_ticket(at=SESSION_OPEN)
    assert denied["reason"] == PAPER_EXECUTION_CLOSED_REASON
    assert denied["filled"] is False
    opened = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "paper_execution", "value": "OPEN"},
    )
    assert opened.status_code == 200
    assert opened.json()["ok"] is True
    assert opened.json()["reason"] == GRAND_OPENING_PAPER_REASON
    session.expire_all()
    after = client.get("/controls").json()
    assert after["paper_execution"] == "OPEN"
    assert after["trading_mode"] == "LIVE_BLOCKED"
    assert after["addendum_i"]["grand_opening_live"] == "not"
    filled = EmployeeRuntime(session, _trader(session)).propose_paper_ticket(at=SESSION_OPEN)
    assert filled["allowed"] is True
    assert filled["filled"] is True
    assert filled["reason"] == "PAPER_FILL_SIMULATED"
    live = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "grand_opening_live", "value": "yes"},
    )
    assert live.status_code == 403
    assert live.json()["detail"] == GRAND_OPENING_LIVE_NOT_IMPLEMENTED_REASON
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_shel_l_denied_by_k_after_london_cash_close_while_paper_open(session):
    engine = ControlEngine(session)
    assert engine.paper_execution_closed() is False
    d = engine.place_order(
        actor_id=_trader(session).id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=LONDON_CASH_CLOSE,
    )
    assert d.allowed is False
    assert d.reason == LSE_AFTER_LONDON_CASH_CLOSE_REASON
    assert session.query(PaperFill).count() == 0
    aapl = engine.place_order(
        actor_id=_trader(session).id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=LONDON_CASH_CLOSE,
    )
    assert aapl.allowed is True
    assert aapl.reason == "PAPER_FILL_SIMULATED"


def test_kill_switch_and_over_limit_still_deny_when_open(session):
    trader = _trader(session)
    over = EmployeeRuntime(session, trader).propose_paper_ticket(
        order={
            "symbol": "AAPL",
            "side": "buy",
            "notional_gbp": 201,
            "execution_port": "SIMULATOR",
        },
        at=SESSION_OPEN,
    )
    assert over["allowed"] is False
    assert over["reason"] == "MAX_POSITION_EXCEEDED"
    assert over["filled"] is False
    trip_kill_switch(session, actor_id="board-member", reason="BOARD_MEMBER_HALT")
    halted = EmployeeRuntime(session, trader).propose_paper_ticket(at=SESSION_OPEN)
    assert halted["allowed"] is False
    assert halted["reason"] == "KILL_SWITCH"
    assert halted["filled"] is False
    assert session.query(PaperFill).count() == 0
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_overnight_and_after_us_close_flatten_rules_hold(session):
    trader = _trader(session)
    engine = ControlEngine(session)
    filled = engine.place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert filled.allowed is True
    assert session.query(PaperPosition).count() == 1
    for when in (BEFORE_UK_OPEN, us_regular_cash_close_london(SESSION_OPEN), WEEKEND):
        d = engine.place_order(
            actor_id=trader.id,
            actor_type="employee",
            order={"symbol": "MSFT", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
            at=when,
        )
        assert d.allowed is False
        assert d.reason == "PAPER_SESSION_CLOSED"
    close = us_regular_cash_close_london(SESSION_OPEN)
    result = flatten_all_paper(session, actor_id="board-member", at=close, started_by="cli")
    assert result["flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert result["flatten_not_at"] == "LONDON_CASH_CLOSE"
    assert result["flatten_at_london_cash_close"] is False
    assert result["closed_positions"] == 1
    assert result["flatten_fills"] == 1
    assert result["trading_mode_after"] == "LIVE_BLOCKED"
    assert session.query(PaperPosition).count() == 0
    overnight = engine.place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=close,
    )
    assert overnight.allowed is False
    assert overnight.reason == "PAPER_SESSION_CLOSED"
    gate = BoardObservability(session).snapshot()["paper_gate"]
    assert gate["paper_execution"] == "OPEN"
    assert gate["grand_opening_live"] == "not"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
