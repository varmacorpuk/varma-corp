"""Risk policy. This slice is a deny-path demo. Risk cannot approve LIVE."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.engine import ControlEngine, Decision

GOLD_SYMBOLS = {"XAU", "XAUUSD", "GOLD", "GC"}

UNSAFE_DEMO_PATH: dict[str, Any] = {
    "label": "DENY-PATH DEMO — not a live trade",
    "path_kind": "unsafe_live_gold_execution",
    "symbol": "XAUUSD",
    "side": "buy",
    "quantity": 1,
    "execution_port": "LIVE",
    "treat_sample_thesis_as_order": True,
    "note": (
        "Out-of-policy demo path: LIVE execution of gold, treating a SAMPLE thesis as an order. "
        "Gold is FUTURE SCOPE ONLY. trading_mode is LIVE_BLOCKED. Allow-list is empty. "
        "This is not a live trade."
    ),
}


class RiskPolicy:
    """Deterministic deny. Consults the control engine. Never approves LIVE in this slice."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.engine = ControlEngine(session)

    def review(self, *, actor_id: str, proposed: dict[str, Any]) -> Decision:
        reasons: list[str] = []
        symbol = str(proposed.get("symbol") or "")
        execution_port = str(proposed.get("execution_port") or "SIMULATOR")

        engine_decision = self.engine.place_order(
            actor_id=actor_id,
            actor_type="employee",
            order={
                "symbol": symbol,
                "side": proposed.get("side") or "buy",
                "quantity": proposed.get("quantity") or 0,
                "execution_port": execution_port,
            },
        )
        if not engine_decision.allowed:
            reasons.append(engine_decision.reason)

        if execution_port == "LIVE" or self.engine.state().trading_mode != "LIVE":
            if "LIVE_BLOCKED" not in reasons:
                reasons.append("LIVE_BLOCKED")

        if symbol.upper() in GOLD_SYMBOLS:
            if "GOLD_NOT_AUTHORISED" not in reasons:
                reasons.append("GOLD_NOT_AUTHORISED")

        if proposed.get("treat_sample_thesis_as_order"):
            reasons.append("SAMPLE_THESIS_IS_NOT_AN_ORDER")

        if self.engine.allow_list_symbols() == []:
            if "EMPTY_ALLOW_LIST" not in reasons:
                reasons.append("EMPTY_ALLOW_LIST")

        reasons.append("RISK_DENIED")
        # Unique, stable order
        seen: list[str] = []
        for r in reasons:
            if r not in seen:
                seen.append(r)
        return Decision(
            False,
            "RISK_DENIED",
            {
                "reasons": seen,
                "control_engine_reason": engine_decision.reason,
                "control_engine_allowed": engine_decision.allowed,
                "cannot_approve_live_trading": True,
            },
        )
