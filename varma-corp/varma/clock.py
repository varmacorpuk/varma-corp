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


def describe_0630_weekday_routine() -> str:
    return (
        "Weekdays 06:30 Europe/London. Output due before the 07:30 "
        "Europe/London company meeting (parameterisable; Documents 02, 09, 18). "
        "On-demand runs use the same skill. This slice does not start a "
        "daemon scheduler; invoke via CLI or API."
    )
