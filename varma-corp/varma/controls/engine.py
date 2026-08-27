"""Deterministic control engine. Employees propose; the engine permits or denies.

LIVE adapter is not loaded unless trading_mode is LIVE and a Board approval exists.
This slice never loads a live adapter. Empty allow-list cannot execute.
Missing numeric limits deny. Employees cannot write control tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import (
    AllowListInstrument,
    BoardApproval,
    ControlState,
    Evidence,
    NumericLimit,
    Permission,
)

LIVE_ADAPTER_LOADED = False  # hard invariant for this slice and default environments

TRADING_MODES = ("PAPER", "EVALUATION", "LIVE_BLOCKED", "LIVE")
REQUIRED_LIMIT_KEYS = (
    "simulated_capital",
    "max_position",
    "max_daily_loss",
    "max_orders_per_day",
    "kill_switch_threshold",
)


@dataclass
class Decision:
    allowed: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


class ControlEngine:
    def __init__(self, session: Session) -> None:
        self.session = session

    def state(self) -> ControlState:
        row = self.session.get(ControlState, 1)
        if row is None:
            raise RuntimeError("control_state missing")
        return row

    def allow_list_symbols(self) -> list[str]:
        return [r.symbol for r in self.session.query(AllowListInstrument).all()]

    def missing_limits(self) -> list[str]:
        missing: list[str] = []
        for key in REQUIRED_LIMIT_KEYS:
            row = self.session.get(NumericLimit, key)
            if row is None or row.value in (None, ""):
                missing.append(key)
        return missing

    def has_permission(self, subject_id: str, action: str) -> bool:
        row = (
            self.session.query(Permission)
            .filter_by(subject_type="employee", subject_id=subject_id, action=action)
            .one_or_none()
        )
        return bool(row and row.allowed)

    def live_adapter_loaded(self) -> bool:
        state = self.state()
        if state.trading_mode != "LIVE":
            return False
        approval = (
            self.session.query(BoardApproval)
            .filter_by(action="transition_to_live")
            .first()
        )
        if approval is None:
            return False
        return LIVE_ADAPTER_LOADED

    def place_order(self, *, actor_id: str, actor_type: str, order: dict[str, Any]) -> Decision:
        """Employees propose. Engine denies in this slice. Never executes live."""
        state = self.state()
        symbol = str(order.get("symbol") or "")
        execution_port = str(order.get("execution_port") or "SIMULATOR")

        if actor_type != "employee" and actor_type != "board_member":
            return self._deny("UNKNOWN_ACTOR", actor_id, order)

        if actor_type == "employee" and not self.has_permission(actor_id, "place_order"):
            return self._deny("NO_PERMISSION", actor_id, order)

        if state.kill_switch:
            return self._deny("KILL_SWITCH", actor_id, order)

        if execution_port == "LIVE" or state.trading_mode == "LIVE":
            if state.trading_mode != "LIVE":
                return self._deny("LIVE_BLOCKED", actor_id, order)
            if not self.live_adapter_loaded():
                return self._deny("LIVE_ADAPTER_NOT_LOADED", actor_id, order)

        if state.trading_mode == "LIVE_BLOCKED" and execution_port != "SIMULATOR":
            return self._deny("LIVE_BLOCKED", actor_id, order)

        # Even paper/simulator execution requires a Board-set allow-list and limits.
        allow = self.allow_list_symbols()
        if not allow:
            return self._deny("EMPTY_ALLOW_LIST", actor_id, order)

        if symbol not in allow:
            return self._deny("SYMBOL_NOT_ON_ALLOW_LIST", actor_id, order)

        if symbol.upper() in {"XAU", "XAUUSD", "GOLD", "GC"}:
            return self._deny("GOLD_NOT_AUTHORISED", actor_id, order)

        missing = self.missing_limits()
        if missing:
            return self._deny("MISSING_NUMERIC_LIMITS", actor_id, order, {"missing": missing})

        # This slice has no fill path. Reaching here still does not execute.
        return self._deny("EXECUTION_NOT_IMPLEMENTED_IN_THIS_SLICE", actor_id, order)

    def write_control(
        self,
        *,
        actor_id: str,
        actor_type: str,
        field: str,
        value: Any,
    ) -> Decision:
        if actor_type != "board_member":
            self._evidence(
                "control_write_denied",
                actor_id,
                {"field": field, "reason": "EMPLOYEE_CANNOT_WRITE_CONTROLS"},
            )
            return Decision(False, "EMPLOYEE_CANNOT_WRITE_CONTROLS")
        # Board writes are reserved actions; this slice does not implement LIVE transition.
        if field == "trading_mode" and value == "LIVE":
            return Decision(False, "LIVE_TRANSITION_NOT_IMPLEMENTED_REQUIRES_BOARD_APPROVAL_ROW")
        return Decision(False, "CONTROL_MUTATION_NOT_ENABLED_IN_THIS_SLICE")

    def snapshot(self) -> dict[str, Any]:
        state = self.state()
        return {
            "trading_mode": state.trading_mode,
            "kill_switch": state.kill_switch,
            "allow_list": self.allow_list_symbols(),
            "allow_list_empty": len(self.allow_list_symbols()) == 0,
            "missing_numeric_limits": self.missing_limits(),
            "live_adapter_loaded": self.live_adapter_loaded(),
            "live_gate": "PAPER → EVALUATION → LIVE-TRADING RECOMMENDATION → BOARD REVIEW → EXPLICIT BOARD APPROVAL → LIVE",
            "note": "Silence, elapsed time, paper success, and employee confidence are not approval.",
        }

    def _deny(self, reason: str, actor_id: str, order: dict[str, Any], extra: dict | None = None) -> Decision:
        details = {"order": order, **(extra or {})}
        self._evidence("order_denied", actor_id, {"reason": reason, **details})
        return Decision(False, reason, details)

    def _evidence(self, kind: str, actor: str, payload: dict[str, Any]) -> None:
        import json

        self.session.add(
            Evidence(
                kind=kind,
                actor=actor,
                payload=json.dumps(payload, default=str),
                created_at=now_london(),
            )
        )
        self.session.commit()
