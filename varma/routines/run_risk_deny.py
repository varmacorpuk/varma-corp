"""On-demand Risk deny-path demo. Not a live trade. No daemon scheduler.

Usage:
    python -m varma.routines.run_risk_deny
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.controls.risk import UNSAFE_DEMO_PATH
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.meetings.handoff import CHALLENGE_SLUG, get_employee
from varma.skills.review_unsafe_path import (
    ReviewUnsafePath,
    get_risk,
    latest_challenge_review,
    risk_decision_to_dict,
)


def run_risk_deny(session: Session) -> dict:
    risk = get_risk(session)
    review = latest_challenge_review(session)
    originator = get_employee(session, CHALLENGE_SLUG) if review is not None else None
    decision = ReviewUnsafePath(session).run(
        risk,
        proposed=UNSAFE_DEMO_PATH,
        thesis_id=review.thesis_id if review else None,
        challenge_review_id=review.id if review else None,
        originator=originator,
    )
    data = risk_decision_to_dict(decision)
    data["sample_not_a_live_trade"] = True
    data["risk_cannot_approve_live"] = True
    return data


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        result = run_risk_deny(session)
        print("Risk deny-path demo — not a live trade")
        print("decision_id:", result["id"])
        print("decision:", result["decision"])
        print("path_kind:", result["path_kind"])
        print("reasons:", result["reasons"])
        print("control_engine_reason:", result["control_engine_reason"])
        print("cannot_approve_live:", result["cannot_approve_live"])
    finally:
        session.close()


if __name__ == "__main__":
    main()
