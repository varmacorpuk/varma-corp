"""On-demand Trader paper-ticket proposal. No daemon.

Usage:
    python -m varma.routines.run_paper_trade_path
    python -m varma.routines.run_paper_trade_path --ticket PAPER-20260903-02

Chris Adeyemi · Trader proposes a legal allow-list paper buy. ControlEngine
permit/deny is authoritative. After Grand Opening PAPER the internal paper
simulator may fill when in session and within limits. LIVE stays off.
FakeLLM is not called. Board-only via the API. GET /observability does not run this.

Named ticket PAPER-20260903-02 (SHEL.L BUY 5) writes only to
data/varma_paper_open.db. It never opens data/varma.db. LIVE and BROKER_PAPER
ports are not loaded.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from varma.clock import LONDON, now_london
from varma.config import DATA_DIR
from varma.controls.addendum_f import TRADER_SLUG
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.employees.runtime import EmployeeRuntime
from varma.meetings.handoff import get_employee
from varma.skills.propose_paper_ticket import (
    PAPER_20260903_02_AT,
    PAPER_20260903_02_ID,
    PAPER_OPEN_BOOK_ONLY_TICKETS,
    REFUSE_LIVE_OR_BROKER_PORT,
    named_paper_ticket,
)

PAPER_OPEN_DB_FILENAME = "varma_paper_open.db"
DEFAULT_DEV_DB_FILENAME = "varma.db"
REFUSE_DEFAULT_VARMA_DB = "REFUSE_DEFAULT_VARMA_DB"


def paper_open_book_sqlite_path() -> Path:
    """Practice paper book. Must not resolve to data/varma.db."""
    path = (DATA_DIR / PAPER_OPEN_DB_FILENAME).resolve()
    forbidden = (DATA_DIR / DEFAULT_DEV_DB_FILENAME).resolve()
    if path == forbidden or path.name == DEFAULT_DEV_DB_FILENAME:
        raise RuntimeError(REFUSE_DEFAULT_VARMA_DB)
    return path


def paper_open_book_url() -> str:
    return f"sqlite:///{paper_open_book_sqlite_path()}"


def sqlite_path_from_url(url: str) -> Path | None:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    raw = url[len(prefix) :]
    if raw in {":memory:", ""}:
        return None
    return Path(raw).resolve()


def assert_url_is_not_default_varma_db(url: str) -> str:
    path = sqlite_path_from_url(url)
    if path is not None and path.name == DEFAULT_DEV_DB_FILENAME:
        raise RuntimeError(REFUSE_DEFAULT_VARMA_DB)
    return url


def run_paper_trade_path(
    session: Session,
    *,
    started_by: str = "cli",
    at=None,
    order: dict | None = None,
) -> dict:
    trader = get_employee(session, TRADER_SLUG)
    return EmployeeRuntime(session, trader).propose_paper_ticket(
        order=order,
        at=at,
        started_by=started_by,
    )


def _parse_london_at(value: str | None):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=LONDON)
    return parsed.astimezone(LONDON)


def _build_cli_order(args: argparse.Namespace) -> dict | None:
    if args.ticket:
        order = named_paper_ticket(args.ticket)
    elif args.symbol:
        order = {
            "symbol": args.symbol,
            "side": (args.side or "buy").lower(),
            "execution_port": "SIMULATOR",
        }
        if args.quantity is not None:
            order["quantity"] = float(args.quantity)
        if args.notional_gbp is not None:
            order["notional_gbp"] = float(args.notional_gbp)
    else:
        return None
    port = str(order.get("execution_port") or "SIMULATOR").upper()
    if port in {"LIVE", "BROKER_PAPER"}:
        raise RuntimeError(REFUSE_LIVE_OR_BROKER_PORT)
    order["execution_port"] = "SIMULATOR"
    return order


def _resolve_database_url(args: argparse.Namespace) -> str | None:
    ticket_id = args.ticket
    wants_paper_open = bool(args.paper_open_book) or (
        ticket_id in PAPER_OPEN_BOOK_ONLY_TICKETS
    )
    if wants_paper_open:
        if args.database_url:
            return assert_url_is_not_default_varma_db(args.database_url)
        return paper_open_book_url()
    if args.database_url:
        return args.database_url
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "On-demand Trader paper-ticket path. ControlEngine permit/deny. "
            "Internal simulator only. LIVE and BROKER_PAPER stay UNLOADED."
        )
    )
    parser.add_argument(
        "--ticket",
        default=None,
        help=f"Named paper ticket id (e.g. {PAPER_20260903_02_ID})",
    )
    parser.add_argument("--symbol", default=None, help="Override symbol")
    parser.add_argument("--side", default="buy", help="buy or sell")
    parser.add_argument("--quantity", type=float, default=None)
    parser.add_argument("--notional-gbp", type=float, default=None)
    parser.add_argument(
        "--at",
        default=None,
        help="ISO datetime on the Europe/London clock",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLite URL. Named paper-open tickets refuse data/varma.db.",
    )
    parser.add_argument(
        "--paper-open-book",
        action="store_true",
        help="Use data/varma_paper_open.db. Never data/varma.db.",
    )
    args = parser.parse_args()

    url = _resolve_database_url(args)
    order = _build_cli_order(args)
    at = _parse_london_at(args.at)
    if args.ticket == PAPER_20260903_02_ID and at is None:
        at = PAPER_20260903_02_AT

    if url is not None:
        init_db(url, reset=True)
        factory = get_session_factory(url, reset=False)
    else:
        init_db()
        factory = get_session_factory()
    session = factory()
    try:
        from varma.db.models import PaperAccount, PaperPosition
        from varma.paper.persist import (
            existing_shel_l_buy_5_fill,
            maybe_restore_tracked_paper_ledger,
            write_tracked_paper_ledger,
        )

        seed_if_empty(session)
        maybe_restore_tracked_paper_ledger(session)
        print("Trader paper-ticket proposal — first paper-trade PATH")
        print("PAPER execution: OPEN after Grand Opening PAPER (LIVE still blocked)")
        print("Daemon: False")
        print("AI called: False")
        if url is not None:
            print("database_url:", url)
        print("Now Europe/London:", now_london().isoformat())
        if at is not None:
            print("ticket_at Europe/London:", at.isoformat())

        existing = None
        if args.ticket == PAPER_20260903_02_ID:
            existing = existing_shel_l_buy_5_fill(session)
        if existing is not None:
            acc = session.get(PaperAccount, 1)
            pos = session.get(PaperPosition, "SHEL.L")
            print("proposed: True")
            print("already_filled: True")
            print("proposer: Chris Adeyemi · Trader")
            print("symbol: SHEL.L")
            print("allowed: True")
            print("reason: PAPER_FILL_SIMULATED")
            print("filled: True")
            print("paper_fills: True")
            print("live_fills: False")
            print("paper_execution: OPEN")
            print("trading_mode: LIVE_BLOCKED")
            print("ai_called: False")
            print("path_reached: internal_simulator")
            print("fill_id:", existing.id)
            print("fill_price:", existing.price)
            print("quantity:", existing.quantity)
            print("notional_gbp:", existing.notional_gbp)
            print("cash_gbp:", None if acc is None else acc.cash)
            print("position_qty:", None if pos is None else pos.quantity)
        else:
            result = run_paper_trade_path(session, started_by="cli", at=at, order=order)
            print("proposed:", result["proposed"])
            print("proposer:", result["proposer"]["display_name"])
            print("symbol:", result["order"]["symbol"])
            print("allowed:", result["allowed"])
            print("reason:", result["reason"])
            print("filled:", result["filled"])
            print("paper_fills:", result["paper_fills"])
            print("live_fills:", result["live_fills"])
            print("paper_execution:", result["paper_execution"])
            print("trading_mode:", result["trading_mode"])
            print("ai_called:", result["ai_called"])
            print("path_reached:", result["path"]["reached"])
            if result.get("details"):
                details = result["details"]
                print("fill_id:", details.get("fill_id"))
                print("fill_price:", details.get("fill_price"))
                print("quantity:", details.get("quantity"))
                print("notional_gbp:", details.get("notional_gbp"))
                print("cash_gbp:", details.get("cash_gbp"))

        path = sqlite_path_from_url(url) if url else None
        if path is not None and path.name == PAPER_OPEN_DB_FILENAME:
            written = write_tracked_paper_ledger(
                session, ticket_id=args.ticket or PAPER_20260903_02_ID
            )
            print("tracked_ledger:", written)
    finally:
        session.close()


if __name__ == "__main__":
    main()
