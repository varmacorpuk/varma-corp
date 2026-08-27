"""Independent verification of the intelligence brief. Employee 'done' is not proof."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from varma.clock import as_london, now_london
from varma.config import get_settings

REQUIRED_FIELDS = (
    "headline",
    "summary",
    "items",
    "watchlist_snapshot",
    "freshness_flag",
    "produced_at",
    "as_of",
    "employee_id",
    "skill_name",
    "skill_version",
    "trading_mode_at_production",
    "no_execution_authority",
    "cost_units",
)


def _parse(ts: str | datetime | None) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return as_london(ts)
    try:
        return as_london(datetime.fromisoformat(ts.replace("Z", "+00:00")))
    except ValueError:
        return None


def expected_freshness(items: list[dict[str, Any]], prices: list[dict[str, Any]]) -> str:
    settings = get_settings()
    now = now_london()
    flags: list[str] = []
    for it in items:
        dt = _parse(it.get("published_at"))
        if dt is None:
            flags.append("STALE")
            continue
        hours = (now - dt).total_seconds() / 3600
        flags.append("FRESH" if hours <= settings.temporary_news_fresh_hours else "STALE")
    for p in prices:
        dt = _parse(p.get("observed_at"))
        if dt is None:
            flags.append("STALE")
            continue
        hours = (now - dt).total_seconds() / 3600
        flags.append("FRESH" if hours <= settings.temporary_price_fresh_hours else "STALE")
    if not flags:
        return "STALE"
    if all(f == "FRESH" for f in flags):
        return "FRESH"
    if all(f == "STALE" for f in flags):
        return "STALE"
    return "MIXED"


def verify_brief(artefact: dict[str, Any], *, cost_cap: int) -> dict[str, Any]:
    notes: list[str] = []
    passed = True

    if not artefact:
        return {"passed": False, "notes": ["artefact missing"]}

    for field in REQUIRED_FIELDS:
        if artefact.get(field) in (None, "", []):
            passed = False
            notes.append(f"missing required field: {field}")

    items = artefact.get("items") or []
    for i, item in enumerate(items):
        if not item.get("material"):
            continue
        if not item.get("source"):
            passed = False
            notes.append(f"material claim {i} missing source")
        if not item.get("published_at"):
            passed = False
            notes.append(f"material claim {i} missing timestamp")

    prices = artefact.get("watchlist_snapshot") or []
    expected = expected_freshness(items, prices)
    actual = artefact.get("freshness_flag")
    if actual != expected:
        passed = False
        notes.append(f"freshness_flag {actual} does not match independent check {expected}")

    cost = int(artefact.get("cost_units") or 0)
    if cost > cost_cap:
        passed = False
        notes.append(f"cost {cost} exceeds TEMPORARY cap {cost_cap}")

    if artefact.get("no_execution_authority") is not True:
        passed = False
        notes.append("brief must declare no_execution_authority")

    if artefact.get("trading_mode_at_production") == "LIVE":
        passed = False
        notes.append("brief produced while trading_mode LIVE is not accepted in this slice")

    if passed:
        notes.append("independent verification passed")
    return {"passed": passed, "notes": notes, "expected_freshness": expected}
