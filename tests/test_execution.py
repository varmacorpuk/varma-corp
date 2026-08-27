from tests.conftest import BOARD_HEADERS, EMPLOYEE_HEADERS, SESSION_OPEN
from varma.controls.engine import ControlEngine
from varma.db.models import Employee
from varma.db.seed import MI_SLUG
from varma.ports.execution import ExecutionPort, LiveBrokerAdapter


def test_live_place_order_denied_via_api(client):
    r = client.post(
        "/execution/place-order",
        headers=EMPLOYEE_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["allowed"] is False
    reason = r.json()["detail"]["reason"]
    assert reason in {"LIVE_BLOCKED", "NO_PERMISSION", "EMPTY_ALLOW_LIST", "LIVE_ADAPTER_NOT_LOADED"}


def test_unknown_ticker_cannot_execute(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    engine = ControlEngine(session)
    assert "ZZQQ" not in engine.allow_list_symbols()
    d = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "ZZQQ", "execution_port": "SIMULATOR", "quantity": 1},
    )
    assert d.allowed is False
    assert d.reason in {"NO_PERMISSION", "SYMBOL_NOT_ON_ALLOW_LIST"}


def test_unknown_ticker_denies_even_if_permission_granted(session):
    from varma.db.models import Permission

    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    perm = (
        session.query(Permission)
        .filter_by(subject_id=emp.id, action="place_order")
        .one()
    )
    perm.allowed = True
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "ZZQQ", "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "SYMBOL_NOT_ON_ALLOW_LIST"


def test_live_adapter_cannot_be_constructed():
    try:
        LiveBrokerAdapter()
        raise AssertionError("LIVE adapter must not construct")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)


def test_broker_paper_adapter_cannot_be_constructed():
    from varma.ports.execution import PaperBrokerAdapter

    try:
        PaperBrokerAdapter()
        raise AssertionError("BROKER_PAPER adapter must not construct")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)
        assert "UNLOADED" in str(exc)


def test_constructing_and_using_unloaded_ports_is_denied():
    from varma.ports.execution import (
        BROKER_PAPER_LOADED,
        LIVE_PORT_LOADED,
        construct_execution_port,
        use_broker_paper_port,
        use_live_port,
    )

    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
    try:
        construct_execution_port("BROKER_PAPER")
        raise AssertionError("BROKER_PAPER must not construct")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)
    try:
        construct_execution_port("LIVE")
        raise AssertionError("LIVE must not construct")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)
    try:
        use_broker_paper_port(order={"symbol": "AAPL", "side": "buy"})
        raise AssertionError("using BROKER_PAPER must be denied")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)
    try:
        use_live_port(order={"symbol": "AAPL", "side": "buy"})
        raise AssertionError("using LIVE must be denied")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)


def test_execution_port_reports_broker_paper_and_live_unloaded(session):
    from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED

    port = ExecutionPort(session)
    assert "BROKER_PAPER" not in port.available_ports()
    assert "LIVE" not in port.available_ports()
    assert port.unloaded_ports() == ["BROKER_PAPER", "LIVE"]
    assert port.broker_paper_loaded() is False
    assert port.live_loaded() is False
    status = port.port_status()
    assert status["fills"] is False
    assert status["paper_fills"] is False
    assert status["live_fills"] is False
    assert status["broker_paper"]["status"] == "UNLOADED"
    assert status["broker_paper"]["loaded"] is False
    assert status["live"]["status"] == "UNLOADED"
    assert status["live"]["loaded"] is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_place_order_via_unloaded_ports_is_denied(session):
    port = ExecutionPort(session)
    paper = port.place_order(
        actor_id="board-member",
        actor_type="board_member",
        order={"symbol": "AAPL", "execution_port": "BROKER_PAPER", "quantity": 1},
    )
    assert paper.allowed is False
    assert paper.reason == "BROKER_PAPER_NOT_LOADED"
    live = port.place_order(
        actor_id="board-member",
        actor_type="board_member",
        order={"symbol": "AAPL", "execution_port": "LIVE", "quantity": 1},
    )
    assert live.allowed is False
    assert live.reason in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}


def test_gold_cannot_execute(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    from varma.db.models import Permission

    perm = (
        session.query(Permission)
        .filter_by(subject_id=emp.id, action="place_order")
        .one()
    )
    perm.allowed = True
    session.commit()
    d = ExecutionPort(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "XAUUSD", "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "GOLD_NOT_AUTHORISED"


def test_missing_limits_deny_after_allow_list(session):
    from varma.clock import now_london
    from varma.db.models import AllowListInstrument, NumericLimit, Permission

    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    for row in session.query(NumericLimit).all():
        session.delete(row)
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == "PAPER_EXECUTION_CLOSED"
