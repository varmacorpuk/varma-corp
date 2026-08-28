"""Stage 3: idempotent handoffs (deterministic, existing columns only, no schema change)."""

from __future__ import annotations

from varma.db.models import Employee, Evidence, Handoff
from varma.db.seed import MI_SLUG
from varma.meetings.handoff import deliver_handoff, find_handoff, get_ceo
from varma.routines.run_brief import run_brief


def _mi(session):
    return session.query(Employee).filter_by(slug=MI_SLUG).one()


def _deliver(session, artefact_id):
    return deliver_handoff(
        session,
        from_employee=_mi(session),
        to_employee=get_ceo(session),
        artefact_type="intelligence_brief",
        artefact_id=artefact_id,
        purpose="p",
        note="n",
        evidence_kind="brief_handoff",
    )


def test_same_artefact_handoff_is_idempotent(session):
    h1 = _deliver(session, "ART-1")
    ev_after_first = session.query(Evidence).filter_by(kind="brief_handoff").count()
    h2 = _deliver(session, "ART-1")
    assert h1.id == h2.id
    assert session.query(Handoff).filter_by(artefact_id="ART-1").count() == 1
    # No duplicate evidence appended for the idempotent repeat.
    assert session.query(Evidence).filter_by(kind="brief_handoff").count() == ev_after_first
    assert find_handoff(session, to_employee_id=get_ceo(session).id, artefact_type="intelligence_brief", artefact_id="ART-1") is not None


def test_new_artefact_is_a_legitimate_new_event(session):
    _deliver(session, "ART-A")
    _deliver(session, "ART-B")
    assert session.query(Handoff).filter(Handoff.artefact_id.in_(["ART-A", "ART-B"])).count() == 2


def test_repeated_brief_routine_creates_distinct_handoffs(session):
    run_brief(session)
    run_brief(session)
    ceo = get_ceo(session)
    n = (
        session.query(Handoff)
        .filter_by(to_employee_id=ceo.id, artefact_type="intelligence_brief")
        .count()
    )
    # Two distinct briefs are two legitimate events -> two handoffs (not merged).
    assert n == 2
