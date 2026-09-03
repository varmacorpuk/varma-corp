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

