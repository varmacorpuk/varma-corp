"""Board Addendum M 2026-09-03: five US-listed commodity ETPs, WATCH-ONLY.

Source: Board Member follow-up, 3 Sep 2026, then CEO ruling the same day.
Challenge's hole stands: GLD/SLV/USO/UNG/CPER opening ranges are mostly
overnight futures repricing, not equity-style discovery. Until Quant
(Nina) produces a separate proxy test, these five are WATCH-ONLY.

They may appear on the watchlist / universe list / docs. They must NOT
be seeded as executable AllowListInstrument rows and must NOT fill in
ControlEngine. Not futures, not margin, not expiry, not rollover.
LIVE stays BLOCKED. Paper only.
"""

from __future__ import annotations

from typing import Any

from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS, canonical_feed_symbol
from varma.controls.addendum_l import ADDENDUM_L_LABEL, ADDENDUM_L_NAMES

ADDENDUM_M_LABEL = "Board Addendum M 2026-09-03"
ADDENDUM_M_SET_BY = "board-member"
ADDENDUM_M_SOURCE = "Board Member follow-up; CEO ruling (watch-only until proxy test)"
ADDENDUM_M_SOURCE_DATE = "2026-09-03"
ADDENDUM_M_EXTENDS = ADDENDUM_L_LABEL

WATCH_ONLY_REASON = "WATCH_ONLY_COMMODITY_ETP"
WATCH_ONLY_LABEL = "WATCH-ONLY — Addendum M (not executable)"
WATCH_ONLY_NOTE = (
    "Opening ranges are mostly overnight futures repricing, not equity-style "
    "discovery. Watch-only until Quant produces a separate proxy test."
)

ADDENDUM_M_ETPS: tuple[tuple[str, str, str], ...] = (
    ("GLD", "SPDR Gold Shares", "NYSE"),
    ("SLV", "iShares Silver Trust", "NYSE"),
    ("USO", "United States Oil Fund", "NYSE"),
    ("UNG", "United States Natural Gas Fund", "NYSE"),
    ("CPER", "United States Copper Index Fund", "NYSE"),
)

ADDENDUM_M_ETP_SYMBOLS: tuple[str, ...] = tuple(symbol for symbol, _name, _venue in ADDENDUM_M_ETPS)
ADDENDUM_M_ETP_VENUES: dict[str, str] = {symbol: venue for symbol, _name, venue in ADDENDUM_M_ETPS}

PAPER_UNIVERSE_EQUITIES: tuple[str, ...] = tuple(symbol for symbol, _name in ADDENDUM_L_NAMES)
# Visible universe = 10 executables + 5 watch-only ETPs. Executable set is Addendum E.
PAPER_UNIVERSE_SYMBOLS: tuple[str, ...] = PAPER_UNIVERSE_EQUITIES + ADDENDUM_M_ETP_SYMBOLS


def is_watch_only_etp(symbol: str) -> bool:
    return canonical_feed_symbol(symbol) in ADDENDUM_M_ETP_SYMBOLS


def addendum_m_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_M_LABEL,
        "set_by": ADDENDUM_M_SET_BY,
        "board_set": True,
        "source": ADDENDUM_M_SOURCE,
        "source_date": ADDENDUM_M_SOURCE_DATE,
        "extends": ADDENDUM_M_EXTENDS,
        "etps": {symbol: name for symbol, name, _venue in ADDENDUM_M_ETPS},
        "etp_symbols": list(ADDENDUM_M_ETP_SYMBOLS),
        "equity_symbols": list(PAPER_UNIVERSE_EQUITIES),
        "symbols": list(PAPER_UNIVERSE_SYMBOLS),
        "executable_symbols": list(ADDENDUM_E_SYMBOLS),
        "venues": dict(ADDENDUM_M_ETP_VENUES),
        "currencies": {symbol: "USD" for symbol in ADDENDUM_M_ETP_SYMBOLS},
        "count": len(PAPER_UNIVERSE_SYMBOLS),
        "executable_count": len(ADDENDUM_E_SYMBOLS),
        "watch_only_count": len(ADDENDUM_M_ETP_SYMBOLS),
        "equity_count": len(PAPER_UNIVERSE_EQUITIES),
        "etp_count": len(ADDENDUM_M_ETP_SYMBOLS),
        "executable": False,
        "watch_only": True,
        "all_us_market": True,
        "all_usd_quoted": True,
        "futures": False,
        "margin": False,
        "expiry": False,
        "rollover": False,
        "deny_reason": WATCH_ONLY_REASON,
        "watch_label": WATCH_ONLY_LABEL,
        "execution_window": "New York open (watch only — no paper fills)",
        "trading_mode_stays": "LIVE_BLOCKED",
        "paper_only": True,
        "note": (
            "Board Addendum M 2026-09-03, CEO ruling: GLD/SLV/USO/UNG/CPER are "
            "WATCH-ONLY. Not on the paper execution allow-list. "
            f"{WATCH_ONLY_NOTE} LIVE stays BLOCKED."
        ),
    }
