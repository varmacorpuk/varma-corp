"""Board memory policy: conservative selective retrieval for working + org memory.

Recency-based RETRIEVAL only. Nothing is deleted; the full durable records remain in
the database and in the full Board observability view.
"""

from __future__ import annotations

from varma.db.models import Employee, MemoryOrg, MemoryWorking
from varma.db.seed import MI_SLUG
from varma.employees.brain import ORG_TITLES_LIMIT, WORKING_CONTEXT_LIMIT, EmployeeBrain
from varma.employees.context import classify
from varma.memory.stores import MemoryStores
from varma.observability.board import BoardObservability


def _mi(session):
    return session.query(Employee).filter_by(slug=MI_SLUG).one()


def test_working_and_org_memory_are_recency_selective_without_deletion(session):
    emp = _mi(session)
    stores = MemoryStores(session)
    for i in range(20):
        stores.working_put(emp.id, f"key_{i}", f"value {i}")
        stores.promote_org_knowledge(promoter_slug="ceo", title=f"Org lesson {i}", content=f"content {i}")

    working_total = session.query(MemoryWorking).filter_by(employee_id=emp.id).count()
    org_total = session.query(MemoryOrg).count()
    assert working_total >= 20
    assert org_total >= 20

    pack = EmployeeBrain(session).invocation(emp)
    # Only the most-recent entries are supplied to the model.
    assert len(pack["working"]) == WORKING_CONTEXT_LIMIT
    assert pack["working_total"] == working_total
    assert pack["working_truncated"] is True
    assert len(pack["org_knowledge_titles"]) == ORG_TITLES_LIMIT
    assert pack["org_titles_total"] == org_total
    assert pack["org_titles_truncated"] is True

    # Nothing deleted — durable records intact.
    assert session.query(MemoryWorking).filter_by(employee_id=emp.id).count() == working_total
    assert session.query(MemoryOrg).count() == org_total

    # Board observability still shows the FULL org-memory list (auditable).
    obs = BoardObservability(session).snapshot()
    assert len(obs["organisation_memory"]["titles"]) == org_total

    # Context stays fully classified (no untracked growth).
    assert classify(pack)["other"] == []


def test_small_memory_sets_are_not_truncated(session):
    pack = EmployeeBrain(session).invocation(_mi(session))
    assert pack["working_truncated"] is False
    assert pack["org_titles_truncated"] is False
    assert pack["working_total"] == len(pack["working"])
    assert pack["org_titles_total"] == len(pack["org_knowledge_titles"])
