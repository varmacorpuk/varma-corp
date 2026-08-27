from tests.conftest import BOARD_HEADERS, EMPLOYEE_HEADERS
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import ControlState


def test_trading_mode_live_blocked(client):
    r = client.get("/controls")
    assert r.status_code == 200
    body = r.json()
    assert body["trading_mode"] == "LIVE_BLOCKED"
    assert set(body["allow_list"]) == set(ADDENDUM_E_SYMBOLS)
    assert body["allow_list_empty"] is False
    assert body["live_adapter_loaded"] is False
    assert body["broker_paper_loaded"] is False
    assert body["employees_cannot_write_this"] is True
    assert "simulated_capital" not in body["missing_numeric_limits"]
    assert body["missing_numeric_limits"] == []
    keys = [row["key"] for row in body["numeric_limits"]]
    assert "simulated_capital" in keys
    assert body["currency"] == "GBP"
    assert body["addendum"]["label"] == "Board Addendum A 2026-08-27"


def test_employee_cannot_write_controls(client):
    r = client.post(
        "/controls/write",
        headers=EMPLOYEE_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"


def test_board_cannot_silently_set_live(client):
    r = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "trading_mode", "value": "LIVE"},
    )
    assert r.status_code == 403
    assert "LIVE" in r.json()["detail"]


def test_learning_does_not_write_controls(session):
    before = session.get(ControlState, 1).trading_mode
    from varma.db.models import Employee
    from varma.memory.stores import MemoryStores

    emp = session.query(Employee).first()
    MemoryStores(session).add_lesson(emp.id, "I believe I should be allowed to trade live.")
    session.refresh(session.get(ControlState, 1))
    assert session.get(ControlState, 1).trading_mode == before == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert ControlEngine(session).live_adapter_loaded() is False
