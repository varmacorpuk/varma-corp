"""Board Addendum I 2026-08-27.

Hari asked the Founding Architect to encode: the company is CLOSED until
Grand Opening. These are Board-set control-table values, labelled Board
Addendum I 2026-08-27. They are not invented silent defaults.

TWO OPENINGS, both require Hari's EXPLICIT yes. Silence is not approval.
This module is the two-opening rule. It is not deleted when paper opens.

1) Grand Opening PAPER — Hari explicit yes 3 Sep 2026 (word: "Open").
   Practice / paper only. Internal simulator on the £1000 paper book.
   LIVE still blocked. BROKER_PAPER and LIVE remain UNLOADED.
2) Grand Opening LIVE — later, only if Hari says so after paper evidence.
   Never auto-switch. Not given. Not implemented.

Opening is a Board-only control write (write_control). Employees including
the CEO cannot open or close the firm or write locks.

AFTER PAPER GRAND OPENING (authorised default / seed):
- trading_mode stays LIVE_BLOCKED
- PAPER execution is OPEN (Board-set flag)
- Simulator may fill a legal allow-list practice order when in session
  and within Addendum A limits
- Allow-list E is usable for paper fills
- Addendum A limits apply (£200 position, £50 daily loss, 6 orders/day,
  kill switch)
- Addendum C flatten-before-US-close still holds
- Addendum K still denies SHEL.L / AZN.L / ULVR.L after London cash close
- BROKER_PAPER and LIVE remain UNLOADED
- No 07:30 diary invite to the Board Member
- Kill switch still Board-only
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import ControlSetting

ADDENDUM_I_LABEL = "Board Addendum I 2026-08-27"
ADDENDUM_I_SET_BY = "board-member"
GRAND_OPENING_PAPER_LABEL = "Board Grand Opening PAPER 2026-09-03"

PAPER_EXECUTION_CLOSED = "CLOSED"
PAPER_EXECUTION_OPEN = "OPEN"
PAPER_EXECUTION_KEY = "paper_execution"
GRAND_OPENING_PAPER_KEY = "grand_opening_paper"
GRAND_OPENING_LIVE_KEY = "grand_opening_live"
SIMULATED_CAPITAL_STATUS_KEY = "simulated_capital_status"

# Authorised default after Hari's explicit Grand Opening PAPER yes.
GRAND_OPENING_PAPER = "yes"
GRAND_OPENING_LIVE = "not"
SIMULATED_CAPITAL_STATUS = "PAPER_STARTING_BOOK"
SIMULATED_CAPITAL_STATUS_CLOSED = "FUTURE_PAPER_STARTING_BOOK_ONLY"

PAPER_EXECUTION_CLOSED_REASON = "PAPER_EXECUTION_CLOSED"
FIRM_CLOSED_REASON = "FIRM_CLOSED"  # alias of PAPER_EXECUTION_CLOSED
CLOSED_FILL_REASONS = frozenset({PAPER_EXECUTION_CLOSED_REASON, FIRM_CLOSED_REASON})
GRAND_OPENING_PAPER_REASON = "GRAND_OPENING_PAPER"
PAPER_EXECUTION_CLOSED_BY_BOARD_REASON = "PAPER_EXECUTION_CLOSED_BY_BOARD"
FIRM_NOT_OPEN_NOTE = (
    "Board Addendum I is the two-opening rule. Grand Opening PAPER happened "
    "(Hari explicit yes, 3 Sep 2026, word: Open). Practice / paper only. "
    "LIVE has not opened. Silence is not approval. Employees cannot open "
    "or close the firm."
)

# Original CLOSED-gate rows (Addendum I as encoded before Grand Opening PAPER).
# Kept so the CLOSED gate still exists. Tests may re-apply these as a fixture.
# Production seed uses ADDENDUM_I_SETTINGS (paper OPEN).
ADDENDUM_I_CLOSED_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (PAPER_EXECUTION_KEY, PAPER_EXECUTION_CLOSED, "flag"),
    (GRAND_OPENING_PAPER_KEY, "not", "flag"),
    (GRAND_OPENING_LIVE_KEY, GRAND_OPENING_LIVE, "flag"),
    (SIMULATED_CAPITAL_STATUS_KEY, SIMULATED_CAPITAL_STATUS_CLOSED, "label"),
    ("board_member_0730_diary_invite", "false", "flag"),
    ("board_member_0730_calendar_invite", "false", "flag"),
    ("board_member_approval_email", "false", "flag"),
)

# Board-authorised production / fresh-seed default after Grand Opening PAPER.
ADDENDUM_I_SETTINGS: tuple[tuple[str, str, str], ...] = (
    (PAPER_EXECUTION_KEY, PAPER_EXECUTION_OPEN, "flag"),
    (GRAND_OPENING_PAPER_KEY, GRAND_OPENING_PAPER, "flag"),
    (GRAND_OPENING_LIVE_KEY, GRAND_OPENING_LIVE, "flag"),
    (SIMULATED_CAPITAL_STATUS_KEY, SIMULATED_CAPITAL_STATUS, "label"),
    ("board_member_0730_diary_invite", "false", "flag"),
    ("board_member_0730_calendar_invite", "false", "flag"),
    ("board_member_approval_email", "false", "flag"),
)

PAPER_OPEN_WRITE_FIELDS = frozenset(
    {
        PAPER_EXECUTION_KEY,
        GRAND_OPENING_PAPER_KEY,
        "firm_open",
        "open_firm",
        "paper_grand_opening",
        "grand_opening",
    }
)
LIVE_OPEN_WRITE_FIELDS = frozenset(
    {
        GRAND_OPENING_LIVE_KEY,
        "live_grand_opening",
    }
)
FIRM_OPEN_WRITE_FIELDS = PAPER_OPEN_WRITE_FIELDS | LIVE_OPEN_WRITE_FIELDS | {
    SIMULATED_CAPITAL_STATUS_KEY,
    "addendum_i",
}

EMPLOYEES_CANNOT_OPEN_REASON = "EMPLOYEE_CANNOT_WRITE_CONTROLS"
GRAND_OPENING_NOT_IMPLEMENTED_REASON = (
    "GRAND_OPENING_REQUIRES_EXPLICIT_YES_NOT_IMPLEMENTED_IN_THIS_SLICE"
)
GRAND_OPENING_LIVE_NOT_IMPLEMENTED_REASON = GRAND_OPENING_NOT_IMPLEMENTED_REASON

_OPEN_VALUES = frozenset({"OPEN", "YES", "TRUE", "1"})
_CLOSE_VALUES = frozenset({"CLOSED", "NOT", "NO", "FALSE", "0", ""})


def paper_execution_is_closed(session: Session) -> bool:
    """Fail closed. Missing or non-OPEN means PAPER execution is CLOSED."""
    row = session.get(ControlSetting, PAPER_EXECUTION_KEY)
    if row is None or row.value in (None, ""):
        return True
    return str(row.value).upper() != PAPER_EXECUTION_OPEN


def paper_open_intent(value: Any) -> bool | None:
    """True = open paper, False = close paper, None = unrecognised."""
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in _OPEN_VALUES:
        return True
    if text in _CLOSE_VALUES:
        return False
    return None


def _upsert_setting(
    session: Session,
    key: str,
    value: str,
    unit: str,
    *,
    actor_id: str,
    source: str,
) -> None:
    now = now_london()
    row = session.get(ControlSetting, key)
    if row is None:
        session.add(
            ControlSetting(
                key=key,
                value=value,
                unit=unit,
                set_by=actor_id,
                set_at=now,
                source=source,
            )
        )
        return
    row.value = value
    row.unit = unit
    row.set_by = actor_id
    row.set_at = now
    row.source = source


def apply_grand_opening_paper(session: Session, *, actor_id: str) -> None:
    """Board-only: open PRACTICE paper. Does not open LIVE. Does not load brokers."""
    for key, value, unit in ADDENDUM_I_SETTINGS:
        source = GRAND_OPENING_PAPER_LABEL if key in {
            PAPER_EXECUTION_KEY,
            GRAND_OPENING_PAPER_KEY,
            SIMULATED_CAPITAL_STATUS_KEY,
        } else ADDENDUM_I_LABEL
        _upsert_setting(session, key, value, unit, actor_id=actor_id, source=source)
    session.commit()


def force_paper_execution_closed(session: Session, *, actor_id: str = "board-member") -> None:
    """Close paper execution. CLOSED gate remains. Used by Board write and test fixtures.

    Does not delete Addendum I. Does not open LIVE. Does not load brokers.
    """
    _upsert_setting(
        session,
        PAPER_EXECUTION_KEY,
        PAPER_EXECUTION_CLOSED,
        "flag",
        actor_id=actor_id,
        source=ADDENDUM_I_LABEL,
    )
    session.commit()


def apply_paper_execution_closed_fixture(session: Session) -> None:
    """Re-apply the original CLOSED-gate rows. Tests only. Not production default."""
    now_actor = "board-member"
    for key, value, unit in ADDENDUM_I_CLOSED_SETTINGS:
        _upsert_setting(
            session, key, value, unit, actor_id=now_actor, source=ADDENDUM_I_LABEL
        )
    session.commit()


def _setting(session: Session | None, key: str, default: str) -> str:
    if session is None:
        return default
    row = session.get(ControlSetting, key)
    if row is None or row.value in (None, ""):
        return default
    return str(row.value)


def addendum_i_public(session: Session | None = None) -> dict[str, Any]:
    paper = _setting(session, PAPER_EXECUTION_KEY, PAPER_EXECUTION_OPEN)
    paper_closed = str(paper).upper() != PAPER_EXECUTION_OPEN
    grand_paper = _setting(session, GRAND_OPENING_PAPER_KEY, GRAND_OPENING_PAPER)
    grand_live = _setting(session, GRAND_OPENING_LIVE_KEY, GRAND_OPENING_LIVE)
    capital = _setting(session, SIMULATED_CAPITAL_STATUS_KEY, SIMULATED_CAPITAL_STATUS)
    return {
        "label": ADDENDUM_I_LABEL,
        "set_by": ADDENDUM_I_SET_BY,
        "board_set": True,
        "values_invented": False,
        "two_opening_rule_still_exists": True,
        "company_closed_until_grand_opening": paper_closed and grand_paper != "yes",
        "paper_execution": "CLOSED" if paper_closed else "OPEN",
        "paper_execution_closed": paper_closed,
        "firm_closed": paper_closed,
        "firm_open": not paper_closed,
        "grand_opening_paper": grand_paper,
        "grand_opening_paper_done": grand_paper == "yes",
        "grand_opening_live": grand_live,
        "grand_opening_live_done": False,
        "silence_is_not_approval": True,
        "trading_mode_stays": "LIVE_BLOCKED",
        "does_not_switch_to_paper": True,
        "does_not_load_live": True,
        "does_not_load_broker_paper": True,
        "allow_list_e_exists": True,
        "allow_list_e_cannot_fill_until_open": paper_closed,
        "first_paper_trade_path_implemented": True,
        "grand_opening_paper_implemented": True,
        "simulated_capital_status": capital,
        "addendum_a_numbers_stored": True,
        "addendum_a_numbers_unused_until_open": paper_closed,
        "kill_switch_board_only": True,
        "flatten_as_if_there_were_positions": False,
        "propose_fills": not paper_closed,
        "board_member_0730_diary_invite": False,
        "board_member_0730_calendar_invite": False,
        "board_member_approval_email": False,
        "meeting_0730_internal_staff_artefact_allowed": True,
        "employees_cannot_write": True,
        "ceo_cannot_write": True,
        "employees_cannot_open_the_firm": True,
        "ceo_cannot_open_the_firm": True,
        "employees_cannot_close_the_firm": True,
        "two_openings": (
            "Grand Opening PAPER requires Hari explicit yes; LIVE still blocked. "
            "Grand Opening LIVE later requires Hari explicit yes after paper evidence. "
            "Never auto-switch. Paper opening has happened (3 Sep 2026). "
            "Live opening has not."
        ),
        "note": FIRM_NOT_OPEN_NOTE if paper_closed else (
            "Grand Opening PAPER is done (Hari explicit yes, 3 Sep 2026, word: Open). "
            "Practice / paper only on the £1000 book. LIVE still blocked. "
            "BROKER_PAPER and LIVE remain UNLOADED. Addendum I still exists as "
            "the two-opening rule. Live opening has not happened."
        ),
        "grand_opening_paper_label": GRAND_OPENING_PAPER_LABEL,
    }
