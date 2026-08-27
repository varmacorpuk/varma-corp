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


def london_day(dt: datetime | None = None) -> str:
    """Calendar day in Europe/London (ISO date). Used for daily paper P&L and order caps."""
    return as_london(dt or now_london()).date().isoformat()


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
        "Internal staff artefact only. No 07:30 diary invite to the Board Member. "
        "Must not email or calendar-invite Hari. Not a trade. Not LIVE approval. "
        "Not a daemon. Employees cannot start LIVE from a meeting."
    )


def describe_paper_session() -> str:
    return (
        "Board Addendum C 2026-08-27: paper desk open from UK cash open "
        "(08:00 Europe/London weekdays) through US regular cash close "
        "(16:00 America/New_York converted onto the Europe/London clock — "
        "not hardcoded 21:00). Trade UK open, US open, and other regular cash "
        "opens inside that window for allow-listed names. No overnight. "
        "No US after-hours. No extended hours unless later Board-approved."
    )


def describe_company_backup() -> str:
    return (
        "Board Addendum J 2026-08-27: daily Europe/London backup after US close "
        "/ end of London evening. On-demand via Board Member right-hand panel, "
        "API, or documented CLI. This slice does not start a daemon scheduler. "
        "Encrypted artefact stays in the database (same StoragePort). Not in "
        "GitHub. Not on the Board Member laptop. Technology (Owen Blake · "
        "Technology) owns the job and cannot write trading_mode, allow-list, "
        "or open the firm. Included: paper ledger, evidence, organisational "
        "memory, control snapshots. Excluded: secrets, live broker credentials "
        "(which must not exist yet). Employees including the CEO cannot download "
        "secrets. Does not fill orders."
    )


def describe_flatten_us_close() -> str:
    return (
        "Board Addendum C 2026-08-27: flatten ALL paper before US regular cash "
        "close. Do NOT flatten at London cash close (16:30 Europe/London). "
        "On-demand via Board Member right-hand panel, API, or documented CLI. "
        "This slice does not start a daemon scheduler. Flatten uses the internal "
        "paper fill simulator, not a broker. Empty allow-list still denies new "
        "orders; flatten of existing paper is session hygiene (no-op if none). "
        "GET /observability does not flatten. Board Addendum I: do not run "
        "flatten-as-if-there-were-positions while PAPER execution is CLOSED."
    )
