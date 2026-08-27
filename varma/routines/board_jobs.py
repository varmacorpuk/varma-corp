"""Board-only on-demand jobs. POST endpoints, not GET /observability.

CLI entry points remain. Running a job must not load broker ports,
must not change trading_mode, and must not fill paper/live orders.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.engine import ControlEngine
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED, execution_port_status

JOB_SAFETY_FLAGS: dict[str, Any] = {
    "loads_broker_ports": False,
    "changes_trading_mode": False,
    "fills": False,
    "paper_fills": False,
    "live_fills": False,
    "writes_controls": False,
    "not_get_observability": True,
    "board_only": True,
    "employees_denied": True,
    "cli_still_works": True,
    "daemon": False,
}

BOARD_JOBS: tuple[dict[str, Any], ...] = (
    {
        "id": "run-brief",
        "label": "Run morning intelligence brief",
        "method": "POST",
        "path": "/routines/run-brief",
        "cli": "python -m varma.routines.run_brief",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
    },
    {
        "id": "run-challenge",
        "label": "Run SAMPLE challenge",
        "method": "POST",
        "path": "/routines/run-challenge",
        "cli": "python -m varma.routines.run_challenge",
        "sample": True,
        "is_live_trade": False,
        "is_live_approval": False,
    },
    {
        "id": "run-risk-deny",
        "label": "Run Risk deny-path",
        "method": "POST",
        "path": "/routines/run-risk-deny",
        "cli": "python -m varma.routines.run_risk_deny",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "cannot_approve_live": True,
    },
    {
        "id": "run-0730-meeting",
        "label": "Run 07:30 meeting record",
        "method": "POST",
        "path": "/routines/run-0730-meeting",
        "cli": "python -m varma.routines.run_0730_meeting",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "cannot_start_live": True,
    },
    {
        "id": "run-nightly-filter",
        "label": "Run nightly memory filter",
        "method": "POST",
        "path": "/routines/run-nightly-filter",
        "cli": "python -m varma.routines.run_nightly_filter",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
    },
)


def runnable_jobs_catalog() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for job in BOARD_JOBS:
        item = dict(job)
        item.update(JOB_SAFETY_FLAGS)
        items.append(item)
    catalog = {
        "read_only_list": True,
        "source": "kernel",
        "items": items,
        "note": (
            "Board Member can run these on-demand jobs via POST from the right-hand "
            "panel or the API. Not GET /observability. Employees are denied. CLI "
            "entry points still work. Running a job does not load BROKER_PAPER or "
            "LIVE, does not change trading_mode, and does not fill paper/live orders. "
            "After a run, the same panel refreshes from the database."
        ),
    }
    catalog.update(JOB_SAFETY_FLAGS)
    return catalog


def with_job_safety(session: Session, result: dict[str, Any]) -> dict[str, Any]:
    """Attach safety flags. Does not load broker ports or write controls."""
    snap = ControlEngine(session).snapshot()
    ports = execution_port_status()
    out = dict(result)
    out["job_safety"] = {
        "loads_broker_ports": False,
        "changes_trading_mode": False,
        "fills": False,
        "paper_fills": False,
        "live_fills": False,
        "writes_controls": False,
        "not_get_observability": True,
        "trading_mode": snap["trading_mode"],
        "trading_mode_unchanged": snap["trading_mode"] == "LIVE_BLOCKED",
        "allow_list_empty": snap["allow_list_empty"],
        "broker_paper_loaded": bool(BROKER_PAPER_LOADED) or bool(snap.get("broker_paper_loaded")),
        "live_adapter_loaded": bool(LIVE_PORT_LOADED) or bool(snap.get("live_adapter_loaded")),
        "broker_paper_status": ports["broker_paper"]["status"],
        "live_status": ports["live"]["status"],
    }
    return out
