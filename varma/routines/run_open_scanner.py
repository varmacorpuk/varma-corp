"""On-demand NY-open scanner. No daemon. Does not place orders.

Usage:
    python -m varma.routines.run_open_scanner

Board Member API: POST /routines/run-open-scanner
Paper only. LIVE stays BLOCKED. Not a trade. Not LIVE approval.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import describe_open_scanner, now_london
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.ports.bars import FakeDelayedBars
from varma.scanner.open_scanner import (
    DEFAULT_LATENCY_SECONDS,
    OpenScanner,
    scan_result_envelope,
)


def run_open_scanner(
    session: Session,
    *,
    started_by: str = "cli",
    as_of: datetime | None = None,
    latency_buffer_seconds: int = DEFAULT_LATENCY_SECONDS,
    bar_provider=None,
    meeting_trigger_levels: dict[str, float] | None = None,
) -> dict[str, Any]:
    now = as_of or now_london()
    scanner = OpenScanner(
        latency_buffer_seconds=latency_buffer_seconds,
        meeting_trigger_levels=meeting_trigger_levels,
    )
    provider = bar_provider or FakeDelayedBars()
    candidates = scanner.scan(session, bar_provider=provider, as_of=now)
    result = scan_result_envelope(
        candidates, as_of=now, latency_buffer_seconds=latency_buffer_seconds
    )
    result["started_by"] = started_by
    result["cli"] = "python -m varma.routines.run_open_scanner"
    result["daemon"] = False
    result["places_orders"] = False
    result["is_trade"] = False
    result["is_live_approval"] = False
    result["trading_mode"] = "LIVE_BLOCKED"
    return result


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        print(describe_open_scanner())
        print("Now Europe/London:", now_london().isoformat())
        print("Daemon: False")
        print("Places orders: False")
        result = run_open_scanner(session, started_by="cli")
        print("candidate_count:", result["candidate_count"])
        print("window_start:", result["window_start"])
        print("window_end:", result["window_end"])
        print("as_of:", result["as_of"])
        print("live_blocked:", result["live_blocked"])
        for row in result["candidates"]:
            print(
                f"  {row['symbol']} {row['side']} entry={row['entry_price']} "
                f"stop={row['stop']} target={row['target']} "
                f"gbp={row['gbp_notional']} at {row['trigger_time']}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
