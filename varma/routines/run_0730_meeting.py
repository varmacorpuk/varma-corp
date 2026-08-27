"""On-demand 07:30 Europe/London company meeting record. No daemon scheduler.

Usage:
    python -m varma.routines.run_0730_meeting

Board Member API: POST /routines/run-0730-meeting
Not a trade. Not LIVE approval. Employees cannot start LIVE from a meeting.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import describe_0730_company_meeting, now_london
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.meetings.company_meeting import CLI, CompanyMeetingRunner


def run_0730_meeting(session: Session, *, started_by: str = "cli") -> dict:
    return CompanyMeetingRunner(session).run(started_by=started_by)


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        print(describe_0730_company_meeting())
        print("Now Europe/London:", now_london().isoformat())
        print("Daemon: False")
        print("CLI:", CLI)
        result = run_0730_meeting(session, started_by="cli")
        print("meeting_id:", result["id"])
        print("started_by:", result["started_by"])
        print("brief_headline:", result["brief_headline"])
        print("ceo_handoff_status:", result["ceo_handoff_status"])
        print("challenge_status:", result["challenge_status"])
        print("risk_status:", result["risk_status"])
        print("is_trade:", result["is_trade"])
        print("is_live_approval:", result["is_live_approval"])
        print("cannot_start_live:", result["cannot_start_live"])
        print("live_started:", result["live_started"])
        print("attendees:", [a["slug"] for a in result.get("attendees") or []])
        print("attendee_count:", result.get("attendee_count"))
        print("trading_mode:", result["trading_mode_at_run"])
        print("stored_in: database table company_meetings")
    finally:
        session.close()


if __name__ == "__main__":
    main()
