"""Board Addendum C 2026-08-27.

Hari asked the Founding Architect to set these as Board-set control-table
values. They are labelled Board Addendum C 2026-08-27. They are not invented
silent defaults.

Paper desk is open from UK cash open through US regular cash close on the
Europe/London company clock. Flatten ALL paper before US regular cash close.
Do NOT flatten at London cash close. No overnight. No US after-hours.
No extended hours unless later Board-approved.

trading_mode stays LIVE_BLOCKED. PAPER allow-list is Board Addendum E.
Unknown tickers still deny. Flatten of existing paper is session hygiene and
does not require allow-list membership (no-op when there are no positions).
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from varma.clock import LONDON, as_london, is_weekday, now_london

ADDENDUM_C_LABEL = "Board Addendum C 2026-08-27"
ADDENDUM_C_SET_BY = "board-member"

NEW_YORK = ZoneInfo("America/New_York")
COMPANY_CLOCK = "Europe/London"
UK_CASH_OPEN_TZ = "Europe/London"
US_REGULAR_CASH_CLOSE_TZ = "America/New_York"

UK_CASH_OPEN = time(8, 0)  # Europe/London weekdays
US_REGULAR_CASH_CLOSE = time(16, 0)  # America/New_York regular cash session
LONDON_CASH_CLOSE = time(16, 30)  # Europe/London — still INSIDE the paper desk window

FLATTEN_AT = "US_REGULAR_CASH_CLOSE"
FLATTEN_NOT_AT = "LONDON_CASH_CLOSE"
OVERNIGHT_HOLDS = False
US_AFTER_HOURS = False
EXTENDED_HOURS = False
DAEMON = False

# key, value (string), unit — Board-set control-table rows
ADDENDUM_C_SETTINGS: tuple[tuple[str, str, str], ...] = (
    ("paper_desk_uk_cash_open", "08:00", "Europe/London"),
    ("paper_desk_us_regular_cash_close", "16:00", "America/New_York"),
    ("paper_desk_company_clock", COMPANY_CLOCK, "tz"),
    ("paper_flatten_at", FLATTEN_AT, "session"),
    ("paper_flatten_not_at", FLATTEN_NOT_AT, "session"),
    ("paper_overnight_holds", "false", "flag"),
    ("paper_us_after_hours", "false", "flag"),
    ("paper_extended_hours", "false", "flag"),
)


def uk_cash_open_london(dt: datetime | None = None) -> datetime:
    """08:00 Europe/London on the London calendar day of dt."""
    d = as_london(dt or now_london())
    return datetime(d.year, d.month, d.day, UK_CASH_OPEN.hour, UK_CASH_OPEN.minute, tzinfo=LONDON)


def us_regular_cash_close_london(dt: datetime | None = None) -> datetime:
    """16:00 America/New_York on the same London calendar date, converted to Europe/London.

    Convert. Do not hardcode 21:00 — DST edge weeks differ.
    """
    d = as_london(dt or now_london())
    ny_close = datetime(
        d.year,
        d.month,
        d.day,
        US_REGULAR_CASH_CLOSE.hour,
        US_REGULAR_CASH_CLOSE.minute,
        tzinfo=NEW_YORK,
    )
    return ny_close.astimezone(LONDON)


def london_cash_close_london(dt: datetime | None = None) -> datetime:
    """16:30 Europe/London. Documented only as NOT the flatten time."""
    d = as_london(dt or now_london())
    return datetime(
        d.year,
        d.month,
        d.day,
        LONDON_CASH_CLOSE.hour,
        LONDON_CASH_CLOSE.minute,
        tzinfo=LONDON,
    )


def paper_session_status(dt: datetime | None = None) -> dict[str, Any]:
    """Desk open from UK cash open through (not including) US regular cash close."""
    now = as_london(dt or now_london())
    open_at = uk_cash_open_london(now)
    close_at = us_regular_cash_close_london(now)
    london_close = london_cash_close_london(now)
    weekday = is_weekday(now)
    inside = weekday and open_at <= now < close_at
    before_open = weekday and now < open_at
    after_us_close = weekday and now >= close_at
    weekend = not weekday
    overnight = weekend or before_open or after_us_close
    closed_reason = None
    closed_detail = None
    if inside:
        pass
    elif weekend:
        closed_reason = "PAPER_SESSION_CLOSED"
        closed_detail = "weekend"
    elif before_open:
        closed_reason = "PAPER_SESSION_CLOSED"
        closed_detail = "before_uk_cash_open"
    else:
        closed_reason = "PAPER_SESSION_CLOSED"
        closed_detail = "after_us_regular_cash_close"
    return {
        "open": inside,
        "weekday": weekday,
        "overnight": overnight,
        "us_after_hours": False,
        "extended_hours": False,
        "now_london": now.isoformat(),
        "uk_cash_open_london": open_at.isoformat(),
        "us_regular_cash_close_london": close_at.isoformat(),
        "london_cash_close_london": london_close.isoformat(),
        "london_cash_close_still_inside": inside and now >= london_close and now < close_at,
        "flatten_at": FLATTEN_AT,
        "flatten_not_at": FLATTEN_NOT_AT,
        "split_flatten_clocks": True,
        "lse_flatten_at": "LONDON_CLOSING_AUCTION",
        "closed_reason": closed_reason,
        "closed_detail": closed_detail,
        "timezone": COMPANY_CLOCK,
        "us_close_converted_not_hardcoded": True,
    }


def paper_desk_open(dt: datetime | None = None) -> bool:
    return bool(paper_session_status(dt)["open"])


def addendum_c_public(dt: datetime | None = None) -> dict[str, Any]:
    status = paper_session_status(dt)
    return {
        "label": ADDENDUM_C_LABEL,
        "set_by": ADDENDUM_C_SET_BY,
        "board_set": True,
        "values_invented": False,
        "company_clock": COMPANY_CLOCK,
        "uk_cash_open": "08:00",
        "uk_cash_open_tz": UK_CASH_OPEN_TZ,
        "us_regular_cash_close": "16:00",
        "us_regular_cash_close_tz": US_REGULAR_CASH_CLOSE_TZ,
        "flatten_at": FLATTEN_AT,
        "flatten_not_at": FLATTEN_NOT_AT,
        "flatten_at_london_cash_close": False,
        "split_flatten_clocks": True,
        "lse_flatten_at": "LONDON_CLOSING_AUCTION",
        "overnight_holds": OVERNIGHT_HOLDS,
        "us_after_hours": US_AFTER_HOURS,
        "extended_hours": EXTENDED_HOURS,
        "daemon": DAEMON,
        "empty_allow_list_denies_new_orders": False,
        "unknown_tickers_deny": True,
        "flatten_does_not_require_allow_list": True,
        "trading_mode_stays": "LIVE_BLOCKED",
        "cli": "python -m varma.routines.run_flatten_us_close",
        "method": "POST",
        "path": "/routines/run-flatten-us-close",
        "get_observability_flattens": False,
        "session": status,
    }
