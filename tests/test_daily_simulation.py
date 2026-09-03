"""Stages 6/7/9: deterministic-first discipline + a representative operating day.

Proves AI is invoked ONLY for reasoning/prose tasks, and deterministic operations
(meeting record, nightly filter, backup, control deny path) make ZERO AI calls.
Uses FakeLLM. No live trading. No network.
"""

from __future__ import annotations

from varma.backup.job import run_company_backup
from varma.controls.engine import ControlEngine
from varma.db.engine import get_session_factory
from varma.db.models import AICallLog, Employee, PaperFill
from varma.db.seed import MI_SLUG
from varma.employees.runtime import EmployeeRuntime
from varma.observability.ai_usage import ai_usage_summary
from varma.ports.execution import ExecutionPort
from varma.routines.run_0730_meeting import run_0730_meeting
from varma.routines.run_brief import run_brief
from varma.routines.run_challenge import run_challenge
from varma.routines.run_nightly_filter import run_nightly_filter
from varma.routines.run_risk_deny import run_risk_deny
from varma.routines.run_paper_trade_path import run_paper_trade_path

REASONING_TASKS = {
    "prepare_daily_intelligence_brief",
    "challenge_sample_thesis",
    "review_unsafe_path",
    "chat",
}


def _ai_count() -> int:
    s = get_session_factory()()
    try:
        return s.query(AICallLog).count()
    finally:
        s.close()


def test_ai_only_for_reasoning_deterministic_ops_make_no_ai_calls(session):
    mi = session.query(Employee).filter_by(slug=MI_SLUG).one()

    # Reasoning tasks legitimately use AI (prose/judgement).
    run_brief(session)
    run_challenge(session)
    run_risk_deny(session)
    EmployeeRuntime(session, mi).chat("What is in the brief?")
    assert _ai_count() >= 4

    # Deterministic operations must make ZERO additional AI calls.
    before = _ai_count()
    run_0730_meeting(session, started_by="board-member")
    run_nightly_filter(session)
    run_company_backup(session, started_by="board-member")
    path = run_paper_trade_path(session, started_by="board-member")
    assert path["allowed"] is False
    assert path["reason"] == "PAPER_EXECUTION_CLOSED"
    assert path["ai_called"] is False
    trader = session.query(Employee).filter_by(slug="trader").one()
    deny = ExecutionPort(session).place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert deny.allowed is False
    assert deny.reason == "PAPER_EXECUTION_CLOSED"
    assert _ai_count() == before  # meeting/filter/backup/paper-path/deny used ordinary software only

    # Measurement: every AI call is a reasoning task; no real model was used.
    summary = ai_usage_summary(get_session_factory()())
    assert set(summary["by_task"]).issubset(REASONING_TASKS)
    assert summary["real_model_calls"] == 0

    # Governance and trading safety intact after a full day.
    snap = ControlEngine(session).snapshot()
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert snap["live_adapter_loaded"] is False
    assert snap["broker_paper_loaded"] is False
    assert ControlEngine(session).paper_execution_closed() is True
    assert session.query(PaperFill).count() == 0
