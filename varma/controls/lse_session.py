"""LSE names: deny after London cash close until Board picks a session rule.

SHEL.L, AZN.L, ULVR.L stay on the LSE form already used by this repo.
Do not invent US listings. Do not rewrite Board Addendum C: flatten remains
US regular cash close, not London cash close 16:30. Split flatten clocks
(LSE 16:30 vs US close) is a Board Addendum C change — not a default here.

Until the Board chooses, these three deny after London cash close
(deny-until-resolved). Distinct deny: LSE_SESSION_RULE_UNSET. Before 16:30
Europe/London, they wait on PAPER_EXECUTION_CLOSED like US names. They must
not fill in the London-close-to-US-close window without a Board rule.
US names still wait on Hari's explicit Grand Opening. Employees cannot write
this lock.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import as_london, now_london
from varma.controls.addendum_c import FLATTEN_AT, FLATTEN_NOT_AT, london_cash_close_london
from varma.db.models import ControlSetting

LSE_HOLD_LABEL = "LSE session rule unset (pending Board Addendum C choice)"
LSE_HOLD_SET_BY = "board-member"

LSE_HOLD_SYMBOLS: tuple[str, ...] = ("SHEL.L", "AZN.L", "ULVR.L")
# Must not appear on the allow-list. Do not invent US listings for these names.
INVENTED_US_LISTINGS: tuple[str, ...] = ("SHEL", "AZN", "ULVR")

LSE_SESSION_RULE_KEY = "lse_session_rule"
LSE_SESSION_RULE_UNSET = "UNSET"
LSE_SESSION_RULE_REASON = "LSE_SESSION_RULE_UNSET"

LSE_HOLD_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (LSE_SESSION_RULE_KEY, LSE_SESSION_RULE_UNSET, "flag"),
)

LSE_WRITE_FIELDS = frozenset(
    {
        LSE_SESSION_RULE_KEY,
        "lse_session",
        "lse_flatten",
        "london_cash_close_flatten",
    }
)


def lse_session_rule_is_unset(session: Session) -> bool:
    """Fail closed. Missing or anything other than a Board-picked rule is UNSET."""
    row = session.get(ControlSetting, LSE_SESSION_RULE_KEY)
    if row is None or row.value in (None, ""):
        return True
    return str(row.value).upper() == LSE_SESSION_RULE_UNSET


def lse_hold_blocks(session: Session, symbol: str, at: datetime | None = None) -> bool:
    """Deny SHEL.L / AZN.L / ULVR.L after London cash close while the rule is UNSET.

    Not an all-day hold. Not a flatten-at-16:30 default.
    """
    if symbol not in LSE_HOLD_SYMBOLS:
        return False
    if not lse_session_rule_is_unset(session):
        return False
    now = as_london(at or now_london())
    return now >= london_cash_close_london(now)


def lse_session_public(session: Session | None = None) -> dict[str, Any]:
    unset = True if session is None else lse_session_rule_is_unset(session)
    return {
        "label": LSE_HOLD_LABEL,
        "board_set": True,
        "values_invented": False,
        "employees_cannot_write": True,
        "ceo_cannot_write": True,
        "symbols": list(LSE_HOLD_SYMBOLS),
        "invented_us_listings": False,
        "invented_us_symbols_forbidden": list(INVENTED_US_LISTINGS),
        "session_rule": LSE_SESSION_RULE_UNSET if unset else "SET",
        "session_rule_unset": unset,
        "deny_reason": LSE_SESSION_RULE_REASON,
        "deny_after_london_cash_close": True,
        "deny_until_resolved": True,
        "deny_all_day": False,
        "fail_closed": True,
        "cannot_silently_fill_after_london_cash_close": True,
        "addendum_c_not_rewritten": True,
        "flatten_at": FLATTEN_AT,
        "flatten_not_at": FLATTEN_NOT_AT,
        "split_flatten_clocks": False,
        "london_cash_close_is_not_flatten_default": True,
        "us_names_wait_on_grand_opening": True,
        "paper_execution_stays": "CLOSED",
        "note": (
            "Until the Board picks a session rule, SHEL.L, AZN.L, ULVR.L deny "
            "after London cash close (deny-until-resolved, LSE_SESSION_RULE_UNSET). "
            "Not an all-day hold. Not a split flatten-clock default (Addendum C "
            "stays flatten-at-US-close, not 16:30). Do not invent US listings. "
            "Before 16:30 they wait on PAPER_EXECUTION_CLOSED like US names. "
            "US names still wait on Hari Grand Opening PAPER."
        ),
    }
