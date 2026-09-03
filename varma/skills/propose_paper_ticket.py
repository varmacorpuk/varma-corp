"""Trader paper-ticket proposal. Deterministic. No AI.

Chris Adeyemi · Trader proposes a paper order. ControlEngine is the
authoritative permit/deny. If allowed, the internal paper fill simulator
updates the paper ledger. After Grand Opening PAPER a legal allow-list
ticket may fill in the simulator. LIVE and BROKER_PAPER stay UNLOADED.
FakeLLM is not called: permit/deny, hours, kill switch, and fills are never AI.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import LONDON, now_london
from varma.controls.addendum_f import TRADER_SLUG, staff_display_for_slug
from varma.controls.addendum_i import (
    ADDENDUM_I_LABEL,
    PAPER_EXECUTION_CLOSED_REASON,
    paper_execution_is_closed,
)
from varma.controls.engine import BROKER_PAPER_LOADED, LIVE_ADAPTER_LOADED, Decision
from varma.db.models import Employee, Evidence, PaperFill, PaperOrder
from varma.employees.brain import EmployeeBrain
from varma.ports.execution import LIVE_PORT_LOADED, ExecutionPort

SKILL_NAME = "propose_paper_ticket"
SKILL_VERSION = "0.1.0"
ONLY_TRADER_MAY_PROPOSE = "ONLY_TRADER_MAY_PROPOSE_PAPER_TICKETS"

# Legal allow-list paper buy inside Addendum A numeric limits (max_position 200 GBP,
# max_orders_per_day 6, max_daily_loss 50 GBP). AAPL is on Addendum E. Not LSE.
LEGAL_PAPER_TICKET: dict[str, Any] = {
    "symbol": "AAPL",
    "side": "buy",
    "notional_gbp": 50.0,
    "execution_port": "SIMULATOR",
}

# Desk ticket PAPER-20260903-02. Practice / paper only. LIVE stays blocked.
# Entry ref 3409.3p Yahoo LSE delayed (GBP last = pence/100). Notional ~£170.47,
# under Addendum A £200 max per name. Stop 3384p / target 3447p are desk-managed
# and are not resting engine orders. Overnight off. Latest London 16:30 exit is
# a later job. Named ticket writes only to data/varma_paper_open.db.
PAPER_20260903_02_ID = "PAPER-20260903-02"
PAPER_20260903_02_AT = datetime(2026, 9, 3, 9, 59, tzinfo=LONDON)
PAPER_20260903_02: dict[str, Any] = {
    "symbol": "SHEL.L",
    "side": "buy",
    "quantity": 5.0,
    "execution_port": "SIMULATOR",
    "ticket_id": PAPER_20260903_02_ID,
}

NAMED_PAPER_TICKETS: dict[str, dict[str, Any]] = {
    PAPER_20260903_02_ID: PAPER_20260903_02,
}
PAPER_OPEN_BOOK_ONLY_TICKETS = frozenset({PAPER_20260903_02_ID})

PATH_STEPS = ("trader_proposal", "control_engine", "internal_simulator")

REFUSE_LIVE_OR_BROKER_PORT = "REFUSE_LIVE_OR_BROKER_PORT"
UNKNOWN_NAMED_PAPER_TICKET = "UNKNOWN_NAMED_PAPER_TICKET"


def named_paper_ticket(ticket_id: str) -> dict[str, Any]:
    """Return a copy of a Board paper ticket. LIVE/BROKER_PAPER are refused."""
    key = str(ticket_id or "").strip()
    if key not in NAMED_PAPER_TICKETS:
        raise RuntimeError(UNKNOWN_NAMED_PAPER_TICKET)
    ticket = dict(NAMED_PAPER_TICKETS[key])
    port = str(ticket.get("execution_port") or "SIMULATOR").upper()
    if port in {"LIVE", "BROKER_PAPER"}:
        raise RuntimeError(REFUSE_LIVE_OR_BROKER_PORT)
    ticket["execution_port"] = "SIMULATOR"
    return ticket


def run_propose_paper_ticket(
    session: Session,
    employee: Employee,
    *,
    order: dict[str, Any] | None = None,
    at=None,
    started_by: str = "cli",
) -> dict[str, Any]:
    """Propose a paper ticket as the Trader. Engine permit/deny. No AI."""
    if employee.slug != TRADER_SLUG:
        raise RuntimeError(ONLY_TRADER_MAY_PROPOSE)

    now = at or now_london()
    ticket = dict(LEGAL_PAPER_TICKET if order is None else order)
    ticket.setdefault("symbol", LEGAL_PAPER_TICKET["symbol"])
    ticket.setdefault("side", LEGAL_PAPER_TICKET["side"])
    ticket.setdefault("execution_port", "SIMULATOR")
    proposal_id = str(uuid.uuid4())
    ticket["proposal_id"] = proposal_id

    fills_before = session.query(PaperFill).count()
    filled_orders_before = session.query(PaperOrder).filter_by(status="FILLED").count()

    port = ExecutionPort(session)
    decision: Decision = port.place_order(
        actor_id=employee.id,
        actor_type="employee",
        order=ticket,
        at=now,
    )

    fills_after = session.query(PaperFill).count()
    filled_orders_after = session.query(PaperOrder).filter_by(status="FILLED").count()
    filled = bool(decision.allowed) and fills_after > fills_before

    brain = EmployeeBrain(session)
    invocation = brain.invocation(employee)
    artefact_id = str(decision.details.get("order_id") or proposal_id)
    brain.record_invocation(
        employee,
        skill_name=SKILL_NAME,
        artefact_id=artefact_id,
        invocation=invocation,
    )

    closed = paper_execution_is_closed(session)
    reached = "control_engine"
    if filled:
        reached = "internal_simulator"
    path = {
        "steps": list(PATH_STEPS),
        "reached": reached,
        "next_on_allow": "internal_simulator",
        "filled": filled,
        "gate": None if decision.allowed else decision.reason,
        "closed_gate_on_engine": (not decision.allowed)
        and decision.reason == PAPER_EXECUTION_CLOSED_REASON,
        "simulator_fill_invoked": filled,
        "note": (
            "Trader proposes. ControlEngine permit/deny is authoritative. "
            "If allowed, PaperFillSimulator.fill updates the paper ledger. "
            "While PAPER execution is CLOSED the engine DENY before fill. "
            "After Grand Opening PAPER a legal ticket may fill in the simulator."
        ),
    }

    payload = {
        "proposal_id": proposal_id,
        "skill": SKILL_NAME,
        "skill_version": SKILL_VERSION,
        "proposer_slug": employee.slug,
        "proposer_display_name": employee.display_name,
        "order": ticket,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "filled": filled,
        "paper_fills": filled,
        "live_fills": False,
        "started_by": started_by,
        "path": path,
        "ai_called": False,
        "source": ADDENDUM_I_LABEL,
    }
    session.add(
        Evidence(
            kind="paper_ticket_proposed",
            actor=employee.id,
            payload=json.dumps(payload, default=str),
            created_at=now_london(),
        )
    )
    session.commit()

    return {
        "proposed": True,
        "proposal_id": proposal_id,
        "skill": SKILL_NAME,
        "skill_version": SKILL_VERSION,
        "ai_called": False,
        "llm_task": None,
        "proposer": {
            "slug": employee.slug,
            "display_name": employee.display_name or staff_display_for_slug(TRADER_SLUG),
            "person_name": employee.person_name,
            "department": employee.department,
            "actor_type": "employee",
        },
        "order": ticket,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "details": decision.details,
        "filled": filled,
        "paper_fills": filled,
        "live_fills": False,
        "fills_delta": fills_after - fills_before,
        "filled_orders_delta": filled_orders_after - filled_orders_before,
        "paper_execution_closed": closed,
        "paper_execution": "CLOSED" if closed else "OPEN",
        "trading_mode": "LIVE_BLOCKED",
        "broker_paper_loaded": bool(BROKER_PAPER_LOADED),
        "live_adapter_loaded": bool(LIVE_ADAPTER_LOADED) or bool(LIVE_PORT_LOADED),
        "first_paper_trade_path_implemented": True,
        "grand_opening_not_performed": False,
        "grand_opening_paper_done": True,
        "path": path,
        "started_by": started_by,
        "daemon": False,
        "sample_not_a_live_trade": True,
        "is_live_trade": False,
        "is_live_approval": False,
        "source": ADDENDUM_I_LABEL,
        "note": (
            "Chris Adeyemi · Trader proposed a paper ticket. ControlEngine "
            "permit/deny is authoritative. Internal simulator fills only if "
            "the engine allows. After Grand Opening PAPER a legal allow-list "
            "practice order may fill in the internal simulator. LIVE stays off."
        ),
    }
