"""Durable employee record (Document 03). An LLM call is an invocation of this person."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.addendum_f import ALL_STAFF_SLUGS
from varma.db.models import (
    Employee,
    EmployeeFoundation,
    EmployeeRelationship,
    Skill,
    SkillInvocation,
)
from varma.memory.stores import MEMORY_POINTERS, MemoryStores

# TEMPORARY DEVELOPMENT DEFAULT — how many of an employee's most-recent lessons are
# supplied to the model per invocation. Selective RETRIEVAL only: nothing is deleted,
# memory-store semantics are unchanged, and the full lesson history stays in the
# database. A permanent pruning/summarisation policy is a Board decision (not invented).
LESSON_CONTEXT_LIMIT = 8

# Challenge does not inherit Quant belief. Risk does not inherit Trader belief.
RELATIONSHIPS: tuple[tuple[str, str, str, str], ...] = (
    (
        "market-intelligence-research",
        "ceo",
        "briefs_to",
        "Intelligence brief is a meeting pack for the CEO. Not a trade.",
    ),
    (
        "challenge",
        "quant-strategy",
        "independent_of",
        "Challenge stays independent of Quant. Do not load Quant's 'I believe this' as Challenge belief.",
    ),
    (
        "challenge",
        "risk",
        "hands_review_to",
        "Challenge review is handed to Risk. SAMPLE is not an order.",
    ),
    (
        "risk",
        "trader",
        "independent_of",
        "Risk stays independent of Trader. Do not load Trader's 'I believe this' as Risk belief.",
    ),
    (
        "risk",
        "ceo",
        "recommends_to",
        "Risk may recommend to the CEO. Risk cannot halt. Kill switch is Board-only.",
    ),
    (
        "technology",
        "technology",
        "owns_job",
        "Technology owns the encrypted company backup. No trading adapter.",
    ),
)

DEFAULT_SKILLS: dict[str, tuple[str, str]] = {
    "ceo": ("hold_meeting_pack", "Hold the intelligence meeting pack. Not LIVE approval."),
    "trader": (
        "propose_paper_ticket",
        "Propose paper tickets. Engine denies fills while PAPER execution is CLOSED.",
    ),
    "quant-strategy": (
        "analyse_inside_allow_list",
        "Quant analysis inside Board Addendum E. A note is not an order.",
    ),
}

ROLE_KNOWLEDGE: dict[str, str] = {
    "ceo": (
        "Chief Executive of Varma Corp. Holds the meeting pack. Sets operational "
        "priorities as database artefacts. Learning writes Document 08 memory, "
        "never control tables. Cannot approve LIVE. Cannot place orders. Cannot "
        "open the firm. Silence is not Board approval."
    ),
    "market-intelligence-research": (
        "Market Intelligence / Research. Produces the pre-07:30 Europe/London "
        "intelligence brief from delayed news and prices. Material claims need "
        "source and timestamp. A brief is not a trade and grants no execution "
        "authority. Cannot write controls."
    ),
    "challenge": (
        "Independent Challenge. Stress-tests theses and research notes. A SAMPLE "
        "or a note is not an order. Does not inherit Quant belief. Cannot approve "
        "LIVE. Cannot place orders. Cannot write controls."
    ),
    "risk": (
        "Independent Risk. Reviews paths against the control engine. Denies unsafe "
        "or out-of-policy proposals. May recommend halt to the CEO only; cannot "
        "trip the Board-only kill switch. Does not inherit Trader belief. Cannot "
        "approve LIVE. Cannot open the firm."
    ),
    "trader": (
        "Paper-desk Trader. May propose paper tickets. The engine denies fills "
        "while PAPER execution is CLOSED. Cannot write locks, allow-list, or "
        "trading_mode. Cannot approve LIVE. Risk stays independent of Trader."
    ),
    "quant-strategy": (
        "Quant / Strategy. Analysis stays inside Board locks. A research note is "
        "not an order. Challenge stays independent of Quant. Cannot write controls "
        "or approve LIVE."
    ),
    "technology": (
        "Technology. Owns encrypted company backup in the database. No trading "
        "adapter. Cannot write trading_mode, allow-list, or open the firm. Cannot "
        "download secrets. The office is a projection; the database is the ledger."
    ),
}


class EmployeeBrain:
    """Assemble the durable person. Skills invoke this; they do not prompt a blank role."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.memory = MemoryStores(session)

    def record(self, employee: Employee) -> dict[str, Any]:
        foundation = self.session.get(EmployeeFoundation, employee.id)
        skills = (
            self.session.query(Skill)
            .filter_by(employee_id=employee.id, active=True)
            .all()
        )
        rels = (
            self.session.query(EmployeeRelationship)
            .filter_by(from_employee_id=employee.id)
            .all()
        )
        return {
            "identity": {
                "id": employee.id,
                "slug": employee.slug,
                "display_name": employee.display_name,
                "person_name": employee.person_name or "",
                "role_title": employee.role_title,
                "department": employee.department,
                "is_primary_agent": bool(employee.is_primary_agent),
            },
            "role_knowledge": foundation.role_knowledge if foundation else "",
            "professional_foundation": foundation.role_knowledge if foundation else "",
            "authority_boundaries": employee.authority_boundaries,
            "responsibilities": employee.responsibilities,
            "memory_pointers": dict(MEMORY_POINTERS),
            "skills": [{"name": s.name, "version": s.version, "active": bool(s.active)} for s in skills],
            "relationships": [
                {
                    "to_employee_id": r.to_employee_id,
                    "kind": r.kind,
                    "note": r.note,
                }
                for r in rels
            ],
            "llm_call_is_invocation": True,
            "employee_is_not_a_prompt": True,
        }

    def independent_of_ids(self, employee: Employee) -> list[str]:
        rows = (
            self.session.query(EmployeeRelationship)
            .filter_by(from_employee_id=employee.id, kind="independent_of")
            .all()
        )
        return [r.to_employee_id for r in rows]

    def invocation(
        self,
        employee: Employee,
        *,
        originator: Employee | None = None,
    ) -> dict[str, Any]:
        """Context for one skill/chat call. Own lessons only. Never originator belief."""
        pack = self.record(employee)
        excluded_ids = set(self.independent_of_ids(employee))
        if originator is not None:
            excluded_ids.add(originator.id)
        # employee_lessons() returns oldest -> newest; the model only needs the most
        # recent lessons (recency-selective retrieval). Nothing is deleted; the full
        # set is still counted and used for the fail-closed independence check below.
        full_own = [m.content for m in self.memory.employee_lessons(employee.id)]
        if LESSON_CONTEXT_LIMIT and len(full_own) > LESSON_CONTEXT_LIMIT:
            own_lessons = full_own[-LESSON_CONTEXT_LIMIT:]
        else:
            own_lessons = list(full_own)
        leaked = []
        for oid in excluded_ids:
            leaked.extend(m.content for m in self.memory.employee_lessons(oid))
        pack["lessons"] = own_lessons
        pack["lessons_total"] = len(full_own)
        pack["lessons_truncated"] = len(own_lessons) < len(full_own)
        pack["working"] = [
            {"key": w.key, "value": w.value} for w in self.memory.working_get(employee.id)
        ]
        pack["org_knowledge_titles"] = [r.title for r in self.memory.org_titles()]
        pack["originator_beliefs_loaded"] = False
        pack["blank_prompt"] = False
        pack["independent_of_employee_ids"] = sorted(excluded_ids)
        pack["excluded_originator_lessons"] = leaked
        # Fail closed over the FULL own-lesson set (not just the sent slice): an
        # originator's belief must never have become this employee's own lesson.
        for belief in leaked:
            if belief and belief in full_own:
                raise RuntimeError("ORIGINATOR_BELIEF_MUST_NOT_BECOME_OWN_LESSON")
        return pack

    def record_invocation(
        self,
        employee: Employee,
        *,
        skill_name: str,
        artefact_id: str,
        invocation: dict[str, Any],
    ) -> SkillInvocation:
        lessons = list(invocation.get("lessons") or [])
        row = SkillInvocation(
            employee_id=employee.id,
            skill_name=skill_name,
            artefact_id=artefact_id,
            lessons_json=json.dumps(lessons, default=str),
            originator_beliefs_loaded=bool(invocation.get("originator_beliefs_loaded")),
            blank_prompt=len(lessons) == 0,
            independent_of_json=json.dumps(
                invocation.get("independent_of_employee_ids") or [], default=str
            ),
            created_at=now_london(),
        )
        self.session.add(row)
        self.session.commit()
        return row


def seed_employee_brains(session: Session) -> None:
    """Upsert Document 03 foundations and relationships. Safe on stale SQLite."""
    by_slug = {e.slug: e for e in session.query(Employee).all()}
    now = now_london()
    for slug in ALL_STAFF_SLUGS:
        emp = by_slug.get(slug)
        if emp is None:
            continue
        row = session.get(EmployeeFoundation, emp.id)
        knowledge = ROLE_KNOWLEDGE[slug]
        if row is None:
            session.add(
                EmployeeFoundation(
                    employee_id=emp.id,
                    role_knowledge=knowledge,
                    updated_at=now,
                )
            )
        else:
            row.role_knowledge = knowledge
            row.updated_at = now
    for from_slug, to_slug, kind, note in RELATIONSHIPS:
        left = by_slug.get(from_slug)
        right = by_slug.get(to_slug)
        if left is None or right is None:
            continue
        existing = (
            session.query(EmployeeRelationship)
            .filter_by(from_employee_id=left.id, to_employee_id=right.id, kind=kind)
            .one_or_none()
        )
        if existing is None:
            session.add(
                EmployeeRelationship(
                    from_employee_id=left.id,
                    to_employee_id=right.id,
                    kind=kind,
                    note=note,
                )
            )
        else:
            existing.note = note
    for slug, (name, description) in DEFAULT_SKILLS.items():
        emp = by_slug.get(slug)
        if emp is None:
            continue
        if (
            session.query(Skill).filter_by(employee_id=emp.id, name=name).one_or_none()
            is None
        ):
            session.add(
                Skill(
                    name=name,
                    version="0.1.0",
                    employee_id=emp.id,
                    description=description,
                    active=True,
                )
            )
    session.flush()
