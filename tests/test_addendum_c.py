from tests.conftest import (
    BEFORE_UK_OPEN,
    BOARD_HEADERS,
    CEO_HEADERS,
    EMPLOYEE_HEADERS,
    LONDON_CASH_CLOSE,
    SESSION_OPEN,
    WEEKEND,
)
from varma.clock import LONDON
from varma.controls.addendum_c import (
    ADDENDUM_C_LABEL,
    london_cash_close_london,
    paper_desk_open,
    us_regular_cash_close_london,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import ControlState, Employee, PaperPosition, Permission
from varma.db.seed import MI_SLUG
from varma.observability.board import BoardObservability
from varma.paper.flatten import flatten_all_paper
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.routines.board_jobs import BOARD_JOBS

from datetime import datetime


def _grant_place(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    return emp


def test_us_close_converts_not_hardcoded_2100():
    # 16 Mar 2026: US on EDT, UK still GMT → 16:00 NY is 20:00 London.
    march = datetime(2026, 3, 16, 12, 0, tzinfo=LONDON)
    close_march = us_regular_cash_close_london(march)
    assert close_march.tzinfo == LONDON
    assert close_march.hour == 20
    # 27 Aug 2026: both on summer time → 16:00 NY is 21:00 London.
    august = datetime(2026, 8, 27, 12, 0, tzinfo=LONDON)
    close_august = us_regular_cash_close_london(august)
    assert close_august.hour == 21
    assert close_march.hour != close_august.hour


def test_london_cash_close_is_inside_session():
    assert paper_desk_open(LONDON_CASH_CLOSE) is True
    assert paper_desk_open(SESSION_OPEN) is True
    assert london_cash_close_london(LONDON_CASH_CLOSE).hour == 16
    assert london_cash_close_london(LONDON_CASH_CLOSE).minute == 30


def test_outside_window_denies_allow_listed_ticker(session):
    emp = _grant_place(session)
    engine = ControlEngine(session)
    for when, detail in (
        (BEFORE_UK_OPEN, "before_uk_cash_open"),
        (us_regular_cash_close_london(SESSION_OPEN), "after_us_regular_cash_close"),
        (WEEKEND, "weekend"),
    ):
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
            at=when,
        )
        assert d.allowed is False, d.reason
        assert d.reason == "PAPER_SESSION_CLOSED"
        assert d.details.get("overnight") is True or detail == "weekend"


def test_london_1630_still_allows_paper_fill(session):
    emp = _grant_place(session)
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 50, "execution_port": "SIMULATOR"},
        at=LONDON_CASH_CLOSE,
    )
    assert d.allowed is True, d.reason
    assert d.reason == "PAPER_FILL_SIMULATED"
    assert d.details["is_live"] is False
    assert LIVE_ADAPTER_LOADED is False


def test_flatten_at_us_close_closes_paper(session):
    emp = _grant_place(session)
    filled = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "MSFT", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert filled.allowed is True, filled.reason
    assert session.query(PaperPosition).count() >= 1
    close = us_regular_cash_close_london(SESSION_OPEN)
    result = flatten_all_paper(
        session,
        actor_id="board-member",
        at=close,
        started_by="cli",
    )
    assert result["flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert result["flatten_not_at"] == "LONDON_CASH_CLOSE"
    assert result["flatten_at_london_cash_close"] is False
    assert result["closed_positions"] >= 1
    assert result["positions_remaining"] == 0
    assert result["trading_mode_after"] == "LIVE_BLOCKED"
    assert result["broker"] is False
    assert result["live_loaded"] is False
    assert session.query(PaperPosition).count() == 0
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_get_observability_does_not_flatten(session):
    emp = _grant_place(session)
    ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 30, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    before = session.query(PaperPosition).count()
    assert before >= 1
    snap = BoardObservability(session).snapshot()
    assert snap["paper_flatten"]["get_observability_flattens"] is False
    assert snap["paper_flatten"]["run"] is None
    assert snap["paper_session"]["flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert snap["paper_session"]["flatten_at_london_cash_close"] is False
    assert snap["paper_session"]["overnight_holds"] is False
    assert snap["addendum_c"]["label"] == ADDENDUM_C_LABEL
    assert session.query(PaperPosition).count() == before


def test_flatten_job_is_board_only(client):
    paths = [job["path"] for job in BOARD_JOBS]
    assert "/routines/run-flatten-us-close" in paths
    anon = client.post("/routines/run-flatten-us-close")
    assert anon.status_code == 401
    emp = client.post("/routines/run-flatten-us-close", headers=EMPLOYEE_HEADERS)
    assert emp.status_code == 401
    ceo = client.post("/routines/run-flatten-us-close", headers=CEO_HEADERS)
    assert ceo.status_code == 401
    get_r = client.get("/routines/run-flatten-us-close", headers=BOARD_HEADERS)
    assert get_r.status_code == 405
    ok = client.post("/routines/run-flatten-us-close", headers=BOARD_HEADERS)
    assert ok.status_code == 200
    body = ok.json()
    assert body["flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert body["job_safety"]["loads_broker_ports"] is False
    assert body["job_safety"]["live_fills"] is False
    assert body["job_safety"]["internal_simulator_flatten"] is True
    assert body["job_safety"]["trading_mode"] == "LIVE_BLOCKED"
    after = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after["paper_flatten"]["run"]["id"] == body["id"]
    assert after["controls"]["trading_mode"] == "LIVE_BLOCKED"
    assert after["execution_ports"]["broker_paper"]["status"] == "UNLOADED"
    assert after["execution_ports"]["live"]["status"] == "UNLOADED"
