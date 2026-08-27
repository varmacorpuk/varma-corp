from tests.conftest import BOARD_HEADERS
from varma.db.models import ChatMessage, Employee
from varma.employees.runtime import EmployeeRuntime
from varma.routines.run_brief import run_brief


def test_chat_hits_same_employee_runtime(session):
    run_brief(session)
    emp = session.query(Employee).filter_by(slug="market-intelligence-research").one()
    rt = EmployeeRuntime(session, emp)
    reply = rt.chat("What is in the brief?")
    assert emp.display_name.split()[0] in reply.body or "Research" in reply.body
    assert "brief" in reply.body.lower() or "Brief" in reply.body
    rows = session.query(ChatMessage).filter_by(employee_id=emp.id).all()
    assert len(rows) >= 2


def test_chat_api_requires_board_member(client):
    r = client.post(
        "/employees/market-intelligence-research/chat",
        json={"message": "hello"},
    )
    assert r.status_code == 401
    r2 = client.post(
        "/employees/market-intelligence-research/chat",
        headers=BOARD_HEADERS,
        json={"message": "Status?"},
    )
    assert r2.status_code == 200
    assert r2.json()["same_runtime"] is True
    assert "Talk" in r2.json()["talk_voice"] or "disabled" in r2.json()["talk_voice"]
