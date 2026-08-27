"""Simple cost ledger. Cap is a TEMPORARY DEVELOPMENT DEFAULT, not a Board number."""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.config import get_settings
from varma.db.models import CostEntry

TEMPORARY_BRIEF_COST_CAP_LABEL = (
    "TEMPORARY DEVELOPMENT DEFAULT cost cap for the intelligence brief. "
    "Not a Board-approved budget (Document 17 OPEN: material-cost thresholds)."
)


class CostLedger:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.cap = get_settings().temporary_brief_cost_cap_units

    def record(self, *, employee_id: str | None, workflow: str, kind: str, units: int, note: str = "") -> None:
        self.session.add(
            CostEntry(
                employee_id=employee_id,
                workflow=workflow,
                kind=kind,
                units=units,
                note=note,
                created_at=now_london(),
            )
        )
        self.session.commit()

    def within_cap(self, units: int) -> bool:
        return units <= self.cap
