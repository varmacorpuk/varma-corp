"""Skill review_unsafe_path. Deny-path demo. Risk cannot approve LIVE."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.risk import UNSAFE_DEMO_PATH, RiskPolicy
from varma.cost.ledger import CostLedger
from varma.db.models import ChallengeReview, Employee, RiskDecision
from varma.meetings.handoff import RISK_SLUG, get_employee
from varma.memory.stores import MemoryStores
from varma.ports.llm import LLMPort, get_llm

SKILL_NAME = "review_unsafe_path"
SKILL_VERSION = "0.1.0"


class ReviewUnsafePath:
    def __init__(self, session: Session, *, llm: LLMPort | None = None) -> None:
        self.session = session
        self.llm = llm or get_llm()
        self.cost = CostLedger(session)
        self.memory = MemoryStores(session)
        self.policy = RiskPolicy(session)

    def run(
        self,
        employee: Employee,
        *,
        proposed: dict[str, Any] | None = None,
        thesis_id: str | None = None,
        challenge_review_id: str | None = None,
    ) -> RiskDecision:
        proposed = dict(proposed or UNSAFE_DEMO_PATH)
        decision = self.policy.review(actor_id=employee.id, proposed=proposed)
        context = {
            "employee": {
                "slug": employee.slug,
                "display_name": employee.display_name,
                "role_title": employee.role_title,
                "authority_boundaries": employee.authority_boundaries,
            },
            "proposed": proposed,
            "policy": {"allowed": decision.allowed, "reason": decision.reason, **decision.details},
        }
        raw = self.llm.complete(task=SKILL_NAME, context=context)
        units = int(raw.get("cost_units") or 1)
        summary = str(raw.get("summary") or "DENIED. Unsafe/out-of-policy path.")
        row = RiskDecision(
            employee_id=employee.id,
            produced_at=now_london(),
            path_kind=str(proposed.get("path_kind") or "unsafe_path"),
            proposed_json=json.dumps(proposed, default=str),
            decision="DENIED",
            reasons_json=json.dumps(decision.details.get("reasons") or [decision.reason], default=str),
            control_engine_reason=str(decision.details.get("control_engine_reason") or decision.reason),
            thesis_id=thesis_id,
            challenge_review_id=challenge_review_id,
            no_execution_authority=True,
            cannot_approve_live=True,
            skill_name=SKILL_NAME,
            skill_version=SKILL_VERSION,
            summary=summary,
            label=str(proposed.get("label") or "DENY-PATH DEMO"),
        )
        self.session.add(row)
        self.session.commit()
        self.cost.record(
            employee_id=employee.id,
            workflow=SKILL_NAME,
            kind="llm",
            units=units,
            note="TEMPORARY FakeLLM units for Risk deny-path demo",
        )
        self.memory.append_evidence(
            "risk_denied",
            employee.slug,
            json.dumps(
                {
                    "decision_id": row.id,
                    "decision": row.decision,
                    "reasons": json.loads(row.reasons_json),
                    "control_engine_reason": row.control_engine_reason,
                }
            ),
        )
        self.memory.working_put(employee.id, "last_risk_decision_id", row.id)
        employee.status = "AVAILABLE"
        employee.status_bubble = "DENIED"
        self.session.commit()
        return row


def risk_decision_to_dict(row: RiskDecision) -> dict[str, Any]:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "produced_at": row.produced_at.isoformat() if row.produced_at else None,
        "path_kind": row.path_kind,
        "proposed": json.loads(row.proposed_json),
        "decision": row.decision,
        "reasons": json.loads(row.reasons_json),
        "control_engine_reason": row.control_engine_reason,
        "thesis_id": row.thesis_id,
        "challenge_review_id": row.challenge_review_id,
        "no_execution_authority": row.no_execution_authority,
        "cannot_approve_live": row.cannot_approve_live,
        "cannot_approve_live_trading": True,
        "skill_name": row.skill_name,
        "skill_version": row.skill_version,
        "summary": row.summary,
        "label": row.label,
    }


def latest_challenge_review(session: Session) -> ChallengeReview | None:
    return session.query(ChallengeReview).order_by(ChallengeReview.produced_at.desc()).first()


def get_risk(session: Session) -> Employee:
    return get_employee(session, RISK_SLUG)
