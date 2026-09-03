"""Board Addendum E 2026-09-03 (revised).

Board-set PAPER execution allow-list. Revised 2026-09-03 to the final
strategy universe: ten US-listed equities. Addendum M the same day records
five commodity ETPs as WATCH-ONLY — they are not on this executable list.

The existing SHEL.L paper book (PAPER-20260903-02) stays valid as
historical data; SHEL.L / AZN.L / ULVR.L are removed from the
executable allow-list going forward.

PAPER membership only. trading_mode stays LIVE_BLOCKED. The internal paper
fill simulator is the paper ledger. Do not load LIVE or BROKER_PAPER.
Employees (including the CEO) cannot write this list.

SpaceX (SPCX) is Nasdaq-listed since 12 Jun 2026. Berkshire Hathaway
uses the class-B line; the feed symbol is BRK-B (dash form) but the
canonical desk symbol is BRK.B.
"""

from __future__ import annotations

from typing import Any

ADDENDUM_E_LABEL = "Board Addendum E 2026-09-03"
ADDENDUM_E_SET_BY = "board-member"

# Final executable strategy universe: ten US equities. US market only.
# BRK-B is the feed/Yahoo form; canonical desk symbol BRK.B.
# Addendum M commodity ETPs (GLD/SLV/USO/UNG/CPER) are watch-only — not listed here.
ADDENDUM_E_INSTRUMENTS: tuple[tuple[str, str], ...] = (
    ("NVDA", "NASDAQ"),
    ("AAPL", "NASDAQ"),
    ("GOOGL", "NASDAQ"),
    ("MSFT", "NASDAQ"),
    ("AMZN", "NASDAQ"),
    ("SPCX", "NASDAQ"),
    ("AVGO", "NASDAQ"),
    ("META", "NASDAQ"),
    ("TSLA", "NASDAQ"),
    ("BRK-B", "NYSE"),
)

# Desk form → feed/Yahoo form. Only BRK has a syntax split.
DESK_TO_FEED_SYMBOL: dict[str, str] = {"BRK.B": "BRK-B"}
FEED_TO_DESK_SYMBOL: dict[str, str] = {"BRK-B": "BRK.B"}


def canonical_feed_symbol(symbol: str) -> str:
    """Map a desk symbol onto the allow-list / feed form."""
    key = str(symbol or "").strip()
    return DESK_TO_FEED_SYMBOL.get(key, key)


def desk_symbol(symbol: str) -> str:
    """Map a feed symbol onto the canonical desk form."""
    key = str(symbol or "").strip()
    return FEED_TO_DESK_SYMBOL.get(key, key)


ADDENDUM_E_SYMBOLS: tuple[str, ...] = tuple(symbol for symbol, _venue in ADDENDUM_E_INSTRUMENTS)
ADDENDUM_E_VENUES: dict[str, str] = dict(ADDENDUM_E_INSTRUMENTS)

# All ten executables are USD. No GBP names in the final strategy.
ADDENDUM_E_CURRENCIES: dict[str, str] = {
    symbol: "USD" for symbol, _venue in ADDENDUM_E_INSTRUMENTS
}

# All US names are major USD. No pence.
ADDENDUM_E_QUOTE_UNITS: dict[str, str] = {
    symbol: "USD" for symbol in ADDENDUM_E_CURRENCIES
}

# Keep backward-compat functions for existing SHEL.L paper book history.
# SHEL.L fills pre-date the universe revision and remain valid GBP data.


def instrument_currency(symbol: str) -> str:
    """USD for US-venue names; GBP for .L names. Default USD for unknowns."""
    key = canonical_feed_symbol(symbol)
    if key in ADDENDUM_E_CURRENCIES:
        return ADDENDUM_E_CURRENCIES[key]
    if key.endswith(".L"):
        return "GBP"
    return "USD"


def instrument_quote_unit(symbol: str) -> str:
    """Native quote unit. LSE cash is pence (GBX). Does not change membership."""
    key = canonical_feed_symbol(symbol)
    if key in ADDENDUM_E_QUOTE_UNITS:
        return ADDENDUM_E_QUOTE_UNITS[key]
    if key.endswith(".L"):
        return "GBX"
    return "USD"


def addendum_e_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_E_LABEL,
        "set_by": ADDENDUM_E_SET_BY,
        "board_set": True,
        "values_invented": False,
        "paper_membership_only": True,
        "live_membership": False,
        "trading_mode_stays": "LIVE_BLOCKED",
        "does_not_load_live": True,
        "does_not_load_broker_paper": True,
        "employees_cannot_write": True,
        "ceo_cannot_write": True,
        "symbols": list(ADDENDUM_E_SYMBOLS),
        "venues": dict(ADDENDUM_E_INSTRUMENTS),
        "currencies": dict(ADDENDUM_E_CURRENCIES),
        "quote_units": dict(ADDENDUM_E_QUOTE_UNITS),
        "count": len(ADDENDUM_E_SYMBOLS),
        "allow_list_e_cannot_fill_until_open": True,
        "note": (
            "Board-set PAPER execution allow-list. Exists but cannot be used "
            "for fills until Grand Opening PAPER (Board Addendum I). Internal "
            "simulator DENY all fills while PAPER execution is CLOSED, even for "
            "these names. LIVE and BROKER_PAPER remain UNLOADED. Gold is not on "
            "this list. Unknown tickers deny."
        ),
    }
