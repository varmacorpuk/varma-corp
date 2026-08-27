"""On-demand + documented 06:30 Europe/London weekday intelligence brief routine.

Usage:
    python -m varma.routines.run_brief
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import describe_0630_weekday_routine, is_weekday, now_london
from varma.db.engine import get_session_factory, init_db
from varma.db.models import Employee, Handoff
from varma.db.seed import MI_SLUG, seed_if_empty
from varma.meetings.handoff import CEO_SLUG, handoff_to_dict
from varma.skills.prepare_daily_intelligence_brief import (
    PrepareDailyIntelligenceBrief,
    brief_to_dict,
)


def run_brief(session: Session) -> dict:
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    skill = PrepareDailyIntelligenceBrief(session)
    brief = skill.run(emp)
    data = brief_to_dict(brief)
    handoff = (
        session.query(Handoff).filter_by(artefact_id=brief.id).order_by(Handoff.created_at.desc()).first()
    )
    if handoff is not None:
        data["handoff"] = handoff_to_dict(handoff)
        data["handoff_recipient"] = CEO_SLUG
    return data


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        now = now_london()
        print("Routine:", describe_0630_weekday_routine())
        print("Now Europe/London:", now.isoformat())
        print("Weekday:", is_weekday(now), "(on-demand still runs on weekends)")
        result = run_brief(session)
        print("brief_id:", result["id"])
        print("headline:", result["headline"])
        print("freshness:", result["freshness_flag"])
        print("verification_passed:", result["verification_passed"])
        print("stored_in: database table intelligence_briefs")
        print("handoff_recipient:", result.get("handoff_recipient"))
        print("handoff_id:", (result.get("handoff") or {}).get("id"))
        print("verification_notes:", result["verification_notes"])
    finally:
        session.close()


if __name__ == "__main__":
    main()
