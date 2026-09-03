"""Board Addendum L 2026-09-03: final strategy universe.

Source: Board Member direct instruction (Hari), 3 Sep 2026.
Supersedes the earlier same-day top-100 market-cap attempt and the original
Addendum E 2026-08-27 ten-name list. Extended the same day to the final
fifteen-name US book: ten equities plus five US-listed commodity ETP proxies.

The paper-tradeable universe is exactly fifteen US-market names, all
NYSE/Nasdaq, all USD-quoted. Single execution window: New York open.
No other names or venues. Commodity exposures are ETP proxies, not futures.

The allow-list constants live in ``addendum_e.py`` (which was updated in
place to avoid churn across dozens of importers). This module exists as
the Board record documenting the change, its source, and its date.

Addendum A limits still apply in GBP after FX conversion:
£1000 book, £200 max per name, £50 daily loss, 6 orders/day including exits.

LIVE stays BLOCKED. Paper only. No real broker. No real money.
"""

from __future__ import annotations

from typing import Any

from varma.controls.addendum_e import (
    ADDENDUM_E_COMMODITY_ETP_SYMBOLS,
    ADDENDUM_E_CURRENCIES,
    ADDENDUM_E_EQUITY_SYMBOLS,
    ADDENDUM_E_ETP_UNDERLYING,
    ADDENDUM_E_INSTRUMENTS,
    ADDENDUM_E_SYMBOLS,
    ADDENDUM_E_VENUES,
)

ADDENDUM_L_LABEL = "Board Addendum L 2026-09-03"
ADDENDUM_L_SET_BY = "board-member"
ADDENDUM_L_SOURCE = "Board Member direct instruction (Hari)"
ADDENDUM_L_SOURCE_DATE = "2026-09-03"
ADDENDUM_L_SUPERSEDES = "Board Addendum E 2026-08-27"

ADDENDUM_L_EQUITY_NAMES: tuple[tuple[str, str], ...] = (
    ("NVDA", "Nvidia"),
    ("AAPL", "Apple"),
    ("GOOGL", "Alphabet"),
    ("MSFT", "Microsoft"),
    ("AMZN", "Amazon"),
    ("SPCX", "SpaceX"),
    ("AVGO", "Broadcom"),
    ("META", "Meta Platforms"),
    ("TSLA", "Tesla"),
    ("BRK-B", "Berkshire Hathaway class B"),
)

ADDENDUM_L_ETP_NAMES: tuple[tuple[str, str], ...] = (
    ("GLD", "SPDR Gold Shares"),
    ("SLV", "iShares Silver Trust"),
    ("USO", "United States Oil Fund"),
    ("UNG", "United States Natural Gas Fund"),
    ("CPER", "United States Copper Index Fund"),
)

ADDENDUM_L_NAMES: tuple[tuple[str, str], ...] = ADDENDUM_L_EQUITY_NAMES + ADDENDUM_L_ETP_NAMES


def addendum_l_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_L_LABEL,
        "set_by": ADDENDUM_L_SET_BY,
        "board_set": True,
        "source": ADDENDUM_L_SOURCE,
        "source_date": ADDENDUM_L_SOURCE_DATE,
        "supersedes": ADDENDUM_L_SUPERSEDES,
        "symbols": list(ADDENDUM_E_SYMBOLS),
        "equity_symbols": list(ADDENDUM_E_EQUITY_SYMBOLS),
        "commodity_etp_symbols": list(ADDENDUM_E_COMMODITY_ETP_SYMBOLS),
        "venues": dict(ADDENDUM_E_VENUES),
        "currencies": dict(ADDENDUM_E_CURRENCIES),
        "names": {t: n for t, n in ADDENDUM_L_NAMES},
        "etp_underlying": dict(ADDENDUM_E_ETP_UNDERLYING),
        "count": len(ADDENDUM_E_SYMBOLS),
        "all_us_market": True,
        "all_usd_quoted": True,
        "execution_window": "New York open",
        "no_lse_names": True,
        "no_non_us_venues": True,
        "futures": False,
        "futures_margin": False,
        "futures_leverage": False,
        "futures_expiry": False,
        "futures_rollover": False,
        "addendum_a_limits_apply": True,
        "trading_mode_stays": "LIVE_BLOCKED",
        "paper_only": True,
        "note": (
            "Board Addendum L 2026-09-03 (Hari direct instruction). Final "
            "strategy universe: 15 US-market names (10 equities + 5 listed "
            "commodity ETP proxies). All NYSE/Nasdaq, all USD. Supersedes the "
            "earlier same-day top-100 market-cap attempt and the original "
            "Addendum E ten-name list. Commodity exposures are US-listed ETP "
            "proxies, not futures. Addendum A limits apply in GBP after FX. "
            "LIVE stays BLOCKED."
        ),
    }
