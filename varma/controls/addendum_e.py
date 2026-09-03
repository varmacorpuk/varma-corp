"""Board Addendum E 2026-09-03 (revised).

Board-set PAPER execution allow-list. Revised 2026-09-03 to the final
strategy universe: fifteen US-listed names (ten equities + five commodity
ETP proxies). No LSE, no non-US sessions, no futures.

The existing SHEL.L paper book (PAPER-20260903-02) stays valid as
historical data; SHEL.L / AZN.L / ULVR.L are removed from the
executable allow-list going forward.

PAPER membership only. trading_mode stays LIVE_BLOCKED. The internal paper
fill simulator is the paper ledger. Do not load LIVE or BROKER_PAPER.
Employees (including the CEO) cannot write this list.

SpaceX (SPCX) is Nasdaq-listed since 12 Jun 2026 in this universe. Public
delayed feeds may not resolve SPCX — that is a feed-symbol issue, not a
desk-symbol change. Berkshire Hathaway uses the class-B line; the feed
symbol is BRK-B (dash form) but the canonical desk symbol is BRK.B.

Commodity exposures are US-listed ETP proxies (GLD, SLV, USO, UNG, CPER),
not futures. No futures contracts, margin, leverage, expiry, or rollover.
They use the ordinary USD ETP sizing/control path. GLD is not gold futures
and is not the GOLD/XAU/XAUUSD/GC deny set.
"""

from __future__ import annotations

from typing import Any

ADDENDUM_E_LABEL = "Board Addendum E 2026-09-03"
ADDENDUM_E_SET_BY = "board-member"

# Final strategy universe: fifteen US-listed names. US market only.
# BRK-B is the feed/Yahoo form; canonical desk symbol BRK.B.
# Commodity names are listed ETP proxies, not futures.
ADDENDUM_E_EQUITY_INSTRUMENTS: tuple[tuple[str, str], ...] = (
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

ADDENDUM_E_COMMODITY_ETP_INSTRUMENTS: tuple[tuple[str, str], ...] = (
    ("GLD", "NYSE"),
    ("SLV", "NYSE"),
    ("USO", "NYSE"),
    ("UNG", "NYSE"),
    ("CPER", "NYSE"),
)

ADDENDUM_E_INSTRUMENTS: tuple[tuple[str, str], ...] = (
    ADDENDUM_E_EQUITY_INSTRUMENTS + ADDENDUM_E_COMMODITY_ETP_INSTRUMENTS
)

ADDENDUM_E_SYMBOLS: tuple[str, ...] = tuple(symbol for symbol, _venue in ADDENDUM_E_INSTRUMENTS)
ADDENDUM_E_VENUES: dict[str, str] = dict(ADDENDUM_E_INSTRUMENTS)
ADDENDUM_E_EQUITY_SYMBOLS: tuple[str, ...] = tuple(
    symbol for symbol, _venue in ADDENDUM_E_EQUITY_INSTRUMENTS
)
ADDENDUM_E_COMMODITY_ETP_SYMBOLS: tuple[str, ...] = tuple(
    symbol for symbol, _venue in ADDENDUM_E_COMMODITY_ETP_INSTRUMENTS
)

ASSET_CLASS_LISTED_EQUITY = "listed_equity"
ASSET_CLASS_LISTED_ETP = "listed_etp"

ADDENDUM_E_ASSET_CLASSES: dict[str, str] = {
    **{symbol: ASSET_CLASS_LISTED_EQUITY for symbol in ADDENDUM_E_EQUITY_SYMBOLS},
    **{symbol: ASSET_CLASS_LISTED_ETP for symbol in ADDENDUM_E_COMMODITY_ETP_SYMBOLS},
}

# ETP underlying is descriptive only. Not a futures contract. Not margin.
ADDENDUM_E_ETP_UNDERLYING: dict[str, str] = {
    "GLD": "gold",
    "SLV": "silver",
    "USO": "crude_oil",
    "UNG": "natural_gas",
    "CPER": "copper",
}

# All fifteen are USD. No GBP names in the final strategy.
ADDENDUM_E_CURRENCIES: dict[str, str] = {
    symbol: "USD" for symbol, _venue in ADDENDUM_E_INSTRUMENTS
}

# All US names are major USD. No pence.
ADDENDUM_E_QUOTE_UNITS: dict[str, str] = {
    symbol: "USD" for symbol in ADDENDUM_E_CURRENCIES
}

# Feed form vs desk form. Identity except Berkshire class B.
ADDENDUM_E_FEED_SYMBOLS: dict[str, str] = {
    "BRK-B": "BRK-B",
    "BRK.B": "BRK-B",
}
ADDENDUM_E_DESK_SYMBOLS: dict[str, str] = {
    "BRK-B": "BRK.B",
}

# Keep backward-compat functions for existing SHEL.L paper book history.
# SHEL.L fills pre-date the universe revision and remain valid GBP data.

# Gold *futures* / bullion codes stay denied even if written onto the list.
# GLD is a listed ETP and is not in this set.
GOLD_FUTURES_DENY_SYMBOLS = frozenset({"XAU", "XAUUSD", "GOLD", "GC"})


def instrument_currency(symbol: str) -> str:
    """USD for US-venue names; GBP for .L names. Default USD for unknowns."""
    key = str(symbol or "")
    if key in ADDENDUM_E_CURRENCIES:
        return ADDENDUM_E_CURRENCIES[key]
    if key.endswith(".L"):
        return "GBP"
    return "USD"


def instrument_quote_unit(symbol: str) -> str:
    """Native quote unit. LSE cash is pence (GBX). Does not change membership."""
    key = str(symbol or "")
    if key in ADDENDUM_E_QUOTE_UNITS:
        return ADDENDUM_E_QUOTE_UNITS[key]
    if key.endswith(".L"):
        return "GBX"
    return "USD"


def instrument_asset_class(symbol: str) -> str:
    """listed_equity or listed_etp. Unknowns default to listed_equity."""
    key = str(symbol or "")
    return ADDENDUM_E_ASSET_CLASSES.get(key, ASSET_CLASS_LISTED_EQUITY)


def is_commodity_etp(symbol: str) -> bool:
    return str(symbol or "") in ADDENDUM_E_COMMODITY_ETP_SYMBOLS


def is_gold_futures_symbol(symbol: str) -> bool:
    return str(symbol or "").upper() in GOLD_FUTURES_DENY_SYMBOLS


def feed_symbol(symbol: str) -> str:
    """Yahoo/feed form. Desk BRK.B maps to BRK-B. Others are identity."""
    key = str(symbol or "")
    return ADDENDUM_E_FEED_SYMBOLS.get(key, key)


def desk_symbol(symbol: str) -> str:
    """Canonical desk form. Feed BRK-B maps to BRK.B. Others are identity."""
    key = str(symbol or "")
    return ADDENDUM_E_DESK_SYMBOLS.get(key, key)


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
        "equity_symbols": list(ADDENDUM_E_EQUITY_SYMBOLS),
        "commodity_etp_symbols": list(ADDENDUM_E_COMMODITY_ETP_SYMBOLS),
        "venues": dict(ADDENDUM_E_INSTRUMENTS),
        "currencies": dict(ADDENDUM_E_CURRENCIES),
        "quote_units": dict(ADDENDUM_E_QUOTE_UNITS),
        "asset_classes": dict(ADDENDUM_E_ASSET_CLASSES),
        "etp_underlying": dict(ADDENDUM_E_ETP_UNDERLYING),
        "count": len(ADDENDUM_E_SYMBOLS),
        "equity_count": len(ADDENDUM_E_EQUITY_SYMBOLS),
        "commodity_etp_count": len(ADDENDUM_E_COMMODITY_ETP_SYMBOLS),
        "all_us_market": True,
        "all_usd_quoted": True,
        "futures": False,
        "futures_margin": False,
        "futures_leverage": False,
        "futures_expiry": False,
        "futures_rollover": False,
        "allow_list_e_cannot_fill_until_open": True,
        "note": (
            "Board-set PAPER execution allow-list. Exists but cannot be used "
            "for fills until Grand Opening PAPER (Board Addendum I). Internal "
            "simulator DENY all fills while PAPER execution is CLOSED, even for "
            "these names. LIVE and BROKER_PAPER remain UNLOADED. Gold futures "
            "(XAU/XAUUSD/GOLD/GC) stay denied. GLD/SLV/USO/UNG/CPER are US-listed "
            "ETP proxies on the ordinary USD path. Unknown tickers deny."
        ),
    }
