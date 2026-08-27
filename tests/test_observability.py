from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    RISK_HEADERS,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import AllowListInstrument, ControlState
from varma.observability.board import BoardObservability
from varma.routines.run_brief import run_brief


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
