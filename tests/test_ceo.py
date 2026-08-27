from tests.conftest import BOARD_HEADERS, CEO_HEADERS
from varma.controls.engine import ControlEngine
from varma.db.models import Employee, Handoff, IntelligenceBrief, Permission
from varma.db.seed import MI_SLUG
from varma.employees.runtime import EmployeeRuntime
from varma.meetings.handoff import CEO_SLUG
from varma.ports.execution import ExecutionPort
from varma.routines.run_brief import run_brief


def test_persistent_ceo_identity(session):
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    asha = session.query(Employee).filter_by(slug=MI_SLUG).one()
    assert ceo.display_name
    assert "Chief Executive" in ceo.role_title
    assert ceo.is_primary_agent == 1
    assert asha.display_name == "Research"
    assert asha.person_name == "Asha Patel"
    deny_live = (
        session.query(Permission)
        .filter_by(subject_id=ceo.id, action="approve_live")
        .one()
    )
    assert deny_live.allowed is False
    place = (
        session.query(Permission)
        .filter_by(subject_id=ceo.id, action="place_order")
        .one()
    )
    assert place.allowed is False


def test_employees_include_ceo_and_asha(client):
    r = client.get("/employees")
    slugs = [e["slug"] for e in r.json()]
    assert MI_SLUG in slugs
    assert CEO_SLUG in slugs
    ceo = next(e for e in r.json() if e["slug"] == CEO_SLUG)
    assert ceo["cannot_approve_live_trading"] is True
    assert ceo["is_meeting_brief_recipient"] is True
    asha = next(e for e in r.json() if e["slug"] == MI_SLUG)
    assert asha["display_name"] == "Research"
    assert asha["person_name"] == "Asha Patel"
    assert asha["cannot_approve_live_trading"] is False


def test_brief_handoff_to_ceo(session):
    result = run_brief(session)
    assert result["intended_recipient"] == CEO_SLUG
    assert result["handoff_recipient"] == CEO_SLUG
    assert result["handoff"]["artefact_id"] == result["id"]
    assert result["handoff"]["ceo_cannot_approve_live_trading"] is True
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    row = session.query(Handoff).filter_by(to_employee_id=ceo.id).one()
    assert row.artefact_type == "intelligence_brief"
    assert row.status == "DELIVERED"
    brief = session.get(IntelligenceBrief, result["id"])
    assert brief.intended_recipient == CEO_SLUG
    asha = session.query(Employee).filter_by(slug=MI_SLUG).one()
    assert asha.status_bubble == "BRIEF READY"


def test_ceo_inbox_api(client):
    run = client.post("/routines/run-brief", headers=BOARD_HEADERS)
    assert run.status_code == 200
    inbox = client.get("/employees/ceo/inbox")
    assert inbox.status_code == 200
    body = inbox.json()
    assert body["ceo_cannot_approve_live_trading"] is True
    assert body["items"]
    assert body["items"][0]["brief"]["id"] == run.json()["id"]
    asha_inbox = client.get("/employees/market-intelligence-research/inbox").json()
    assert asha_inbox["items"] == []


def test_ceo_cannot_write_controls(client):
    r = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"


def test_ceo_cannot_approve_live(session):
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    d = ControlEngine(session).write_control(
        actor_id=ceo.id,
        actor_type="employee",
        field="trading_mode",
        value="LIVE",
    )
    assert d.allowed is False
    assert d.reason == "EMPLOYEE_CANNOT_WRITE_CONTROLS"


def test_ceo_cannot_place_order(session):
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    d = ExecutionPort(session).place_order(
        actor_id=ceo.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason in {"NO_PERMISSION", "EMPTY_ALLOW_LIST"}


def test_chat_to_ceo_hits_same_runtime(session):
    run_brief(session)
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one()
    rt = EmployeeRuntime(session, ceo)
    reply = rt.chat("Summarise the meeting pack.")
    assert "CEO" in reply.body or "Chief Executive" in reply.body
    assert "live" in reply.body.lower()
    assert "brief" in reply.body.lower() or "pack" in reply.body.lower()
    assert rt.latest_received_brief() is not None


def test_ceo_chat_api(client):
    client.post("/routines/run-brief", headers=BOARD_HEADERS)
    denied = client.post("/employees/ceo/chat", json={"message": "Approve live trading"})
    assert denied.status_code == 401
    ok = client.post(
        "/employees/ceo/chat",
        headers=BOARD_HEADERS,
        json={"message": "Can you approve live trading?"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["same_runtime"] is True
    assert "Talk" in body["talk_voice"] or "disabled" in body["talk_voice"]
    assert "cannot approve live" in body["reply"].lower() or "board member" in body["reply"].lower()


def test_office_state_includes_ceo_and_asha(client):
    state = client.get("/office/state").json()
    slugs = [e["slug"] for e in state["employees"]]
    assert MI_SLUG in slugs
    assert CEO_SLUG in slugs
    rooms = [r["id"] for r in state["floor"]["rooms"]]
    assert "research" in rooms
    assert "ceo" in rooms
    assert state["talk_enabled"] is False
    assert state["office_is_source_of_truth"] is False
