from tests.conftest import BOARD_HEADERS, EMPLOYEE_HEADERS, SESSION_OPEN
from varma.clock import now_london
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import (
    AllowListInstrument,
    ClosedPaperTrade,
    ControlState,
    Employee,
    PaperFill,
    PaperOrder,
    Permission,
)
from varma.db.seed import MI_SLUG
from varma.observability.board import BoardObservability
from varma.paper.ledger import evaluation_snapshot
from varma.paper.simulator import ASSUMPTIONS_NOTE, SPREAD_BPS, simulator_assumptions
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED, ExecutionPort


def _grant_place_and_allow(session, symbol="AAPL"):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    if session.query(AllowListInstrument).filter_by(symbol=symbol).one_or_none() is None:
        session.add(
            AllowListInstrument(
                symbol=symbol,
                venue="NASDAQ",
                approved_by="test-only",
                approved_at=now_london(),
            )
        )
    session.commit()
    return emp


def test_evaluation_ledger_exists_with_zero_fills(session):
    snap = evaluation_snapshot(session)
    assert snap["closed_trades"] == 0
    assert snap["profitable_closes"] == 0
    assert snap["win_rate"] == 0
    assert snap["book_pnl_gbp"] == 0
    assert snap["book_profitable"] is False
    assert snap["evaluation_trigger_met"] is False
    assert snap["evaluation_auto_switch_live"] is False
    assert snap["live_switched"] is False
    assert snap["zero_fills_valid"] is True
    assert "profit > 0" in snap["successful_trade_definition"]
    assert session.query(PaperFill).count() == 0
    assert session.query(ClosedPaperTrade).count() == 0
    obs = BoardObservability(session).snapshot()
    assert obs["evaluation"]["closed_trades"] == 0
    assert obs["paper_ledger"]["fills"] == 0
    assert obs["paper_ledger"]["assumptions"]["spread_bps"] == SPREAD_BPS
    assert obs["controls"]["trading_mode"] == "LIVE_BLOCKED"
    assert ASSUMPTIONS_NOTE
    assert simulator_assumptions()["broker"] is False


def test_simulator_denies_empty_allow_list_live_kill_switch_and_limits(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    engine = ControlEngine(session)
    empty = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "ZZQQ", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert empty.reason == "SYMBOL_NOT_ON_ALLOW_LIST"

    live = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.reason == "LIVE_BLOCKED"

    _grant_place_and_allow(session)
    over = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 201, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert over.reason == "MAX_POSITION_EXCEEDED"

    from varma.controls.kill_switch import trip_kill_switch

    trip_kill_switch(session, actor_id="board-member", reason="BOARD_MEMBER_HALT")
    halted = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
    )
    assert halted.reason == "KILL_SWITCH"
    assert session.query(PaperFill).count() == 0
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_simulator_fills_allow_listed_ticker_when_paper_open(session):
    emp = _grant_place_and_allow(session)
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 0.5, "notional_gbp": 50, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is True
    assert d.reason == "PAPER_FILL_SIMULATED"
    assert session.query(PaperFill).count() == 1
    assert session.query(PaperOrder).filter_by(status="FILLED").count() == 1
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    paper = ExecutionPort(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "BROKER_PAPER", "quantity": 1},
    )
    assert paper.reason == "BROKER_PAPER_NOT_LOADED"


def test_place_order_api_denies_unknown_ticker(client):
    r = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "ZZQQ", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "SYMBOL_NOT_ON_ALLOW_LIST"
    employee = client.post(
        "/execution/place-order",
        headers=EMPLOYEE_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert employee.status_code == 403
