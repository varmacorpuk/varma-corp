"""ExecutionPort. LIVE is not loaded. No brokerage. Employees propose; engine denies."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.engine import ControlEngine, Decision


class LiveBrokerAdapter:
    """Must not be instantiated unless trading_mode is LIVE and Board approval exists."""

    def __init__(self) -> None:
        raise RuntimeError("LIVE adapter is not loaded. trading_mode is not LIVE.")


class ExecutionPort:
    def __init__(self, session: Session) -> None:
        self.engine = ControlEngine(session)

    def available_ports(self) -> list[str]:
        return ["SIMULATOR"]  # BROKER_PAPER and LIVE are not loaded

    def place_order(self, *, actor_id: str, actor_type: str, order: dict[str, Any]) -> Decision:
        order = dict(order)
        order.setdefault("execution_port", "SIMULATOR")
        if order["execution_port"] == "LIVE":
            # Do not construct LiveBrokerAdapter.
            return self.engine.place_order(actor_id=actor_id, actor_type=actor_type, order=order)
        return self.engine.place_order(actor_id=actor_id, actor_type=actor_type, order=order)
