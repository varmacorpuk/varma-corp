"""Seed persistent identities and TEMPORARY development defaults. Does not invent Board-permanent numbers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import (
    ControlState,
    Employee,
    MemoryEmployee,
    Permission,
    Routine,
    Skill,
    WatchlistItem,
)
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG

MI_SLUG = "market-intelligence-research"

# TEMPORARY DEVELOPMENT DEFAULT watchlist. Listed stocks/equities only.
# NOT the execution allow-list. Not Board-approved universe membership (OPEN).
TEMPORARY_WATCHLIST = (
    ("AAPL", "Apple Inc.", "NASDAQ"),
    ("MSFT", "Microsoft Corporation", "NASDAQ"),
    ("SHEL.L", "Shell plc", "LSE"),
    ("AZN.L", "AstraZeneca PLC", "LSE"),
)


def seed_if_empty(session: Session) -> None:
    if session.get(ControlState, 1) is None:
        session.add(
            ControlState(
                id=1,
                trading_mode="LIVE_BLOCKED",
                kill_switch=False,
                updated_at=now_london(),
                updated_by="system-seed",
            )
        )

    mi = session.query(Employee).filter_by(slug=MI_SLUG).one_or_none()
    if mi is None:
        mi = Employee(
            slug=MI_SLUG,
            display_name="Asha Patel",
            role_title="Market Intelligence / Research Analyst",
            department="Market Intelligence / Research",
            personality=(
                "Calm, source-first, distinguishes fact from commentary. "
                "Does not overclaim. Personality never overrides controls."
            ),
            responsibilities=(
                "Answer: what is happening, and what might matter to Varma Corp.? "
                "Produce the pre-07:30 Europe/London intelligence brief. "
                "Research-only. Cannot place orders. Cannot write control tables."
            ),
            authority_boundaries=(
                "No execution. No allow-list writes. No trading_mode writes. "
                "No numeric limit writes. Opportunity Radar (future) is research-only. "
                "Gold is FUTURE SCOPE ONLY and is not an execution universe."
            ),
            status="AVAILABLE",
            status_bubble="AVAILABLE",
            office_x=96,
            office_y=108,
            is_primary_agent=1,
            created_at=now_london(),
        )
        session.add(mi)
        session.flush()

        session.add(
            Skill(
                name="prepare_daily_intelligence_brief",
                version="0.1.0",
                employee_id=mi.id,
                description="Structured pre-07:30 intelligence brief for the company meeting.",
                active=True,
            )
        )
        session.add(
            Routine(
                name="weekday_0630_london_intelligence_brief",
                employee_id=mi.id,
                skill_name="prepare_daily_intelligence_brief",
                schedule="06:30 weekdays",
                timezone="Europe/London",
                enabled=True,
                notes=(
                    "Documented 06:30 Europe/London weekday routine (Document 18). "
                    "On-demand via python -m varma.routines.run_brief. "
                    "No daemon scheduler in this slice."
                ),
            )
        )
        session.add(
            MemoryEmployee(
                employee_id=mi.id,
                kind="lesson",
                content=(
                    "Material claims in a brief must carry source and timestamp. "
                    "Stale data must be flagged, never presented as current. "
                    "A brief is not a trade recommendation and grants no execution authority."
                ),
                created_at=now_london(),
            )
        )
        session.add(
            Permission(
                subject_type="employee",
                subject_id=mi.id,
                action="run_skill:prepare_daily_intelligence_brief",
                allowed=True,
            )
        )
        session.add(
            Permission(
                subject_type="employee",
                subject_id=mi.id,
                action="place_order",
                allowed=False,
            )
        )
        session.add(
            Permission(
                subject_type="employee",
                subject_id=mi.id,
                action="write_controls",
                allowed=False,
            )
        )

    _seed_ceo(session)
    _seed_challenge(session)
    _seed_risk(session)

    if session.query(WatchlistItem).count() == 0:
        for symbol, name, venue in TEMPORARY_WATCHLIST:
            session.add(
                WatchlistItem(
                    symbol=symbol,
                    name=name,
                    venue=venue,
                    asset_class="listed_equity",
                    label="TEMPORARY DEVELOPMENT DEFAULT",
                )
            )

    session.commit()


def _seed_ceo(session: Session) -> None:
    """Persistent CEO identity. Meeting recipient of the MI brief. Cannot approve LIVE."""
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one_or_none()
    if ceo is not None:
        return
    ceo = Employee(
        slug=CEO_SLUG,
        display_name="CEO",
        role_title="Chief Executive Officer",
        department="CEO / Management",
        personality=(
            "Operational, holds the meeting pack, does not treat a brief as a trade. "
            "Does not approve live trading. Personality never overrides controls."
        ),
        responsibilities=(
            "Meeting recipient of the Market Intelligence brief for the 07:30 "
            "Europe/London company meeting (Document 18). "
            "Cannot place orders. Cannot write control tables. Cannot approve LIVE."
        ),
        authority_boundaries=(
            "No live-trading approval — Board Member only (Document 11). "
            "No execution. No allow-list writes. No trading_mode writes. "
            "No numeric limit writes. A handoff is not execution authority."
        ),
        status="AVAILABLE",
        status_bubble="AVAILABLE",
        office_x=220,
        office_y=70,
        is_primary_agent=1,
        created_at=now_london(),
    )
    session.add(ceo)
    session.flush()
    session.add(
        MemoryEmployee(
            employee_id=ceo.id,
            kind="lesson",
            content=(
                "The intelligence brief is a meeting pack, not a trade. "
                "CEO cannot approve live trading. Explicit Board Member approval is required. "
                "Silence is not approval."
            ),
            created_at=now_london(),
        )
    )
    for action, allowed in (
        ("place_order", False),
        ("write_controls", False),
        ("approve_live", False),
        ("transition_to_live", False),
    ):
        session.add(
            Permission(
                subject_type="employee",
                subject_id=ceo.id,
                action=action,
                allowed=allowed,
            )
        )


def _deny_live_and_execution(session: Session, employee_id: str, extra: tuple[tuple[str, bool], ...] = ()) -> None:
    for action, allowed in (
        ("place_order", False),
        ("write_controls", False),
        ("approve_live", False),
        ("transition_to_live", False),
        *extra,
    ):
        session.add(
            Permission(
                subject_type="employee",
                subject_id=employee_id,
                action=action,
                allowed=allowed,
            )
        )


def _seed_challenge(session: Session) -> None:
    """Persistent Challenge identity. Challenges a SAMPLE thesis. Not a live trade."""
    emp = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one_or_none()
    if emp is not None:
        return
    emp = Employee(
        slug=CHALLENGE_SLUG,
        display_name="Challenge",
        role_title="Challenge",
        department="Challenge / Research Quality",
        personality=(
            "Sceptical, assumption-hunting, distinguishes a SAMPLE thesis from an order. "
            "Does not approve live trading. Personality never overrides controls."
        ),
        responsibilities=(
            "Challenge a SAMPLE thesis (not a live trade). "
            "Surface invalidating assumptions. Cannot place orders. "
            "Cannot write control tables. Cannot approve LIVE."
        ),
        authority_boundaries=(
            "No live-trading approval — Board Member only (Document 11). "
            "No execution. A challenged SAMPLE thesis is not an order. "
            "Watchlist membership is not allow-list membership."
        ),
        status="AVAILABLE",
        status_bubble="AVAILABLE",
        office_x=40,
        office_y=48,
        is_primary_agent=1,
        created_at=now_london(),
    )
    session.add(emp)
    session.flush()
    session.add(
        Skill(
            name="challenge_sample_thesis",
            version="0.1.0",
            employee_id=emp.id,
            description="Challenge a SAMPLE thesis. Not a live trade.",
            active=True,
        )
    )
    session.add(
        MemoryEmployee(
            employee_id=emp.id,
            kind="lesson",
            content=(
                "A SAMPLE thesis is an exercise, not an order. "
                "Challenge does not grant execution authority. "
                "Challenge cannot approve live trading."
            ),
            created_at=now_london(),
        )
    )
    _deny_live_and_execution(
        session,
        emp.id,
        extra=(("run_skill:challenge_sample_thesis", True),),
    )


def _seed_risk(session: Session) -> None:
    """Persistent Risk identity. Deny-path demo. Cannot approve LIVE."""
    emp = session.query(Employee).filter_by(slug=RISK_SLUG).one_or_none()
    if emp is not None:
        return
    emp = Employee(
        slug=RISK_SLUG,
        display_name="Risk",
        role_title="Risk",
        department="Risk / Controls",
        personality=(
            "Policy-first, deny unsafe paths, does not treat a SAMPLE thesis as an order. "
            "Does not approve live trading. Personality never overrides controls."
        ),
        responsibilities=(
            "Review proposed paths against controls. Deny unsafe or out-of-policy paths. "
            "Cannot place orders. Cannot write control tables. Cannot approve LIVE."
        ),
        authority_boundaries=(
            "No live-trading approval — Board Member only (Document 11). "
            "No execution. Empty allow-list cannot execute. Gold is not an execution universe. "
            "A Risk DENY is recorded in the database. Silence is not approval."
        ),
        status="AVAILABLE",
        status_bubble="AVAILABLE",
        office_x=255,
        office_y=175,
        is_primary_agent=1,
        created_at=now_london(),
    )
    session.add(emp)
    session.flush()
    session.add(
        Skill(
            name="review_unsafe_path",
            version="0.1.0",
            employee_id=emp.id,
            description="Deny-path demo: review an unsafe/out-of-policy proposal and DENY it.",
            active=True,
        )
    )
    session.add(
        MemoryEmployee(
            employee_id=emp.id,
            kind="lesson",
            content=(
                "Unsafe paths are denied. LIVE is blocked. The allow-list is empty. "
                "Gold is FUTURE SCOPE ONLY. A SAMPLE thesis is not an order. "
                "Risk cannot approve live trading."
            ),
            created_at=now_london(),
        )
    )
    _deny_live_and_execution(
        session,
        emp.id,
        extra=(("run_skill:review_unsafe_path", True),),
    )
