"""Meeting / workflow handoff artefacts. Database is source of truth (Documents 09, 18)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import Employee, Handoff, IntelligenceBrief
from varma.memory.stores import MemoryStores

CEO_SLUG = "ceo"
CHALLENGE_SLUG = "challenge"
RISK_SLUG = "risk"
BRIEF_HANDOFF_PURPOSE = (
    "07:30 Europe/London company meeting pack. "
    "CEO is the meeting recipient of the Market Intelligence brief (Document 18)."
)


def get_employee(session: Session, slug: str) -> Employee:
    emp = session.query(Employee).filter_by(slug=slug).one_or_none()
    if emp is None:
        raise RuntimeError(f"employee {slug!r} missing — seed_if_empty must persist the identity")
    return emp


def get_ceo(session: Session) -> Employee:
    return get_employee(session, CEO_SLUG)


def deliver_handoff(
    session: Session,
    *,
    from_employee: Employee,
    to_employee: Employee,
    artefact_type: str,
    artefact_id: str,
    purpose: str,
    note: str,
    evidence_kind: str,
    status_bubble: str | None = None,
) -> Handoff:
    row = Handoff(
        from_employee_id=from_employee.id,
        to_employee_id=to_employee.id,
        artefact_type=artefact_type,
        artefact_id=artefact_id,
        purpose=purpose,
        status="DELIVERED",
        created_at=now_london(),
        note=note,
    )
    session.add(row)
    session.flush()
    MemoryStores(session).append_evidence(
        evidence_kind,
        from_employee.slug,
        json.dumps(
            {
                "handoff_id": row.id,
                "artefact_type": artefact_type,
                "artefact_id": artefact_id,
                "to": to_employee.slug,
                "purpose": purpose,
            }
        ),
    )
    MemoryStores(session).working_put(to_employee.id, "last_handoff_id", row.id)
    to_employee.status = "AVAILABLE"
    if status_bubble:
        to_employee.status_bubble = status_bubble
    session.commit()
    return row


def handoff_brief_to_ceo(
    session: Session, brief: IntelligenceBrief, from_employee: Employee
) -> Handoff:
    ceo = get_ceo(session)
    return deliver_handoff(
        session,
        from_employee=from_employee,
        to_employee=ceo,
        artefact_type="intelligence_brief",
        artefact_id=brief.id,
        purpose=BRIEF_HANDOFF_PURPOSE,
        note=(
            "Research-only meeting pack. Not a trade recommendation. "
            "CEO does not approve live trading. Board Member is the human authority."
        ),
        evidence_kind="brief_handoff",
        status_bubble="PACK READY",
    )


def handoff_to_dict(row: Handoff) -> dict[str, Any]:
    return {
        "id": row.id,
        "from_employee_id": row.from_employee_id,
        "to_employee_id": row.to_employee_id,
        "artefact_type": row.artefact_type,
        "artefact_id": row.artefact_id,
        "purpose": row.purpose,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "note": row.note,
        "cannot_approve_live_trading": True,
        "ceo_cannot_approve_live_trading": True,
    }
