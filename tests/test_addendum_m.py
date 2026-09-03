"""Board Addendum M: five US-listed commodity ETPs are WATCH-ONLY."""

from tests.conftest import SESSION_OPEN
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS, desk_symbol
from varma.controls.addendum_l import ADDENDUM_L_NAMES
from varma.controls.addendum_m import (
    ADDENDUM_M_ETP_SYMBOLS,
    ADDENDUM_M_LABEL,
    PAPER_UNIVERSE_SYMBOLS,
    WATCH_ONLY_LABEL,
    WATCH_ONLY_REASON,
    addendum_m_public,
    is_watch_only_etp,
)
from varma.controls.engine import ControlEngine
from varma.db.models import AllowListInstrument, Employee, PaperFill, Permission, WatchlistItem
from varma.db.seed import MI_SLUG, seed_board_addendum_e


EXACT_10 = (
    "NVDA",
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "SPCX",
    "AVGO",
    "META",
    "TSLA",
    "BRK-B",
)


def test_addendum_m_etps_are_watch_only_not_executable(session):
    pub = addendum_m_public()
    assert pub["label"] == ADDENDUM_M_LABEL
    assert pub["executable"] is False
    assert pub["watch_only"] is True
    assert pub["executable_count"] == 10
    assert pub["watch_only_count"] == 5
    assert pub["etp_count"] == 5
    assert pub["equity_count"] == 10
    assert pub["deny_reason"] == WATCH_ONLY_REASON
    assert pub["futures"] is False
    assert tuple(ADDENDUM_E_SYMBOLS) == EXACT_10
    assert [s for s, _n in ADDENDUM_L_NAMES] == list(EXACT_10)
    assert set(ADDENDUM_M_ETP_SYMBOLS) == {"GLD", "SLV", "USO", "UNG", "CPER"}
    assert set(PAPER_UNIVERSE_SYMBOLS) == set(EXACT_10) | set(ADDENDUM_M_ETP_SYMBOLS)

    engine = ControlEngine(session)
    allow = set(engine.allow_list_symbols())
    assert allow == set(EXACT_10)
    assert session.query(AllowListInstrument).count() == 10
    for etp in ADDENDUM_M_ETP_SYMBOLS:
        assert etp not in allow
        assert is_watch_only_etp(etp) is True
        row = session.get(WatchlistItem, etp)
        assert row is not None
        assert row.label == WATCH_ONLY_LABEL
        assert row.asset_class == "listed_etp"
        assert row.venue == "NYSE"
    snap = engine.snapshot()
    assert snap["addendum_m"]["watch_only"] is True
    assert snap["addendum_m"]["executable_count"] == 10
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert desk_symbol("BRK-B") == "BRK.B"


def test_control_engine_denies_gld_watch_only(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    fills_before = session.query(PaperFill).count()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "GLD", "side": "buy", "notional_gbp": 150.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == WATCH_ONLY_REASON
    assert d.details["watch_only"] is True
    assert d.details["executable"] is False
    assert session.query(PaperFill).count() == fills_before
    for etp in ("SLV", "USO", "UNG", "CPER"):
        denied = ControlEngine(session).place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": etp, "side": "buy", "notional_gbp": 50.0, "execution_port": "SIMULATOR"},
            at=SESSION_OPEN,
        )
        assert denied.allowed is False
        assert denied.reason == WATCH_ONLY_REASON
    assert session.query(PaperFill).count() == fills_before


def test_stale_etp_allow_list_row_is_stripped(session):
    session.add(
        AllowListInstrument(
            symbol="GLD",
            venue="NYSE",
            approved_by="stale-seed",
            approved_at=SESSION_OPEN,
        )
    )
    session.commit()
    assert session.query(AllowListInstrument).filter_by(symbol="GLD").one_or_none() is not None
    seed_board_addendum_e(session)
    session.commit()
    assert session.query(AllowListInstrument).filter_by(symbol="GLD").one_or_none() is None
    assert session.query(AllowListInstrument).count() == 10


def test_xauusd_still_denied_as_gold_futures(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "XAUUSD", "side": "buy", "notional_gbp": 50.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == "GOLD_NOT_AUTHORISED"
