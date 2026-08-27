"""Company clock. Timezone is Europe/London (Documents 02, 08, 14, 18)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def now_london() -> datetime:
    return datetime.now(LONDON)


def as_london(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LONDON)
    return dt.astimezone(LONDON)


def is_weekday(dt: datetime | None = None) -> bool:
    d = as_london(dt or now_london())
    return d.weekday() < 5


def describe_nightly_memory_filter() -> str:
    return (
        "Nightly Europe/London working-context filter (Document 08). "
        "On-demand via Board Member right-hand panel, API, or documented CLI. "
        "This slice does not start a daemon scheduler. "
        "Working context is archived in the database. Evidence is append-only "
        "and is never deleted. The filter does not write controls, trading_mode, "
        "allow-list, or permissions."
    )


def describe_0630_weekday_routine() -> str:
    return (
        "Weekdays 06:30 Europe/London. Output due before the 07:30 "
        "Europe/London company meeting (parameterisable; Documents 02, 09, 18). "
        "On-demand runs use the same skill. This slice does not start a "
        "daemon scheduler; invoke via the Board Member right-hand panel, API, or CLI."
    )


def describe_0730_company_meeting() -> str:
    return (
        "07:30 Europe/London company meeting (Documents 02, 09, 18). "
        "On-demand via Board Member right-hand panel, API, or documented CLI. "
        "Writes a meeting artefact to the database from existing handoffs "
        "(MI brief, CEO pack, Challenge SAMPLE, Risk DENY). "
        "Not a trade. Not LIVE approval. Not a daemon. "
        "Employees cannot start LIVE from a meeting."
    )
