"""Deterministic control engine. Employees propose; the engine permits or denies.

LIVE adapter is not loaded unless trading_mode is LIVE and a Board approval exists.
This slice never loads a live adapter. Unknown tickers and gold deny.
Numeric limits are Board Addendum A 2026-08-27 (Board-set). Missing limits deny.
PAPER allow-list is Board Addendum E 2026-08-27. Employees cannot write control tables.

trading_mode stays LIVE_BLOCKED. Internal paper fill simulator is the paper ledger.
Do not load LIVE or BROKER_PAPER.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.addendum_a import (
    ADDENDUM_A_LABEL,
    CURRENCY,
    TIMEZONE,
    addendum_a_public,
)
from varma.controls.addendum_c import (
    ADDENDUM_C_LABEL,
    addendum_c_public,
    paper_desk_open,
    paper_session_status,
)
from varma.controls.addendum_e import addendum_e_public
from varma.controls.addendum_f import addendum_f_public
from varma.db.models import (
    AllowListInstrument,
    BoardApproval,
    ControlSetting,
    ControlState,
    Evidence,
    NumericLimit,
    Permission,
)

LIVE_ADAPTER_LOADED = False  # hard invariant for this slice and default environments
BROKER_PAPER_LOADED = False  # hard invariant — BROKER_PAPER remains UNLOADED. No broker fills.

TRADING_MODES = ("PAPER", "EVALUATION", "LIVE_BLOCKED", "LIVE")
REQUIRED_LIMIT_KEYS = (
    "simulated_capital",
    "max_position",
    "max_daily_loss",
    "max_orders_per_day",
    "kill_switch_equity_floor",
    "kill_switch_daily_pnl_floor",
)

LIMIT_WRITE_FIELDS = set(REQUIRED_LIMIT_KEYS) | {
    "numeric_limits",
    "allow_list",
    "kill_switch",
    "evaluation_policy",
    "paper_session",
    "addendum_c",
    "control_settings",
}


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

    def limit_value(self, key: str) -> float | None:
        row = self.session.get(NumericLimit, key)
        if row is None or row.value in (None, ""):
            return None
        return float(row.value)

    def limit_rows(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for key in REQUIRED_LIMIT_KEYS:
            row = self.session.get(NumericLimit, key)
            if row is None:
                continue
            items.append(
                {
                    "key": key,
                    "value": row.value,
                    "numeric_value": float(row.value) if row.value not in (None, "") else None,
                    "unit": row.unit or "",
                    "set_by": row.set_by,
                    "set_at": row.set_at.isoformat() if row.set_at else None,
                    "source": row.source or ADDENDUM_A_LABEL,
                    "board_set": True,
                }
            )
        return items

    def setting_rows(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        rows = self.session.query(ControlSetting).order_by(ControlSetting.key.asc()).all()
        for row in rows:
            items.append(
                {
                    "key": row.key,
                    "value": row.value,
                    "unit": row.unit or "",
                    "set_by": row.set_by,
                    "set_at": row.set_at.isoformat() if row.set_at else None,
                    "source": row.source or ADDENDUM_C_LABEL,
                    "board_set": True,
                }
            )
        return items

    def has_permission(self, subject_id: str, action: str) -> bool:
        row = (
            self.session.query(Permission)
            .filter_by(subject_type="employee", subject_id=subject_id, action=action)
            .one_or_none()
        )
        return bool(row and row.allowed)

    def broker_paper_loaded(self) -> bool:
        return BROKER_PAPER_LOADED

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

    def place_order(
        self,
        *,
        actor_id: str,
        actor_type: str,
        order: dict[str, Any],
        at=None,
    ) -> Decision:
        """Employees propose. Empty allow-list, LIVE, kill switch, limits, and closed session deny.

        When all gates pass, the internal paper fill simulator is the paper ledger.
        BROKER_PAPER and LIVE remain UNLOADED. trading_mode stays LIVE_BLOCKED.
        """
        now = at or now_london()
        state = self.state()
        symbol = str(order.get("symbol") or "")
        execution_port = str(order.get("execution_port") or "SIMULATOR")

        if actor_type != "employee" and actor_type != "board_member":
            return self._deny("UNKNOWN_ACTOR", actor_id, order)

        if actor_type == "employee" and not self.has_permission(actor_id, "place_order"):
            return self._deny("NO_PERMISSION", actor_id, order)

        if execution_port == "BROKER_PAPER":
            # Do not construct PaperBrokerAdapter. Port remains UNLOADED. No broker fills.
            return self._deny("BROKER_PAPER_NOT_LOADED", actor_id, order)

        if execution_port == "LIVE":
            if state.trading_mode != "LIVE":
                return self._deny("LIVE_BLOCKED", actor_id, order)
            if not self.live_adapter_loaded():
                return self._deny("LIVE_ADAPTER_NOT_LOADED", actor_id, order)

        if state.trading_mode == "LIVE":
            return self._deny("SIMULATOR_DENIED_WHEN_LIVE", actor_id, order)

        if state.trading_mode == "LIVE_BLOCKED" and execution_port != "SIMULATOR":
            return self._deny("LIVE_BLOCKED", actor_id, order)

        from varma.controls.kill_switch import maybe_auto_trip

        maybe_auto_trip(self.session, actor_id=actor_id)
        state = self.state()
        if state.kill_switch:
            return self._deny("KILL_SWITCH", actor_id, order)

        # Gold is never an execution universe, even if someone writes it onto the list.
        if symbol.upper() in {"XAU", "XAUUSD", "GOLD", "GC"}:
            return self._deny("GOLD_NOT_AUTHORISED", actor_id, order)

        # Even the internal simulator requires a Board-set allow-list and limits.
        allow = self.allow_list_symbols()
        if not allow:
            return self._deny("EMPTY_ALLOW_LIST", actor_id, order)

        if symbol not in allow:
            return self._deny("SYMBOL_NOT_ON_ALLOW_LIST", actor_id, order)

        missing = self.missing_limits()
        if missing:
            return self._deny("MISSING_NUMERIC_LIMITS", actor_id, order, {"missing": missing})

        notional = self._requested_notional_gbp(order)
        max_position = self.limit_value("max_position")
        if max_position is not None and notional > max_position:
            return self._deny(
                "MAX_POSITION_EXCEEDED",
                actor_id,
                order,
                {"notional_gbp": notional, "max_position": max_position, "currency": CURRENCY},
            )

        from varma.paper.ledger import PaperLedger

        ledger = PaperLedger(self.session)
        ledger.ensure_account(at=now)
        max_orders = self.limit_value("max_orders_per_day")
        if max_orders is not None and ledger.orders_today(at=now) >= int(max_orders):
            return self._deny(
                "MAX_ORDERS_PER_DAY",
                actor_id,
                order,
                {"orders_today": ledger.orders_today(at=now), "max_orders_per_day": int(max_orders)},
            )

        max_daily_loss = self.limit_value("max_daily_loss")
        pnl = ledger.london_day_pnl(at=now)
        if max_daily_loss is not None and pnl <= -abs(max_daily_loss):
            maybe_auto_trip(self.session, actor_id=actor_id)
            return self._deny(
                "MAX_DAILY_LOSS",
                actor_id,
                order,
                {"london_day_pnl_gbp": pnl, "max_daily_loss": max_daily_loss},
            )

        session_status = paper_session_status(now)
        if not paper_desk_open(now):
            reason = session_status.get("closed_reason") or "PAPER_SESSION_CLOSED"
            return self._deny(
                reason,
                actor_id,
                order,
                {
                    "paper_session": session_status,
                    "overnight": bool(session_status.get("overnight")),
                    "flatten_at": session_status.get("flatten_at"),
                    "source": ADDENDUM_C_LABEL,
                },
            )

        if execution_port != "SIMULATOR":
            return self._deny("EXECUTION_PORT_NOT_SIMULATOR", actor_id, order)

        from varma.paper.simulator import PaperFillSimulator

        decision = PaperFillSimulator(self.session).fill(actor_id=actor_id, order=order, at=now)
        maybe_auto_trip(self.session, actor_id=actor_id)
        return decision

    def _requested_notional_gbp(self, order: dict[str, Any]) -> float:
        raw = order.get("notional_gbp")
        if raw not in (None, ""):
            return abs(float(raw))
        quantity = abs(float(order.get("quantity") or 0))
        from varma.paper.simulator import PaperFillSimulator

        mid = PaperFillSimulator(self.session).mid_gbp(str(order.get("symbol") or ""))
        return quantity * mid

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
        if field == "trading_mode" and value == "PAPER":
            return Decision(
                False,
                "TRADING_MODE_STAYS_LIVE_BLOCKED_PAPER_LEDGER_IS_INTERNAL_SIMULATOR",
            )
        if field == "allow_list":
            return Decision(False, "ALLOW_LIST_IS_BOARD_ADDENDUM_E_EMPLOYEES_CANNOT_WRITE")
        if field in LIMIT_WRITE_FIELDS:
            # Board Addendum A already wrote the numeric limits. Generic write is not
            # the kill-switch endpoint. Employees never reach here.
            return Decision(False, "USE_BOARD_ADDENDUM_OR_KILL_SWITCH_ENDPOINT")
        return Decision(False, "CONTROL_MUTATION_NOT_ENABLED_IN_THIS_SLICE")

    def snapshot(self) -> dict[str, Any]:
        state = self.state()
        from varma.controls.kill_switch import kill_switch_state

        return {
            "trading_mode": state.trading_mode,
            "kill_switch": state.kill_switch,
            "kill_switch_state": kill_switch_state(self.session),
            "allow_list": self.allow_list_symbols(),
            "allow_list_empty": len(self.allow_list_symbols()) == 0,
            "missing_numeric_limits": self.missing_limits(),
            "numeric_limits": self.limit_rows(),
            "currency": CURRENCY,
            "timezone": TIMEZONE,
            "addendum": addendum_a_public(),
            "addendum_c": addendum_c_public(),
            "addendum_e": addendum_e_public(),
            "addendum_f": addendum_f_public(),
            "paper_session": paper_session_status(),
            "control_settings": self.setting_rows(),
            "live_adapter_loaded": self.live_adapter_loaded(),
            "broker_paper_loaded": BROKER_PAPER_LOADED,
            "live_gate": "PAPER → EVALUATION → LIVE-TRADING RECOMMENDATION → BOARD REVIEW → EXPLICIT BOARD APPROVAL → LIVE",
            "note": (
                "Silence, elapsed time, paper success, and employee confidence are not approval. "
                "PAPER allow-list is Board Addendum E. trading_mode stays LIVE_BLOCKED. "
                "Internal simulator is the paper ledger. LIVE and BROKER_PAPER remain UNLOADED."
            ),
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
