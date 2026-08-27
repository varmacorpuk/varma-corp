from tests.conftest import BOARD_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS
from varma.controls.engine import ControlEngine
from varma.controls.risk import UNSAFE_DEMO_PATH, RiskPolicy
from varma.db.models import ChallengeReview, Employee, Handoff, Permission, RiskDecision, SampleThesis
from varma.db.seed import MI_SLUG
from varma.employees.runtime import EmployeeRuntime
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG
from varma.ports.execution import ExecutionPort
from varma.routines.run_brief import run_brief
from varma.routines.run_challenge import run_challenge
from varma.routines.run_risk_deny import run_risk_deny


def test_persistent_challenge_and_risk_identities(session):
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    asha = session.query(Employee).filter_by(slug=MI_SLUG).one()
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    assert challenge.is_primary_agent == 1
    assert risk.is_primary_agent == 1
    assert asha.display_name == "Asha Patel"
    assert "Chief Executive" in ceo.role_title
    for emp in (challenge, risk):
        assert (
            session.query(Permission)
            .filter_by(subject_id=emp.id, action="approve_live")
            .one()
            .allowed
            is False
        )
        assert (
            session.query(Permission)
            .filter_by(subject_id=emp.id, action="place_order")
            .one()
            .allowed
            is False
        )


def test_employees_include_four_identities(client):
    slugs = [e["slug"] for e in client.get("/employees").json()]
    assert MI_SLUG in slugs
    assert CEO_SLUG in slugs
    assert CHALLENGE_SLUG in slugs
    assert RISK_SLUG in slugs
    by_slug = {e["slug"]: e for e in client.get("/employees").json()}
    assert by_slug[CEO_SLUG]["is_meeting_brief_recipient"] is True
    assert by_slug[CHALLENGE_SLUG]["cannot_approve_live_trading"] is True
    assert by_slug[RISK_SLUG]["cannot_approve_live_trading"] is True


def test_challenge_sample_thesis_not_a_live_trade(session):
    result = run_challenge(session)
    assert result["sample_not_a_live_trade"] is True
    thesis = session.get(SampleThesis, result["thesis"]["id"])
    assert thesis is not None
    assert thesis.is_live_trade is False
    assert thesis.no_execution_authority is True
    assert "SAMPLE" in thesis.label
    assert thesis.symbol != "XAUUSD"
    review = session.get(ChallengeReview, result["review"]["id"])
    assert review.verdict == "CHALLENGED"
    assert review.no_execution_authority is True
    assert review.does_not_approve_live is True
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    inbox = session.query(Handoff).filter_by(to_employee_id=challenge.id, artefact_type="sample_thesis").all()
    assert inbox
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    to_risk = session.query(Handoff).filter_by(to_employee_id=risk.id, artefact_type="challenge_review").one()
    assert to_risk.artefact_id == review.id


def test_asha_still_produces_brief_ceo_still_recipient(session):
    brief = run_brief(session)
    assert brief["intended_recipient"] == CEO_SLUG
    asha = session.query(Employee).filter_by(slug=MI_SLUG).one()
    assert asha.status_bubble == "BRIEF READY"
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    briefs = session.query(Handoff).filter_by(to_employee_id=ceo.id, artefact_type="intelligence_brief").all()
    assert len(briefs) == 1


def test_challenge_via_api(client):
    denied = client.post("/routines/run-challenge")
    assert denied.status_code == 401
    r = client.post("/routines/run-challenge", headers=BOARD_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["review"]["verdict"] == "CHALLENGED"
    inbox = client.get("/employees/challenge/inbox").json()
    assert inbox["items"]
    assert inbox["items"][0]["thesis"]["id"] == body["thesis"]["id"]
    work = client.get("/employees/challenge/work").json()
    assert work["thesis"]["id"] == body["thesis"]["id"]
    assert work["challenge_review"]["id"] == body["review"]["id"]


def test_risk_denies_unsafe_path(session):
    run_challenge(session)
    result = run_risk_deny(session)
    assert result["decision"] == "DENIED"
    assert result["risk_cannot_approve_live"] is True
    assert result["cannot_approve_live"] is True
    assert "RISK_DENIED" in result["reasons"]
    assert "LIVE_BLOCKED" in result["reasons"] or result["control_engine_reason"] in {
        "LIVE_BLOCKED",
        "NO_PERMISSION",
        "EMPTY_ALLOW_LIST",
        "GOLD_NOT_AUTHORISED",
        "LIVE_ADAPTER_NOT_LOADED",
    }
    assert "GOLD_NOT_AUTHORISED" in result["reasons"]
    assert "SAMPLE_THESIS_IS_NOT_AN_ORDER" in result["reasons"]
    row = session.get(RiskDecision, result["id"])
    assert row.decision == "DENIED"
    assert row.cannot_approve_live is True
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    assert risk.status_bubble == "DENIED"


def test_risk_policy_never_allows_unsafe_demo(session):
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    d = RiskPolicy(session).review(actor_id=risk.id, proposed=UNSAFE_DEMO_PATH)
    assert d.allowed is False
    assert d.reason == "RISK_DENIED"


def test_risk_cannot_write_controls_or_approve_live(client):
    r = client.post(
        "/controls/write",
        headers=RISK_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
    r2 = client.post(
        "/controls/write",
        headers=CHALLENGE_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert r2.status_code == 403


def test_risk_cannot_place_order(session):
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    d = ExecutionPort(session).place_order(
        actor_id=risk.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "LIVE"},
    )
    assert d.allowed is False
    assert ControlEngine(session).state().trading_mode == "LIVE_BLOCKED"


def test_chat_to_challenge_and_risk_same_runtime(session):
    run_challenge(session)
    run_risk_deny(session)
    challenge = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one()
    risk = session.query(Employee).filter_by(slug=RISK_SLUG).one()
    c_reply = EmployeeRuntime(session, challenge).chat("Is this a live trade?")
    assert "SAMPLE" in c_reply.body or "sample" in c_reply.body.lower()
    assert "live" in c_reply.body.lower()
    r_reply = EmployeeRuntime(session, risk).chat("Can you approve live trading?")
    assert "DENIED" in r_reply.body or "deny" in r_reply.body.lower()
    assert "cannot approve live" in r_reply.body.lower()


def test_risk_deny_via_api(client):
    client.post("/routines/run-challenge", headers=BOARD_HEADERS)
    r = client.post("/routines/run-risk-deny", headers=BOARD_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "DENIED"
    work = client.get("/employees/risk/work").json()
    assert work["risk_decision"]["id"] == body["id"]
    assert work["cannot_approve_live_trading"] is True
    chat = client.post(
        "/employees/risk/chat",
        headers=BOARD_HEADERS,
        json={"message": "Approve LIVE"},
    )
    assert chat.status_code == 200
    assert chat.json()["same_runtime"] is True
    assert "Talk" in chat.json()["talk_voice"] or "disabled" in chat.json()["talk_voice"]


def test_office_state_includes_challenge_and_risk(client):
    state = client.get("/office/state").json()
    slugs = [e["slug"] for e in state["employees"]]
    assert {MI_SLUG, CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG} <= set(slugs)
    rooms = [r["id"] for r in state["floor"]["rooms"]]
    assert "challenge" in rooms
    assert "risk" in rooms
    assert state["talk_enabled"] is False
