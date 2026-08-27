from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    RISK_HEADERS,
)
from varma.clock import now_london
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.controls.kill_switch import trip_kill_switch
from varma.db.models import AllowListInstrument, ControlState, Employee, PaperOrder, Permission
from varma.db.seed import MI_SLUG
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED

EMPLOYEE_SETS = (EMPLOYEE_HEADERS, CEO_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS)


def test_board_can_halt_without_ai_employee(client):
    r = client.post("/controls/kill-switch", headers=BOARD_HEADERS, json={"halt": True})
    assert r.status_code == 200
    body = r.json()
    assert body["halted"] is True
    assert body["ai_employee_not_required"] is True
    assert body["loads_live"] is False
    assert body["flattens_live"] is False
    assert body["trading_mode"] == "LIVE_BLOCKED"
    assert body["broker_paper_loaded"] is False
    assert body["live_adapter_loaded"] is False
    controls = client.get("/controls").json()
    assert controls["kill_switch"] is True
    assert controls["trading_mode"] == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_employees_cannot_halt_or_reset_kill_switch(client):
    for headers in EMPLOYEE_SETS:
        halt = client.post("/controls/kill-switch", headers=headers, json={"halt": True})
        assert halt.status_code == 401
        reset = client.post("/controls/kill-switch/reset", headers=headers)
        assert reset.status_code == 403
        assert reset.json()["detail"] == "EMPLOYEE_CANNOT_RESET_KILL_SWITCH"
    controls = client.get("/controls").json()
    assert controls["kill_switch"] is False
    assert controls["trading_mode"] == "LIVE_BLOCKED"


def test_board_can_reset_kill_switch_employees_cannot(client):
    halt = client.post("/controls/kill-switch", headers=BOARD_HEADERS, json={"halt": True})
    assert halt.status_code == 200
    for headers in EMPLOYEE_SETS:
        reset = client.post("/controls/kill-switch/reset", headers=headers)
        assert reset.status_code == 403
        assert reset.json()["detail"] == "EMPLOYEE_CANNOT_RESET_KILL_SWITCH"
    assert client.get("/controls").json()["kill_switch"] is True
    ok = client.post("/controls/kill-switch/reset", headers=BOARD_HEADERS)
    assert ok.status_code == 200
    assert ok.json()["halted"] is False
    assert client.get("/controls").json()["kill_switch"] is False
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"


def test_halt_cancels_open_paper_orders_only(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.add(
        PaperOrder(
            symbol="AAPL",
            side="buy",
            quantity=1,
            notional_gbp=50,
            status="OPEN",
            london_day="2026-08-27",
            actor_id=emp.id,
            execution_port="SIMULATOR",
            is_paper=True,
            is_live=False,
            created_at=now_london(),
        )
    )
    session.commit()
    result = trip_kill_switch(session, actor_id="board-member", reason="BOARD_MEMBER_HALT")
    assert result["cancelled_open_paper_orders"] == 1
    assert result["loads_live"] is False
    assert result["flattens_live"] is False
    open_left = session.query(PaperOrder).filter_by(status="OPEN").count()
    assert open_left == 0
    cancelled = session.query(PaperOrder).filter_by(status="CANCELLED").one()
    assert cancelled.is_live is False
    assert LIVE_ADAPTER_LOADED is False


def test_auto_trip_on_equity_floor(session):
    from varma.db.models import PaperAccount
    from varma.paper.ledger import PaperLedger

    acc = session.get(PaperAccount, 1)
    acc.cash = 800
    acc.equity_at_day_start = 1000
    session.commit()
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    assert PaperLedger(session).equity() <= 800
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "KILL_SWITCH"
    assert session.get(ControlState, 1).kill_switch is True
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
