"""Board Addendum E 2026-08-27.

Hari asked the Founding Architect to encode the starting PAPER execution
allow-list from the CEO recommendation, now Board-used. These are Board-set
control-table values, labelled Board Addendum E 2026-08-27. They are not
invented silent defaults.

PAPER membership only. trading_mode stays LIVE_BLOCKED. The internal paper
fill simulator is the paper ledger. Do not load LIVE or BROKER_PAPER.
Employees (including the CEO) cannot write this list.
"""

from __future__ import annotations

from typing import Any

ADDENDUM_E_LABEL = "Board Addendum E 2026-08-27"
ADDENDUM_E_SET_BY = "board-member"

# US listed names, then LSE names in the instrument form already used by this repo.
# JPM and JNJ are NYSE names. US tech stays NASDAQ. LSE three stay LSE.
ADDENDUM_E_INSTRUMENTS: tuple[tuple[str, str], ...] = (
    ("AAPL", "NASDAQ"),
    ("MSFT", "NASDAQ"),
    ("NVDA", "NASDAQ"),
    ("AMZN", "NASDAQ"),
    ("GOOGL", "NASDAQ"),
    ("JPM", "NYSE"),
    ("JNJ", "NYSE"),
    ("SHEL.L", "LSE"),
    ("AZN.L", "LSE"),
    ("ULVR.L", "LSE"),
)

ADDENDUM_E_SYMBOLS: tuple[str, ...] = tuple(symbol for symbol, _venue in ADDENDUM_E_INSTRUMENTS)
ADDENDUM_E_VENUES: dict[str, str] = dict(ADDENDUM_E_INSTRUMENTS)


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
