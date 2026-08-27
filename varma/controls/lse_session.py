"""LSE names on allow-list E cannot fill until Board picks a session rule.

SHEL.L, AZN.L, ULVR.L stay on the LSE form already used by this repo.
Do not invent US listings. Do not rewrite Board Addendum C: flatten remains
US regular cash close, not London cash close 16:30.

Until the Board chooses flatten-at-US-close vs LSE cash end 16:30, these
three are fail-closed. Distinct deny: LSE_SESSION_RULE_UNSET. They must not
silently start at Grand Opening PAPER. US names still wait on Hari's
explicit Grand Opening. Employees cannot write this lock.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.addendum_c import FLATTEN_AT, FLATTEN_NOT_AT
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


def lse_hold_blocks(session: Session, symbol: str) -> bool:
    if symbol not in LSE_HOLD_SYMBOLS:
        return False
    return lse_session_rule_is_unset(session)


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
        "fail_closed": True,
        "cannot_silently_fill_at_grand_opening": True,
        "addendum_c_not_rewritten": True,
        "flatten_at": FLATTEN_AT,
        "flatten_not_at": FLATTEN_NOT_AT,
        "split_flatten_clocks": False,
        "london_cash_close_is_not_flatten_default": True,
        "us_names_wait_on_grand_opening": True,
        "paper_execution_stays": "CLOSED",
        "note": (
            "SHEL.L, AZN.L, ULVR.L cannot fill until the Board picks a session "
            "rule (Addendum C flatten-at-US-close vs LSE cash end 16:30). "
            "Fail-closed. Distinct hold LSE_SESSION_RULE_UNSET. Do not invent "
            "US listings. Do not rewrite Addendum C. US names still wait on "
            "Hari Grand Opening PAPER."
        ),
    }
