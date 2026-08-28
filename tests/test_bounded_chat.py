"""Stage 1: bounded chat context. Full history stays append-only in the database."""

from __future__ import annotations

import json

from varma.clock import now_london
from varma.db.models import ChatMessage, Employee
from varma.db.seed import MI_SLUG
from varma.employees.context import classify
from varma.employees.runtime import RECENT_CHAT_TURNS, EmployeeRuntime


def _mi(session):
    return session.query(Employee).filter_by(slug=MI_SLUG).one()


def test_bounded_chat_caps_recent_but_preserves_full_history(session):
    emp = _mi(session)
    body = "The Board Member asked a detailed question about the intelligence brief. " * 3
    for i in range(200):
        session.add(
            ChatMessage(employee_id=emp.id, from_role="board_member", body=f"{i}: {body}", created_at=now_london())
        )
    session.commit()

    bc = EmployeeRuntime(session, emp).bounded_chat_context()
    assert bc["total_messages"] == 200
    assert len(bc["recent"]) == RECENT_CHAT_TURNS
    assert bc["older_count"] == 200 - RECENT_CHAT_TURNS
    assert bc["durable_full_history_in_database"] is True
    assert bc["older_summary_policy"] == "BOARD_DECISION_NOT_INVENTED"

    # Nothing deleted: the durable append-only history is intact.
    assert session.query(ChatMessage).filter_by(employee_id=emp.id).count() == 200

    # Bounded context stays capped instead of resending the whole (growing) history.
    full = session.query(ChatMessage).filter_by(employee_id=emp.id).all()
    naive_full = [
        {"from_role": m.from_role, "body": m.body, "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in full
    ]
    assert len(json.dumps(bc, default=str)) < len(json.dumps(naive_full, default=str)) // 10


def test_context_pack_includes_bounded_chat(session):
    packed = EmployeeRuntime(session, _mi(session)).context_pack()
    assert "chat_recent" in packed
    assert isinstance(packed["chat_recent"]["recent"], list)
    assert classify(packed)["other"] == []
