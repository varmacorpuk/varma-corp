"""PR #2 regression tests: context slimming must not change behaviour or controls."""

from __future__ import annotations

from varma.controls.addendum_f import ALL_STAFF_SLUGS
from varma.controls.engine import ControlEngine
from varma.db.models import Employee, PaperFill
from varma.db.seed import MI_SLUG
from varma.employees.context import DYNAMIC_KEYS, PERSISTENT_KEYS, STATIC_KEYS, classify
from varma.employees.runtime import EmployeeRuntime
from varma.meetings.handoff import CHALLENGE_SLUG
from varma.ports.execution import ExecutionPort
from varma.ports.llm import FakeLLM, get_llm
from varma.routines.run_brief import run_brief
from varma.skills.challenge_sample_thesis import SKILL_NAME as CHALLENGE_TASK
from varma.skills.challenge_sample_thesis import ChallengeSampleThesis
from varma.skills.prepare_daily_intelligence_brief import SKILL_NAME as BRIEF_TASK
from varma.skills.prepare_daily_intelligence_brief import PrepareDailyIntelligenceBrief
from varma.skills.prepare_sample_thesis import create_sample_thesis
from varma.skills.review_unsafe_path import SKILL_NAME as RISK_TASK


class CapturingLLM:
    """Transparent capture of the context delivered to the model (test-only)."""

    def __init__(self, inner):
        self.inner = inner
        self.last = None

    @property
    def provider_name(self):
        return self.inner.provider_name

    def complete(self, *, task, context):
        self.last = {"task": task, "context": context}
        return self.inner.complete(task=task, context=context)


def _mi(session):
    return session.query(Employee).filter_by(slug=MI_SLUG).one()


def test_brief_context_drops_verbose_controls_and_keeps_compact_hint(session):
    cap = CapturingLLM(FakeLLM())
    brief = PrepareDailyIntelligenceBrief(session, llm=cap).run(_mi(session))
    ctx = cap.last["context"]

    # Verbose full snapshot is gone; its large keys are not present.
    assert "controls" not in ctx
    for verbose in ("addendum_a", "addendum_i", "addendum_c", "live_gate", "numeric_limits"):
        assert verbose not in ctx

    # Compact, correct, informational hint is present.
    hint = ctx["controls_hint"]
    assert hint["can_place_orders"] is False
    assert hint["paper_trading"] == "CLOSED"
    assert hint["live_trading"] == "BLOCKED"
    assert hint["trading_mode"] == "LIVE_BLOCKED"
    assert hint["broker_paper_loaded"] is False

    # Required DYNAMIC info still supplied; persistent lessons present exactly once.
    assert ctx["news"] and ctx["prices"]
    assert "lessons" in ctx
    assert sum(1 for k in ctx if k == "lessons") == 1

    # Behaviour preserved.
    assert brief.verification_passed is True
    assert brief.trading_mode_at_production == "LIVE_BLOCKED"


def test_context_categories_static_persistent_dynamic(session):
    cap = CapturingLLM(FakeLLM())
    PrepareDailyIntelligenceBrief(session, llm=cap).run(_mi(session))
    groups = classify(cap.last["context"])
    assert groups["other"] == []  # every delivered key is classified
    assert "role_knowledge" in groups["static"]
    assert "lessons" in groups["persistent"]
    assert "controls_hint" in groups["dynamic"]
    assert "news" in groups["dynamic"] and "prices" in groups["dynamic"]
    # Categories are disjoint.
    assert STATIC_KEYS.isdisjoint(PERSISTENT_KEYS)
    assert STATIC_KEYS.isdisjoint(DYNAMIC_KEYS)
    assert PERSISTENT_KEYS.isdisjoint(DYNAMIC_KEYS)


def test_chat_context_pack_uses_compact_hint(session):
    run_brief(session)
    packed = EmployeeRuntime(session, _mi(session)).context_pack()
    assert "controls" not in packed
    assert packed["controls_hint"]["live_trading"] == "BLOCKED"
    # Dynamic info required for chat reasoning is still present.
    assert packed["latest_brief"] is not None
    assert classify(packed)["other"] == []


def test_challenge_context_supplies_required_thesis(session):
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    thesis = create_sample_thesis(session)
    cap = CapturingLLM(FakeLLM())
    ChallengeSampleThesis(session, llm=cap).run(challenge, thesis)
    ctx = cap.last["context"]
    assert ctx["thesis"]["symbol"] == thesis.symbol
    assert classify(ctx)["other"] == []


def test_controls_remain_deterministic_live_off_paper_closed(session):
    trader = session.query(Employee).filter_by(slug="trader").one()
    d = ExecutionPort(session).place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "PAPER_EXECUTION_CLOSED"
    snap = ControlEngine(session).snapshot()
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert snap["live_adapter_loaded"] is False
    assert ControlEngine(session).paper_execution_closed() is True
    assert session.query(PaperFill).count() == 0


def test_identities_slugs_and_task_strings_unchanged(session):
    slugs = {e.slug for e in session.query(Employee).all()}
    assert slugs == set(ALL_STAFF_SLUGS)
    assert _mi(session).display_name == "Asha Patel · Research"
    assert BRIEF_TASK == "prepare_daily_intelligence_brief"
    assert CHALLENGE_TASK == "challenge_sample_thesis"
    assert RISK_TASK == "review_unsafe_path"
    assert get_llm().provider_name == "fake"


def test_persistent_lesson_still_reaches_the_model(session):
    first = run_brief(session)
    token = f"JOB_LESSON:{first['id']}"
    second = run_brief(session)
    # The lesson from job #1 is still delivered as persistent context to job #2.
    assert token in second["summary"]
