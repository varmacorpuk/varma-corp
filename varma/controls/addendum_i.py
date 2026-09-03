"""Board Addendum I 2026-08-27.

Hari asked the Founding Architect to encode: the company is CLOSED until
Grand Opening. These are Board-set control-table values, labelled Board
Addendum I 2026-08-27. They are not invented silent defaults.

Nothing is trading. Not paper, not live. The £1000 is the FUTURE paper
starting book only. Do not fill. Do not propose fills. Do not run
flatten-as-if-there-were-positions. Do not send Board Member meeting
invites or approval emails.

TWO OPENINGS, both require Hari's EXPLICIT yes. Silence is not approval.
This slice implements the CLOSED gate and the first paper-trade PATH
(Trader proposal → ControlEngine → internal simulator). PAPER execution
remains CLOSED. No fills until Hari's explicit Grand Opening PAPER yes.

1) Grand Opening PAPER — only when Hari says the firm is built, everyone
   is in place, and we are not adding more to open. Then paper trading on
   the £1000 book may start (internal simulator). LIVE still blocked.
2) Grand Opening LIVE — later, only if Hari says so after paper evidence.
   Never auto-switch.

UNTIL PAPER GRAND OPENING:
- trading_mode stays LIVE_BLOCKED
- PAPER execution is CLOSED (Board-set flag; employees including CEO cannot write)
- Simulator DENY all fills because the firm is not open, even for allow-listed tickers
- Allow-list E still exists but cannot be used for fills until open
- BROKER_PAPER and LIVE remain UNLOADED
- No 07:30 diary invite to the Board Member. 07:30 may exist as an internal
  staff artefact but must not email or calendar-invite Hari.
- Kill switch still Board-only. Addendum A numbers still stored but unused
  until open.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.db.models import ControlSetting

ADDENDUM_I_LABEL = "Board Addendum I 2026-08-27"
ADDENDUM_I_SET_BY = "board-member"

PAPER_EXECUTION_CLOSED = "CLOSED"
PAPER_EXECUTION_KEY = "paper_execution"
GRAND_OPENING_PAPER_KEY = "grand_opening_paper"
GRAND_OPENING_LIVE_KEY = "grand_opening_live"
SIMULATED_CAPITAL_STATUS_KEY = "simulated_capital_status"

GRAND_OPENING_PAPER = "not"
GRAND_OPENING_LIVE = "not"
SIMULATED_CAPITAL_STATUS = "FUTURE_PAPER_STARTING_BOOK_ONLY"

PAPER_EXECUTION_CLOSED_REASON = "PAPER_EXECUTION_CLOSED"
FIRM_CLOSED_REASON = "FIRM_CLOSED"  # alias of PAPER_EXECUTION_CLOSED
CLOSED_FILL_REASONS = frozenset({PAPER_EXECUTION_CLOSED_REASON, FIRM_CLOSED_REASON})
FIRM_NOT_OPEN_NOTE = (
    "The company is CLOSED until Grand Opening. PAPER execution is CLOSED. "
    "Nothing is trading. Not paper, not live. Allow-list E exists but cannot "
    "be used for fills until Hari's explicit Grand Opening PAPER yes. "
    "Silence is not approval."
)

# Board-set control-table rows. Fail closed if missing.
ADDENDUM_I_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (PAPER_EXECUTION_KEY, PAPER_EXECUTION_CLOSED, "flag"),
    (GRAND_OPENING_PAPER_KEY, GRAND_OPENING_PAPER, "flag"),
    (GRAND_OPENING_LIVE_KEY, GRAND_OPENING_LIVE, "flag"),
    (SIMULATED_CAPITAL_STATUS_KEY, SIMULATED_CAPITAL_STATUS, "label"),
    ("board_member_0730_diary_invite", "false", "flag"),
    ("board_member_0730_calendar_invite", "false", "flag"),
    ("board_member_approval_email", "false", "flag"),
)

FIRM_OPEN_WRITE_FIELDS = frozenset(
    {
        PAPER_EXECUTION_KEY,
        GRAND_OPENING_PAPER_KEY,
        GRAND_OPENING_LIVE_KEY,
        "firm_open",
        "open_firm",
        "paper_grand_opening",
        "live_grand_opening",
        "grand_opening",
        SIMULATED_CAPITAL_STATUS_KEY,
        "addendum_i",
    }
)

EMPLOYEES_CANNOT_OPEN_REASON = "EMPLOYEE_CANNOT_WRITE_CONTROLS"
GRAND_OPENING_NOT_IMPLEMENTED_REASON = (
    "GRAND_OPENING_REQUIRES_EXPLICIT_YES_NOT_IMPLEMENTED_IN_THIS_SLICE"
)


def paper_execution_is_closed(session: Session) -> bool:
    """Fail closed. Missing or non-OPEN means PAPER execution is CLOSED."""
    row = session.get(ControlSetting, PAPER_EXECUTION_KEY)
    if row is None or row.value in (None, ""):
        return True
    return str(row.value).upper() != "OPEN"


def addendum_i_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_I_LABEL,
        "set_by": ADDENDUM_I_SET_BY,
        "board_set": True,
        "values_invented": False,
        "company_closed_until_grand_opening": True,
        "paper_execution": PAPER_EXECUTION_CLOSED,
        "paper_execution_closed": True,
        "firm_closed": True,
        "grand_opening_paper": GRAND_OPENING_PAPER,
        "grand_opening_live": GRAND_OPENING_LIVE,
        "silence_is_not_approval": True,
        "trading_mode_stays": "LIVE_BLOCKED",
        "does_not_switch_to_paper": True,
        "does_not_load_live": True,
        "does_not_load_broker_paper": True,
        "allow_list_e_exists": True,
        "allow_list_e_cannot_fill_until_open": True,
        "first_paper_trade_path_implemented": True,
        "simulated_capital_status": SIMULATED_CAPITAL_STATUS,
        "addendum_a_numbers_stored": True,
        "addendum_a_numbers_unused_until_open": True,
        "kill_switch_board_only": True,
        "flatten_as_if_there_were_positions": False,
        "propose_fills": False,
        "board_member_0730_diary_invite": False,
        "board_member_0730_calendar_invite": False,
        "board_member_approval_email": False,
        "meeting_0730_internal_staff_artefact_allowed": True,
        "employees_cannot_write": True,
        "ceo_cannot_write": True,
        "employees_cannot_open_the_firm": True,
        "ceo_cannot_open_the_firm": True,
        "two_openings": (
            "Grand Opening PAPER requires Hari explicit yes; LIVE still blocked. "
            "Grand Opening LIVE later requires Hari explicit yes after paper evidence. "
            "Never auto-switch."
        ),
        "note": FIRM_NOT_OPEN_NOTE,
    }
