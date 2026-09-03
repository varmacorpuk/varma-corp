"""On-demand US-open PAPER scanner. No daemon.

Usage:
    python -m varma.routines.run_us_open_scanner
    python -m varma.routines.run_us_open_scanner --submit

Scans the final 15-name US book from New York open through the first 32
minutes. Accepts frozen 14:00 plan levels. Completed 1m/5m bars only.
Optional submit goes through ControlEngine → internal simulator.
LIVE stays blocked. Never writes the canonical runtime ledger unless that
path is already the configured database_url.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from varma.clock import LONDON, now_london
from varma.config import CANONICAL_PAPER_OPEN_DB, get_settings
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.scanner.opening import run_us_open_scanner
from varma.scanner.plan import freeze_opening_plan


def run_us_open_scan(
    session: Session,
    *,
    plan: list[dict] | None = None,
    at=None,
    submit: bool = False,
    max_concurrent_positions: int = 1,
    started_by: str = "cli",
) -> dict:
    levels = plan or []
    frozen = freeze_opening_plan(levels, as_of=at or now_london())
    return run_us_open_scanner(
        session,
        plan=frozen,
        at=at,
        submit=submit,
        max_concurrent_positions=max_concurrent_positions,
        started_by=started_by,
    )


def _parse_london_at(value: str | None):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=LONDON)
    return parsed.astimezone(LONDON)


def _load_plan(path: str | None) -> list[dict]:
    if not path:
        return []
    raw = Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if isinstance(payload, list):
        return payload
    return list(payload.get("levels") or [])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "On-demand US-open PAPER scanner. Completed bars only. "
            "Internal simulator only. LIVE and BROKER_PAPER stay UNLOADED."
        )
    )
    parser.add_argument("--plan", default=None, help="JSON file of frozen 14:00 levels")
    parser.add_argument("--at", default=None, help="ISO datetime (evaluation clock)")
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit the first eligible candidate through the paper path",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=1,
        help="Scanner proposal default (not a ControlEngine lock)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLite URL. Does not create the canonical runtime ledger.",
    )
    args = parser.parse_args()

    url = args.database_url
    if url:
        canonical = str(CANONICAL_PAPER_OPEN_DB)
        if canonical in url and not CANONICAL_PAPER_OPEN_DB.is_file():
            raise RuntimeError("REFUSE_CREATE_CANONICAL_PAPER_OPEN_DB")
        init_db(url, reset=False)
        factory = get_session_factory(url, reset=False)
    else:
        # Default configured book. Do not point tests at the canonical file.
        settings = get_settings()
        init_db(settings.database_url, reset=False)
        factory = get_session_factory(settings.database_url, reset=False)
    session = factory()
    try:
        seed_if_empty(session)
        result = run_us_open_scan(
            session,
            plan=_load_plan(args.plan),
            at=_parse_london_at(args.at),
            submit=bool(args.submit),
            max_concurrent_positions=int(args.max_concurrent),
            started_by="cli",
        )
        print("US-open PAPER scanner")
        print("universe:", result["universe_count"])
        print("in_scan_window:", result["in_scan_window"])
        print("candidates:", len(result["candidates"]))
        print("submit:", result["submit"])
        print("trading_mode:", result["trading_mode"])
        print("live_fills:", result["live_fills"])
        print("ai_called:", result["ai_called"])
        print("daemon:", result["daemon"])
        for row in result["evaluations"]:
            print(f"  {row['symbol']}: candidate={row['candidate']} reason={row['reason']}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
