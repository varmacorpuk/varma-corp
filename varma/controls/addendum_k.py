"""Board Addendum K 2026-09-03.

Hari explicit yes. After London cash market shuts, deny paper orders in
SHEL.L, AZN.L, ULVR.L only. Concentrate on the US seven until US flatten.

Does not rewrite Board Addendum C: desk remains UK cash open through US
regular cash close. Flatten remains US regular cash close. London cash
close is NOT the flatten. No overnight.

While London cash is open, those three remain on Addendum E (subject to
CLOSED, limits, kill switch). Dual-listed US lines SHEL / AZN / ULVR are
not on the allow-list. Do not invent them.

PAPER opening is a separate Board control (Addendum I). This is not live
opening. No real broker. trading_mode stays LIVE_BLOCKED.

The Addendum K letter exists outside the repo. Chat is not the record.
"""

from __future__ import annotations

from typing import Any

from varma.controls.addendum_c import FLATTEN_AT, FLATTEN_NOT_AT

ADDENDUM_K_LABEL = "Board Addendum K 2026-09-03"
ADDENDUM_K_SET_BY = "board-member"

LSE_SESSION_RULE_KEY = "lse_session_rule"
LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE = "DENY_LSE_AFTER_LONDON_CASH_CLOSE"
LSE_AFTER_LONDON_CASH_CLOSE_REASON = "LSE_AFTER_LONDON_CASH_CLOSE"

# LSE form already used by Addendum E. Dual-listed US lines are not on the list.
ADDENDUM_K_LSE_SYMBOLS: tuple[str, ...] = ("SHEL.L", "AZN.L", "ULVR.L")
INVENTED_US_LISTINGS: tuple[str, ...] = ("SHEL", "AZN", "ULVR")

# Board-set control-table row. Fail closed (UNSET hold) if missing.
ADDENDUM_K_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (LSE_SESSION_RULE_KEY, LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE, "session"),
)

ADDENDUM_K_WRITE_FIELDS = frozenset(
    {
        "addendum_k",
        LSE_SESSION_RULE_KEY,
        "lse_session",
        "lse_flatten",
        "london_cash_close_flatten",
    }
)


def addendum_k_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_K_LABEL,
        "set_by": ADDENDUM_K_SET_BY,
        "board_set": True,
        "hari_explicit_yes": True,
        "values_invented": False,
        "letter_exists_outside_repo": True,
        "chat_is_not_the_record": True,
        "session_rule": LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE,
        "deny_reason_after_london_cash_close": LSE_AFTER_LONDON_CASH_CLOSE_REASON,
        "symbols": list(ADDENDUM_K_LSE_SYMBOLS),
        "invented_us_listings": False,
        "invented_us_symbols_forbidden": list(INVENTED_US_LISTINGS),
        "while_london_cash_open_remain_on_allow_list_e": True,
        "after_london_cash_close_deny_lse_three_only": True,
        "us_names_not_denied_by_k": True,
        "addendum_c_not_rewritten": True,
        "desk_uk_open_through_us_close": True,
        "flatten_at": FLATTEN_AT,
        "flatten_not_at": FLATTEN_NOT_AT,
        "london_cash_close_is_not_flatten": True,
        "split_flatten_clocks": False,
        "overnight_holds": False,
        "paper_execution_stays": "OPEN_OR_CLOSED_BY_ADDENDUM_I",
        "not_grand_opening": False,
        "not_grand_opening_live": True,
        "does_not_fill": False,
        "does_not_open_live": True,
        "trading_mode_stays": "LIVE_BLOCKED",
        "employees_cannot_write": True,
        "ceo_cannot_write": True,
        "pr_21_leftover_draft_supersede_after_merge": True,
        "note": (
            "Board Addendum K 2026-09-03 (Hari explicit yes). After London cash "
            "shuts, deny paper orders in SHEL.L, AZN.L, ULVR.L only. Concentrate "
            "on the US seven until US flatten. Desk still UK cash open through US "
            "cash close. Flatten still at US regular cash close. London close is "
            "not the flatten. Dual-listed US lines are not on the allow-list. "
            "Addendum I is the two-opening rule. LIVE_BLOCKED. The letter "
            "exists outside the repo. Chat is not the record."
        ),
    }
