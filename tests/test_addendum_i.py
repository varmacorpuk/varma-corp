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
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_i import (
    ADDENDUM_I_LABEL,
    GRAND_OPENING_NOT_IMPLEMENTED_REASON,
    PAPER_EXECUTION_CLOSED_REASON,
    addendum_i_public,
    paper_execution_is_closed,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import (
    ControlSetting,
    ControlState,
    Employee,
    PaperFill,
    PaperPosition,
    Permission,
)
from varma.db.seed import MI_SLUG
from varma.observability.board import BoardObservability
from varma.paper.flatten import flatten_all_paper
from varma.paper.simulator import PaperFillSimulator
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.routines.run_0730_meeting import run_0730_meeting

EMPLOYEE_SETS = (
    EMPLOYEE_HEADERS,
    CEO_HEADERS,
    CHALLENGE_HEADERS,
    RISK_HEADERS,
    TRADER_HEADERS,
    QUANT_HEADERS,
    TECH_HEADERS,
)

OPEN_FIELDS = (
    ("paper_execution", "OPEN"),
    ("grand_opening_paper", "yes"),
    ("grand_opening_live", "yes"),
    ("firm_open", True),
    ("open_firm", True),
)


def _grant_place(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    return emp


def test_addendum_i_paper_execution_is_closed(session):
    engine = ControlEngine(session)
    assert paper_execution_is_closed(session) is True
    snap = engine.snapshot()
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert snap["paper_execution"] == "CLOSED"
    assert snap["paper_execution_closed"] is True
    assert snap["addendum_i"]["label"] == ADDENDUM_I_LABEL
    assert snap["addendum_i"]["paper_execution_closed"] is True
    assert snap["addendum_i"]["first_paper_trade_path_implemented"] is True
    assert snap["addendum_i"]["simulated_capital_status"] == "FUTURE_PAPER_STARTING_BOOK_ONLY"
    assert snap["addendum_i"]["addendum_a_numbers_unused_until_open"] is True
    assert snap["addendum_i"]["board_member_0730_diary_invite"] is False
    assert set(engine.allow_list_symbols()) == set(ADDENDUM_E_SYMBOLS)
    row = session.get(ControlSetting, "paper_execution")
    assert row is not None
    assert row.value == "CLOSED"
    assert row.source == ADDENDUM_I_LABEL
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    pub = addendum_i_public()
    assert pub["employees_cannot_open_the_firm"] is True
    assert pub["ceo_cannot_open_the_firm"] is True
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_no_fills_while_paper_closed_even_for_allow_listed(session):
    emp = _grant_place(session)
    engine = ControlEngine(session)
    d = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == PAPER_EXECUTION_CLOSED_REASON
    assert d.details["allow_list_cannot_fill_until_open"] is True
    assert session.query(PaperFill).count() == 0
    assert session.query(PaperPosition).count() == 0
    sim = PaperFillSimulator(session).fill(
        actor_id=emp.id,
        order={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert sim.allowed is False
    assert sim.reason == PAPER_EXECUTION_CLOSED_REASON
    assert session.query(PaperFill).count() == 0
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_live_denied_while_closed(client):
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


def test_employees_cannot_open_the_firm(client):
    for headers in EMPLOYEE_SETS:
        for field, value in OPEN_FIELDS:
            r = client.post(
                "/controls/write",
                headers=headers,
                json={"field": field, "value": value},
            )
            assert r.status_code == 403
            assert r.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
    after = client.get("/controls").json()
    assert after["paper_execution"] == "CLOSED"
    assert after["trading_mode"] == "LIVE_BLOCKED"


def test_ceo_cannot_open_the_firm(client, session):
    ceo = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "paper_execution", "value": "OPEN"},
    )
    assert ceo.status_code == 403
    assert ceo.json()["detail"] == "EMPLOYEE_CANNOT_WRITE_CONTROLS"
    live = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "grand_opening_live", "value": "yes"},
    )
    assert live.status_code == 403
    paper = client.post(
        "/controls/write",
        headers=CEO_HEADERS,
        json={"field": "grand_opening_paper", "value": "yes"},
    )
    assert paper.status_code == 403
    order = client.post(
        "/execution/place-order",
        headers=CEO_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
    )
    assert order.status_code == 403
    assert client.get("/controls").json()["paper_execution"] == "CLOSED"
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_gold_denied_while_closed(session):
    emp = _grant_place(session)
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "XAUUSD", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == "GOLD_NOT_AUTHORISED"
    assert session.query(PaperFill).count() == 0


def test_board_cannot_open_firm_in_this_slice(client):
    r = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "paper_execution", "value": "OPEN"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == GRAND_OPENING_NOT_IMPLEMENTED_REASON
    live = client.post(
        "/controls/write",
        headers=BOARD_HEADERS,
        json={"field": "grand_opening_live", "value": "yes"},
    )
    assert live.status_code == 403
    after = client.get("/controls").json()
    assert after["paper_execution"] == "CLOSED"
    assert after["trading_mode"] == "LIVE_BLOCKED"
    paper = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
    )
    assert paper.status_code == 403
    assert paper.json()["detail"]["reason"] == PAPER_EXECUTION_CLOSED_REASON


def test_flatten_is_noop_while_closed(session):
    emp = _grant_place(session)
    denied = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "MSFT", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert denied.reason == PAPER_EXECUTION_CLOSED_REASON
    assert session.query(PaperPosition).count() == 0
    result = flatten_all_paper(session, actor_id="board-member", at=SESSION_OPEN, started_by="cli")
    assert result["flatten_fills"] == 0
    assert result["closed_positions"] == 0
    assert result["flatten_as_if_there_were_positions"] is False
    assert result["paper_execution_closed"] is True
    assert result["trading_mode_after"] == "LIVE_BLOCKED"
    assert session.query(PaperFill).count() == 0


def test_0730_does_not_invite_board_member(session):
    meeting = run_0730_meeting(session, started_by="cli")
    assert meeting["is_trade"] is False
    assert meeting["board_member_diary_invite"] is False
    assert meeting["board_member_calendar_invite"] is False
    assert meeting["board_member_email"] is False
    assert meeting["internal_staff_artefact"] is True
    assert all(a["is_board_member"] is False for a in meeting["attendees"])
    assert "diary invite" in meeting["description"]
    obs = BoardObservability(session).snapshot()
    assert obs["company_meeting"]["board_member_diary_invite"] is False
    assert obs["paper_gate"]["paper_execution"] == "CLOSED"
    assert obs["paper_gate"]["first_paper_trade_path_implemented"] is True
    assert obs["addendum_i"]["label"] == ADDENDUM_I_LABEL
