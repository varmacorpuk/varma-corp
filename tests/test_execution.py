from tests.conftest import BOARD_HEADERS, EMPLOYEE_HEADERS
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


def test_empty_allow_list_cannot_execute(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    engine = ControlEngine(session)
    assert engine.allow_list_symbols() == []
    d = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "SIMULATOR", "quantity": 1},
    )
    assert d.allowed is False
    assert d.reason in {"NO_PERMISSION", "EMPTY_ALLOW_LIST"}


def test_empty_allow_list_denies_even_if_permission_granted(session):
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
        order={"symbol": "AAPL", "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "EMPTY_ALLOW_LIST"


def test_live_adapter_cannot_be_constructed():
    try:
        LiveBrokerAdapter()
        raise AssertionError("LIVE adapter must not construct")
    except RuntimeError as exc:
        assert "not loaded" in str(exc)


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
    assert d.reason in {"EMPTY_ALLOW_LIST", "GOLD_NOT_AUTHORISED", "SYMBOL_NOT_ON_ALLOW_LIST"}


def test_missing_limits_deny_after_allow_list(session):
    from varma.clock import now_london
    from varma.db.models import AllowListInstrument, Permission

    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.add(
        AllowListInstrument(
            symbol="AAPL",
            venue="NASDAQ",
            approved_by="board-member",
            approved_at=now_london(),
        )
    )
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "execution_port": "SIMULATOR"},
    )
    assert d.allowed is False
    assert d.reason == "MISSING_NUMERIC_LIMITS"
