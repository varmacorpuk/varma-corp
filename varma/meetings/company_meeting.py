"""On-demand 07:30 Europe/London company meeting record (Documents 09, 18).

Board Member or documented CLI. Writes a database artefact from existing
handoffs. Not a trade. Not LIVE approval. Not a daemon.
Employees cannot start LIVE from a meeting.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import describe_0730_company_meeting, now_london
from varma.controls.engine import ControlEngine
from varma.db.models import (
    AllowListInstrument,
    ChallengeReview,
    CompanyMeeting,
    CompanyMeetingAttendee,
    ControlState,
    Employee,
    Evidence,
    Handoff,
    IntelligenceBrief,
    NumericLimit,
    Permission,
    RiskDecision,
    SampleThesis,
)
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG

MI_SLUG = "market-intelligence-research"

MEETING_LABEL = "07:30 Europe/London company meeting"
SCHEDULE = "07:30 weekdays"
TIMEZONE = "Europe/London"
CLI = "python -m varma.routines.run_0730_meeting"
MEETING_ACTOR = "0730-company-meeting"
# Documented 07:30 attendees: the four existing employees only. Not a 12-person roster.
ATTENDEE_SLUGS = (MI_SLUG, CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG)


def _permission_fingerprint(session: Session) -> list[tuple[str, str, bool]]:
    rows = (
        session.query(Permission)
        .order_by(Permission.subject_id, Permission.action)
        .all()
    )
    return [(r.subject_id, r.action, bool(r.allowed)) for r in rows]


def _limit_fingerprint(session: Session) -> list[tuple[str, str | None]]:
    rows = session.query(NumericLimit).order_by(NumericLimit.key).all()
    return [(r.key, r.value) for r in rows]


def _controls_guard(session: Session) -> dict[str, Any]:
    engine = ControlEngine(session)
    state = session.get(ControlState, 1)
    return {
        "snapshot": engine.snapshot(),
        "trading_mode": state.trading_mode if state else None,
        "kill_switch": bool(state.kill_switch) if state else None,
        "allow_list": sorted(r.symbol for r in session.query(AllowListInstrument).all()),
        "permissions": _permission_fingerprint(session),
        "limits": _limit_fingerprint(session),
    }


def latest_meeting_pack(session: Session) -> dict[str, Any]:
    """Read existing handoff artefacts. Does not create a trade or LIVE approval."""
    brief = (
        session.query(IntelligenceBrief)
        .order_by(IntelligenceBrief.produced_at.desc())
        .first()
    )
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one_or_none()
    handoff = None
    if brief is not None and ceo is not None:
        handoff = (
            session.query(Handoff)
            .filter_by(
                to_employee_id=ceo.id,
                artefact_type="intelligence_brief",
                artefact_id=brief.id,
            )
            .order_by(Handoff.created_at.desc())
            .first()
        )
    thesis = session.query(SampleThesis).order_by(SampleThesis.created_at.desc()).first()
    review = None
    if thesis is not None:
        review = (
            session.query(ChallengeReview)
            .filter_by(thesis_id=thesis.id)
            .order_by(ChallengeReview.produced_at.desc())
            .first()
        )
    risk = session.query(RiskDecision).order_by(RiskDecision.produced_at.desc()).first()
    if review is not None:
        challenge_status = str(review.verdict or "SAMPLE")
    elif thesis is not None:
        challenge_status = "SAMPLE"
    else:
        challenge_status = "not"
    risk_denied = bool(risk is not None and risk.decision == "DENIED")
    return {
        "brief": brief,
        "ceo": ceo,
        "handoff": handoff,
        "thesis": thesis,
        "review": review,
        "risk": risk,
        "brief_headline": brief.headline if brief else None,
        "ceo_handoff_status": "DELIVERED" if (handoff and handoff.status == "DELIVERED") else "not",
        "challenge_status": challenge_status,
        "risk_status": "DENIED" if risk_denied else "not",
        "risk_denied": risk_denied,
    }


def attendee_to_dict(row: CompanyMeetingAttendee) -> dict[str, Any]:
    return {
        "employee_id": row.employee_id,
        "slug": row.slug,
        "display_name": row.display_name,
        "role_title": row.role_title,
        "department": row.department,
        "cannot_approve_live": bool(row.cannot_approve_live),
        "is_board_member": bool(row.is_board_member),
        "read_only": True,
    }


def attendees_for(session: Session, meeting_id: str) -> list[CompanyMeetingAttendee]:
    rows = (
        session.query(CompanyMeetingAttendee)
        .filter_by(meeting_id=meeting_id)
        .all()
    )
    order = {slug: i for i, slug in enumerate(ATTENDEE_SLUGS)}
    return sorted(rows, key=lambda r: order.get(r.slug, 99))


def meeting_to_dict(row: CompanyMeeting, attendees: list[CompanyMeetingAttendee] | None = None) -> dict[str, Any]:
    attendee_rows = attendees if attendees is not None else []
    return {
        "id": row.id,
        "ran_at": row.ran_at.isoformat() if row.ran_at else None,
        "timezone": row.timezone,
        "schedule": row.schedule,
        "meeting": MEETING_LABEL,
        "daemon": bool(row.daemon),
        "started_by": row.started_by,
        "brief_id": row.brief_id,
        "ceo_handoff_id": row.ceo_handoff_id,
        "thesis_id": row.thesis_id,
        "challenge_review_id": row.challenge_review_id,
        "risk_decision_id": row.risk_decision_id,
        "brief_headline": row.brief_headline,
        "ceo_handoff_status": row.ceo_handoff_status,
        "challenge_status": row.challenge_status,
        "risk_status": row.risk_status,
        "trading_mode_at_run": row.trading_mode_at_run,
        "is_trade": bool(row.is_trade),
        "is_live_approval": bool(row.is_live_approval),
        "cannot_start_live": bool(row.cannot_start_live),
        "live_started": bool(row.live_started),
        "writes_controls": bool(row.writes_controls),
        "notes": row.notes,
        "cli": CLI,
        "sample_not_a_live_trade": True,
        "employees_cannot_start_live": True,
        "attendees": [attendee_to_dict(a) for a in attendee_rows],
        "attendee_count": len(attendee_rows),
        "roster_size": 4,
        "not_a_twelve_employee_roster": True,
    }


class CompanyMeetingRunner:
    """Record a 07:30 meeting from existing handoffs. Never start LIVE. Never fill."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self, *, started_by: str) -> dict[str, Any]:
        before = _controls_guard(self.session)
        pack = latest_meeting_pack(self.session)
        row = CompanyMeeting(
            ran_at=now_london(),
            timezone=TIMEZONE,
            schedule=SCHEDULE,
            daemon=False,
            started_by=started_by,
            brief_id=pack["brief"].id if pack["brief"] is not None else None,
            ceo_handoff_id=pack["handoff"].id if pack["handoff"] is not None else None,
            thesis_id=pack["thesis"].id if pack["thesis"] is not None else None,
            challenge_review_id=pack["review"].id if pack["review"] is not None else None,
            risk_decision_id=pack["risk"].id if pack["risk"] is not None else None,
            brief_headline=pack["brief_headline"],
            ceo_handoff_status=pack["ceo_handoff_status"],
            challenge_status=pack["challenge_status"],
            risk_status=pack["risk_status"],
            trading_mode_at_run=str(before["trading_mode"] or ""),
            is_trade=False,
            is_live_approval=False,
            cannot_start_live=True,
            live_started=False,
            writes_controls=False,
            notes=describe_0730_company_meeting(),
        )
        self.session.add(row)
        self.session.flush()
        attendees = _record_attendees(self.session, row.id)
        self.session.add(
            Evidence(
                kind="company_meeting_ran",
                actor=MEETING_ACTOR,
                payload=json.dumps(
                    {
                        "meeting_id": row.id,
                        "started_by": started_by,
                        "is_trade": False,
                        "is_live_approval": False,
                        "cannot_start_live": True,
                        "live_started": False,
                        "writes_controls": False,
                        "daemon": False,
                        "brief_id": row.brief_id,
                        "ceo_handoff_id": row.ceo_handoff_id,
                        "thesis_id": row.thesis_id,
                        "challenge_review_id": row.challenge_review_id,
                        "risk_decision_id": row.risk_decision_id,
                        "attendee_slugs": [a.slug for a in attendees],
                        "attendee_count": len(attendees),
                        "not_a_twelve_employee_roster": True,
                    }
                ),
                created_at=now_london(),
            )
        )
        self.session.flush()
        after = _controls_guard(self.session)
        if after["trading_mode"] != before["trading_mode"]:
            raise RuntimeError("COMPANY_MEETING_MUST_NOT_WRITE_CONTROLS")
        if after["kill_switch"] != before["kill_switch"]:
            raise RuntimeError("COMPANY_MEETING_MUST_NOT_WRITE_CONTROLS")
        if after["allow_list"] != before["allow_list"]:
            raise RuntimeError("COMPANY_MEETING_MUST_NOT_WRITE_CONTROLS")
        if after["permissions"] != before["permissions"]:
            raise RuntimeError("COMPANY_MEETING_MUST_NOT_WRITE_CONTROLS")
        if after["limits"] != before["limits"]:
            raise RuntimeError("COMPANY_MEETING_MUST_NOT_WRITE_CONTROLS")
        if after["trading_mode"] == "LIVE":
            raise RuntimeError("COMPANY_MEETING_MUST_NOT_START_LIVE")
        self.session.commit()
        data = meeting_to_dict(row, attendees)
        data["live_still_blocked"] = row.trading_mode_at_run == "LIVE_BLOCKED"
        data["description"] = describe_0730_company_meeting()
        return data


def _record_attendees(session: Session, meeting_id: str) -> list[CompanyMeetingAttendee]:
    """Snapshot the four existing employees. Do not invent a 12-person roster."""
    recorded: list[CompanyMeetingAttendee] = []
    for slug in ATTENDEE_SLUGS:
        emp = session.query(Employee).filter_by(slug=slug).one()
        row = CompanyMeetingAttendee(
            meeting_id=meeting_id,
            employee_id=emp.id,
            slug=emp.slug,
            display_name=emp.display_name,
            role_title=emp.role_title,
            department=emp.department,
            cannot_approve_live=True,
            is_board_member=False,
        )
        session.add(row)
        recorded.append(row)
    session.flush()
    return recorded
