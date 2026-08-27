from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    RISK_HEADERS,
)
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import AllowListInstrument, ControlState
from varma.observability.board import BoardObservability
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.routines.board_jobs import BOARD_JOBS

JOB_PATHS = [job["path"] for job in BOARD_JOBS]
EMPLOYEE_SETS = (EMPLOYEE_HEADERS, CEO_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS)


def _assert_execution_untouched(client, session=None):
    controls = client.get("/controls").json()
    assert controls["trading_mode"] == "LIVE_BLOCKED"
    assert set(controls["allow_list"]) == set(ADDENDUM_E_SYMBOLS)
    assert controls["allow_list_empty"] is False
    assert controls["live_adapter_loaded"] is False
    assert controls["broker_paper_loaded"] is False
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
    if session is not None:
        assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
        assert set(r.symbol for r in session.query(AllowListInstrument).all()) == set(ADDENDUM_E_SYMBOLS)
        assert ControlEngine(session).live_adapter_loaded() is False
        assert ControlEngine(session).broker_paper_loaded() is False


def _assert_job_safety(body):
    safety = body["job_safety"]
    assert safety["loads_broker_ports"] is False
    assert safety["changes_trading_mode"] is False
    assert safety["fills"] is False
    assert safety["paper_fills"] is False
    assert safety["live_fills"] is False
    assert safety["writes_controls"] is False
    assert safety["not_get_observability"] is True
    assert safety["trading_mode"] == "LIVE_BLOCKED"
    assert safety["trading_mode_unchanged"] is True
    assert safety["allow_list_empty"] is False
    assert safety["broker_paper_loaded"] is False
    assert safety["live_adapter_loaded"] is False
    assert safety["broker_paper_status"] == "UNLOADED"
    assert safety["live_status"] == "UNLOADED"


def test_runnable_jobs_listed_on_observability_not_run_by_get(client):
    empty = client.get("/observability", headers=BOARD_HEADERS).json()
    jobs = empty["runnable_jobs"]
    assert jobs["board_only"] is True
    assert jobs["employees_denied"] is True
    assert jobs["not_get_observability"] is True
    assert jobs["get_observability_runs_jobs"] is False
    assert jobs["loads_broker_ports"] is False
    assert jobs["changes_trading_mode"] is False
    assert jobs["fills"] is False
    assert jobs["cli_still_works"] is True
    assert jobs["daemon"] is False
    paths = [row["path"] for row in jobs["items"]]
    assert paths == JOB_PATHS
    labels = [row["label"] for row in jobs["items"]]
    assert "Run morning intelligence brief" in labels
    assert "Run SAMPLE challenge" in labels
    assert "Run Risk deny-path" in labels
    assert "Run 07:30 meeting record" in labels
    assert "Run nightly memory filter" in labels
    assert "Flatten paper before US cash close" in labels
    for row in jobs["items"]:
        assert row["method"] == "POST"
        assert row["path"] != "/observability"
        assert row["cli"].startswith("python -m varma.routines.")
        assert row["loads_broker_ports"] is False
        if row["id"] == "run-flatten-us-close":
            assert row["internal_simulator_flatten"] is True
            assert row["flatten_at"] == "US_REGULAR_CASH_CLOSE"
            assert row["paper_fills"] is True
        else:
            assert row["paper_fills"] is False
        assert row["fills"] is False

    assert empty["meeting_pack"]["brief_headline"] is None
    assert empty["nightly_filter"]["run"] is None
    assert empty["company_meeting"]["run"] is None
    assert empty["meeting_pack"]["risk_denied"] is False

    again = client.get("/observability", headers=BOARD_HEADERS).json()
    assert again["meeting_pack"]["brief_headline"] is None
    assert again["nightly_filter"]["run"] is None
    assert again["company_meeting"]["run"] is None
    assert again["meeting_artefacts"]["items"] == []
    office = client.get("/office/state").json()
    assert "runnable_jobs" in office["board_observability"]["includes"]
    _assert_execution_untouched(client)


def test_employees_cannot_run_board_jobs(client):
    for path in JOB_PATHS:
        anon = client.post(path)
        assert anon.status_code == 401
        get_r = client.get(path, headers=BOARD_HEADERS)
        assert get_r.status_code == 405
        for headers in EMPLOYEE_SETS:
            denied = client.post(path, headers=headers)
            assert denied.status_code == 401
            live = client.post(
                "/controls/write",
                headers=headers,
                json={"field": "trading_mode", "value": "LIVE"},
            )
            assert live.status_code == 403
    post_obs = client.post(
        "/observability",
        headers=EMPLOYEE_HEADERS,
        json={"run": "run-brief"},
    )
    assert post_obs.status_code == 403
    assert post_obs.json()["detail"] == "OBSERVABILITY_IS_READ_ONLY"
    _assert_execution_untouched(client)


def test_board_runs_jobs_from_post_then_panel_refreshes(client):
    empty = client.get("/observability", headers=BOARD_HEADERS).json()
    assert empty["meeting_pack"]["brief_headline"] is None

    brief = client.post("/routines/run-brief", headers=BOARD_HEADERS)
    assert brief.status_code == 200
    _assert_job_safety(brief.json())
    after_brief = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after_brief["meeting_pack"]["brief_headline"] == brief.json()["headline"]
    assert after_brief["meeting_pack"]["ceo_handoff_status"] == "DELIVERED"
    assert after_brief["costs"]["entries"]
    assert after_brief["trading_mode"] == "LIVE_BLOCKED"

    challenge = client.post("/routines/run-challenge", headers=BOARD_HEADERS)
    assert challenge.status_code == 200
    _assert_job_safety(challenge.json())
    assert challenge.json()["sample_not_a_live_trade"] is True
    after_challenge = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after_challenge["meeting_pack"]["challenge_sample_thesis"]["present"] is True
    assert after_challenge["meeting_pack"]["challenge_sample_thesis"]["is_live_trade"] is False

    risk = client.post("/routines/run-risk-deny", headers=BOARD_HEADERS)
    assert risk.status_code == 200
    _assert_job_safety(risk.json())
    assert risk.json()["decision"] == "DENIED"
    after_risk = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after_risk["meeting_pack"]["risk_status"] == "DENIED"
    assert after_risk["meeting_pack"]["risk_denied"] is True

    meeting = client.post("/routines/run-0730-meeting", headers=BOARD_HEADERS)
    assert meeting.status_code == 200
    _assert_job_safety(meeting.json())
    assert meeting.json()["is_trade"] is False
    assert meeting.json()["is_live_approval"] is False
    assert meeting.json()["live_started"] is False
    after_meeting = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after_meeting["company_meeting"]["run"]["id"] == meeting.json()["id"]
    assert after_meeting["company_meeting"]["is_trade"] is False

    filt = client.post("/routines/run-nightly-filter", headers=BOARD_HEADERS)
    assert filt.status_code == 200
    _assert_job_safety(filt.json())
    assert filt.json()["controls_written"] is False
    after_filter = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after_filter["nightly_filter"]["run"]["id"] == filt.json()["id"]
    assert after_filter["nightly_filter"]["run"]["controls_written"] is False
    assert after_filter["execution_ports"]["broker_paper"]["status"] == "UNLOADED"
    assert after_filter["execution_ports"]["live"]["status"] == "UNLOADED"
    assert after_filter["execution_ports"]["fills"] is False
    assert after_filter["controls"]["trading_mode"] == "LIVE_BLOCKED"
    _assert_execution_untouched(client)

    paper = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "BROKER_PAPER"},
    )
    assert paper.status_code == 403
    assert paper.json()["detail"]["allowed"] is False
    live = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.status_code == 403
    assert live.json()["detail"]["allowed"] is False
    _assert_execution_untouched(client)


def test_board_job_catalog_matches_cli(session):
    snap = BoardObservability(session).snapshot()
    jobs = snap["runnable_jobs"]
    assert jobs["cli_still_works"] is True
    assert jobs["get_observability_runs_jobs"] is False
    clis = {row["id"]: row["cli"] for row in jobs["items"]}
    assert clis["run-brief"] == "python -m varma.routines.run_brief"
    assert clis["run-challenge"] == "python -m varma.routines.run_challenge"
    assert clis["run-risk-deny"] == "python -m varma.routines.run_risk_deny"
    assert clis["run-0730-meeting"] == "python -m varma.routines.run_0730_meeting"
    assert clis["run-nightly-filter"] == "python -m varma.routines.run_nightly_filter"
    assert clis["run-flatten-us-close"] == "python -m varma.routines.run_flatten_us_close"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert snap["writes_controls"] is False
    assert LIVE_ADAPTER_LOADED is False
