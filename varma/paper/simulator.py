"""Internal PAPER FILL SIMULATOR — the paper ledger (Document 12).

This is not a broker. BROKER_PAPER and LIVE adapters remain UNLOADED.
No gold execution. No live/paper fills against a broker.

The simulator still DENIES when:
- PAPER execution is CLOSED (Board Addendum I — firm not open)
- the execution allow-list is empty
- trading_mode is LIVE or the order asks for LIVE
- the kill switch is on
- numeric limits are exceeded (max_position, max_orders_per_day, max_daily_loss)
- missing Board-set limits (should not happen after Addendum A)

Board Addendum I: the firm is CLOSED until Grand Opening. Simulator DENY all
fills because the firm is not open, even for allow-listed tickers. Allow-list
E still exists. £1000 is the FUTURE paper starting book only. Addendum A
numbers are stored but unused until open. Do not implement the first paper
trade path.

Empty allow-list ⇒ no orders, so production seed records zero fills. Evaluation
ledger tables still exist (closed trades, pnl, win rate of profitable closes).

INTERNAL SIMULATOR ASSUMPTIONS (not a vendor contract, not Board FX, not LIVE):
- Currency: GBP. Timezone: Europe/London (Board Addendum A 2026-08-27).
- Mid: FakeMarketData delayed last, treated as GBP notional for this simulator
  only. There is no FX vendor in this slice. Labelled INTERNAL ASSUMPTION.
- Spread: 10 bps (0.10%) of mid. Half-spread is charged against the taker.
- Slippage: 5 bps (0.05%) of mid, additional adverse movement.
- Combined adverse vs mid: 10 bps (half-spread 5 + slippage 5).
- Commission: 5 bps (0.05%) of fill notional, deducted from cash.
- Buy fill = mid * (1 + 10 bps). Sell fill = mid * (1 - 10 bps).
- No short-locate, borrow, or overnight financing in this slice.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import london_day, now_london
from varma.controls.addendum_a import ADDENDUM_A_LABEL, CURRENCY, TIMEZONE
from varma.controls.addendum_i import (
    ADDENDUM_I_LABEL,
    PAPER_EXECUTION_CLOSED_REASON,
    paper_execution_is_closed,
)
from varma.controls.engine import Decision
from varma.db.models import ClosedPaperTrade, Evidence, PaperFill, PaperOrder, PaperPosition
from varma.paper.ledger import PaperLedger
from varma.ports.data import FakeMarketData

# --- Internal simulator assumptions (Document 12). Not a broker schedule. ---
SPREAD_BPS = 10.0
SLIPPAGE_BPS = 5.0
COMMISSION_BPS = 5.0
ADVERSE_BPS = (SPREAD_BPS / 2.0) + SLIPPAGE_BPS  # 10 bps vs mid
ASSUMPTIONS_NOTE = (
    "INTERNAL PAPER FILL SIMULATOR assumptions: spread 10 bps of mid; "
    "half-spread + slippage 5 bps = 10 bps adverse vs mid; commission 5 bps "
    "of notional; FakeMarketData last treated as GBP (no FX vendor). "
    "Not BROKER_PAPER. Not LIVE. Not a vendor contract."
)


def simulator_assumptions() -> dict[str, Any]:
    return {
        "kind": "INTERNAL_PAPER_FILL_SIMULATOR",
        "broker": False,
        "broker_paper_loaded": False,
        "live_loaded": False,
        "currency": CURRENCY,
        "timezone": TIMEZONE,
        "spread_bps": SPREAD_BPS,
        "slippage_bps": SLIPPAGE_BPS,
        "commission_bps": COMMISSION_BPS,
        "adverse_bps_vs_mid": ADVERSE_BPS,
        "fx": "none — FakeMarketData last treated as GBP (INTERNAL ASSUMPTION)",
        "source": ADDENDUM_A_LABEL,
        "paper_execution": "CLOSED",
        "firm_open": False,
        "first_paper_trade_path_implemented": False,
        "addendum_i": ADDENDUM_I_LABEL,
        "note": ASSUMPTIONS_NOTE,
    }


class PaperFillSimulator:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.ledger = PaperLedger(session)
        self.data = FakeMarketData()

    def mid_gbp(self, symbol: str) -> float:
        rows = self.data.delayed_prices([symbol])
        last = float(rows[0]["last"]) if rows else 1.0
        return last if last > 0 else 1.0

    def fill(self, *, actor_id: str, order: dict[str, Any], at=None, is_flatten: bool = False) -> Decision:
        """Simulate a paper fill. Caller has already passed control gates.

        Board Addendum I: DENY all fills while PAPER execution is CLOSED,
        including flatten close-outs. Do not run flatten-as-if-there-were-positions.
        Flatten close-outs call this directly (session hygiene) only after
        Grand Opening PAPER. They do not require allow-list membership.
        New risk orders still go through ControlEngine.
        """
        now = at or now_london()
        if paper_execution_is_closed(self.session):
            return self._deny(
                PAPER_EXECUTION_CLOSED_REASON,
                actor_id,
                {**dict(order), "is_flatten": is_flatten},
            )
        self.ledger.ensure_account(at=now)
        symbol = str(order.get("symbol") or "")
        side = str(order.get("side") or "buy").lower()
        if side not in {"buy", "sell"}:
            return self._deny("INVALID_SIDE", actor_id, order)
        mid = self.mid_gbp(symbol)
        quantity = abs(float(order.get("quantity") or 0))
        requested_notional = order.get("notional_gbp")
        if quantity == 0 and requested_notional:
            quantity = abs(float(requested_notional)) / mid
        if quantity <= 0:
            return self._deny("INVALID_QUANTITY", actor_id, order)

        if side == "buy":
            fill_price = mid * (1.0 + ADVERSE_BPS / 10000.0)
        else:
            fill_price = mid * (1.0 - ADVERSE_BPS / 10000.0)
        fill_price = round(fill_price, 6)
        notional = round(quantity * fill_price, 6)
        commission = round(notional * COMMISSION_BPS / 10000.0, 6)
        day = london_day(now)

        paper_order = PaperOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional_gbp=notional,
            status="OPEN",
            london_day=day,
            mid_price=mid,
            fill_price=fill_price,
            spread_bps=SPREAD_BPS,
            slippage_bps=SLIPPAGE_BPS,
            commission_gbp=commission,
            actor_id=actor_id,
            execution_port="SIMULATOR",
            is_paper=True,
            is_live=False,
            is_flatten=is_flatten,
            created_at=now,
            notes=ASSUMPTIONS_NOTE if not is_flatten else "FLATTEN_BEFORE_US_REGULAR_CASH_CLOSE",
        )
        self.session.add(paper_order)
        self.session.flush()

        fill_row = PaperFill(
            order_id=paper_order.id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=fill_price,
            notional_gbp=notional,
            commission_gbp=commission,
            london_day=day,
            filled_at=now,
            is_live=False,
        )
        self.session.add(fill_row)
        closed = self._apply_position(symbol, side, quantity, fill_price, commission, day, now)
        account = self.ledger.account()
        if side == "buy":
            account.cash = round(account.cash - notional - commission, 6)
        else:
            account.cash = round(account.cash + notional - commission, 6)
        account.updated_at = now
        paper_order.status = "FILLED"
        paper_order.filled_at = now
        self.session.commit()

        details = {
            "order_id": paper_order.id,
            "fill_id": fill_row.id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "mid_price": mid,
            "fill_price": fill_price,
            "notional_gbp": notional,
            "commission_gbp": commission,
            "currency": CURRENCY,
            "london_day": day,
            "is_paper": True,
            "is_live": False,
            "broker": False,
            "execution_port": "SIMULATOR",
            "assumptions": simulator_assumptions(),
            "closed_trade_id": closed.id if closed else None,
            "cash_gbp": self.ledger.account(at=now).cash,
            "equity_gbp": self.ledger.equity(),
            "london_day_pnl_gbp": self.ledger.london_day_pnl(at=now),
            "is_flatten": is_flatten,
        }
        self._evidence("paper_fill_simulated", actor_id, details)
        return Decision(True, "PAPER_FILL_SIMULATED", details)

    def _apply_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        fill_price: float,
        commission: float,
        day: str,
        now,
    ) -> ClosedPaperTrade | None:
        pos = self.session.get(PaperPosition, symbol)
        signed = quantity if side == "buy" else -quantity
        if pos is None or pos.quantity == 0:
            self.session.add(
                PaperPosition(
                    symbol=symbol,
                    quantity=signed,
                    avg_cost_gbp=fill_price,
                    updated_at=now,
                )
            )
            return None

        old_qty = pos.quantity
        # Same direction: extend. Opposite: reduce / close / reverse.
        if (old_qty > 0 and signed > 0) or (old_qty < 0 and signed < 0):
            new_qty = old_qty + signed
            pos.avg_cost_gbp = (
                (abs(old_qty) * pos.avg_cost_gbp + quantity * fill_price) / abs(new_qty)
            )
            pos.quantity = new_qty
            pos.updated_at = now
            return None

        closing_qty = min(abs(old_qty), quantity)
        if old_qty > 0:
            pnl = round((fill_price - pos.avg_cost_gbp) * closing_qty - commission * (closing_qty / quantity), 6)
        else:
            pnl = round((pos.avg_cost_gbp - fill_price) * closing_qty - commission * (closing_qty / quantity), 6)
        closed = ClosedPaperTrade(
            symbol=symbol,
            quantity=closing_qty,
            entry_price=pos.avg_cost_gbp,
            exit_price=fill_price,
            pnl_gbp=pnl,
            profit_positive=pnl > 0,
            london_day=day,
            closed_at=now,
            is_paper=True,
            is_live=False,
        )
        self.session.add(closed)
        remaining = old_qty + signed
        if remaining == 0:
            self.session.delete(pos)
        elif (old_qty > 0 and remaining < 0) or (old_qty < 0 and remaining > 0):
            pos.quantity = remaining
            pos.avg_cost_gbp = fill_price
            pos.updated_at = now
        else:
            pos.quantity = remaining
            pos.updated_at = now
        return closed

    def _deny(self, reason: str, actor_id: str, order: dict[str, Any]) -> Decision:
        details = {"order": order, "simulator": True}
        self._evidence("order_denied", actor_id, {"reason": reason, **details})
        return Decision(False, reason, details)

    def _evidence(self, kind: str, actor: str, payload: dict[str, Any]) -> None:
        import json

        self.session.add(
            Evidence(
                kind=kind,
                actor=actor,
                payload=json.dumps(payload, default=str),
                created_at=now_london(),
            )
        )
        self.session.commit()
