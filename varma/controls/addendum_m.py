"""Board Addendum M 2026-09-03: five US-listed commodity ETPs.

Source: Board Member follow-up, 3 Sep 2026.
Extends Addendum L's ten equities to fifteen instruments. These are
ETP proxies, not futures: no contract sizing, margin, expiry, or rollover.

They trade on the existing paper equity/ETP path:
- same New York-open window
- same USD→GBP fractional/notional sizing
- same Addendum A limits (£200/name, £50 daily loss, 6 orders/day)
- flatten at US close; no overnight
- LIVE stays BLOCKED
"""

from __future__ import annotations

from typing import Any

from varma.controls.addendum_e import ADDENDUM_E_CURRENCIES, ADDENDUM_E_SYMBOLS, ADDENDUM_E_VENUES
from varma.controls.addendum_l import ADDENDUM_L_LABEL, ADDENDUM_L_NAMES

ADDENDUM_M_LABEL = "Board Addendum M 2026-09-03"
ADDENDUM_M_SET_BY = "board-member"
ADDENDUM_M_SOURCE = "Board Member follow-up (commodity ETP proxies)"
ADDENDUM_M_SOURCE_DATE = "2026-09-03"
ADDENDUM_M_EXTENDS = ADDENDUM_L_LABEL

ADDENDUM_M_ETPS: tuple[tuple[str, str], ...] = (
    ("GLD", "gold"),
    ("SLV", "silver"),
    ("USO", "crude oil"),
    ("UNG", "natural gas"),
    ("CPER", "copper"),
)

ADDENDUM_M_ETP_SYMBOLS: tuple[str, ...] = tuple(symbol for symbol, _name in ADDENDUM_M_ETPS)

# Exact 15-name paper universe: Addendum L equities + Addendum M ETPs.
PAPER_UNIVERSE_EQUITIES: tuple[str, ...] = tuple(symbol for symbol, _name in ADDENDUM_L_NAMES)
PAPER_UNIVERSE_SYMBOLS: tuple[str, ...] = ADDENDUM_E_SYMBOLS


def addendum_m_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_M_LABEL,
        "set_by": ADDENDUM_M_SET_BY,
        "board_set": True,
        "source": ADDENDUM_M_SOURCE,
        "source_date": ADDENDUM_M_SOURCE_DATE,
        "extends": ADDENDUM_M_EXTENDS,
        "etps": {symbol: name for symbol, name in ADDENDUM_M_ETPS},
        "etp_symbols": list(ADDENDUM_M_ETP_SYMBOLS),
        "equity_symbols": list(PAPER_UNIVERSE_EQUITIES),
        "symbols": list(ADDENDUM_E_SYMBOLS),
        "venues": {symbol: ADDENDUM_E_VENUES[symbol] for symbol in ADDENDUM_M_ETP_SYMBOLS},
        "currencies": {symbol: ADDENDUM_E_CURRENCIES[symbol] for symbol in ADDENDUM_M_ETP_SYMBOLS},
        "count": len(ADDENDUM_E_SYMBOLS),
        "equity_count": len(PAPER_UNIVERSE_EQUITIES),
        "etp_count": len(ADDENDUM_M_ETP_SYMBOLS),
        "all_us_market": True,
        "all_usd_quoted": True,
        "equity_etp_path_only": True,
        "futures": False,
        "margin": False,
        "expiry": False,
        "rollover": False,
        "execution_window": "New York open",
        "addendum_a_limits_apply": True,
        "trading_mode_stays": "LIVE_BLOCKED",
        "paper_only": True,
        "note": (
            "Board Addendum M 2026-09-03. Adds GLD/SLV/USO/UNG/CPER as US-listed "
            "commodity ETP proxies on the existing paper equity/ETP path. Extends "
            "Addendum L from 10 to 15 instruments. Not futures. LIVE stays BLOCKED."
        ),
    }
