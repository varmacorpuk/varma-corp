from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    RISK_HEADERS,
    SESSION_OPEN,
)
from varma.clock import now_london
from varma.controls.addendum_a import ADDENDUM_A_LABEL
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import AllowListInstrument, ControlState, Employee, Permission
from varma.db.seed import MI_SLUG
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED

EMPLOYEE_SETS = (EMPLOYEE_HEADERS, CEO_HEADERS, CHALLENGE_HEADERS, RISK_HEADERS)


def _grant_place_and_allow(session, symbol="AAPL"):
    """Test-only allow-list row. Not a Board 10-ticker universe."""
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    if session.query(AllowListInstrument).filter_by(symbol=symbol).one_or_none() is None:
        session.add(
            AllowListInstrument(
                symbol=symbol,
                venue="NASDAQ",
                approved_by="test-only",
                approved_at=now_london(),
            )
        )
    session.commit()
    return emp


def test_addendum_a_limits_are_board_set(session):
    engine = ControlEngine(session)
    assert engine.missing_limits() == []
    by_key = {row["key"]: row for row in engine.limit_rows()}
    assert by_key["simulated_capital"]["numeric_value"] == 1000
    assert by_key["max_position"]["numeric_value"] == 200
    assert by_key["max_daily_loss"]["numeric_value"] == 50
    assert by_key["max_orders_per_day"]["numeric_value"] == 6
    assert by_key["kill_switch_equity_floor"]["numeric_value"] == 800
    assert by_key["kill_switch_daily_pnl_floor"]["numeric_value"] == -50
    for row in by_key.values():
        assert row["source"] == ADDENDUM_A_LABEL
        assert row["board_set"] is True
    snap = engine.snapshot()
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert set(snap["allow_list"]) == set(ADDENDUM_E_SYMBOLS)
    assert snap["currency"] == "GBP"
    assert snap["timezone"] == "Europe/London"
    assert snap["addendum"]["does_not_switch_to_paper"] is True
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_observability_shows_addendum_a_values_and_kill_switch(client):
    body = client.get("/observability", headers=BOARD_HEADERS).json()
    items = {row["key"]: row for row in body["numeric_limits"]["items"]}
    assert items["simulated_capital"]["value"] == "1000"
    assert items["max_position"]["unit"] == "GBP"
    assert body["numeric_limits"]["addendum"] == ADDENDUM_A_LABEL
    assert body["kill_switch"]["halted"] is False
    assert body["kill_switch"]["equity_floor_gbp"] == 800
    assert body["kill_switch"]["daily_pnl_floor_gbp"] == -50
    assert body["kill_switch"]["board_member_can_trigger"] is True
    assert body["kill_switch"]["employees_cannot_reset"] is True
    assert body["evaluation"]["closed_trades"] == 0
    assert body["evaluation"]["win_rate"] == 0
    assert body["evaluation"]["evaluation_trigger_met"] is False
    assert body["evaluation"]["evaluation_auto_switch_live"] is False
    assert body["paper_ledger"]["fills"] == 0
    assert body["paper_ledger"]["simulated_capital_gbp"] == 1000
    assert body["controls"]["trading_mode"] == "LIVE_BLOCKED"
    assert set(body["controls"]["allow_list"]) == set(ADDENDUM_E_SYMBOLS)


def test_employees_cannot_write_limits(client):
    for headers in EMPLOYEE_SETS:
        for field, value in (
            ("simulated_capital", "1"),
            ("max_position", "999"),
            ("allow_list", ["AAPL"]),
            ("kill_switch", True),
            ("trading_mode", "PAPER"),
        ):
            r = client.post(
                "/controls/write",
                headers=headers,
                json={"field": field, "value": value},
            )
            assert r.status_code == 403
            assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
    ceo = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "allow_list", "value": ["AAPL"]},
    )
    assert ceo.status_code == 403
    after = client.get("/controls").json()
    assert set(after["allow_list"]) == set(ADDENDUM_E_SYMBOLS)
    assert after["trading_mode"] == "LIVE_BLOCKED"
    assert after["numeric_limits"][0]["source"] == ADDENDUM_A_LABEL


def test_unknown_ticker_still_denies_with_limits(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "ZZQQ", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "SYMBOL_NOT_ON_ALLOW_LIST"
    assert session.query(AllowListInstrument).count() == len(ADDENDUM_E_SYMBOLS)


def test_live_still_blocked_with_limits(client):
    live = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.status_code == 403
    assert live.json()["detail"]["allowed"] is False
    assert live.json()["detail"]["reason"] in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_order_over_max_position_denies(session):
    emp = _grant_place_and_allow(session)
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 1,
            "notional_gbp": 201,
            "execution_port": "SIMULATOR",
        },
    )
    assert d.allowed is False
    assert d.reason == "MAX_POSITION_EXCEEDED"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_seventh_order_in_a_day_denies(session):
    emp = _grant_place_and_allow(session)
    engine = ControlEngine(session)
    for i in range(6):
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={
                "symbol": "AAPL",
                "side": "buy",
                "quantity": 0.1,
                "notional_gbp": 10,
                "execution_port": "SIMULATOR",
            },
            at=SESSION_OPEN,
        )
        assert d.allowed is True, d.reason
    seventh = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 0.1,
            "notional_gbp": 10,
            "execution_port": "SIMULATOR",
        },
        at=SESSION_OPEN,
    )
    assert seventh.allowed is False
    assert seventh.reason == "MAX_ORDERS_PER_DAY"


def test_kill_switch_denies_orders(session):
    emp = _grant_place_and_allow(session)
    from varma.controls.kill_switch import trip_kill_switch

    trip_kill_switch(session, actor_id="board-member", reason="BOARD_MEMBER_HALT")
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "notional_gbp": 50, "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "KILL_SWITCH"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False


def test_board_cannot_switch_to_paper_mode(client):
    r = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "trading_mode", "value": "PAPER"},
    )
    assert r.status_code == 403
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
