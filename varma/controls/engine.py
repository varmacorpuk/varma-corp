"""Deterministic control engine. Employees propose; the engine permits or denies.

LIVE adapter is not loaded unless trading_mode is LIVE and a Board approval exists.
This slice never loads a live adapter. Unknown tickers and gold deny.
Numeric limits are Board Addendum A 2026-08-27 (Board-set; unused until open).
PAPER allow-list is Board Addendum E 2026-08-27. Employees cannot write control tables.
Board Addendum I 2026-08-27: two-opening rule. Grand Opening PAPER happened
(Hari explicit yes, 3 Sep 2026). Practice / paper only. LIVE still blocked.
Board Addendum K 2026-09-03: after London cash shuts, deny SHEL.L / AZN.L /
ULVR.L only. CEO desk 02F binds LSE flatten to the London closing auction
16:30–16:35; US names still flatten at US regular cash close. split_flatten_clocks
is true. The LSE auction exit cannot be dropped independently of the opening buy.

trading_mode stays LIVE_BLOCKED. Do not load LIVE or BROKER_PAPER.
The first paper-trade PATH exists (Trader proposal → ControlEngine →
internal simulator). Opening is a Board-only write_control. Employees
cannot open or close the firm.
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
from varma.controls.addendum_l import addendum_l_public
from varma.controls.addendum_i import (
    ADDENDUM_I_LABEL,
    FIRM_CLOSED_REASON,
    FIRM_OPEN_WRITE_FIELDS,
    GRAND_OPENING_LIVE_NOT_IMPLEMENTED_REASON,
    GRAND_OPENING_PAPER_LABEL,
    GRAND_OPENING_PAPER_REASON,
    LIVE_OPEN_WRITE_FIELDS,
    PAPER_EXECUTION_CLOSED_BY_BOARD_REASON,
    PAPER_EXECUTION_CLOSED_REASON,
    PAPER_OPEN_WRITE_FIELDS,
    SIMULATED_CAPITAL_STATUS_KEY,
    addendum_i_public,
    apply_grand_opening_paper,
    force_paper_execution_closed,
    paper_execution_is_closed,
    paper_open_intent,
)
from varma.controls.addendum_j import (
    BACKUP_WRITE_FIELDS,
    addendum_j_public,
)
from varma.controls.addendum_k import (
    ADDENDUM_K_LABEL,
    ADDENDUM_K_WRITE_FIELDS,
    LSE_AFTER_LONDON_CASH_CLOSE_REASON,
    LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE,
    addendum_k_public,
)
from varma.controls.lse_session import (
    LSE_SESSION_RULE_REASON,
    LSE_WRITE_FIELDS,
    lse_hold_blocks,
    lse_session_public,
    lse_session_rule_is_unset,
)
from varma.controls.venue_flatten import (
    SPLIT_FLATTEN_CLOCKS,
    bound_session_exit,
    ceo_desk_public,
    risk_02f_public,
)
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
    "addendum_i",
    "addendum_j",
    "addendum_k",
    "control_settings",
} | set(FIRM_OPEN_WRITE_FIELDS) | set(BACKUP_WRITE_FIELDS) | set(LSE_WRITE_FIELDS) | set(
    ADDENDUM_K_WRITE_FIELDS
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

    def paper_execution_closed(self) -> bool:
        return paper_execution_is_closed(self.session)

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
        """Employees propose. LIVE, gold, unknown tickers, and PAPER-closed deny.

        Board Addendum I: two-opening rule. While paper is CLOSED, simulator
        DENY all fills, even for allow-listed tickers. Deny reason is
        PAPER_EXECUTION_CLOSED (FIRM_CLOSED alias). After Grand Opening PAPER,
        a legal allow-list practice order may fill in the internal simulator
        when in session and within Addendum A limits. LIVE stays blocked.
        BROKER_PAPER and LIVE remain UNLOADED. AI never enforces this.
        """
        now = at or now_london()
        state = self.state()
        symbol = str(order.get("symbol") or "")
        execution_port = str(order.get("execution_port") or "SIMULATOR")

        if actor_type != "employee" and actor_type != "board_member":
            return self._deny("UNKNOWN_ACTOR", actor_id, order)

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

        closed = self.paper_execution_closed()
        if not closed:
            maybe_auto_trip(self.session, actor_id=actor_id)
        state = self.state()
        if state.kill_switch:
            return self._deny("KILL_SWITCH", actor_id, order)

        # Gold is never an execution universe, even if someone writes it onto the list.
        if symbol.upper() in {"XAU", "XAUUSD", "GOLD", "GC"}:
            return self._deny("GOLD_NOT_AUTHORISED", actor_id, order)

        allow = self.allow_list_symbols()
        if allow and symbol not in allow:
            return self._deny("SYMBOL_NOT_ON_ALLOW_LIST", actor_id, order)

        # Addendum K: after London cash shut, deny SHEL.L / AZN.L / ULVR.L only.
        # Checked before CLOSED so the London-shut reason is visible even if
        # paper is later closed again. During London open, K does not block.
        if lse_hold_blocks(self.session, symbol, at=now):
            if lse_session_rule_is_unset(self.session):
                return self._deny_lse_session_unset(actor_id, order)
            return self._deny_lse_after_london_cash_close(actor_id, order)

        if closed:
            return self._deny_paper_closed(actor_id, order)

        if actor_type == "employee" and not self.has_permission(actor_id, "place_order"):
            return self._deny("NO_PERMISSION", actor_id, order)

        if not allow:
            return self._deny("EMPTY_ALLOW_LIST", actor_id, order)

        missing = self.missing_limits()
        if missing:
            return self._deny("MISSING_NUMERIC_LIMITS", actor_id, order, {"missing": missing})

        # Session check before sizing so overnight/closed fires before cap math.
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

        notional = self._requested_notional_gbp(order)
        max_position = self.limit_value("max_position")
        if max_position is not None and notional > max_position:
            return self._deny(
                "MAX_POSITION_EXCEEDED",
                actor_id,
                order,
                {"notional_gbp": notional, "max_position": max_position, "currency": CURRENCY},
            )
        if max_position is not None:
            from varma.paper.quote import mark_gbp
            from varma.db.models import PaperPosition

            pos = self.session.get(PaperPosition, symbol)
            if pos is not None and pos.quantity != 0:
                existing = abs(float(pos.quantity)) * mark_gbp(symbol)
                side = str(order.get("side") or "buy").lower()
                adding = (side == "buy" and pos.quantity > 0) or (
                    side == "sell" and pos.quantity < 0
                )
                if adding and existing + notional > max_position:
                    return self._deny(
                        "MAX_POSITION_EXCEEDED",
                        actor_id,
                        order,
                        {
                            "notional_gbp": notional,
                            "existing_name_gbp": existing,
                            "max_position": max_position,
                            "currency": CURRENCY,
                        },
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

        if execution_port != "SIMULATOR":
            return self._deny("EXECUTION_PORT_NOT_SIMULATOR", actor_id, order)

        from varma.paper.simulator import PaperFillSimulator

        decision = PaperFillSimulator(self.session).fill(actor_id=actor_id, order=order, at=now)
        maybe_auto_trip(self.session, actor_id=actor_id)
        if decision.allowed:
            decision.details.update(bound_session_exit(symbol))
            decision.details["split_flatten_clocks"] = SPLIT_FLATTEN_CLOCKS
            decision.details["risk_02f"] = risk_02f_public()
        return decision

    def _requested_notional_gbp(self, order: dict[str, Any]) -> float:
        from varma.controls.addendum_a import MAX_POSITION
        from varma.paper.quote import paper_order_economics

        econ = paper_order_economics(order, max_position_gbp=MAX_POSITION)
        if econ.fx and not order.get("fx_quote"):
            order["fx_quote"] = econ.fx.to_dict()
        return econ.cap_check_gbp

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
        # Board Member is the sole writer. Grand Opening PAPER is a Board control
        # write. Grand Opening LIVE is not given and stays unimplemented.
        # Silence is not approval. trading_mode stays LIVE_BLOCKED.
        if field == "trading_mode" and value == "LIVE":
            return Decision(False, "LIVE_TRANSITION_NOT_IMPLEMENTED_REQUIRES_BOARD_APPROVAL_ROW")
        if field == "trading_mode" and value == "PAPER":
            return Decision(
                False,
                "TRADING_MODE_STAYS_LIVE_BLOCKED_PAPER_LEDGER_IS_INTERNAL_SIMULATOR",
            )
        if field in LIVE_OPEN_WRITE_FIELDS:
            return Decision(False, GRAND_OPENING_LIVE_NOT_IMPLEMENTED_REASON)
        if field == "addendum_i":
            return Decision(False, "ADDENDUM_I_IS_THE_TWO_OPENING_RULE_USE_PAPER_EXECUTION")
        if field == SIMULATED_CAPITAL_STATUS_KEY:
            return Decision(False, "USE_BOARD_ADDENDUM_OR_KILL_SWITCH_ENDPOINT")
        if field in PAPER_OPEN_WRITE_FIELDS:
            intent = paper_open_intent(value)
            if intent is True:
                apply_grand_opening_paper(self.session, actor_id=actor_id)
                self._evidence(
                    "grand_opening_paper",
                    actor_id,
                    {
                        "field": field,
                        "value": value,
                        "paper_execution": "OPEN",
                        "grand_opening_live": "not",
                        "trading_mode": "LIVE_BLOCKED",
                        "source": GRAND_OPENING_PAPER_LABEL,
                    },
                )
                return Decision(True, GRAND_OPENING_PAPER_REASON, {"paper_execution": "OPEN"})
            if intent is False:
                force_paper_execution_closed(self.session, actor_id=actor_id)
                self._evidence(
                    "paper_execution_closed_by_board",
                    actor_id,
                    {
                        "field": field,
                        "value": value,
                        "paper_execution": "CLOSED",
                        "grand_opening_live": "not",
                        "trading_mode": "LIVE_BLOCKED",
                        "source": ADDENDUM_I_LABEL,
                    },
                )
                return Decision(
                    True,
                    PAPER_EXECUTION_CLOSED_BY_BOARD_REASON,
                    {"paper_execution": "CLOSED"},
                )
            return Decision(False, "UNRECOGNISED_PAPER_EXECUTION_VALUE")
        if field == "allow_list":
            return Decision(False, "ALLOW_LIST_IS_BOARD_ADDENDUM_E_EMPLOYEES_CANNOT_WRITE")
        if field in LIMIT_WRITE_FIELDS:
            # Board Addendum A already wrote the numeric limits. Generic write is not
            # the kill-switch endpoint. Employees never reach here.
            return Decision(False, "USE_BOARD_ADDENDUM_OR_KILL_SWITCH_ENDPOINT")
        return Decision(False, "CONTROL_MUTATION_NOT_ENABLED_IN_THIS_SLICE")

    def constraints_hint(self) -> dict[str, Any]:
        """Compact, INFORMATIONAL control hint for AI context (PR #2).

        This is a small projection of the authoritative control state so an AI
        employee can *know* the current constraints. It is NOT an enforcement
        surface: every deterministic control check in ``place_order`` /
        ``write_control`` still runs exactly as before. The AI never enforces
        controls. Do not weaken any deny logic, gate, or Addendum by reading this.
        """
        state = self.state()
        allow = self.allow_list_symbols()
        paper_closed = self.paper_execution_closed()
        can_place_orders = (
            not paper_closed
            and state.trading_mode != "LIVE"
            and len(allow) > 0
            and not state.kill_switch
        )
        risk_02f = risk_02f_public()
        return {
            "can_place_orders": can_place_orders,
            "paper_trading": "CLOSED" if paper_closed else "OPEN",
            "live_trading": "BLOCKED" if state.trading_mode != "LIVE" else "LIVE",
            "trading_mode": state.trading_mode,
            "allow_list_empty": len(allow) == 0,
            "broker_paper_loaded": BROKER_PAPER_LOADED,
            "live_adapter_loaded": self.live_adapter_loaded(),
            "kill_switch": bool(state.kill_switch),
            "firm_open": not paper_closed,
            "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
            "risk_02f": risk_02f["id"],
            "risk_02f_bound": True,
            "lse_flatten_at": risk_02f["lse_flatten_at"],
            "us_flatten_at": risk_02f["us_flatten_at"],
            "authoritative_source": "deterministic ControlEngine",
            "note": (
                "Informational only. Controls are enforced deterministically by "
                "ControlEngine; the AI does not enforce them. Full detail is in "
                "GET /observability and the control tables."
            ),
        }

    def risk_02f(self) -> dict[str, Any]:
        """Bound 02F state. Risk re-clears from engine snapshot, not from chat."""
        return risk_02f_public()

    def bound_session_exit(self, symbol: str) -> dict[str, Any]:
        return bound_session_exit(symbol)

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
            "addendum_l": addendum_l_public(),
            "addendum_f": addendum_f_public(),
            "addendum_i": addendum_i_public(self.session),
            "addendum_j": addendum_j_public(),
            "addendum_k": addendum_k_public(),
            "lse_session": lse_session_public(self.session),
            "ceo_desk": ceo_desk_public(),
            "risk_02f": risk_02f_public(),
            "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
            "paper_execution": "CLOSED" if self.paper_execution_closed() else "OPEN",
            "paper_execution_closed": self.paper_execution_closed(),
            "paper_session": paper_session_status(),
            "control_settings": self.setting_rows(),
            "live_adapter_loaded": self.live_adapter_loaded(),
            "broker_paper_loaded": BROKER_PAPER_LOADED,
            "live_gate": "PAPER → EVALUATION → LIVE-TRADING RECOMMENDATION → BOARD REVIEW → EXPLICIT BOARD APPROVAL → LIVE",
            "note": (
                "Silence, elapsed time, paper success, and employee confidence are not approval. "
                "Board Addendum I is the two-opening rule. Grand Opening PAPER happened "
                "(Hari explicit yes, 3 Sep 2026). Practice / paper only. "
                "LIVE has not opened. The first paper-trade PATH exists "
                "(Trader proposal → ControlEngine → internal simulator). "
                "trading_mode stays LIVE_BLOCKED. LIVE and BROKER_PAPER remain UNLOADED."
            ),
        }

    def _deny(self, reason: str, actor_id: str, order: dict[str, Any], extra: dict | None = None) -> Decision:
        details = {"order": order, **(extra or {})}
        self._evidence("order_denied", actor_id, {"reason": reason, **details})
        return Decision(False, reason, details)

    def _deny_lse_session_unset(self, actor_id: str, order: dict[str, Any]) -> Decision:
        """Fail-closed LSE hold when the Board K rule is missing."""
        return self._deny(
            LSE_SESSION_RULE_REASON,
            actor_id,
            order,
            {
                "fail_closed": True,
                "session_rule": "UNSET",
                "cannot_silently_fill_at_grand_opening": True,
                "addendum_c_not_rewritten": True,
                "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
                "risk_02f": risk_02f_public(),
                "risk_02f_bound": True,
                "flatten_at": "US_REGULAR_CASH_CLOSE",
                "lse_flatten_at": "LONDON_CLOSING_AUCTION",
                "flatten_not_at": "LONDON_CASH_CLOSE",
                "invented_us_listings": False,
                "us_names_wait_on_grand_opening": True,
                "paper_execution_closed": self.paper_execution_closed(),
                "employees_cannot_write": True,
            },
        )

    def _deny_lse_after_london_cash_close(
        self, actor_id: str, order: dict[str, Any]
    ) -> Decision:
        """Board Addendum K: LSE three only, after London cash shut. Not flatten."""
        return self._deny(
            LSE_AFTER_LONDON_CASH_CLOSE_REASON,
            actor_id,
            order,
            {
                "session_rule": LSE_SESSION_RULE_DENY_AFTER_LONDON_CASH_CLOSE,
                "addendum_k": ADDENDUM_K_LABEL,
                "london_cash_close_is_not_flatten": True,
                "addendum_c_not_rewritten": True,
                "split_flatten_clocks": SPLIT_FLATTEN_CLOCKS,
                "risk_02f": risk_02f_public(),
                "risk_02f_bound": True,
                "lse_flatten_at": "LONDON_CLOSING_AUCTION",
                "flatten_at": "US_REGULAR_CASH_CLOSE",
                "flatten_not_at": "LONDON_CASH_CLOSE",
                "invented_us_listings": False,
                "us_names_not_denied_by_k": True,
                "paper_execution_closed": self.paper_execution_closed(),
                "not_grand_opening_live": True,
                "not_grand_opening": True,  # K is not a live opening
                "employees_cannot_write": True,
            },
        )

    def _deny_paper_closed(self, actor_id: str, order: dict[str, Any]) -> Decision:
        """PAPER_EXECUTION_CLOSED; FIRM_CLOSED is an alias, not a second reason."""
        return self._deny(
            PAPER_EXECUTION_CLOSED_REASON,
            actor_id,
            order,
            {
                "paper_execution": "CLOSED",
                "firm_closed": True,
                "firm_open": False,
                "alias": FIRM_CLOSED_REASON,
                "grand_opening_paper": addendum_i_public(self.session).get(
                    "grand_opening_paper", "not"
                ),
                "grand_opening_live": "not",
                "allow_list_cannot_fill_until_open": True,
                "addendum_a_unused_until_open": True,
                "simulated_capital_status": "FUTURE_PAPER_STARTING_BOOK_ONLY",
                "first_paper_trade_path_implemented": True,
                "source": ADDENDUM_I_LABEL,
            },
        )

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
