from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from tests.conftest import SESSION_OPEN
from varma.controls.engine import ControlEngine
from varma.db.models import (
    AICallLog,
    AllowListInstrument,
    Employee,
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperPosition,
    Permission,
)
from varma.db.seed import MI_SLUG
from varma.paper.ledger import PaperLedger
from varma.paper.quote import (
    is_pence_unit,
    major_units,
    mid_gbp_from_row,
    paper_order_economics,
)
from varma.paper.fx import FAKE_USDGBP_LAST, FakeDelayedFx
from varma.clock import now_london


def _grant_place_and_allow(session: Session, *, symbol: str) -> Employee:
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    if session.query(AllowListInstrument).filter_by(symbol=symbol).one_or_none() is None:
        # Most tests already get Addendum E membership; this is defensive.
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


def test_msft_paper_notional_150_passes_cap_and_is_fractional(session):
    emp = _grant_place_and_allow(session, symbol="MSFT")
    assert session.query(PaperFill).count() == 0

    before_ai = session.query(AICallLog).count()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "MSFT", "side": "buy", "notional_gbp": 150.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is True
    assert d.reason == "PAPER_FILL_SIMULATED"
    assert session.query(PaperFill).count() == 1

    fill = session.query(PaperFill).one()
    order_row = session.query(PaperOrder).filter_by(status="FILLED").one()
    assert fill.fx_source  # rate provenance recorded on the fill
    assert fill.fx_rate is not None and fill.fx_rate > 0

    # Fractional sizing: a £150 order should not require whole-share count.
    assert fill.quantity < 1
    assert fill.quantity > 0

    # Must not exceed the £200 cap after conversion.
    assert order_row.notional_gbp <= 200.0 + 1e-6
    assert order_row.notional_gbp <= 150.0 + 1e-6

    assert session.query(AICallLog).count() == before_ai  # no AI calls in fill path


def test_msft_paper_notional_250_denied_by_max_position_cap(session):
    emp = _grant_place_and_allow(session, symbol="MSFT")
    before_ai = session.query(AICallLog).count()

    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "MSFT", "side": "buy", "notional_gbp": 250.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is False
    assert d.reason == "MAX_POSITION_EXCEEDED"
    assert session.query(PaperFill).count() == 0
    assert session.query(AICallLog).count() == before_ai  # no AI calls in fill path


def test_shel_l_pence_handling_keeps_cash_and_london_day_pnl(session):
    emp = _grant_place_and_allow(session, symbol="SHEL.L")
    assert session.query(PaperFill).count() == 0

    before_ai = session.query(AICallLog).count()
    d = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "SHEL.L", "side": "buy", "quantity": 5.0, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert d.allowed is True
    assert d.reason == "PAPER_FILL_SIMULATED"

    fill = session.query(PaperFill).one()
    assert abs(fill.price - 34.127093) < 1e-6

    acc = session.get(PaperAccount, 1)
    # Existing SHEL.L fill cash must stay stable: no pence double-conversion.
    assert abs(acc.cash - 829.279217) < 1e-4

    pnl = PaperLedger(session).london_day_pnl(at=SESSION_OPEN)
    # Based on FakeMarketData last=34.093 for SHEL.L; cash update is deterministic.
    assert abs(pnl - (-0.255783)) < 1e-6

    # No AI calls in fill path.
    assert session.query(AICallLog).count() == before_ai


# ---------------------------------------------------------------------------
# BLOCKING correctness: pence vs pounds and USD FX (Risk/Challenge required)
# ---------------------------------------------------------------------------


def test_shel_l_pence_quote_sizes_identically_to_pound_equivalent():
    """A GBp (pence) feed quote must ÷100 before notional math.

    3409.3 GBp == £34.093. Both representations must produce the same
    mid_gbp and the same notional_gbp for a given quantity.
    """
    pence_last = 3409.3
    pound_last = 34.093

    assert is_pence_unit("GBp") is True
    assert is_pence_unit("GBX") is True
    assert is_pence_unit("GBP") is False

    assert abs(major_units(pence_last, "GBp") - pound_last) < 1e-6
    assert abs(major_units(pence_last, "GBX") - pound_last) < 1e-6
    assert abs(major_units(pound_last, "GBP") - pound_last) < 1e-6

    pence_row = {"symbol": "SHEL.L", "last": pence_last, "currency": "GBP", "quote_unit": "GBp"}
    pound_row = {"symbol": "SHEL.L", "last": pound_last, "currency": "GBP", "quote_unit": "GBP"}

    _, mid_from_pence, _, _, _ = mid_gbp_from_row("SHEL.L", pence_row)
    _, mid_from_pounds, _, _, _ = mid_gbp_from_row("SHEL.L", pound_row)
    assert abs(mid_from_pence - mid_from_pounds) < 1e-6
    assert abs(mid_from_pence - pound_last) < 1e-6

    econ_pence = paper_order_economics(
        {"symbol": "SHEL.L", "side": "buy", "quantity": 5.0},
        price_row=pence_row,
    )
    econ_pounds = paper_order_economics(
        {"symbol": "SHEL.L", "side": "buy", "quantity": 5.0},
        price_row=pound_row,
    )
    assert abs(econ_pence.mid_gbp - econ_pounds.mid_gbp) < 1e-6
    assert abs(econ_pence.notional_gbp - econ_pounds.notional_gbp) < 1e-6
    assert abs(econ_pence.fill_price_gbp - econ_pounds.fill_price_gbp) < 1e-6

    assert econ_pence.notional_gbp < 200.0
    assert econ_pence.fx.pair == "GBPGBP"
    assert econ_pence.fx.rate == 1.0


def test_usd_name_must_go_through_fx_conversion_never_treated_as_gbp():
    """A USD-quoted name (AAPL) must be FX-converted to GBP.

    If the conversion were skipped (treated as GBP), the mid_gbp would
    equal the raw USD last. After proper conversion it must be lower
    (USDGBP < 1).
    """
    usd_last = 190.0
    row = {"symbol": "AAPL", "last": usd_last, "currency": "USD", "quote_unit": "USD"}

    _, mid_gbp, quote_ccy, _, fx = mid_gbp_from_row("AAPL", row)
    assert quote_ccy == "USD"
    assert fx.pair == "USDGBP"
    assert fx.rate > 0 and fx.rate < 1.0
    assert fx.source  # provenance must be recorded

    expected_gbp = usd_last * FAKE_USDGBP_LAST
    assert abs(mid_gbp - expected_gbp) < 1e-4
    assert mid_gbp != usd_last  # must NOT be silently equal to USD last

    econ = paper_order_economics(
        {"symbol": "AAPL", "side": "buy", "notional_gbp": 150.0},
        price_row=row,
    )
    assert econ.instrument_currency == "USD"
    assert econ.fx.pair == "USDGBP"
    assert econ.fx.rate == FAKE_USDGBP_LAST
    assert econ.mid_gbp == mid_gbp
    assert econ.notional_gbp <= 150.0 + 1e-6
    assert econ.quantity > 0

    raw_fill_usd = econ.native_fill_price
    fill_gbp = econ.fill_price_gbp
    assert abs(fill_gbp - raw_fill_usd * FAKE_USDGBP_LAST) < 0.01
    assert fill_gbp != raw_fill_usd

