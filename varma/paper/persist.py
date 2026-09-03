"""Tracked practice paper ledger for the paper-OPEN book.

The floor / kernel still read SQLite at runtime. This JSON is the git-tracked
paper-book source of truth so SHEL.L fills survive a fresh VM (the sqlite file
was gitignored). Employee memory, chat, and secrets are not included.

LIVE stays blocked. Never writes data/varma.db.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import LONDON, now_london
from varma.config import DATA_DIR
from varma.db.models import (
    ClosedPaperTrade,
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperPosition,
)

TRACKED_LEDGER_FILENAME = "paper_open_ledger.json"
PAPER_OPEN_DB_FILENAME = "varma_paper_open.db"
LEDGER_KIND = "PAPER_OPEN_LEDGER"
TICKET_PAPER_20260903_02 = "PAPER-20260903-02"


def tracked_ledger_path() -> Path:
    return DATA_DIR / TRACKED_LEDGER_FILENAME


def is_paper_open_book_session(session: Session) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    url = str(bind.url)
    return url.rstrip("/").endswith(PAPER_OPEN_DB_FILENAME)


def _dt_to_str(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=LONDON)
    return parsed


def dump_paper_ledger(session: Session, *, ticket_id: str | None = None) -> dict[str, Any]:
    """Serialize paper account / orders / fills / positions. No employee memory."""
    acc = session.get(PaperAccount, 1)
    fills = session.query(PaperFill).order_by(PaperFill.filled_at.asc()).all()
    orders = session.query(PaperOrder).order_by(PaperOrder.created_at.asc()).all()
    positions = session.query(PaperPosition).order_by(PaperPosition.symbol.asc()).all()
    closed = session.query(ClosedPaperTrade).order_by(ClosedPaperTrade.closed_at.asc()).all()
    payload: dict[str, Any] = {
        "kind": LEDGER_KIND,
        "book": PAPER_OPEN_DB_FILENAME,
        "trading_mode": "LIVE_BLOCKED",
        "is_live": False,
        "live_fills": False,
        "broker_paper_loaded": False,
        "ticket_id": ticket_id,
        "account": None
        if acc is None
        else {
            "id": acc.id,
            "currency": acc.currency,
            "timezone": acc.timezone,
            "simulated_capital": acc.simulated_capital,
            "cash": acc.cash,
            "equity_at_day_start": acc.equity_at_day_start,
            "london_day": acc.london_day,
            "source": acc.source,
            "updated_at": _dt_to_str(acc.updated_at),
        },
        "orders": [
            {
                "id": row.id,
                "symbol": row.symbol,
                "side": row.side,
                "quantity": row.quantity,
                "notional_gbp": row.notional_gbp,
                "status": row.status,
                "london_day": row.london_day,
                "mid_price": row.mid_price,
                "fill_price": row.fill_price,
                "spread_bps": row.spread_bps,
                "slippage_bps": row.slippage_bps,
                "commission_gbp": row.commission_gbp,
                "actor_id": row.actor_id,
                "execution_port": row.execution_port,
                "is_paper": row.is_paper,
                "is_live": row.is_live,
                "created_at": _dt_to_str(row.created_at),
                "filled_at": _dt_to_str(row.filled_at),
                "cancelled_at": _dt_to_str(row.cancelled_at),
                "cancel_reason": row.cancel_reason,
                "notes": row.notes,
                "is_flatten": row.is_flatten,
            }
            for row in orders
        ],
        "fills": [
            {
                "id": row.id,
                "order_id": row.order_id,
                "symbol": row.symbol,
                "side": row.side,
                "quantity": row.quantity,
                "price": row.price,
                "notional_gbp": row.notional_gbp,
                "commission_gbp": row.commission_gbp,
                "london_day": row.london_day,
                "filled_at": _dt_to_str(row.filled_at),
                "is_live": row.is_live,
            }
            for row in fills
        ],
        "positions": [
            {
                "symbol": row.symbol,
                "quantity": row.quantity,
                "avg_cost_gbp": row.avg_cost_gbp,
                "updated_at": _dt_to_str(row.updated_at),
            }
            for row in positions
        ],
        "closed_trades": [
            {
                "id": row.id,
                "symbol": row.symbol,
                "quantity": row.quantity,
                "entry_price": row.entry_price,
                "exit_price": row.exit_price,
                "pnl_gbp": row.pnl_gbp,
                "profit_positive": row.profit_positive,
                "london_day": row.london_day,
                "closed_at": _dt_to_str(row.closed_at),
                "is_paper": row.is_paper,
                "is_live": row.is_live,
            }
            for row in closed
        ],
    }
    if ticket_id is None and fills:
        payload["ticket_id"] = TICKET_PAPER_20260903_02
    return payload


def write_tracked_paper_ledger(
    session: Session,
    *,
    ticket_id: str | None = None,
    path: Path | None = None,
) -> Path:
    import json

    dest = path or tracked_ledger_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = dump_paper_ledger(session, ticket_id=ticket_id)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def restore_paper_ledger(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """Load paper tables from a tracked ledger. Does not touch employee memory."""
    if payload.get("kind") != LEDGER_KIND:
        raise ValueError("not a PAPER_OPEN_LEDGER")
    account = payload.get("account") or {}
    acc = session.get(PaperAccount, 1)
    if acc is None:
        acc = PaperAccount(id=int(account.get("id") or 1))
        session.add(acc)
    if account:
        acc.currency = str(account.get("currency") or acc.currency or "GBP")
        acc.timezone = str(account.get("timezone") or acc.timezone or "Europe/London")
        acc.simulated_capital = float(account.get("simulated_capital") or 1000)
        acc.cash = float(account["cash"])
        acc.equity_at_day_start = float(
            account.get("equity_at_day_start") or acc.simulated_capital
        )
        acc.london_day = str(account.get("london_day") or acc.london_day or "")
        acc.source = str(account.get("source") or acc.source or "")
        acc.updated_at = _parse_dt(account.get("updated_at")) or acc.updated_at

    for row in payload.get("orders") or []:
        existing = session.get(PaperOrder, row["id"])
        if existing is not None:
            continue
        session.add(
            PaperOrder(
                id=row["id"],
                symbol=row["symbol"],
                side=row["side"],
                quantity=float(row["quantity"]),
                notional_gbp=float(row["notional_gbp"]),
                status=row["status"],
                london_day=row["london_day"],
                mid_price=row.get("mid_price"),
                fill_price=row.get("fill_price"),
                spread_bps=float(row.get("spread_bps") or 0),
                slippage_bps=float(row.get("slippage_bps") or 0),
                commission_gbp=float(row.get("commission_gbp") or 0),
                actor_id=str(row.get("actor_id") or ""),
                execution_port=str(row.get("execution_port") or "SIMULATOR"),
                is_paper=bool(row.get("is_paper", True)),
                is_live=bool(row.get("is_live", False)),
                created_at=_parse_dt(row["created_at"]) or now_london(),
                filled_at=_parse_dt(row.get("filled_at")),
                cancelled_at=_parse_dt(row.get("cancelled_at")),
                cancel_reason=str(row.get("cancel_reason") or ""),
                notes=str(row.get("notes") or ""),
                is_flatten=bool(row.get("is_flatten", False)),
            )
        )

    for row in payload.get("fills") or []:
        existing = session.get(PaperFill, row["id"])
        if existing is not None:
            continue
        session.add(
            PaperFill(
                id=row["id"],
                order_id=row["order_id"],
                symbol=row["symbol"],
                side=row["side"],
                quantity=float(row["quantity"]),
                price=float(row["price"]),
                notional_gbp=float(row["notional_gbp"]),
                commission_gbp=float(row.get("commission_gbp") or 0),
                london_day=row["london_day"],
                filled_at=_parse_dt(row["filled_at"]),
                is_live=bool(row.get("is_live", False)),
            )
        )

    for row in payload.get("positions") or []:
        existing = session.get(PaperPosition, row["symbol"])
        if existing is None:
            existing = PaperPosition(symbol=row["symbol"])
            session.add(existing)
        existing.quantity = float(row["quantity"])
        existing.avg_cost_gbp = float(row["avg_cost_gbp"])
        existing.updated_at = _parse_dt(row.get("updated_at")) or existing.updated_at

    for row in payload.get("closed_trades") or []:
        existing = session.get(ClosedPaperTrade, row["id"])
        if existing is not None:
            continue
        session.add(
            ClosedPaperTrade(
                id=row["id"],
                symbol=row["symbol"],
                quantity=float(row["quantity"]),
                entry_price=float(row["entry_price"]),
                exit_price=float(row["exit_price"]),
                pnl_gbp=float(row["pnl_gbp"]),
                profit_positive=bool(row.get("profit_positive")),
                london_day=row["london_day"],
                closed_at=_parse_dt(row["closed_at"]),
                is_paper=bool(row.get("is_paper", True)),
                is_live=bool(row.get("is_live", False)),
            )
        )

    session.commit()
    return {
        "restored": True,
        "fills": session.query(PaperFill).count(),
        "positions": session.query(PaperPosition).count(),
        "cash_gbp": session.get(PaperAccount, 1).cash if session.get(PaperAccount, 1) else None,
        "ticket_id": payload.get("ticket_id"),
        "trading_mode": "LIVE_BLOCKED",
        "is_live": False,
    }


def maybe_restore_tracked_paper_ledger(
    session: Session,
    *,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Hydrate the paper-OPEN book from git when sqlite has zero fills.

    Test databases (tmp_path / :memory:) are not the paper-OPEN book and are
    left alone. Never opens data/varma.db.
    """
    import json

    if not is_paper_open_book_session(session):
        return None
    if session.query(PaperFill).count() > 0:
        return None
    src = path or tracked_ledger_path()
    if not src.is_file():
        return None
    payload = json.loads(src.read_text(encoding="utf-8"))
    return restore_paper_ledger(session, payload)


def existing_shel_l_buy_5_fill(session: Session) -> PaperFill | None:
    return (
        session.query(PaperFill)
        .filter_by(symbol="SHEL.L", side="buy", quantity=5.0, is_live=False)
        .order_by(PaperFill.filled_at.asc())
        .first()
    )
