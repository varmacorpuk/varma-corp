"""Employee runtime. Chat and skills share this context (Documents 14, 16)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.engine import ControlEngine
from varma.db.models import ChatMessage, Employee, IntelligenceBrief
from varma.memory.stores import MemoryStores
from varma.ports.llm import get_llm
from varma.skills.prepare_daily_intelligence_brief import brief_to_dict


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

    def context_pack(self) -> dict:
        brief = self.latest_brief()
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
