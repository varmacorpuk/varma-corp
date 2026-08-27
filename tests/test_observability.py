from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    RISK_HEADERS,
)
from varma.clock import now_london
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import AllowListInstrument, ControlState, MemoryOrg
from varma.db.seed import MI_SLUG
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG
from varma.observability.board import BoardObservability
from varma.routines.run_brief import run_brief
from varma.routines.run_challenge import run_challenge
from varma.routines.run_nightly_filter import run_nightly_filter
from varma.routines.run_risk_deny import run_risk_deny


def test_board_reads_costs_and_evidence_from_database(session):
    before_mode = session.get(ControlState, 1).trading_mode
    before_allow = [r.symbol for r in session.query(AllowListInstrument).all()]
    empty = BoardObservability(session).snapshot()
    assert empty["read_only"] is True
    assert empty["writes_controls"] is False
    assert empty["source"] == "database"
    assert empty["office_is_source_of_truth"] is False
    assert empty["trading_mode"] == "LIVE_BLOCKED"
    assert empty["allow_list_empty"] is True
    assert empty["live_adapter_loaded"] is False
    assert empty["cost_cap_is_board_budget"] is False
    assert "TEMPORARY" in empty["cost_cap_label"]
    assert empty["evidence"]["append_only"] is True

    result = run_brief(session)
    snap = BoardObservability(session).snapshot()
    assert snap["costs"]["total_units"] == result["cost_units"]
    assert snap["costs"]["entries"]
    assert any(row["workflow"] == "prepare_daily_intelligence_brief" for row in snap["costs"]["entries"])
    kinds = {row["kind"] for row in snap["evidence"]["entries"]}
    assert "brief_produced" in kinds
    assert session.get(ControlState, 1).trading_mode == before_mode == "LIVE_BLOCKED"
    assert [r.symbol for r in session.query(AllowListInstrument).all()] == before_allow == []
    assert LIVE_ADAPTER_LOADED is False
    assert ControlEngine(session).live_adapter_loaded() is False


def test_board_observability_api_is_read_only(client):
    denied = client.get("/observability")
    assert denied.status_code == 401

    r = client.get("/observability", headers=BOARD_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["read_only"] is True
    assert body["writes_controls"] is False
    assert body["source"] == "database"
    assert body["trading_mode"] == "LIVE_BLOCKED"
    assert body["allow_list_empty"] is True
    assert body["live_adapter_loaded"] is False
    assert body["cost_cap_is_board_budget"] is False
    assert "TEMPORARY" in body["cost_cap_label"]

    run = client.post("/routines/run-brief", headers=BOARD_HEADERS)
    assert run.status_code == 200
    after = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after["costs"]["total_units"] == run.json()["cost_units"]
    assert after["costs"]["entries"]
    assert after["evidence"]["entries"]
    assert any(row["kind"] == "brief_produced" for row in after["evidence"]["entries"])
    assert after["writes_controls"] is False

    office = client.get("/office/state").json()
    assert office["board_observability"]["path"] == "/observability"
    assert office["board_observability"]["read_only"] is True
    assert office["board_observability"]["writes_controls"] is False
    assert office["office_is_source_of_truth"] is False
    assert "nightly_filter" in office["board_observability"]["includes"]
    assert "meeting_pack" in office["board_observability"]["includes"]
    assert "meeting_artefacts" in office["board_observability"]["includes"]
    assert "status_bubbles" in office["board_observability"]["includes"]
    assert "routines" in office["board_observability"]["includes"]

    controls = client.get("/controls").json()
    assert controls["trading_mode"] == "LIVE_BLOCKED"
    assert controls["allow_list"] == []
    assert controls["live_adapter_loaded"] is False


def test_employees_cannot_write_controls_via_observability(client):
    for headers in (EMPLOYEE_HEADERS, CEO_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS):
        get_r = client.get("/observability", headers=headers)
        assert get_r.status_code == 401
        post_r = client.post(
            "/observability",
            headers=headers,
            json={"field": "trading_mode", "value": "LIVE"},
        )
        assert post_r.status_code == 403
        assert post_r.json()["detail"] == "OBSERVABILITY_IS_READ_ONLY"
        control_r = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "trading_mode", "value": "LIVE"},
        )
        assert control_r.status_code == 403
        assert control_r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"

    board_post = client.post(
        "/observability",
        headers=BOARD_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert board_post.status_code == 403
    assert board_post.json()["detail"] == "OBSERVABILITY_IS_READ_ONLY"

    controls = client.get("/controls").json()
    assert controls["trading_mode"] == "LIVE_BLOCKED"
    assert controls["allow_list"] == []
    assert controls["live_adapter_loaded"] is False


def test_observability_does_not_unblock_live(client):
    client.get("/observability", headers=BOARD_HEADERS)
    client.post("/observability", headers=EMPLOYEE_HEADERS, json={"trading_mode": "LIVE"})
    live = client.post(
        "/execution/place-order",
        headers=EMPLOYEE_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.status_code == 403
    assert live.json()["detail"]["allowed"] is False
    reason = live.json()["detail"]["reason"]
    assert reason in {"LIVE_BLOCKED", "NO_PERMISSION", "EMPTY_ALLOW_LIST", "LIVE_ADAPTER_NOT_LOADED"}
    controls = client.get("/controls").json()
    assert controls["trading_mode"] == "LIVE_BLOCKED"
    assert controls["allow_list"] == []
    assert controls["live_adapter_loaded"] is False


def test_observability_nightly_filter_and_org_titles(session):
    empty = BoardObservability(session).snapshot()
    assert empty["nightly_filter"]["run"] is None
    assert empty["nightly_filter"]["writes_controls"] is False
    assert empty["nightly_filter"]["daemon"] is False
    assert empty["nightly_filter"]["timezone"] == "Europe/London"
    assert empty["organisation_memory"]["titles"] == []
    assert empty["organisation_memory"]["source"] == "database"

    session.add(
        MemoryOrg(
            title="SAMPLE org title — TEMPORARY DEVELOPMENT DEFAULT",
            content="Not Board-approved organisation knowledge.",
            promoted_by="test",
            created_at=now_london(),
        )
    )
    session.commit()
    run_brief(session)
    before = session.get(ControlState, 1).trading_mode
    result = run_nightly_filter(session)
    snap = BoardObservability(session).snapshot()
    assert snap["nightly_filter"]["run"] is not None
    assert snap["nightly_filter"]["run"]["id"] == result["id"]
    assert snap["nightly_filter"]["run"]["controls_written"] is False
    assert snap["nightly_filter"]["run"]["daemon"] is False
    titles = [row["title"] for row in snap["organisation_memory"]["titles"]]
    assert "SAMPLE org title — TEMPORARY DEVELOPMENT DEFAULT" in titles
    assert "content" not in snap["organisation_memory"]["titles"][0]
    assert session.get(ControlState, 1).trading_mode == before == "LIVE_BLOCKED"
    assert snap["writes_controls"] is False


def test_observability_meeting_pack_status(session):
    empty = BoardObservability(session).snapshot()
    pack = empty["meeting_pack"]
    assert pack["read_only"] is True
    assert pack["source"] == "database"
    assert pack["meeting"] == "07:30 Europe/London company meeting"
    assert pack["brief_headline"] is None
    assert pack["ceo_handoff_status"] == "not"
    assert pack["challenge_sample_thesis"]["status"] == "not"
    assert pack["challenge_sample_thesis"]["sample_not_a_live_trade"] is True
    assert pack["risk_status"] == "not"
    assert pack["risk_denied"] is False

    brief = run_brief(session)
    after_brief = BoardObservability(session).snapshot()["meeting_pack"]
    assert after_brief["brief_headline"] == brief["headline"]
    assert after_brief["ceo_handoff_status"] == "DELIVERED"

    challenge = run_challenge(session)
    after_challenge = BoardObservability(session).snapshot()["meeting_pack"]
    assert after_challenge["challenge_sample_thesis"]["present"] is True
    assert "SAMPLE" in (after_challenge["challenge_sample_thesis"]["label"] or "")
    assert after_challenge["challenge_sample_thesis"]["is_live_trade"] is False
    assert after_challenge["challenge_sample_thesis"]["status"] in {
        "SAMPLE",
        challenge["review"]["verdict"],
        "CHALLENGED",
    }

    run_risk_deny(session)
    after_risk = BoardObservability(session).snapshot()
    assert after_risk["meeting_pack"]["risk_status"] == "DENIED"
    assert after_risk["meeting_pack"]["risk_denied"] is True
    assert after_risk["trading_mode"] == "LIVE_BLOCKED"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_observability_status_bubbles_board_only(client):
    denied = client.get("/observability", headers=EMPLOYEE_HEADERS)
    assert denied.status_code == 401
    for headers in (CEO_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS):
        assert client.get("/observability", headers=headers).status_code == 401

    body = client.get("/observability", headers=BOARD_HEADERS).json()
    slugs = [row["slug"] for row in body["status_bubbles"]]
    assert slugs == sorted(slugs)
    assert MI_SLUG in slugs
    assert CEO_SLUG in slugs
    assert CHALLENGE_SLUG in slugs
    assert RISK_SLUG in slugs
    assert len(body["status_bubbles"]) == 4
    for row in body["status_bubbles"]:
        assert row["status_bubble"]
        assert row["read_only"] is True

    client.post("/routines/run-brief", headers=BOARD_HEADERS)
    after = client.get("/observability", headers=BOARD_HEADERS).json()
    by_slug = {row["slug"]: row for row in after["status_bubbles"]}
    assert by_slug[MI_SLUG]["status_bubble"] == "BRIEF READY"
    assert by_slug[CEO_SLUG]["status_bubble"] == "PACK READY"
    assert after["meeting_pack"]["ceo_handoff_status"] == "DELIVERED"

    post = client.post("/observability", headers=BOARD_HEADERS, json={"status_bubble": "LIVE"})
    assert post.status_code == 403
    assert post.json()["detail"] == "OBSERVABILITY_IS_READ_ONLY"
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False


def test_observability_meeting_artefact_list(session):
    empty = BoardObservability(session).snapshot()["meeting_artefacts"]
    assert empty["read_only"] is True
    assert empty["source"] == "database"
    assert empty["items"] == []
    assert empty["meeting"] == "07:30 Europe/London company meeting"

    run_brief(session)
    run_challenge(session)
    run_risk_deny(session)
    data = BoardObservability(session).snapshot()
    kinds = [row["kind"] for row in data["meeting_artefacts"]["items"]]
    assert kinds == [
        "intelligence_brief",
        "handoff",
        "sample_thesis",
        "challenge_review",
        "risk_decision",
    ]
    by_kind = {row["kind"]: row for row in data["meeting_artefacts"]["items"]}
    assert by_kind["handoff"]["status"] == "DELIVERED"
    assert by_kind["handoff"]["to"] == CEO_SLUG
    assert by_kind["sample_thesis"]["is_live_trade"] is False
    assert "SAMPLE" in by_kind["sample_thesis"]["label"]
    assert by_kind["challenge_review"]["does_not_approve_live"] is True
    assert by_kind["risk_decision"]["decision"] == "DENIED"
    assert by_kind["risk_decision"]["cannot_approve_live"] is True
    assert by_kind["intelligence_brief"]["no_execution_authority"] is True
    assert data["trading_mode"] == "LIVE_BLOCKED"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert data["writes_controls"] is False


def test_observability_routine_schedules_from_database(session):
    snap = BoardObservability(session).snapshot()
    routines = snap["routines"]
    assert routines["read_only"] is True
    assert routines["source"] == "database"
    assert routines["daemon"] is False
    assert routines["writes_controls"] is False
    assert routines["timezone"] == "Europe/London"
    names = [row["name"] for row in routines["items"]]
    assert "weekday_0630_london_intelligence_brief" in names
    brief = routines["documented"]["brief"]
    assert brief["schedule"] == "06:30 weekdays"
    assert brief["timezone"] == "Europe/London"
    assert brief["daemon"] is False
    assert "06:30" in brief["description"]
    filt = routines["documented"]["nightly_filter"]
    assert filt["schedule"] == "nightly"
    assert filt["timezone"] == "Europe/London"
    assert filt["daemon"] is False
    assert filt["writes_controls"] is False
    assert ":" not in filt["schedule"]
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert snap["writes_controls"] is False


def test_observability_routine_schedules_api_board_only(client):
    denied = client.get("/observability", headers=EMPLOYEE_HEADERS)
    assert denied.status_code == 401
    body = client.get("/observability", headers=BOARD_HEADERS).json()
    assert body["routines"]["documented"]["brief"]["schedule"] == "06:30 weekdays"
    assert body["routines"]["documented"]["nightly_filter"]["schedule"] == "nightly"
    assert body["routines"]["daemon"] is False
    assert body["routines"]["writes_controls"] is False
    post = client.post("/observability", headers=BOARD_HEADERS, json={"schedule": "LIVE"})
    assert post.status_code == 403
    assert post.json()["detail"] == "OBSERVABILITY_IS_READ_ONLY"
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"




