"""CEO desk rule 02F: venue-aware bound flatten clocks.

Deterministic ControlEngine binding. Not AI. Not a Board tap. Not a Hari card.

SHEL.L, AZN.L, ULVR.L flatten in the London closing auction 16:30–16:35
Europe/London. That auction exit is bound to the opening buy and cannot be
dropped independently. Do not hold those three to New York.

US allow-list names (NASDAQ and NYSE) flatten at US regular cash close.
The firm desk still runs until then. Overnight off. LIVE_BLOCKED.
paper_execution stays OPEN. Do not load LIVE or BROKER_PAPER.

Risk DENY 02: 02F was unbound (one US-close flatten for every name,
split_flatten_clocks false). This module is the bound engine state Risk
reads to re-clear.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from varma.clock import LONDON, as_london, now_london
from varma.controls.addendum_c import (
    FLATTEN_AT as US_FLATTEN_AT,
    london_cash_close_london,
)
from varma.controls.addendum_e import ADDENDUM_E_INSTRUMENTS, ADDENDUM_E_VENUES
from varma.controls.addendum_k import ADDENDUM_K_LSE_SYMBOLS

RISK_02F = "02F"
RISK_02F_LABEL = "LSE_BOUND_LONDON_AUCTION_EXIT"
CEO_DESK_RULE = "CEO_DESK_RULE_02F"

LSE_FLATTEN_AT = "LONDON_CLOSING_AUCTION"
LSE_FLATTEN_WINDOW = "16:30-16:35"
LSE_FLATTEN_WINDOW_TZ = "Europe/London"
LONDON_CLOSING_AUCTION_END = time(16, 35)

SPLIT_FLATTEN_CLOCKS = True
CANNOT_DROP_BOUND_EXIT_INDEPENDENTLY = True
CANNOT_HOLD_LSE_TO_NEW_YORK = True
FIRM_DAY_RUNS_TO_NY_CLOSE = True

VENUE_LSE = "LSE"
VENUE_US = "US"
US_LISTING_VENUES = frozenset({"NASDAQ", "NYSE"})

LSE_SYMBOLS: tuple[str, ...] = ADDENDUM_K_LSE_SYMBOLS
US_SYMBOLS: tuple[str, ...] = tuple(
    symbol for symbol, venue in ADDENDUM_E_INSTRUMENTS if venue in US_LISTING_VENUES
)


def london_closing_auction_end_london(dt: datetime | None = None) -> datetime:
    """16:35 Europe/London — end of the LSE closing auction window."""
    d = as_london(dt or now_london())
    return datetime(
        d.year,
        d.month,
        d.day,
        LONDON_CLOSING_AUCTION_END.hour,
        LONDON_CLOSING_AUCTION_END.minute,
        tzinfo=LONDON,
    )


def in_london_closing_auction(dt: datetime | None = None) -> bool:
    """True during 16:30–16:35 Europe/London (end exclusive)."""
    now = as_london(dt or now_london())
    return london_cash_close_london(now) <= now < london_closing_auction_end_london(now)


def listing_venue(symbol: str) -> str:
    """Addendum E venue. Unknown `.L` names are LSE; do not invent US listings."""
    known = ADDENDUM_E_VENUES.get(symbol)
    if known:
        return known
    if symbol.endswith(".L"):
        return VENUE_LSE
    return ""


def is_lse_name(symbol: str) -> bool:
    return listing_venue(symbol) == VENUE_LSE or symbol in LSE_SYMBOLS


def is_us_name(symbol: str) -> bool:
    return listing_venue(symbol) in US_LISTING_VENUES


def bound_flatten_at(symbol: str) -> str:
    """Session-exit clock bound to the opening buy. Not a detachable auction sell."""
    if is_lse_name(symbol):
        return LSE_FLATTEN_AT
    return US_FLATTEN_AT


def cannot_drop_bound_exit_independently(symbol: str) -> bool:
    """True for every bound session exit. LSE cannot be dropped while the buy stands."""
    return CANNOT_DROP_BOUND_EXIT_INDEPENDENTLY and bool(symbol)


def may_drop_bound_exit(_symbol: str) -> bool:
    """Unbound auction sells are not permitted. 02F is bound in the engine."""
    return False


def matches_flatten_scope(symbol: str, venue_scope: str) -> bool:
    if venue_scope == VENUE_LSE:
        return is_lse_name(symbol)
    if venue_scope == VENUE_US:
        return is_us_name(symbol)
    return False


def bound_session_exit(symbol: str) -> dict[str, Any]:
    clock = bound_flatten_at(symbol)
    lse = is_lse_name(symbol)
    return {
        "symbol": symbol,
        "venue": listing_venue(symbol),
        "bound": True,
        "risk_02f": RISK_02F,
        "risk_02f_bound": True,
        "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
        "bound_flatten_at": clock,
        "cannot_drop_independently": cannot_drop_bound_exit_independently(symbol),
        "may_drop_independently": may_drop_bound_exit(symbol),
        "cannot_hold_lse_to_new_york": lse,
        "lse_flatten_at": LSE_FLATTEN_AT if lse else None,
        "us_flatten_at": US_FLATTEN_AT if not lse else None,
        "source": CEO_DESK_RULE,
        "deterministic": True,
        "ai_enforced": False,
    }


def flatten_fill_note(symbol: str) -> str:
    return f"BOUND_FLATTEN:{bound_flatten_at(symbol)};RISK_02F_BOUND;CANNOT_DROP_INDEPENDENTLY"


def risk_02f_public() -> dict[str, Any]:
    """Engine-readable 02F state. Risk re-clears from this, not from chat."""
    return {
        "id": RISK_02F,
        "label": RISK_02F_LABEL,
        "bound": True,
        "readable_from_engine": True,
        "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
        "lse_flatten_at": LSE_FLATTEN_AT,
        "lse_flatten_window": LSE_FLATTEN_WINDOW,
        "lse_flatten_window_tz": LSE_FLATTEN_WINDOW_TZ,
        "lse_symbols": list(LSE_SYMBOLS),
        "cannot_hold_lse_to_new_york": CANNOT_HOLD_LSE_TO_NEW_YORK,
        "cannot_drop_lse_exit_independently_of_opening_buy": CANNOT_DROP_BOUND_EXIT_INDEPENDENTLY,
        "may_drop_bound_exit": False,
        "us_flatten_at": US_FLATTEN_AT,
        "us_symbols": list(US_SYMBOLS),
        "jpm_jnj_venues": {"JPM": "NYSE", "JNJ": "NYSE"},
        "firm_day_runs_to_ny_close": FIRM_DAY_RUNS_TO_NY_CLOSE,
        "overnight_holds": False,
        "paper_execution_stays": "OPEN",
        "trading_mode_stays": "LIVE_BLOCKED",
        "loads_live": False,
        "loads_broker_paper": False,
        "not_board_tap": True,
        "not_hari_card": True,
        "deterministic": True,
        "ai_enforced": False,
        "source": CEO_DESK_RULE,
        "note": (
            "Risk 02F bound in ControlEngine. SHEL.L, AZN.L, ULVR.L flatten in "
            "the London closing auction 16:30–16:35 Europe/London. That exit "
            "cannot be dropped independently of the opening buy. US names flatten "
            "at US regular cash close. Firm day still runs to NY close. "
            "split_flatten_clocks is true. LIVE_BLOCKED. paper OPEN."
        ),
    }


def ceo_desk_public() -> dict[str, Any]:
    return {
        "rule": CEO_DESK_RULE,
        "risk_02f": risk_02f_public(),
        "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
        "lse_flatten_at": LSE_FLATTEN_AT,
        "us_flatten_at": US_FLATTEN_AT,
        "firm_day_runs_to_ny_close": FIRM_DAY_RUNS_TO_NY_CLOSE,
        "overnight_holds": False,
        "paper_execution_stays": "OPEN",
        "trading_mode_stays": "LIVE_BLOCKED",
        "not_board_tap": True,
        "not_hari_card": True,
        "does_not_fill": True,
        "does_not_load_live": True,
    }
