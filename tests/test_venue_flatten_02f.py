"""CEO desk 02F: venue-aware bound flatten clocks in ControlEngine.

LSE names exit in the London closing auction 16:30–16:35 and cannot remain
into US hours. US names wait until US flatten. split_flatten_clocks is true.
Risk 02F is readable from engine state. LIVE_BLOCKED. paper OPEN.
Tests use the pytest tmp sqlite fixture, not data/varma.db.
"""

from __future__ import annotations

from tests.conftest import (
    BOARD_HEADERS,
    CEO_HEADERS,
    LONDON_CASH_CLOSE,
    LONDON_CLOSING_AUCTION_END,
    SESSION_OPEN,
    US_HOURS_AFTER_LONDON,
)
from varma.controls.addendum_c import us_regular_cash_close_london
from varma.controls.addendum_k import ADDENDUM_K_LSE_SYMBOLS, LSE_AFTER_LONDON_CASH_CLOSE_REASON
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.controls.venue_flatten import (
    LSE_FLATTEN_AT,
    RISK_02F,
    SPLIT_FLATTEN_CLOCKS,
    bound_flatten_at,
    cannot_drop_bound_exit_independently,
    in_london_closing_auction,
    may_drop_bound_exit,
    risk_02f_public,
)
from varma.db.models import ControlState, Employee, PaperPosition, Permission
from varma.db.seed import MI_SLUG
from varma.observability.board import BoardObservability
from varma.paper.flatten import flatten_all_paper, flatten_lse_paper
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED


def _add_lse_to_allow_list(session):
    from varma.clock import now_london as _now
    from varma.db.models import AllowListInstrument
    now = _now()
    for sym in ADDENDUM_K_LSE_SYMBOLS:
        if session.query(AllowListInstrument).filter_by(symbol=sym).one_or_none() is None:
            session.add(AllowListInstrument(symbol=sym, venue="LSE", approved_by="test-only", approved_at=now))
    session.commit()


def _grant_place(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    return emp


def test_risk_02f_is_bound_and_readable_from_engine(session):
    engine = ControlEngine(session)
    snap = engine.snapshot()
    hint = engine.constraints_hint()
    pub = risk_02f_public()
    assert SPLIT_FLATTEN_CLOCKS is True
    assert snap["split_flatten_clocks"] is True
    assert snap["risk_02f"]["id"] == RISK_02F == "02F"
    assert snap["risk_02f"]["bound"] is True
    assert snap["risk_02f"]["readable_from_engine"] is True
    assert snap["risk_02f"]["lse_flatten_at"] == LSE_FLATTEN_AT == "LONDON_CLOSING_AUCTION"
    assert snap["risk_02f"]["lse_flatten_window"] == "16:30-16:35"
    assert snap["risk_02f"]["cannot_drop_lse_exit_independently_of_opening_buy"] is True
    assert snap["risk_02f"]["cannot_hold_lse_to_new_york"] is True
    assert snap["risk_02f"]["us_flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert snap["risk_02f"]["firm_day_runs_to_ny_close"] is True
    assert snap["risk_02f"]["paper_execution_stays"] == "OPEN"
    assert snap["risk_02f"]["trading_mode_stays"] == "LIVE_BLOCKED"
    assert snap["ceo_desk"]["risk_02f"]["bound"] is True
    assert engine.risk_02f()["bound"] is True
    assert hint["split_flatten_clocks"] is True
    assert hint["risk_02f_bound"] is True
    assert hint["risk_02f"] == "02F"
    assert hint["lse_flatten_at"] == "LONDON_CLOSING_AUCTION"
    assert pub["jpm_jnj_venues"] == {"JPM": "NYSE", "JNJ": "NYSE"}
    obs = BoardObservability(session).snapshot()
    assert obs["split_flatten_clocks"] is True
    assert obs["risk_02f"]["bound"] is True
    assert obs["paper_gate"]["split_flatten_clocks"] is True
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_bound_exit_cannot_be_dropped_independently_of_opening_buy():
    for symbol in ADDENDUM_K_LSE_SYMBOLS:
        bound = bound_flatten_at(symbol)
        assert bound == "LONDON_CLOSING_AUCTION"
        assert cannot_drop_bound_exit_independently(symbol) is True
        assert may_drop_bound_exit(symbol) is False
    assert bound_flatten_at("AAPL") == "US_REGULAR_CASH_CLOSE"
    assert bound_flatten_at("JPM") == "US_REGULAR_CASH_CLOSE"
    assert bound_flatten_at("JNJ") == "US_REGULAR_CASH_CLOSE"
    assert in_london_closing_auction(LONDON_CASH_CLOSE) is True
    assert in_london_closing_auction(LONDON_CLOSING_AUCTION_END) is False
    assert in_london_closing_auction(SESSION_OPEN) is False


def test_open_shel_l_exits_at_london_auction_and_cannot_remain_into_us_hours(session):
    _add_lse_to_allow_list(session)
    emp = _grant_place(session)
    engine = ControlEngine(session)
    shel = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert shel.allowed is True
    assert shel.reason == "PAPER_FILL_SIMULATED"
    assert shel.details["bound_flatten_at"] == "LONDON_CLOSING_AUCTION"
    assert shel.details["cannot_drop_independently"] is True
    assert shel.details["may_drop_independently"] is False
    assert shel.details["risk_02f_bound"] is True
    assert shel.details["split_flatten_clocks"] is True
    aapl = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert aapl.allowed is True
    assert aapl.details["bound_flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert session.query(PaperPosition).count() == 2

    london = flatten_lse_paper(session, actor_id="board-member", at=LONDON_CASH_CLOSE, started_by="cli")
    assert london["flatten_at"] == "LONDON_CLOSING_AUCTION"
    assert london["flatten_at_london_cash_close"] is True
    assert london["split_flatten_clocks"] is True
    assert london["risk_02f"]["bound"] is True
    assert london["cannot_drop_independently"] is True
    assert london["closed_symbols"] == ["SHEL.L"]
    assert london["flatten_fills"] == 1
    assert session.get(PaperPosition, "SHEL.L") is None
    assert session.get(PaperPosition, "AAPL") is not None
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"

    denied = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "notional_gbp": 10, "execution_port": "SIMULATOR"},
        at=US_HOURS_AFTER_LONDON,
    )
    assert denied.allowed is False
    assert denied.reason == LSE_AFTER_LONDON_CASH_CLOSE_REASON
    assert denied.details["risk_02f_bound"] is True
    assert denied.details["split_flatten_clocks"] is True
    assert session.get(PaperPosition, "SHEL.L") is None
    assert session.get(PaperPosition, "AAPL") is not None

    us_close = us_regular_cash_close_london(SESSION_OPEN)
    us_done = flatten_all_paper(session, actor_id="board-member", at=us_close, started_by="cli")
    assert us_done["flatten_at"] == "US_REGULAR_CASH_CLOSE"
    assert us_done["flatten_at_london_cash_close"] is False
    assert "AAPL" in us_done["closed_symbols"]
    assert "SHEL.L" not in us_done["closed_symbols"]
    assert session.query(PaperPosition).count() == 0
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False


def test_us_flatten_does_not_close_lse_inventory(session):
    _add_lse_to_allow_list(session)
    emp = _grant_place(session)
    engine = ControlEngine(session)
    filled = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "notional_gbp": 40, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert filled.allowed is True
    us_close = us_regular_cash_close_london(SESSION_OPEN)
    result = flatten_all_paper(session, actor_id="board-member", at=us_close, started_by="cli")
    assert result["venue_scope"] == "US"
    assert "SHEL.L" not in result["closed_symbols"]
    assert result["flatten_fills"] == 0
    assert session.get(PaperPosition, "SHEL.L") is not None
    london = flatten_lse_paper(session, actor_id="board-member", at=LONDON_CASH_CLOSE, started_by="cli")
    assert london["closed_symbols"] == ["SHEL.L"]
    assert session.get(PaperPosition, "SHEL.L") is None


def test_us_names_remain_after_london_flatten_until_us_close(session):
    emp = _grant_place(session)
    engine = ControlEngine(session)
    for symbol in ("MSFT", "META", "TSLA"):
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": symbol, "side": "buy", "notional_gbp": 20, "execution_port": "SIMULATOR"},
            at=SESSION_OPEN,
        )
        assert d.allowed is True
        assert d.details["bound_flatten_at"] == "US_REGULAR_CASH_CLOSE"
    london = flatten_lse_paper(session, actor_id="board-member", at=LONDON_CASH_CLOSE, started_by="cli")
    assert london["flatten_fills"] == 0
    assert london["closed_positions"] == 0
    assert session.query(PaperPosition).count() == 3
    still_open = engine.place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "AAPL", "side": "buy", "notional_gbp": 20, "execution_port": "SIMULATOR"},
        at=US_HOURS_AFTER_LONDON,
    )
    assert still_open.allowed is True
    assert still_open.reason == "PAPER_FILL_SIMULATED"


def test_london_flatten_job_is_board_only_and_does_not_load_live(client):
    anon = client.post("/routines/run-flatten-london-close")
    assert anon.status_code == 401
    ceo = client.post("/routines/run-flatten-london-close", headers=CEO_HEADERS)
    assert ceo.status_code == 401
    ok = client.post("/routines/run-flatten-london-close", headers=BOARD_HEADERS)
    assert ok.status_code == 200
    body = ok.json()
    assert body["flatten_at"] == "LONDON_CLOSING_AUCTION"
    assert body["split_flatten_clocks"] is True
    assert body["risk_02f"]["bound"] is True
    assert body["job_safety"]["loads_broker_ports"] is False
    assert body["job_safety"]["live_fills"] is False
    assert body["job_safety"]["split_flatten_clocks"] is True
    assert body["trading_mode_after"] == "LIVE_BLOCKED"
    after = client.get("/observability", headers=BOARD_HEADERS).json()
    assert after["split_flatten_clocks"] is True
    assert after["risk_02f"]["bound"] is True
    assert after["controls"]["trading_mode"] == "LIVE_BLOCKED"
    assert after["execution_ports"]["live"]["status"] == "UNLOADED"
    assert after["execution_ports"]["broker_paper"]["status"] == "UNLOADED"
    assert body["flatten_as_if_there_were_positions"] is False
    assert body["live_fills"] is False
