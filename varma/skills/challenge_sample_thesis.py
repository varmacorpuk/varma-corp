"""Skill challenge_sample_thesis (SAMPLE thesis only — not a live trade)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.cost.ledger import CostLedger
from varma.db.models import ChallengeReview, Employee, SampleThesis
from varma.employees.brain import EmployeeBrain
from varma.meetings.handoff import CHALLENGE_SLUG, RISK_SLUG, deliver_handoff, get_employee
from varma.memory.stores import MemoryStores
from varma.ports.llm import LLMPort, get_llm
from varma.skills.prepare_sample_thesis import thesis_to_dict

SKILL_NAME = "challenge_sample_thesis"
SKILL_VERSION = "0.1.0"


class ChallengeSampleThesis:
    def __init__(self, session: Session, *, llm: LLMPort | None = None) -> None:
        self.session = session
        self.llm = llm or get_llm()
        self.cost = CostLedger(session)
        self.memory = MemoryStores(session)
        self.brain = EmployeeBrain(session)

    def run(
        self,
        employee: Employee,
        thesis: SampleThesis,
        *,
        originator: Employee | None = None,
    ) -> ChallengeReview:
        invocation = self.brain.invocation(employee, originator=originator)
        context = {
            **invocation,
            "employee": {
                "slug": employee.slug,
                "display_name": employee.display_name,
                "role_title": employee.role_title,
                "authority_boundaries": employee.authority_boundaries,
            },
            "thesis": thesis_to_dict(thesis),
        }
        raw = self.llm.complete(task=SKILL_NAME, context=context)
        objections = raw.get("objections") or []
        summary = str(raw.get("summary") or "SAMPLE thesis challenged. Not an order.")
        verdict = str(raw.get("verdict") or "CHALLENGED")
        units = int(raw.get("cost_units") or 1)
        review = ChallengeReview(
            employee_id=employee.id,
            thesis_id=thesis.id,
            produced_at=now_london(),
            verdict=verdict,
            summary=summary,
            objections_json=json.dumps(objections, default=str),
            no_execution_authority=True,
            does_not_approve_live=True,
            skill_name=SKILL_NAME,
            skill_version=SKILL_VERSION,
            cost_units=units,
        )
        self.session.add(review)
        self.session.commit()
        self.cost.record(
            employee_id=employee.id,
            workflow=SKILL_NAME,
            kind="llm",
            units=units,
            note="TEMPORARY FakeLLM units for SAMPLE thesis challenge",
        )
        self.memory.append_evidence(
            "challenge_review_produced",
            employee.slug,
            json.dumps({"review_id": review.id, "thesis_id": thesis.id, "verdict": verdict}),
        )
        self.memory.working_put(employee.id, "last_challenge_review_id", review.id)
        employee.status = "AVAILABLE"
        employee.status_bubble = "CHALLENGED"
        self.session.commit()
        risk = get_employee(self.session, RISK_SLUG)
        deliver_handoff(
            self.session,
            from_employee=employee,
            to_employee=risk,
            artefact_type="challenge_review",
            artefact_id=review.id,
            purpose="Risk deny-path input. SAMPLE thesis challenge is not an order and not LIVE approval.",
            note="Challenge complete. Risk must deny any attempt to treat this as execution.",
            evidence_kind="challenge_handoff",
            status_bubble="REVIEW READY",
        )
        self.brain.record_invocation(
            employee,
            skill_name=SKILL_NAME,
            artefact_id=review.id,
            invocation=invocation,
        )
        self.memory.add_lesson(
            employee.id,
            (
                f"JOB_LESSON:{review.id} A SAMPLE thesis is not an order. "
                "Challenge does not inherit originator belief."
            ),
        )
        return review


def challenge_review_to_dict(row: ChallengeReview) -> dict[str, Any]:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "thesis_id": row.thesis_id,
        "produced_at": row.produced_at.isoformat() if row.produced_at else None,
        "verdict": row.verdict,
        "summary": row.summary,
        "objections": json.loads(row.objections_json),
        "no_execution_authority": row.no_execution_authority,
        "does_not_approve_live": row.does_not_approve_live,
        "skill_name": row.skill_name,
        "skill_version": row.skill_version,
        "cost_units": row.cost_units,
        "label": "SAMPLE thesis challenge — not a live trade",
    }


def get_challenge(session: Session) -> Employee:
    return get_employee(session, CHALLENGE_SLUG)
