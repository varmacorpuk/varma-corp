"""Four memory stores (Document 08). Learning writes memory only, never controls."""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import Evidence, MemoryEmployee, MemoryOrg, MemoryWorking


class MemoryStores:
    def __init__(self, session: Session) -> None:
        self.session = session

    def working_get(self, employee_id: str) -> list[MemoryWorking]:
        return self.session.query(MemoryWorking).filter_by(employee_id=employee_id).all()

    def working_put(self, employee_id: str, key: str, value: str) -> None:
        row = (
            self.session.query(MemoryWorking)
            .filter_by(employee_id=employee_id, key=key)
            .one_or_none()
        )
        if row is None:
            self.session.add(
                MemoryWorking(employee_id=employee_id, key=key, value=value, updated_at=now_london())
            )
        else:
            row.value = value
            row.updated_at = now_london()
        self.session.commit()

    def employee_lessons(self, employee_id: str) -> list[MemoryEmployee]:
        return (
            self.session.query(MemoryEmployee)
            .filter_by(employee_id=employee_id)
            .filter(MemoryEmployee.superseded_by.is_(None))
            .all()
        )

    def add_lesson(self, employee_id: str, content: str, kind: str = "lesson") -> None:
        self.session.add(
            MemoryEmployee(
                employee_id=employee_id,
                kind=kind,
                content=content,
                created_at=now_london(),
            )
        )
        self.session.commit()

    def org_knowledge(self) -> list[MemoryOrg]:
        return self.session.query(MemoryOrg).all()

    def append_evidence(self, kind: str, actor: str, payload: str) -> Evidence:
        row = Evidence(kind=kind, actor=actor, payload=payload, created_at=now_london())
        self.session.add(row)
        self.session.commit()
        return row

    def nightly_filter_stub(self) -> dict[str, str]:
        """Nightly Europe/London filter. Must not delete evidence. Must not write controls."""
        return {
            "status": "stub",
            "timezone": "Europe/London",
            "note": "Filter may archive working context later. Evidence is append-only.",
        }
