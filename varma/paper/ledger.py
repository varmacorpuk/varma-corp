"""Paper evaluation ledger (Document 12). Database is the source of truth.

Tables exist even when the allow-list is empty and there are zero fills.
A successful trade is a CLOSED paper trade with profit > 0 (Board Addendum A).
Evaluation trigger: win rate of profitable closes > 50% AND book profitable.
Do not auto-switch LIVE. Paper continues until the Board explicitly approves.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import london_day, now_london
from varma.controls.addendum_a import (
    ADDENDUM_A_LABEL,
    CURRENCY,
    EVALUATION_AUTO_SWITCH_LIVE,
    EVALUATION_REQUIRES_BOOK_PROFITABLE,
    EVALUATION_WIN_RATE_THRESHOLD,
    SIMULATED_CAPITAL,
    SUCCESSFUL_TRADE_DEFINITION,
    TIMEZONE,
)
from varma.db.models import (
    ClosedPaperTrade,
    EvaluationPolicy,
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperPosition,
)
from varma.ports.data import FakeMarketData


def _round_gbp(value: float) -> float:
    return round(float(value), 6)


class PaperLedger:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_account(self, *, at=None) -> PaperAccount:
        row = self.session.get(PaperAccount, 1)
        today = london_day(at)
        now = at or now_london()
        if row is None:
            row = PaperAccount(
                id=1,
                currency=CURRENCY,
                timezone=TIMEZONE,
                simulated_capital=SIMULATED_CAPITAL,
                cash=SIMULATED_CAPITAL,
                equity_at_day_start=SIMULATED_CAPITAL,
                london_day=today,
                source=ADDENDUM_A_LABEL,
                updated_at=now,
            )
            self.session.add(row)
            self.session.flush()
            return row
        if row.london_day != today:
            equity = self.equity()
            row.london_day = today
            row.equity_at_day_start = equity
            row.updated_at = now
            self.session.flush()
        return row

    def account(self, *, at=None) -> PaperAccount:
        return self.ensure_account(at=at)

    def mark_price(self, symbol: str) -> float:
        rows = FakeMarketData().delayed_prices([symbol])
        last = float(rows[0]["last"]) if rows else 0.0
        return last

    def positions_market_value(self) -> float:
        total = 0.0
        for pos in self.session.query(PaperPosition).all():
            if pos.quantity == 0:
                continue
            total += pos.quantity * self.mark_price(pos.symbol)
        return _round_gbp(total)

    def equity(self) -> float:
        acc = self.session.get(PaperAccount, 1)
        cash = acc.cash if acc else SIMULATED_CAPITAL
        return _round_gbp(cash + self.positions_market_value())

    def london_day_pnl(self, *, at=None) -> float:
        acc = self.session.get(PaperAccount, 1)
        if acc is None:
            return 0.0
        start = acc.equity_at_day_start if acc.london_day == london_day(at) else self.equity()
        return _round_gbp(self.equity() - start)

    def orders_today(self, *, at=None) -> int:
        day = london_day(at)
        return (
            self.session.query(PaperOrder)
            .filter(
                PaperOrder.london_day == day,
                PaperOrder.status.in_(("OPEN", "FILLED", "CANCELLED")),
                PaperOrder.is_flatten.is_(False),
            )
            .count()
        )

    def open_orders(self) -> list[PaperOrder]:
        return self.session.query(PaperOrder).filter_by(status="OPEN").all()

    def cancel_open_paper_orders(self, *, reason: str, at=None) -> int:
        """Cancel OPEN paper orders only. Never flatten live. There is no live."""
        now = at or now_london()
        n = 0
        for row in self.open_orders():
            row.status = "CANCELLED"
            row.cancelled_at = now
            row.cancel_reason = reason
            n += 1
        if n:
            self.session.flush()
        return n


def evaluation_snapshot(session: Session) -> dict[str, Any]:
    """Read-only evaluation ledger. Zero fills is a valid state."""
    policy = session.get(EvaluationPolicy, 1)
    closed = session.query(ClosedPaperTrade).order_by(ClosedPaperTrade.closed_at.asc()).all()
    profitable = [row for row in closed if row.pnl_gbp > 0]
    n_closed = len(closed)
    n_profitable = len(profitable)
    win_rate = (n_profitable / n_closed) if n_closed else 0.0
    realized = sum(row.pnl_gbp for row in closed)
    ledger = PaperLedger(session)
    acc = session.get(PaperAccount, 1)
    equity = ledger.equity() if acc else 0.0
    capital = acc.simulated_capital if acc else SIMULATED_CAPITAL
    book_pnl = _round_gbp(equity - capital) if acc else 0.0
    book_profitable = book_pnl > 0
    threshold = float(policy.win_rate_threshold) if policy else EVALUATION_WIN_RATE_THRESHOLD
    requires_book = (
        bool(policy.requires_book_profitable) if policy else EVALUATION_REQUIRES_BOOK_PROFITABLE
    )
    trigger = n_closed > 0 and win_rate > threshold and (book_profitable if requires_book else True)
    auto = bool(policy.auto_switch_live) if policy else EVALUATION_AUTO_SWITCH_LIVE
    return {
        "read_only": True,
        "source": "database",
        "currency": CURRENCY,
        "timezone": TIMEZONE,
        "addendum": ADDENDUM_A_LABEL,
        "board_set": True,
        "values_invented": False,
        "successful_trade_definition": (
            policy.successful_trade_definition if policy else SUCCESSFUL_TRADE_DEFINITION
        ),
        "closed_trades": n_closed,
        "profitable_closes": n_profitable,
        "win_rate": win_rate,
        "win_rate_threshold": threshold,
        "win_rate_trigger_is_strictly_greater": True,
        "realized_pnl_gbp": _round_gbp(realized),
        "book_pnl_gbp": book_pnl,
        "book_profitable": book_profitable,
        "evaluation_trigger_met": trigger,
        "evaluation_auto_switch_live": auto,
        "live_switched": False,
        "paper_continues_until_board_approval": True,
        "fills": session.query(PaperFill).count(),
        "open_orders": session.query(PaperOrder).filter_by(status="OPEN").count(),
        "zero_fills_valid": True,
        "note": (
            "Evaluation ledger. A successful trade is a CLOSED paper trade with "
            "profit > 0. Trigger is win rate > 50% of closed trades AND book "
            "profitable. Do not auto-switch LIVE. Paper continues until the Board "
            "explicitly approves. Empty allow-list ⇒ zero fills is expected."
        ),
        "closed_trade_rows": [
            {
                "id": row.id,
                "symbol": row.symbol,
                "quantity": row.quantity,
                "pnl_gbp": row.pnl_gbp,
                "profit_positive": bool(row.profit_positive),
                "london_day": row.london_day,
            }
            for row in closed
        ],
    }
