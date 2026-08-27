"""Four memory stores (Document 08). Learning writes memory only, never controls."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import (
    AllowListInstrument,
    ControlSetting,
    ControlState,
    Evidence,
    MemoryEmployee,
    MemoryOrg,
    NumericLimit,
    Permission,
    MemoryWorking,
)

MEMORY_POINTERS: dict[str, str] = {
    "working": "memory_working",
    "employee_persistent": "memory_employee",
    "organisational": "memory_org",
    "evidence": "evidence",
}

GOVERNED_PROMOTER_SLUGS = frozenset({"ceo", "board-member", "board_member"})
GOVERNED_PROMOTION_REQUIRED = "GOVERNED_PROMOTION_REQUIRED"
LEARNING_MUST_NOT_WRITE_CONTROLS = "LEARNING_MUST_NOT_WRITE_CONTROLS"


def _control_fingerprint(session: Session) -> dict[str, Any]:
    state = session.get(ControlState, 1)
    paper = session.get(ControlSetting, "paper_execution")
    perms = (
        session.query(Permission)
        .order_by(Permission.subject_id, Permission.action)
        .all()
    )
    limits = session.query(NumericLimit).order_by(NumericLimit.key).all()
    settings = session.query(ControlSetting).order_by(ControlSetting.key).all()
    allow = session.query(AllowListInstrument).order_by(AllowListInstrument.symbol).all()
    return {
        "trading_mode": state.trading_mode if state else None,
        "kill_switch": bool(state.kill_switch) if state else None,
        "paper_execution": paper.value if paper is not None else None,
        "allow_list": tuple(r.symbol for r in allow),
        "permissions": tuple((r.subject_id, r.action, bool(r.allowed)) for r in perms),
        "limits": tuple((r.key, r.value) for r in limits),
        "settings": tuple((r.key, r.value) for r in settings),
    }


class MemoryStores:
    def __init__(self, session: Session) -> None:
        self.session = session

    def pointers(self) -> dict[str, str]:
        return dict(MEMORY_POINTERS)

    def working_get(self, employee_id: str) -> list[MemoryWorking]:
        return self.session.query(MemoryWorking).filter_by(employee_id=employee_id).all()

    def working_put(self, employee_id: str, key: str, value: str) -> None:
        before = _control_fingerprint(self.session)
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
        if _control_fingerprint(self.session) != before:
            raise RuntimeError(LEARNING_MUST_NOT_WRITE_CONTROLS)

    def employee_lessons(self, employee_id: str) -> list[MemoryEmployee]:
        return (
            self.session.query(MemoryEmployee)
            .filter_by(employee_id=employee_id)
            .filter(MemoryEmployee.superseded_by.is_(None))
            .order_by(MemoryEmployee.created_at.asc())
            .all()
        )

    def add_lesson(self, employee_id: str, content: str, kind: str = "lesson") -> MemoryEmployee:
        before = _control_fingerprint(self.session)
        row = MemoryEmployee(
            employee_id=employee_id,
            kind=kind,
            content=content,
            created_at=now_london(),
        )
        self.session.add(row)
        self.session.commit()
        if _control_fingerprint(self.session) != before:
            raise RuntimeError(LEARNING_MUST_NOT_WRITE_CONTROLS)
        return row

    def org_knowledge(self) -> list[MemoryOrg]:
        return self.session.query(MemoryOrg).all()

    def org_titles(self) -> list[MemoryOrg]:
        return self.session.query(MemoryOrg).order_by(MemoryOrg.created_at.desc()).all()

    def promote_org_knowledge(
        self,
        *,
        promoter_slug: str,
        title: str,
        content: str,
    ) -> MemoryOrg:
        """Shared org knowledge only via governed promotion. Never a control write."""
        if promoter_slug not in GOVERNED_PROMOTER_SLUGS:
            raise RuntimeError(GOVERNED_PROMOTION_REQUIRED)
        before = _control_fingerprint(self.session)
        row = MemoryOrg(
            title=title[:160],
            content=content,
            promoted_by=promoter_slug,
            created_at=now_london(),
        )
        self.session.add(row)
        self.session.commit()
        if _control_fingerprint(self.session) != before:
            raise RuntimeError(LEARNING_MUST_NOT_WRITE_CONTROLS)
        return row

    def append_evidence(self, kind: str, actor: str, payload: str) -> Evidence:
        before = _control_fingerprint(self.session)
        row = Evidence(kind=kind, actor=actor, payload=payload, created_at=now_london())
        self.session.add(row)
        self.session.commit()
        if _control_fingerprint(self.session) != before:
            raise RuntimeError(LEARNING_MUST_NOT_WRITE_CONTROLS)
        return row

    def recent_evidence(self, *, limit: int = 20) -> list[Evidence]:
        return (
            self.session.query(Evidence)
            .order_by(Evidence.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete_evidence(self, evidence_id: str) -> None:
        raise RuntimeError("EVIDENCE_IS_APPEND_ONLY")

    def overwrite_evidence(self, evidence_id: str, payload: str) -> None:
        raise RuntimeError("EVIDENCE_IS_APPEND_ONLY")

    def run_nightly_filter(self) -> dict[str, str]:
        from varma.memory.filter import NightlyMemoryFilter

        return NightlyMemoryFilter(self.session).run()
