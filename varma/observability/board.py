"""Board Member read-only observability. Database is the ledger, not the desktop.

This view must not write controls, trading_mode, allow-list, or permissions.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.engine import ControlEngine
from varma.cost.ledger import CostLedger, TEMPORARY_BRIEF_COST_CAP_LABEL
from varma.db.models import CostEntry, Evidence
from varma.memory.stores import MemoryStores

DEFAULT_RECENT_LIMIT = 20

READ_ONLY_NOTE = (
    "Board Member observability. Read-only. Source is the database, not desktop disk. "
    "This view does not write controls, trading_mode, allow-list, or permissions."
)


def cost_entry_to_dict(row: CostEntry) -> dict[str, Any]:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "workflow": row.workflow,
        "kind": row.kind,
        "units": row.units,
        "note": row.note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def evidence_to_dict(row: Evidence) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": row.kind,
        "actor": row.actor,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class BoardObservability:
    """Read path only. Instantiating or calling snapshot() must not mutate controls."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.costs = CostLedger(session)
        self.memory = MemoryStores(session)
        self.controls = ControlEngine(session)

    def snapshot(self, *, recent_limit: int = DEFAULT_RECENT_LIMIT) -> dict[str, Any]:
        limit = max(1, min(int(recent_limit), 100))
        control_snap = self.controls.snapshot()
        entries = self.costs.recent(limit=limit)
        evidence = self.memory.recent_evidence(limit=limit)
        return {
            "read_only": True,
            "writes_controls": False,
            "source": "database",
            "office_is_source_of_truth": False,
            "trading_mode": control_snap["trading_mode"],
            "allow_list_empty": control_snap["allow_list_empty"],
            "live_adapter_loaded": control_snap["live_adapter_loaded"],
            "cost_cap_units": self.costs.cap,
            "cost_cap_label": TEMPORARY_BRIEF_COST_CAP_LABEL,
            "cost_cap_is_board_budget": False,
            "costs": {
                "total_units": self.costs.total_units(),
                "recent_limit": limit,
                "entries": [cost_entry_to_dict(row) for row in entries],
            },
            "evidence": {
                "append_only": True,
                "recent_limit": limit,
                "entries": [evidence_to_dict(row) for row in evidence],
            },
            "note": READ_ONLY_NOTE,
        }
