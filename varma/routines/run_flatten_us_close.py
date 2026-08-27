"""On-demand flatten ALL paper before US regular cash close. No daemon.

Usage:
    python -m varma.routines.run_flatten_us_close

Board Addendum C 2026-08-27. Internal simulator only. Not a broker.
GET /observability does not flatten. Employees cannot run this via the API.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import describe_flatten_us_close, now_london
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.paper.flatten import flatten_all_paper


def run_flatten_us_close(session: Session, *, started_by: str = "cli", at=None) -> dict:
    return flatten_all_paper(
        session,
        actor_id=started_by,
        at=at,
        started_by=started_by,
    )


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        print(describe_flatten_us_close())
        print("Now Europe/London:", now_london().isoformat())
        print("Daemon: False")
        print("Flatten at: US_REGULAR_CASH_CLOSE")
        print("Flatten not at: LONDON_CASH_CLOSE")
        result = run_flatten_us_close(session, started_by="cli")
        print("flatten_run_id:", result["id"])
        print("cancelled_open_paper_orders:", result["cancelled_open_paper_orders"])
        print("closed_positions:", result["closed_positions"])
        print("flatten_fills:", result["flatten_fills"])
        print("positions_remaining:", result["positions_remaining"])
        print("trading_mode:", result["trading_mode_after"])
        print("broker_paper_loaded:", result["broker_paper_loaded"])
        print("live_loaded:", result["live_loaded"])
        print("stored_in: database table paper_flatten_runs")
    finally:
        session.close()


if __name__ == "__main__":
    main()
