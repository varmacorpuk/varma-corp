"""Board Addendum A 2026-08-27.

Hari asked the Founding Architect to set these as Board-set control-table
values. They are labelled Board Addendum A 2026-08-27. They are not invented
silent defaults.

trading_mode stays LIVE_BLOCKED until the execution allow-list has Board-approved
names. This slice does not switch to PAPER because the allow-list is still empty.
Empty allow-list ⇒ no orders (paper or live).
"""

from __future__ import annotations

from typing import Any

ADDENDUM_A_LABEL = "Board Addendum A 2026-08-27"
ADDENDUM_A_SET_BY = "board-member"
CURRENCY = "GBP"
TIMEZONE = "Europe/London"

SIMULATED_CAPITAL = 1000.0
MAX_POSITION = 200.0  # one paper trade, GBP
MAX_DAILY_LOSS = 50.0
MAX_ORDERS_PER_DAY = 6
# Halt if paper equity <= 800 GBP OR London-day P&L <= -50 GBP.
KILL_SWITCH_EQUITY_FLOOR = 800.0
KILL_SWITCH_DAILY_PNL_FLOOR = -50.0

SUCCESSFUL_TRADE_DEFINITION = "CLOSED paper trade with profit > 0"
EVALUATION_WIN_RATE_THRESHOLD = 0.5  # trigger is strictly greater than 50%
EVALUATION_REQUIRES_BOOK_PROFITABLE = True
EVALUATION_AUTO_SWITCH_LIVE = False

# key, value (string), unit
ADDENDUM_A_LIMITS: tuple[tuple[str, str, str], ...] = (
    ("simulated_capital", "1000", "GBP"),
    ("max_position", "200", "GBP"),
    ("max_daily_loss", "50", "GBP"),
    ("max_orders_per_day", "6", "count"),
    ("kill_switch_equity_floor", "800", "GBP"),
    ("kill_switch_daily_pnl_floor", "-50", "GBP"),
)

KILL_SWITCH_HALT_IF = (
    "halt if paper equity <= 800 GBP OR London-day P&L <= -50 GBP"
)
KILL_SWITCH_ON_HALT = (
    "cancel open PAPER orders only; never load LIVE; never flatten live "
    "(there is no live)"
)


def addendum_a_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_A_LABEL,
        "set_by": ADDENDUM_A_SET_BY,
        "board_set": True,
        "values_invented": False,
        "currency": CURRENCY,
        "timezone": TIMEZONE,
        "trading_mode_stays": "LIVE_BLOCKED",
        "does_not_switch_to_paper": True,
        "empty_allow_list_denies": True,
        "kill_switch_halt_if": KILL_SWITCH_HALT_IF,
        "kill_switch_on_halt": KILL_SWITCH_ON_HALT,
        "successful_trade_definition": SUCCESSFUL_TRADE_DEFINITION,
        "evaluation_win_rate_threshold": EVALUATION_WIN_RATE_THRESHOLD,
        "evaluation_requires_book_profitable": EVALUATION_REQUIRES_BOOK_PROFITABLE,
        "evaluation_auto_switch_live": EVALUATION_AUTO_SWITCH_LIVE,
        "paper_continues_until_board_approval": True,
    }
