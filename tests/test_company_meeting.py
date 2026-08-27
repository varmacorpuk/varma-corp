from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    RISK_HEADERS,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import AllowListInstrument, CompanyMeeting, ControlState
from varma.meetings.company_meeting import CompanyMeetingRunner
from varma.observability.board import BoardObservability
from varma.routines.run_0730_meeting import run_0730_meeting
from varma.routines.run_brief import run_brief
from varma.routines.run_challenge import run_challenge
from varma.routines.run_risk_deny import run_risk_deny


def test_company_meeting_records_existing_handoffs(session):
    empty = run_0730_meeting(session, started_by="cli")
    assert empty["is_trade"] is False
    assert empty["is_live_approval"] is False
    assert empty["cannot_start_live"] is True
    assert empty["live_started"] is False
    assert empty["daemon"] is False
    assert empty["writes_controls"] is False
    assert empty["started_by"] == "cli"
    assert empty["ceo_handoff_status"] == "not"
    assert empty["challenge_status"] == "not"
    assert empty["risk_status"] == "not"
    assert empty["trading_mode_at_run"] == "LIVE_BLOCKED"
    assert empty["brief_id"] is None
    assert session.query(CompanyMeeting).count() == 1

    brief = run_brief(session)
    challenge = run_challenge(session)
    risk = run_risk_deny(session)
    before_mode = session.get(ControlState, 1).trading_mode
    before_allow = [r.symbol for r in session.query(AllowListInstrument).all()]
    meeting = run_0730_meeting(session, started_by="cli")
    assert meeting["brief_id"] == brief["id"]
    assert meeting["brief_headline"] == brief["headline"]
    assert meeting["ceo_handoff_status"] == "DELIVERED"
    assert meeting["ceo_handoff_id"] == (brief.get("handoff") or {}).get("id")
    assert meeting["thesis_id"] == challenge["thesis"]["id"]
    assert meeting["challenge_review_id"] == challenge["review"]["id"]
    assert "SAMPLE" in (challenge["thesis"]["label"] or "") or meeting["challenge_status"] in {
        "SAMPLE",
        "CHALLENGED",
        challenge["review"]["verdict"],
    }
    assert meeting["risk_decision_id"] == risk["id"]
    assert meeting["risk_status"] == "DENIED"
    assert meeting["is_trade"] is False
    assert meeting["is_live_approval"] is False
    assert meeting["cannot_start_live"] is True
    assert meeting["live_started"] is False
    assert meeting["sample_not_a_live_trade"] is True
    assert session.get(ControlState, 1).trading_mode == before_mode == "LIVE_BLOCKED"
    assert [r.symbol for r in session.query(AllowListInstrument).all()] == before_allow == []
    assert LIVE_ADAPTER_LOADED is False
    assert ControlEngine(session).live_adapter_loaded() is False
    assert ControlEngine(session).broker_paper_loaded() is False


def test_company_meeting_does_not_start_live(session):
    run_brief(session)
    run_0730_meeting(session, started_by="cli")
    d = ControlEngine(session).place_order(
        actor_id="board-member",
        actor_type="board_member",
        order={"symbol": "AAPL", "execution_port": "LIVE", "quantity": 1},
    )
    assert d.allowed is False
    assert d.reason in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    write = ControlEngine(session).write_control(
        actor_id="ceo",
        actor_type="employee",
        field="trading_mode",
        value="LIVE",
    )
    assert write.allowed is False
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_board_runs_meeting_via_api_employees_cannot(client):
    for headers in (EMPLOYEE_HEADERS, CEO_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS):
        denied = client.post("/routines/run-0730-meeting", headers=headers)
        assert denied.status_code == 401
        live = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "trading_mode", "value": "LIVE"},
        )
        assert live.status_code == 403
        order = client.post(
            "/execution/place-order",
            headers=headers,
            json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
        )
        assert order.status_code == 403
        assert order.json()["detail"]["allowed"] is False

    client.post("/routines/run-brief", headers=BOARD_HEADERS)
    client.post("/routines/run-challenge", headers=BOARD_HEADERS)
    client.post("/routines/run-risk-deny", headers=BOARD_HEADERS)
    run = client.post("/routines/run-0730-meeting", headers=BOARD_HEADERS)
    assert run.status_code == 200
    body = run.json()
    assert body["started_by"] == "board-member"
    assert body["is_trade"] is False
    assert body["is_live_approval"] is False
    assert body["cannot_start_live"] is True
    assert body["live_started"] is False
    assert body["ceo_handoff_status"] == "DELIVERED"
    assert body["risk_status"] == "DENIED"
    assert body["trading_mode_at_run"] == "LIVE_BLOCKED"

    obs = client.get("/observability", headers=BOARD_HEADERS).json()
    assert obs["company_meeting"]["run"]["id"] == body["id"]
    assert obs["company_meeting"]["is_trade"] is False
    assert obs["company_meeting"]["cannot_start_live"] is True
    assert obs["company_meeting"]["daemon"] is False
    assert obs["trading_mode"] == "LIVE_BLOCKED"
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False

    after_live = client.post(
        "/execution/place-order",
        headers=CEO_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert after_live.status_code == 403


def test_observability_latest_company_meeting_board_only(client):
    denied = client.get("/observability", headers=EMPLOYEE_HEADERS)
    assert denied.status_code == 401
    empty = client.get("/observability", headers=BOARD_HEADERS).json()["company_meeting"]
    assert empty["read_only"] is True
    assert empty["source"] == "database"
    assert empty["run"] is None
    assert empty["is_trade"] is False
    assert empty["is_live_approval"] is False
    assert empty["cannot_start_live"] is True
    assert "company_meeting" in client.get("/office/state").json()["board_observability"]["includes"]

    client.post("/routines/run-0730-meeting", headers=BOARD_HEADERS)
    after = client.get("/observability", headers=BOARD_HEADERS).json()
    run = after["company_meeting"]["run"]
    assert run is not None
    assert run["started_by"] == "board-member"
    assert run["is_trade"] is False
    assert run["live_started"] is False
    assert after["routines"]["documented"]["company_meeting"]["schedule"] == "07:30 weekdays"
    assert after["routines"]["documented"]["company_meeting"]["daemon"] is False
    assert after["routines"]["documented"]["company_meeting"]["is_trade"] is False

    post = client.post(
        "/observability",
        headers=BOARD_HEADERS,
        json={"is_live_approval": True, "trading_mode": "LIVE"},
    )
    assert post.status_code == 403
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"


def test_company_meeting_runner_does_not_write_controls(session):
    before_mode = session.get(ControlState, 1).trading_mode
    CompanyMeetingRunner(session).run(started_by="cli")
    assert session.get(ControlState, 1).trading_mode == before_mode == "LIVE_BLOCKED"
    assert session.query(AllowListInstrument).count() == 0
    snap = BoardObservability(session).snapshot()
    assert snap["company_meeting"]["run"]["writes_controls"] is False
    assert snap["writes_controls"] is False
    assert snap["live_adapter_loaded"] is False
    assert snap["broker_paper_loaded"] is False
    assert snap["execution_ports"]["broker_paper"]["status"] == "UNLOADED"
    assert snap["execution_ports"]["live"]["status"] == "UNLOADED"
