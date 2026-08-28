"""PR #1 measurement tests. Observational only; existing behaviour must be unchanged."""

from __future__ import annotations

from varma.controls.engine import ControlEngine
from varma.db.engine import get_session_factory
from varma.db.models import AICallLog, Employee
from varma.db.seed import MI_SLUG
from varma.observability.ai_usage import (
    MeasuredLLM,
    ai_usage_summary,
    estimate_tokens_from_chars,
)
from varma.ports.llm import FakeLLM, get_llm
from varma.skills.prepare_daily_intelligence_brief import PrepareDailyIntelligenceBrief


def test_get_llm_is_transparent_fake_wrapper():
    llm = get_llm()
    # Wrapper is transparent: provider_name still "fake" (existing tests rely on this).
    assert llm.provider_name == "fake"
    assert isinstance(llm, MeasuredLLM)
    assert isinstance(llm.inner, FakeLLM)
    # Same structured result as the underlying FakeLLM for a known task.
    wrapped = llm.complete(task="chat", context={"employee": {"slug": "ceo", "id": "x"}, "message": "hi"})
    direct = FakeLLM().complete(task="chat", context={"employee": {"slug": "ceo", "id": "x"}, "message": "hi"})
    assert wrapped["text"] == direct["text"]


def test_estimate_tokens_is_deterministic_heuristic():
    assert estimate_tokens_from_chars(0) == 0
    assert estimate_tokens_from_chars(3) == 1
    assert estimate_tokens_from_chars(8) == 2
    assert estimate_tokens_from_chars(400) == 100


def test_brief_run_records_ai_call_without_changing_behaviour(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    brief = PrepareDailyIntelligenceBrief(session).run(emp)
    # Existing behaviour preserved: the brief still verifies and hands off.
    assert brief.verification_passed is True
    assert brief.trading_mode_at_production == "LIVE_BLOCKED"

    # Measurement recorded exactly the AI call(s) that happened (read via a fresh session).
    s2 = get_session_factory()()
    try:
        rows = s2.query(AICallLog).all()
        brief_calls = [r for r in rows if r.task == "prepare_daily_intelligence_brief"]
        assert len(brief_calls) >= 1
        row = brief_calls[-1]
        assert row.provider == "fake"
        assert row.is_real_model is False
        assert row.input_chars > 0
        assert row.output_chars > 0
        assert row.estimated_tokens > 0
        assert row.estimate_is_heuristic is True
        assert row.employee_slug == MI_SLUG
    finally:
        s2.close()


def test_ai_usage_summary_is_deterministic(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    PrepareDailyIntelligenceBrief(session).run(emp)
    s2 = get_session_factory()()
    try:
        summary = ai_usage_summary(s2)
    finally:
        s2.close()
    assert summary["total_calls"] >= 1
    assert summary["real_model_calls"] == 0
    assert summary["estimate_is_heuristic"] is True
    assert "prepare_daily_intelligence_brief" in summary["by_task"]
    assert "heuristic" in summary["note"]


def test_measurement_does_not_enable_live_trading(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    PrepareDailyIntelligenceBrief(session).run(emp)
    snap = ControlEngine(session).snapshot()
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert snap["live_adapter_loaded"] is False
    assert snap["broker_paper_loaded"] is False
