"""LSE names on allow-list E: Board Addendum K session rule.

SHEL.L, AZN.L, ULVR.L stay on the LSE form already used by this repo.
Do not invent US listings. Do not rewrite Board Addendum C: flatten remains
US regular cash close, not London cash close 16:30.

Board Addendum K 2026-09-03 (Hari explicit yes): after London cash market
shuts, deny paper orders in those three names only. While London cash is
open they remain on Addendum E (subject to paper OPEN/CLOSED, limits, kill switch).
US names are not denied by K. LIVE stays blocked. Not a live opening.

If the session-rule setting is missing, fail closed with distinct deny
LSE_SESSION_RULE_UNSET so the three cannot silently fill. Employees cannot
write this lock.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import as_london, now_london
from varma.controls.addendum_c import FLATTEN_AT, FLATTEN_NOT_AT, london_cash_close_london
from varma.controls.addendum_k import (
    ADDENDUM_K_LABEL,
    ADDENDUM_K_LSE_SYMBOLS,
    ADDENDUM_K_SET_BY,
    ADDENDUM_K_SETTINGS,
    ADDENDUM_K_WRITE_FIELDS,
    INVENTED_US_LISTINGS,
    LSE_AFTER_LONDON_CASH_CLOSE_REASON,
    LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE,
    LSE_SESSION_RULE_KEY,
    addendum_k_public,
)
from varma.db.models import ControlSetting

LSE_HOLD_LABEL = ADDENDUM_K_LABEL
LSE_HOLD_SET_BY = ADDENDUM_K_SET_BY

LSE_HOLD_SYMBOLS: tuple[str, ...] = ADDENDUM_K_LSE_SYMBOLS

LSE_SESSION_RULE_UNSET = "UNSET"
LSE_SESSION_RULE_REASON = "LSE_SESSION_RULE_UNSET"

LSE_HOLD_SETTINGS = ADDENDUM_K_SETTINGS
LSE_WRITE_FIELDS = ADDENDUM_K_WRITE_FIELDS


def lse_session_rule_value(session: Session) -> str:
    """Board-picked rule, or UNSET if missing. Fail closed on empty."""
    row = session.get(ControlSetting, LSE_SESSION_RULE_KEY)
    if row is None or row.value in (None, ""):
        return LSE_SESSION_RULE_UNSET
    return str(row.value).upper()


def lse_session_rule_is_unset(session: Session) -> bool:
    """True when the Board K rule is not seeded. Missing/unknown is UNSET."""
    return lse_session_rule_value(session) != LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE


def london_cash_is_shut(at: datetime | None = None) -> bool:
    """True at or after 16:30 Europe/London on that London calendar day."""
    now = as_london(at or now_london())
    return now >= london_cash_close_london(now)


def lse_hold_blocks(session: Session, symbol: str, at: datetime | None = None) -> bool:
    """Session-rule unit. Does not consult Addendum I CLOSED.

    US names are never blocked by K. LSE three: UNSET fail-closed all day;
    Board K blocks only after London cash shut.
    """
    if symbol not in LSE_HOLD_SYMBOLS:
        return False
    if lse_session_rule_is_unset(session):
        return True
    return london_cash_is_shut(at)


def lse_session_public(session: Session | None = None) -> dict[str, Any]:
    unset = True if session is None else lse_session_rule_is_unset(session)
    rule = (
        LSE_SESSION_RULE_UNSET
        if unset
        else LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE
    )
    return {
        "label": LSE_HOLD_LABEL,
        "addendum_k": ADDENDUM_K_LABEL,
        "board_set": True,
        "hari_explicit_yes": not unset,
        "values_invented": False,
        "employees_cannot_write": True,
        "ceo_cannot_write": True,
        "symbols": list(LSE_HOLD_SYMBOLS),
        "invented_us_listings": False,
        "invented_us_symbols_forbidden": list(INVENTED_US_LISTINGS),
        "session_rule": rule,
        "session_rule_unset": unset,
        "deny_reason": (
            LSE_SESSION_RULE_REASON if unset else LSE_AFTER_LONDON_CASH_CLOSE_REASON
        ),
        "deny_reason_after_london_cash_close": LSE_AFTER_LONDON_CASH_CLOSE_REASON,
        "deny_reason_if_unset": LSE_SESSION_RULE_REASON,
        "fail_closed_if_unset": True,
        "cannot_silently_fill_if_unset": True,
        "addendum_c_not_rewritten": True,
        "flatten_at": FLATTEN_AT,
        "flatten_not_at": FLATTEN_NOT_AT,
        "split_flatten_clocks": False,
        "london_cash_close_is_not_flatten": True,
        "us_names_not_denied_by_k": True,
        "us_names_wait_on_grand_opening": True,
        "paper_execution_stays": "CLOSED",
        "not_grand_opening": True,
        "letter_exists_outside_repo": True,
        "note": addendum_k_public()["note"]
        if not unset
        else (
            "lse_session_rule is missing or not Board Addendum K. Fail-closed "
            "LSE_SESSION_RULE_UNSET on SHEL.L, AZN.L, ULVR.L. Do not invent US "
            "listings. Do not rewrite Addendum C."
        ),
    }
