"""First paper-trade PATH: Trader proposal → ControlEngine → simulator.

PAPER execution stays CLOSED. A legal allow-list paper buy does not fill.
LIVE stays impossible. No hidden production open-switch. FakeLLM is not called.
"""

from __future__ import annotations

import json
import os

from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    EMPLOYEE_HEADERS,
    SESSION_OPEN,
    TRADER_HEADERS,
    close_paper,
)
from varma.controls.addendum_a import MAX_ORDERS_PER_DAY, MAX_POSITION
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_f import TRADER_SLUG
from varma.controls.addendum_i import (
    PAPER_EXECUTION_CLOSED_REASON,
    paper_execution_is_closed,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.controls.kill_switch import trip_kill_switch
from varma.db.models import (
    AICallLog,
    ControlSetting,
    ControlState,
    Employee,
    Evidence,
    PaperFill,
    PaperOrder,
    PaperPosition,
    SkillInvocation,
)
from varma.employees.runtime import EmployeeRuntime
from varma.observability.board import BoardObservability
from varma.paper.simulator import PaperFillSimulator
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.routines.run_paper_trade_path import run_paper_trade_path
from varma.skills.propose_paper_ticket import LEGAL_PAPER_TICKET, ONLY_TRADER_MAY_PROPOSE


def _trader(session) -> Employee:
    return session.query(Employee).filter_by(slug=TRADER_SLUG).one()


def test_legal_allow_list_paper_buy_is_denied_closed_not_filled(session):
    close_paper(session)
    trader = _trader(session)
    assert paper_execution_is_closed(session) is True
    assert LEGAL_PAPER_TICKET["symbol"] in ADDENDUM_E_SYMBOLS
    assert LEGAL_PAPER_TICKET["notional_gbp"] <= MAX_POSITION
    assert MAX_ORDERS_PER_DAY >= 1

    result = EmployeeRuntime(session, trader).propose_paper_ticket(at=SESSION_OPEN)
    assert result["proposed"] is True
    assert result["proposer"]["slug"] == TRADER_SLUG
    assert result["order"]["symbol"] == "AAPL"
    assert result["order"]["side"] == "buy"
    assert result["order"]["execution_port"] == "SIMULATOR"
    assert result["allowed"] is False
    assert result["reason"] == PAPER_EXECUTION_CLOSED_REASON
    assert result["filled"] is False
    assert result["paper_fills"] is False
    assert result["live_fills"] is False
    assert result["fills_delta"] == 0
    assert result["ai_called"] is False
    assert result["llm_task"] is None
    assert result["paper_execution_closed"] is True
    assert result["trading_mode"] == "LIVE_BLOCKED"
    assert result["path"]["steps"] == [
        "trader_proposal",
        "control_engine",
        "internal_simulator",
    ]
    assert result["path"]["reached"] == "control_engine"
    assert result["path"]["closed_gate_on_engine"] is True
    assert result["path"]["simulator_fill_invoked"] is False
    assert result["details"].get("simulator") is not True
    assert result["details"]["allow_list_cannot_fill_until_open"] is True
    assert session.query(PaperFill).count() == 0
    assert session.query(PaperOrder).filter_by(status="FILLED").count() == 0
    assert session.query(PaperPosition).count() == 0
    denied = (
        session.query(Evidence)
        .filter_by(kind="order_denied")
        .order_by(Evidence.created_at.desc())
        .first()
    )
    assert denied is not None
    payload = json.loads(denied.payload)
    assert payload["reason"] == PAPER_EXECUTION_CLOSED_REASON
    proposed = (
        session.query(Evidence)
        .filter_by(kind="paper_ticket_proposed")
        .order_by(Evidence.created_at.desc())
        .first()
    )
    assert proposed is not None
    proposed_payload = json.loads(proposed.payload)
    assert proposed_payload["filled"] is False
    assert proposed_payload["reason"] == PAPER_EXECUTION_CLOSED_REASON
    inv = (
        session.query(SkillInvocation)
        .filter_by(employee_id=trader.id, skill_name="propose_paper_ticket")
        .order_by(SkillInvocation.created_at.desc())
        .first()
    )
    assert inv is not None
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_board_job_runs_path_and_still_does_not_fill(session):
    close_paper(session)
    result = run_paper_trade_path(session, started_by="board-member", at=SESSION_OPEN)
    assert result["proposed"] is True
    assert result["reason"] == PAPER_EXECUTION_CLOSED_REASON
    assert result["filled"] is False
    assert result["ai_called"] is False
    assert session.query(PaperFill).count() == 0
    assert session.query(AICallLog).count() == 0


def test_board_job_http_closed_deny_employees_denied(client, session):
    close_paper(session)
    anon = client.post("/routines/run-paper-trade-path")
    assert anon.status_code == 401
    get_r = client.get("/routines/run-paper-trade-path", headers=BOARD_HEADERS)
    assert get_r.status_code == 405
    for headers in (EMPLOYEE_HEADERS, CEO_HEADERS, TRADER_HEADERS):
        denied = client.post("/routines/run-paper-trade-path", headers=headers)
        assert denied.status_code == 401
    ok = client.post("/routines/run-paper-trade-path", headers=BOARD_HEADERS)
    assert ok.status_code == 200
    body = ok.json()
    assert body["allowed"] is False
    assert body["reason"] == PAPER_EXECUTION_CLOSED_REASON
    assert body["filled"] is False
    assert body["ai_called"] is False
    assert body["job_safety"]["fills"] is False
    assert body["job_safety"]["paper_fills"] is False
    assert body["job_safety"]["live_fills"] is False
    assert body["job_safety"]["loads_broker_ports"] is False
    assert body["job_safety"]["first_paper_trade_path_implemented"] is True
    assert body["job_safety"]["ai_called"] is False
    assert session.query(PaperFill).count() == 0
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_live_still_impossible_on_the_path(session):
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
    assert broker["filled"] is False
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
    assert session.query(PaperFill).count() == 0


def test_kill_switch_still_denies_on_the_path(session):
    trader = _trader(session)
    trip_kill_switch(session, actor_id="board-member", reason="BOARD_MEMBER_HALT")
    halted = EmployeeRuntime(session, trader).propose_paper_ticket(at=SESSION_OPEN)
    assert halted["allowed"] is False
    assert halted["reason"] == "KILL_SWITCH"
    assert halted["filled"] is False
    assert session.query(PaperFill).count() == 0


def test_addendum_a_over_limit_still_denied_closed_wins_until_open(session):
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
    assert session.query(PaperFill).count() == 0


def test_only_trader_runtime_may_propose(session):
    ceo = session.query(Employee).filter_by(slug="ceo").one()
    try:
        EmployeeRuntime(session, ceo).propose_paper_ticket(at=SESSION_OPEN)
        raise AssertionError("CEO must not run the Trader paper-ticket skill")
    except RuntimeError as exc:
        assert ONLY_TRADER_MAY_PROPOSE in str(exc)
    assert session.query(PaperFill).count() == 0


def test_no_production_open_hook_default_config(session, client):
    assert os.environ.get("VARMA_LLM_PROVIDER", "fake") == "fake"
    assert "VARMA_PAPER_OPEN" not in os.environ
    assert "VARMA_GRAND_OPENING" not in os.environ
    row = session.get(ControlSetting, "paper_execution")
    assert row is not None
    assert row.value == "OPEN"
    assert paper_execution_is_closed(session) is False
    after = client.get("/controls").json()
    assert after["paper_execution"] == "OPEN"
    assert after["trading_mode"] == "LIVE_BLOCKED"
    assert after["addendum_i"]["first_paper_trade_path_implemented"] is True
    assert after["addendum_i"]["grand_opening_live"] == "not"
    assert ControlEngine(session).live_adapter_loaded() is False
    sim = PaperFillSimulator(session).fill(
        actor_id=_trader(session).id,
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert sim.allowed is True
    assert sim.reason == "PAPER_FILL_SIMULATED"
    snap = BoardObservability(session).snapshot()
    assert snap["paper_gate"]["first_paper_trade_path_implemented"] is True
    assert snap["paper_gate"]["paper_execution_closed"] is False
    assert snap["paper_gate"]["execution"] is True
    jobs = [row["id"] for row in snap["runnable_jobs"]["items"]]
    assert "run-paper-trade-path" in jobs
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
