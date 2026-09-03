from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    EMPLOYEE_HEADERS,
    QUANT_HEADERS,
    RISK_HEADERS,
    SESSION_OPEN,
    TECH_HEADERS,
    TRADER_HEADERS,
)
from varma.controls.addendum_e import (
    ADDENDUM_E_INSTRUMENTS,
    ADDENDUM_E_LABEL,
    ADDENDUM_E_SYMBOLS,
    ADDENDUM_E_VENUES,
    addendum_e_public,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import (
    AllowListInstrument,
    ControlSetting,
    ControlState,
    Employee,
    PaperAccount,
    PaperFill,
    PaperPosition,
    Permission,
)
from varma.db.seed import MI_SLUG
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED

EMPLOYEE_SETS = (
    EMPLOYEE_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    RISK_HEADERS,
    TRADER_HEADERS,
    QUANT_HEADERS,
    TECH_HEADERS,
)


def test_addendum_e_allow_list_is_board_set(session):
    engine = ControlEngine(session)
    assert set(engine.allow_list_symbols()) == set(ADDENDUM_E_SYMBOLS)
    assert engine.snapshot()["allow_list_empty"] is False
    assert engine.snapshot()["addendum_e"]["label"] == ADDENDUM_E_LABEL
    assert engine.snapshot()["addendum_e"]["paper_membership_only"] is True
    assert engine.snapshot()["trading_mode"] == "LIVE_BLOCKED"
    assert session.query(AllowListInstrument).count() == 15
    assert "NVDA" in engine.allow_list_symbols()
    assert "BRK-B" in engine.allow_list_symbols()
    assert "SPCX" in engine.allow_list_symbols()
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_addendum_e_final_strategy_venues(session):
    expected = dict(ADDENDUM_E_INSTRUMENTS)
    seeded = {row.symbol: row.venue for row in session.query(AllowListInstrument).all()}
    assert ADDENDUM_E_VENUES == expected
    assert addendum_e_public()["venues"] == expected
    for sym, venue in expected.items():
        assert seeded[sym] == venue
    assert "BRK-B" in seeded
    assert seeded["BRK-B"] == "NYSE"
    for etp in ("GLD", "SLV", "USO", "UNG", "CPER"):
        assert seeded[etp] == "NYSE"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert session.get(ControlSetting, "paper_execution").value == "OPEN"
    account = session.get(PaperAccount, 1)
    assert account.simulated_capital == 1000.0
    assert account.cash == 1000.0
    assert session.query(PaperFill).count() == 0
    assert session.query(PaperPosition).count() == 0
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_employees_and_ceo_cannot_write_allow_list(client):
    before = set(client.get("/controls").json()["allow_list"])
    for headers in EMPLOYEE_SETS:
        r = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "allow_list", "value": ["FAKE"]},
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
        live = client.post(
            "/controls/write",
            headers=headers,
            json={"field": "trading_mode", "value": "LIVE"},
        )
        assert live.status_code == 403
    ceo = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "allow_list", "value": ["TSLA"]},
    )
    assert ceo.status_code == 403
    after = client.get("/controls").json()
    assert set(after["allow_list"]) == before
    assert before == set(ADDENDUM_E_SYMBOLS)
    assert after["trading_mode"] == "LIVE_BLOCKED"
    board = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "allow_list", "value": ["TSLA"]},
    )
    assert board.status_code == 403
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
    assert set(client.get("/controls").json()["allow_list"]) == before


def test_unknown_ticker_denied(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "ZZQQ", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == "SYMBOL_NOT_ON_ALLOW_LIST"


def test_gold_still_denied(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "XAUUSD", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == "GOLD_NOT_AUTHORISED"


def test_live_still_denied_with_allow_list(client):
    live = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.status_code == 403
    assert live.json()["detail"]["allowed"] is False
    assert live.json()["detail"]["reason"] in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}
    paper_broker = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "BROKER_PAPER"},
    )
    assert paper_broker.status_code == 403
    assert paper_broker.json()["detail"]["reason"] == "BROKER_PAPER_NOT_LOADED"
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_simulator_fills_allow_listed_ticker_when_paper_open(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is True
    assert d.reason == "PAPER_FILL_SIMULATED"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert addendum_e_public()["count"] == 15
    assert addendum_e_public()["allow_list_e_cannot_fill_until_open"] is True
