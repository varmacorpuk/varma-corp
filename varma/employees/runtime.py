"""Employee runtime. Chat and skills share this context (Documents 14, 16)."""

from __future__ import annotations

from typing import Any

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
from varma.employees.brain import EmployeeBrain
from varma.memory.stores import MemoryStores
from varma.controls.addendum_f import ALL_STAFF_SLUGS, TRADER_SLUG
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG, handoff_to_dict
from varma.ports.llm import get_llm
from varma.skills.challenge_sample_thesis import challenge_review_to_dict
from varma.skills.prepare_daily_intelligence_brief import brief_to_dict
from varma.skills.prepare_sample_thesis import thesis_to_dict
from varma.skills.review_unsafe_path import risk_decision_to_dict

NO_LIVE_APPROVAL_SLUGS = set(ALL_STAFF_SLUGS)

# TEMPORARY DEVELOPMENT DEFAULT — how many recent chat turns are supplied to the model.
# The full chat history stays append-only in the database (GET /employees/{slug}/chat).
# This only bounds what a real model would receive, preventing unbounded prompt growth.
RECENT_CHAT_TURNS = 6


class EmployeeRuntime:
    def __init__(self, session: Session, employee: Employee) -> None:
        self.session = session
        self.employee = employee
        self.memory = MemoryStores(session)
        self.brain = EmployeeBrain(session)
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

    def bounded_chat_context(self, *, limit: int = RECENT_CHAT_TURNS) -> dict:
        """Deterministic bounded view of chat history for AI context (Stage 1).

        Append-only storage is untouched: the full history remains in the database
        and is served in full by GET /employees/{slug}/chat. Only the most recent
        `limit` turns are exposed here so a real model never receives the entire
        (potentially unbounded) history. No AI call is made and nothing is deleted.
        A semantic rolling summary of older turns is a Board decision and is NOT
        invented here; older turns are represented only by deterministic metadata.
        """
        base = self.session.query(ChatMessage).filter_by(employee_id=self.employee.id)
        total = base.count()
        recent_desc = base.order_by(ChatMessage.created_at.desc()).limit(max(0, limit)).all()
        recent = [
            {
                "from_role": m.from_role,
                "body": m.body,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in reversed(recent_desc)
        ]
        older_count = max(0, total - len(recent))
        older_earliest_at = None
        if older_count:
            first = base.order_by(ChatMessage.created_at.asc()).first()
            older_earliest_at = first.created_at.isoformat() if first and first.created_at else None
        return {
            "recent": recent,
            "recent_limit": limit,
            "total_messages": total,
            "older_count": older_count,
            "older_earliest_at": older_earliest_at,
            "durable_full_history_in_database": True,
            "older_summary_policy": "BOARD_DECISION_NOT_INVENTED",
            "note": (
                "Durable full chat history is retained append-only in the database "
                "(GET /employees/{slug}/chat). Only the most recent turns are supplied "
                "to the model to bound prompt growth. A semantic rolling summary of older "
                "turns is a Board decision and is not invented here."
            ),
        }

    def context_pack(self) -> dict:
        produced = self.latest_brief()
        received = self.latest_received_brief()
        brief = produced or received
        thesis = self.latest_thesis() if self.employee.slug in {CHALLENGE_SLUG, RISK_SLUG} else None
        review = self.latest_challenge_review() if self.employee.slug in {CHALLENGE_SLUG, RISK_SLUG} else None
        risk = self.latest_risk_decision() if self.employee.slug == RISK_SLUG else None
        packed = self.brain.invocation(self.employee)
        packed["employee"] = {
            **packed["identity"],
            "slug": self.employee.slug,
            "display_name": self.employee.display_name,
            "person_name": self.employee.person_name or "",
            "role_title": self.employee.role_title,
            "department": self.employee.department,
            "status": self.employee.status,
            "status_bubble": self.employee.status_bubble,
            "authority_boundaries": self.employee.authority_boundaries,
        }
        packed.update(
            {
                # PR #2: compact informational control hint instead of the full verbose
                # snapshot. Controls remain enforced deterministically by ControlEngine;
                # the chat runtime never used the full snapshot for reasoning.
                "controls_hint": self.controls.constraints_hint(),
                "latest_brief": brief_to_dict(brief) if brief else None,
                "produced_brief": brief_to_dict(produced) if produced else None,
                "received_brief": brief_to_dict(received) if received else None,
                "latest_thesis": thesis_to_dict(thesis) if thesis else None,
                "latest_challenge_review": challenge_review_to_dict(review) if review else None,
                "latest_risk_decision": risk_decision_to_dict(risk) if risk else None,
                "inbox": [handoff_to_dict(h) for h in self.inbox()[:10]],
                "cannot_approve_live_trading": self.employee.slug in NO_LIVE_APPROVAL_SLUGS,
                # Stage 1: bounded recent chat turns; full history stays in the database.
                "chat_recent": self.bounded_chat_context(),
            }
        )
        return packed

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

    def propose_paper_ticket(
        self,
        *,
        order: dict[str, Any] | None = None,
        at=None,
        started_by: str = "cli",
    ) -> dict:
        """Chris Adeyemi proposes a paper ticket. ControlEngine permit/deny. No AI.

        Permit/deny, hours, kill switch, and fills are never an LLM call.
        Only the Trader may use this skill. After Grand Opening PAPER a legal
        ticket may fill in the internal simulator. LIVE stays blocked.
        """
        from varma.skills.propose_paper_ticket import (
            ONLY_TRADER_MAY_PROPOSE,
            run_propose_paper_ticket,
        )

        if self.employee.slug != TRADER_SLUG:
            raise RuntimeError(ONLY_TRADER_MAY_PROPOSE)
        return run_propose_paper_ticket(
            self.session,
            self.employee,
            order=order,
            at=at,
            started_by=started_by,
        )
