"""Board Addendum M: five US-listed commodity ETPs on the equity/ETP path."""

from tests.conftest import SESSION_OPEN
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS, ADDENDUM_E_VENUES, desk_symbol
from varma.controls.addendum_l import ADDENDUM_L_NAMES
from varma.controls.addendum_m import (
    ADDENDUM_M_ETP_SYMBOLS,
    ADDENDUM_M_LABEL,
    PAPER_UNIVERSE_SYMBOLS,
    addendum_m_public,
)
from varma.controls.engine import ControlEngine
from varma.db.models import AICallLog, AllowListInstrument, Employee, PaperFill, PaperOrder, Permission
from varma.db.seed import MI_SLUG
from varma.paper.quote import paper_order_economics


EXACT_15 = (
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
    "GLD",
    "SLV",
    "USO",
    "UNG",
    "CPER",
)


def test_addendum_m_exact_15_name_universe(session):
    pub = addendum_m_public()
    assert pub["label"] == ADDENDUM_M_LABEL
    assert pub["count"] == 15
    assert pub["etp_count"] == 5
    assert pub["equity_count"] == 10
    assert pub["futures"] is False
    assert pub["margin"] is False
    assert pub["expiry"] is False
    assert pub["rollover"] is False
    assert pub["equity_etp_path_only"] is True
    assert tuple(ADDENDUM_E_SYMBOLS) == EXACT_15
    assert tuple(PAPER_UNIVERSE_SYMBOLS) == EXACT_15
    assert set(ADDENDUM_M_ETP_SYMBOLS) == {"GLD", "SLV", "USO", "UNG", "CPER"}
    assert [s for s, _n in ADDENDUM_L_NAMES] == list(EXACT_15[:10])
    engine = ControlEngine(session)
    assert set(engine.allow_list_symbols()) == set(EXACT_15)
    seeded = {row.symbol: row.venue for row in session.query(AllowListInstrument).all()}
    assert set(seeded) == set(EXACT_15)
    for etp in ADDENDUM_M_ETP_SYMBOLS:
        assert ADDENDUM_E_VENUES[etp] == "NYSE"
        assert seeded[etp] == "NYSE"
    snap = engine.snapshot()
    assert snap["addendum_m"]["count"] == 15
    assert snap["trading_mode"] == "LIVE_BLOCKED"
    assert desk_symbol("BRK-B") == "BRK.B"


def test_gld_etp_uses_equity_path_fx_and_cap(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()

    econ = paper_order_economics(
        {"symbol": "GLD", "side": "buy", "notional_gbp": 150.0},
        max_position_gbp=200.0,
    )
    assert econ.quote_currency == "USD"
    assert econ.fx.pair == "USDGBP"
    assert econ.fx.source
    assert econ.quantity > 0
    assert econ.notional_gbp <= 150.0 + 1e-6
    assert econ.cap_check_gbp <= 200.0 + 1e-6

    before_ai = session.query(AICallLog).count()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "GLD", "side": "buy", "notional_gbp": 150.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is True
    assert d.reason == "PAPER_FILL_SIMULATED"
    fill = session.query(PaperFill).one()
    assert fill.symbol == "GLD"
    assert fill.fx_rate is not None and fill.fx_rate > 0
    assert fill.instrument_currency == "USD"
    assert fill.quantity < 2
    assert session.query(PaperOrder).one().notional_gbp <= 200.0 + 1e-6
    assert session.query(AICallLog).count() == before_ai

    denied = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "GLD", "side": "buy", "notional_gbp": 250.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert denied.allowed is False
    assert denied.reason == "MAX_POSITION_EXCEEDED"


def test_xauusd_still_denied_gld_is_not_gold_futures(session):
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
