"""Board-usable kill switch. Board Member only. Employees cannot reset it.

Halt if paper equity <= 800 GBP OR London-day P&L <= -50 GBP
(Board Addendum A 2026-08-27), or when the Board Member triggers halt
without an AI employee.

On halt: cancel open PAPER orders only; never load LIVE; never flatten live
(there is no live).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.addendum_a import (
    ADDENDUM_A_LABEL,
    KILL_SWITCH_DAILY_PNL_FLOOR,
    KILL_SWITCH_EQUITY_FLOOR,
    KILL_SWITCH_HALT_IF,
    KILL_SWITCH_ON_HALT,
)
from varma.controls.engine import LIVE_ADAPTER_LOADED, Decision
from varma.db.models import ControlState, Evidence
from varma.paper.ledger import PaperLedger
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED


def kill_switch_state(session: Session) -> dict[str, Any]:
    state = session.get(ControlState, 1)
    ledger = PaperLedger(session)
    equity = ledger.equity()
    pnl = ledger.london_day_pnl()
    halted = bool(state.kill_switch) if state else False
    return {
        "halted": halted,
        "board_member_can_trigger": True,
        "employees_cannot_trigger": True,
        "employees_cannot_reset": True,
        "ai_employee_not_required": True,
        "equity_floor_gbp": KILL_SWITCH_EQUITY_FLOOR,
        "daily_pnl_floor_gbp": KILL_SWITCH_DAILY_PNL_FLOOR,
        "paper_equity_gbp": equity,
        "london_day_pnl_gbp": pnl,
        "equity_floor_breached": equity <= KILL_SWITCH_EQUITY_FLOOR,
        "daily_pnl_floor_breached": pnl <= KILL_SWITCH_DAILY_PNL_FLOOR,
        "halt_if": KILL_SWITCH_HALT_IF,
        "on_halt": KILL_SWITCH_ON_HALT,
        "cancels_open_paper_orders_only": True,
        "loads_live": False,
        "flattens_live": False,
        "live_adapter_loaded": LIVE_ADAPTER_LOADED,
        "broker_paper_loaded": BROKER_PAPER_LOADED,
        "live_port_loaded": LIVE_PORT_LOADED,
        "source": ADDENDUM_A_LABEL,
        "board_set": True,
        "values_invented": False,
    }


def trip_kill_switch(
    session: Session,
    *,
    actor_id: str,
    reason: str,
) -> dict[str, Any]:
    """Halt paper. Cancel OPEN paper orders only. Never load or flatten live."""
    state = session.get(ControlState, 1)
    if state is None:
        raise RuntimeError("control_state missing")
    already = bool(state.kill_switch)
    state.kill_switch = True
    state.updated_at = now_london()
    state.updated_by = actor_id
    cancelled = PaperLedger(session).cancel_open_paper_orders(reason=f"KILL_SWITCH:{reason}")
    session.commit()
    payload = {
        "reason": reason,
        "already_halted": already,
        "halted": True,
        "cancelled_open_paper_orders": cancelled,
        "loads_live": False,
        "flattens_live": False,
        "live_adapter_loaded": LIVE_ADAPTER_LOADED,
        "broker_paper_loaded": BROKER_PAPER_LOADED,
        "on_halt": KILL_SWITCH_ON_HALT,
        "source": ADDENDUM_A_LABEL,
    }
    session.add(
        Evidence(
            kind="kill_switch_halted",
            actor=actor_id,
            payload=json.dumps(payload, default=str),
            created_at=now_london(),
        )
    )
    session.commit()
    return payload


def reset_kill_switch(session: Session, *, actor_id: str, actor_type: str) -> Decision:
    if actor_type != "board_member":
        session.add(
            Evidence(
                kind="kill_switch_reset_denied",
                actor=actor_id,
                payload=json.dumps({"reason": "EMPLOYEE_CANNOT_RESET_KILL_SWITCH"}),
                created_at=now_london(),
            )
        )
        session.commit()
        return Decision(False, "EMPLOYEE_CANNOT_RESET_KILL_SWITCH")
    state = session.get(ControlState, 1)
    if state is None:
        raise RuntimeError("control_state missing")
    state.kill_switch = False
    state.updated_at = now_london()
    state.updated_by = actor_id
    session.commit()
    session.add(
        Evidence(
            kind="kill_switch_reset",
            actor=actor_id,
            payload=json.dumps({"halted": False, "source": ADDENDUM_A_LABEL}),
            created_at=now_london(),
        )
    )
    session.commit()
    return Decision(True, "KILL_SWITCH_RESET", {"halted": False})


def maybe_auto_trip(session: Session, *, actor_id: str) -> dict[str, Any] | None:
    """Trip if Addendum A floors are breached. Does not run from observability."""
    state = session.get(ControlState, 1)
    if state is None:
        return None
    ledger = PaperLedger(session)
    equity = ledger.equity()
    pnl = ledger.london_day_pnl()
    if equity <= KILL_SWITCH_EQUITY_FLOOR:
        return trip_kill_switch(session, actor_id=actor_id, reason="PAPER_EQUITY_FLOOR")
    if pnl <= KILL_SWITCH_DAILY_PNL_FLOOR:
        return trip_kill_switch(session, actor_id=actor_id, reason="LONDON_DAY_PNL_FLOOR")
    return None
