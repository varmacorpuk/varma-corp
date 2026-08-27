"""On-demand nightly Europe/London working-context filter. No daemon scheduler.

Usage:
    python -m varma.routines.run_nightly_filter
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import describe_nightly_memory_filter, now_london
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.memory.filter import NightlyMemoryFilter


def run_nightly_filter(session: Session) -> dict:
    return NightlyMemoryFilter(session).run()


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        print(describe_nightly_memory_filter())
        print("Now Europe/London:", now_london().isoformat())
        print("Daemon: False")
        result = run_nightly_filter(session)
        print("filter_run_id:", result["id"])
        print("archived_count:", result["archived_count"])
        print("working_remaining:", result.get("working_remaining"))
        print("evidence_count_before:", result["evidence_count_before"])
        print("evidence_count_after:", result["evidence_count_after"])
        print("evidence_deleted:", result["evidence_deleted"])
        print("controls_written:", result["controls_written"])
        print("trading_mode:", result["trading_mode_after"])
        print("live_still_blocked:", result["live_still_blocked"])
        print("stored_in: database tables memory_filter_runs, memory_working_archive")
    finally:
        session.close()


if __name__ == "__main__":
    main()
