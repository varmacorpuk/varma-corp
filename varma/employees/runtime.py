"""Employee runtime. Chat and skills share this context (Documents 14, 16)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.engine import ControlEngine
from varma.db.models import (
    ChallengeReview,
    ChatMessage,
    Employee,
    Handoff,
    IntelligenceBrief,
    RiskDecision,
    SampleThesis,
)
from varma.memory.stores import MemoryStores
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG, handoff_to_dict
from varma.ports.llm import get_llm
from varma.skills.challenge_sample_thesis import challenge_review_to_dict
from varma.skills.prepare_daily_intelligence_brief import brief_to_dict
from varma.skills.prepare_sample_thesis import thesis_to_dict
from varma.skills.review_unsafe_path import risk_decision_to_dict

NO_LIVE_APPROVAL_SLUGS = {CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG}


class EmployeeRuntime:
    def __init__(self, session: Session, employee: Employee) -> None:
        self.session = session
        self.employee = employee
        self.memory = MemoryStores(session)
        self.controls = ControlEngine(session)
        self.llm = get_llm()

    def latest_brief(self) -> IntelligenceBrief | None:
        return (
            self.session.query(IntelligenceBrief)
            .filter_by(employee_id=self.employee.id)
            .order_by(IntelligenceBrief.produced_at.desc())
            .first()
        )

    def inbox(self) -> list[Handoff]:
        return (
            self.session.query(Handoff)
            .filter_by(to_employee_id=self.employee.id)
            .order_by(Handoff.created_at.desc())
            .all()
        )

    def latest_received_brief(self) -> IntelligenceBrief | None:
        handoff = (
            self.session.query(Handoff)
            .filter_by(to_employee_id=self.employee.id, artefact_type="intelligence_brief")
            .order_by(Handoff.created_at.desc())
            .first()
        )
        if handoff is None:
            return None
        return self.session.get(IntelligenceBrief, handoff.artefact_id)

    def latest_thesis(self) -> SampleThesis | None:
        if self.employee.slug == CHALLENGE_SLUG:
            handoff = (
                self.session.query(Handoff)
                .filter_by(to_employee_id=self.employee.id, artefact_type="sample_thesis")
                .order_by(Handoff.created_at.desc())
                .first()
            )
            if handoff:
                return self.session.get(SampleThesis, handoff.artefact_id)
        return self.session.query(SampleThesis).order_by(SampleThesis.created_at.desc()).first()

    def latest_challenge_review(self) -> ChallengeReview | None:
        produced = (
            self.session.query(ChallengeReview)
            .filter_by(employee_id=self.employee.id)
            .order_by(ChallengeReview.produced_at.desc())
            .first()
        )
        if produced:
            return produced
        handoff = (
            self.session.query(Handoff)
            .filter_by(to_employee_id=self.employee.id, artefact_type="challenge_review")
            .order_by(Handoff.created_at.desc())
            .first()
        )
        if handoff is None:
            return None
        return self.session.get(ChallengeReview, handoff.artefact_id)

    def latest_risk_decision(self) -> RiskDecision | None:
        return (
            self.session.query(RiskDecision)
            .filter_by(employee_id=self.employee.id)
            .order_by(RiskDecision.produced_at.desc())
            .first()
        )

    def context_pack(self) -> dict:
        produced = self.latest_brief()
        received = self.latest_received_brief()
        brief = produced or received
        thesis = self.latest_thesis() if self.employee.slug in {CHALLENGE_SLUG, RISK_SLUG} else None
        review = self.latest_challenge_review() if self.employee.slug in {CHALLENGE_SLUG, RISK_SLUG} else None
        risk = self.latest_risk_decision() if self.employee.slug == RISK_SLUG else None
        return {
            "employee": {
                "id": self.employee.id,
                "slug": self.employee.slug,
                "display_name": self.employee.display_name,
                "role_title": self.employee.role_title,
                "department": self.employee.department,
                "status": self.employee.status,
                "status_bubble": self.employee.status_bubble,
                "authority_boundaries": self.employee.authority_boundaries,
            },
            "lessons": [m.content for m in self.memory.employee_lessons(self.employee.id)],
            "controls": self.controls.snapshot(),
            "latest_brief": brief_to_dict(brief) if brief else None,
            "produced_brief": brief_to_dict(produced) if produced else None,
            "received_brief": brief_to_dict(received) if received else None,
            "latest_thesis": thesis_to_dict(thesis) if thesis else None,
            "latest_challenge_review": challenge_review_to_dict(review) if review else None,
            "latest_risk_decision": risk_decision_to_dict(risk) if risk else None,
            "inbox": [handoff_to_dict(h) for h in self.inbox()[:10]],
            "cannot_approve_live_trading": self.employee.slug in NO_LIVE_APPROVAL_SLUGS,
        }

    def chat(self, message: str, *, from_role: str = "board_member") -> ChatMessage:
        self.session.add(
            ChatMessage(
                employee_id=self.employee.id,
                from_role=from_role,
                body=message,
                created_at=now_london(),
            )
        )
        packed = self.context_pack()
        packed["message"] = message
        result = self.llm.complete(task="chat", context=packed)
        reply = ChatMessage(
            employee_id=self.employee.id,
            from_role="employee",
            body=str(result.get("text") or ""),
            created_at=now_london(),
        )
        self.session.add(reply)
        self.memory.working_put(self.employee.id, "last_chat", message[:500])
        self.session.commit()
        return reply
