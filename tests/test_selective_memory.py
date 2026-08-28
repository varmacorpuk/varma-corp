"""Stage 2: selective (recency) lesson retrieval. No deletion; semantics preserved."""

from __future__ import annotations

from varma.db.models import Employee, MemoryEmployee
from varma.db.seed import MI_SLUG
from varma.employees.brain import LESSON_CONTEXT_LIMIT, EmployeeBrain
from varma.memory.stores import MemoryStores


def _mi(session):
    return session.query(Employee).filter_by(slug=MI_SLUG).one()


def test_only_recent_lessons_are_sent_and_none_deleted(session):
    emp = _mi(session)
    stores = MemoryStores(session)
    before = session.query(MemoryEmployee).filter_by(employee_id=emp.id).count()
    for i in range(20):
        stores.add_lesson(emp.id, f"LESSON_{i}")
    total = session.query(MemoryEmployee).filter_by(employee_id=emp.id).count()
    assert total == before + 20

    pack = EmployeeBrain(session).invocation(emp)
    # Only the most recent N are supplied to the model.
    assert len(pack["lessons"]) == LESSON_CONTEXT_LIMIT
    assert pack["lessons_total"] == total
    assert pack["lessons_truncated"] is True
    # The most recent lesson (used by FakeLLM) is retained, in order.
    assert pack["lessons"][-1] == "LESSON_19"
    assert pack["blank_prompt"] is False

    # Storage is untouched — selective RETRIEVAL only, no pruning.
    assert session.query(MemoryEmployee).filter_by(employee_id=emp.id).count() == total


def test_small_lesson_set_is_not_truncated(session):
    pack = EmployeeBrain(session).invocation(_mi(session))
    assert pack["lessons_truncated"] is False
    assert pack["lessons_total"] == len(pack["lessons"])
    assert pack["lessons"]  # seed lessons still present
