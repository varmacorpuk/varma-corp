"""ExecutionPort. BROKER_PAPER and LIVE remain UNLOADED. No brokerage. No fills.

Employees propose; the control engine denies. This slice never constructs
paper or live adapters, never places fills, and never loads those ports.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.engine import ControlEngine, Decision

BROKER_PAPER_LOADED = False  # hard invariant for this slice
LIVE_PORT_LOADED = False  # hard invariant for this slice
UNLOADED_EXECUTION_PORTS = ("BROKER_PAPER", "LIVE")
AVAILABLE_EXECUTION_PORTS = ("SIMULATOR",)

BROKER_PAPER_NOT_LOADED_MESSAGE = (
    "BROKER_PAPER adapter is not loaded. Status: UNLOADED. No paper fills."
)
LIVE_NOT_LOADED_MESSAGE = "LIVE adapter is not loaded. trading_mode is not LIVE."


class PaperBrokerAdapter:
    """Must not be instantiated. BROKER_PAPER remains UNLOADED. No paper fills."""

    def __init__(self) -> None:
        raise RuntimeError(BROKER_PAPER_NOT_LOADED_MESSAGE)

    def place_order(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(BROKER_PAPER_NOT_LOADED_MESSAGE)


class LiveBrokerAdapter:
    """Must not be instantiated unless trading_mode is LIVE and Board approval exists."""

    def __init__(self) -> None:
        raise RuntimeError(LIVE_NOT_LOADED_MESSAGE)

    def place_order(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(LIVE_NOT_LOADED_MESSAGE)


def use_broker_paper_port(*args: Any, **kwargs: Any) -> None:
    """Using BROKER_PAPER is denied because the adapter is not loaded."""
    adapter = PaperBrokerAdapter()
    adapter.place_order(*args, **kwargs)


def use_live_port(*args: Any, **kwargs: Any) -> None:
    """Using LIVE is denied because the adapter is not loaded."""
    adapter = LiveBrokerAdapter()
    adapter.place_order(*args, **kwargs)


def construct_execution_port(name: str) -> Any:
    """Constructing BROKER_PAPER or LIVE is denied. SIMULATOR has no fill adapter."""
    port = str(name or "").upper()
    if port == "BROKER_PAPER":
        return PaperBrokerAdapter()
    if port == "LIVE":
        return LiveBrokerAdapter()
    raise RuntimeError(f"execution port {port!r} has no fill adapter in this slice")


def execution_port_status() -> dict[str, Any]:
    """Status only. No fills. BROKER_PAPER and LIVE remain UNLOADED."""
    return {
        "read_only": True,
        "source": "kernel",
        "fills": False,
        "paper_fills": False,
        "live_fills": False,
        "writes_controls": False,
        "available": list(AVAILABLE_EXECUTION_PORTS),
        "unloaded": list(UNLOADED_EXECUTION_PORTS),
        "broker_paper": {
            "port": "BROKER_PAPER",
            "status": "UNLOADED",
            "loaded": BROKER_PAPER_LOADED,
            "fills": False,
        },
        "live": {
            "port": "LIVE",
            "status": "UNLOADED",
            "loaded": LIVE_PORT_LOADED,
            "fills": False,
        },
        "simulator": {
            "port": "SIMULATOR",
            "status": "NO_FILLS",
            "loaded": True,
            "fills": False,
        },
        "note": (
            "BROKER_PAPER and LIVE execution ports remain UNLOADED. Status only. "
            "No paper/live fills in this slice. Constructing or using those ports is denied."
        ),
    }


class ExecutionPort:
    def __init__(self, session: Session) -> None:
        self.engine = ControlEngine(session)

    def available_ports(self) -> list[str]:
        return list(AVAILABLE_EXECUTION_PORTS)

    def unloaded_ports(self) -> list[str]:
        return list(UNLOADED_EXECUTION_PORTS)

    def port_status(self) -> dict[str, Any]:
        return execution_port_status()

    def broker_paper_loaded(self) -> bool:
        return BROKER_PAPER_LOADED

    def live_loaded(self) -> bool:
        return LIVE_PORT_LOADED

    def place_order(self, *, actor_id: str, actor_type: str, order: dict[str, Any]) -> Decision:
        order = dict(order)
        order.setdefault("execution_port", "SIMULATOR")
        port_name = str(order["execution_port"] or "SIMULATOR")
        # Do not construct PaperBrokerAdapter or LiveBrokerAdapter.
        if port_name in UNLOADED_EXECUTION_PORTS:
            return self.engine.place_order(actor_id=actor_id, actor_type=actor_type, order=order)
        return self.engine.place_order(actor_id=actor_id, actor_type=actor_type, order=order)
