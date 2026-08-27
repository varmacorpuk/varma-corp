"""On-demand SAMPLE thesis + Challenge review. Not a live trade. No daemon scheduler.

Usage:
    python -m varma.routines.run_challenge
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.db.engine import get_session_factory, init_db
from varma.db.models import Employee, Handoff
from varma.db.seed import MI_SLUG, seed_if_empty
from varma.meetings.handoff import deliver_handoff, handoff_to_dict
from varma.skills.challenge_sample_thesis import (
    ChallengeSampleThesis,
    challenge_review_to_dict,
    get_challenge,
)
from varma.skills.prepare_sample_thesis import create_sample_thesis, thesis_to_dict


def run_challenge(session: Session) -> dict:
    thesis = create_sample_thesis(session)
    mi = session.query(Employee).filter_by(slug=MI_SLUG).one()
    challenge = get_challenge(session)
    deliver_handoff(
        session,
        from_employee=mi,
        to_employee=challenge,
        artefact_type="sample_thesis",
        artefact_id=thesis.id,
        purpose="SAMPLE thesis for Challenge. Not a live trade. Not an order.",
        note=(
            "TEMPORARY SAMPLE artefact from Market Intelligence for Challenge. "
            "Watchlist is not the allow-list. No execution authority. "
            "Asha Patel continues to produce the intelligence brief separately."
        ),
        evidence_kind="thesis_handoff",
        status_bubble="THESIS IN",
    )
    review = ChallengeSampleThesis(session).run(challenge, thesis)
    handoff = (
        session.query(Handoff)
        .filter_by(artefact_id=review.id)
        .order_by(Handoff.created_at.desc())
        .first()
    )
    return {
        "thesis": thesis_to_dict(thesis),
        "review": challenge_review_to_dict(review),
        "handoff": handoff_to_dict(handoff) if handoff else None,
        "handoff_recipient": "risk",
        "sample_not_a_live_trade": True,
    }


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        result = run_challenge(session)
        print("SAMPLE thesis — not a live trade")
        print("thesis_id:", result["thesis"]["id"])
        print("symbol:", result["thesis"]["symbol"], "label:", result["thesis"]["label"])
        print("review_id:", result["review"]["id"])
        print("verdict:", result["review"]["verdict"])
        print("handoff_recipient:", result["handoff_recipient"])
        print("no_execution_authority:", result["review"]["no_execution_authority"])
    finally:
        session.close()


if __name__ == "__main__":
    main()
