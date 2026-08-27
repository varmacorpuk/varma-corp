import json

from tests.conftest import BOARD_HEADERS, QUANT_HEADERS, TRADER_HEADERS
from varma.controls.addendum_f import ALL_STAFF_SLUGS, QUANT_SLUG, TECH_SLUG, TRADER_SLUG, staff_display_for_slug
from varma.controls.engine import ControlEngine
from varma.db.models import (
    AllowListInstrument,
    ControlState,
    Employee,
    EmployeeFoundation,
    EmployeeRelationship,
    PaperFill,
    SkillInvocation,
)
from varma.db.seed import MI_SLUG
from varma.employees.brain import EmployeeBrain
from varma.meetings.handoff import CHALLENGE_SLUG, RISK_SLUG
from varma.memory.stores import (
    GOVERNED_PROMOTION_REQUIRED,
    MEMORY_POINTERS,
    MemoryStores,
)
from varma.ports.execution import ExecutionPort
from varma.ports.llm import get_llm
from varma.routines.run_brief import run_brief
from varma.routines.run_challenge import run_challenge
from varma.routines.run_nightly_filter import run_nightly_filter
from varma.routines.run_risk_deny import run_risk_deny


BELIEF = "I believe this: AAPL is a buy."
TRADER_BELIEF = "I believe this: fill AAPL now."


def test_seven_durable_employees_are_records_not_prompts(session):
    brain = EmployeeBrain(session)
    rows = {e.slug: e for e in session.query(Employee).all()}
    assert set(rows) == set(ALL_STAFF_SLUGS)
    for slug in ALL_STAFF_SLUGS:
        emp = rows[slug]
        rec = brain.record(emp)
        assert rec["identity"]["display_name"] == staff_display_for_slug(slug)
        assert rec["identity"]["display_name"] == emp.display_name
        assert rec["role_knowledge"]
        assert rec["professional_foundation"] == rec["role_knowledge"]
        assert rec["authority_boundaries"]
        assert rec["memory_pointers"] == MEMORY_POINTERS
        assert rec["llm_call_is_invocation"] is True
        assert rec["employee_is_not_a_prompt"] is True
        assert session.get(EmployeeFoundation, emp.id) is not None
        lessons = MemoryStores(session).employee_lessons(emp.id)
        assert lessons, f"{slug} must have persistent memory"
        rec_skills = rec["skills"]
        assert rec_skills, f"{slug} must have at least one skill record"
    challenge = rows[CHALLENGE_SLUG]
    quant = rows[QUANT_SLUG]
    rel = (
        session.query(EmployeeRelationship)
        .filter_by(from_employee_id=challenge.id, to_employee_id=quant.id, kind="independent_of")
        .one()
    )
    assert "Quant" in rel.note
    risk = rows[RISK_SLUG]
    trader = rows[TRADER_SLUG]
    assert (
        session.query(EmployeeRelationship)
        .filter_by(from_employee_id=risk.id, to_employee_id=trader.id, kind="independent_of")
        .one()
    )
    assert rows[TECH_SLUG].display_name == "Owen Blake · Technology"


def test_second_brief_loads_lesson_from_first_job(session):
    asha = session.query(Employee).filter_by(slug=MI_SLUG).one()
    first = run_brief(session)
    token = f"JOB_LESSON:{first['id']}"
    lessons_after_first = [m.content for m in MemoryStores(session).employee_lessons(asha.id)]
    assert any(token in content for content in lessons_after_first)

    inv1 = (
        session.query(SkillInvocation)
        .filter_by(employee_id=asha.id, skill_name="prepare_daily_intelligence_brief")
        .order_by(SkillInvocation.created_at.asc())
        .all()
    )
    assert inv1[0].blank_prompt is False
    assert json.loads(inv1[0].lessons_json), "first job must load seed lessons from the database"

    second = run_brief(session)
    inv2 = (
        session.query(SkillInvocation)
        .filter_by(employee_id=asha.id, skill_name="prepare_daily_intelligence_brief")
        .order_by(SkillInvocation.created_at.desc())
        .first()
    )
    loaded = json.loads(inv2.lessons_json)
    assert any(token in content for content in loaded)
    assert inv2.blank_prompt is False
    assert token in second["summary"]
    assert get_llm().provider_name == "fake"


def test_second_challenge_loads_lesson_from_first_job(session):
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    first = run_challenge(session)
    token = f"JOB_LESSON:{first['review']['id']}"
    second = run_challenge(session)
    inv = (
        session.query(SkillInvocation)
        .filter_by(employee_id=challenge.id, skill_name="challenge_sample_thesis")
        .order_by(SkillInvocation.created_at.desc())
        .first()
    )
    loaded = json.loads(inv.lessons_json)
    assert any(token in content for content in loaded)
    assert inv.blank_prompt is False
    assert token in second["review"]["summary"]


def test_challenge_does_not_load_originator_belief_as_own(session):
    mi = session.query(Employee).filter_by(slug=MI_SLUG).one()
    quant = session.query(Employee).filter_by(slug=QUANT_SLUG).one()
    stores = MemoryStores(session)
    stores.add_lesson(mi.id, BELIEF)
    stores.add_lesson(quant.id, BELIEF)
    stores.working_put(quant.id, "belief", BELIEF)
    result = run_challenge(session)
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    inv = (
        session.query(SkillInvocation)
        .filter_by(employee_id=challenge.id, skill_name="challenge_sample_thesis")
        .order_by(SkillInvocation.created_at.desc())
        .first()
    )
    loaded = json.loads(inv.lessons_json)
    assert BELIEF not in loaded
    assert inv.originator_beliefs_loaded is False
    assert BELIEF not in result["review"]["summary"]
    pack = EmployeeBrain(session).invocation(
        challenge,
        originator=mi,
    )
    assert pack["originator_beliefs_loaded"] is False
    assert BELIEF not in pack["lessons"]
    assert BELIEF in pack["excluded_originator_lessons"]


def test_risk_does_not_load_trader_belief_as_own(session):
    trader = session.query(Employee).filter_by(slug=TRADER_SLUG).one()
    MemoryStores(session).add_lesson(trader.id, TRADER_BELIEF)
    run_challenge(session)
    result = run_risk_deny(session)
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    inv = (
        session.query(SkillInvocation)
        .filter_by(employee_id=risk.id, skill_name="review_unsafe_path")
        .order_by(SkillInvocation.created_at.desc())
        .first()
    )
    loaded = json.loads(inv.lessons_json)
    assert TRADER_BELIEF not in loaded
    assert inv.originator_beliefs_loaded is False
    assert TRADER_BELIEF not in result["summary"]


def test_learning_writes_memory_never_controls(session):
    asha = session.query(Employee).filter_by(slug=MI_SLUG).one()
    trader = session.query(Employee).filter_by(slug=TRADER_SLUG).one()
    before_mode = session.get(ControlState, 1).trading_mode
    before_allow = [r.symbol for r in session.query(AllowListInstrument).all()]
    before_paper = ControlEngine(session).paper_execution_closed()
    stores = MemoryStores(session)
    stores.add_lesson(asha.id, "Learning stays in employee memory.")
    org = stores.promote_org_knowledge(
        promoter_slug="ceo",
        title="Governed org lesson",
        content="Allow-list presence is not Grand Opening. PAPER stays CLOSED.",
    )
    assert org.promoted_by == "ceo"
    try:
        stores.promote_org_knowledge(
            promoter_slug="trader",
            title="dump",
            content="should fail",
        )
        raise AssertionError("trader must not promote org knowledge")
    except RuntimeError as exc:
        assert GOVERNED_PROMOTION_REQUIRED in str(exc)
    assert session.get(ControlState, 1).trading_mode == before_mode == "LIVE_BLOCKED"
    assert [r.symbol for r in session.query(AllowListInstrument).all()] == before_allow
    assert ControlEngine(session).paper_execution_closed() is before_paper is True
    d = ExecutionPort(session).place_order(
        actor_id=trader.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "PAPER_EXECUTION_CLOSED"
    assert session.query(PaperFill).count() == 0


def test_nightly_filter_after_learning_still_skips_controls(session):
    run_brief(session)
    before = session.get(ControlState, 1).trading_mode
    result = run_nightly_filter(session)
    assert result["controls_written"] is False
    assert session.get(ControlState, 1).trading_mode == before == "LIVE_BLOCKED"
    assert ControlEngine(session).paper_execution_closed() is True


def test_employee_api_exposes_durable_brain(client):
    body = client.get("/employees/market-intelligence-research").json()
    assert body["display_name"] == "Asha Patel · Research"
    assert body["brain"]["role_knowledge"]
    assert body["brain"]["memory_pointers"] == MEMORY_POINTERS
    assert body["brain"]["llm_call_is_invocation"] is True
    assert body["context"]["lessons"]
    denied = client.post(
        "/controls/write",
        headers=QUANT_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert denied.status_code == 403
    trader_live = client.post(
        "/execution/place-order",
        headers=TRADER_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert trader_live.status_code == 403
    assert trader_live.json()["detail"]["reason"] == "PAPER_EXECUTION_CLOSED"
    obs = client.get("/observability", headers=BOARD_HEADERS).json()
    assert obs["trading_mode"] == "LIVE_BLOCKED"
    assert obs["paper_gate"]["paper_execution_closed"] is True
