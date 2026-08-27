def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["timezone"] == "Europe/London"
    assert body["trading_mode"] == "LIVE_BLOCKED"
    assert body["live_adapter_loaded"] is False
    assert body["broker_paper_loaded"] is False
    assert "DEVELOPMENT" in body["environment"]


def test_whoami_board_member(client):
    r = client.get("/auth/whoami", headers={"Authorization": "Bearer dev-board-member"})
    assert r.json()["actor_type"] == "board_member"
    assert "Board Member" in r.json()["terminology"]
