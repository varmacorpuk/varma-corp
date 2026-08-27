"""Seed persistent identities, TEMPORARY watchlist, and Board Addendum A 2026-08-27.

Numeric limits are Board-set (labelled), not invented silent defaults.
Does not seed an execution allow-list. trading_mode stays LIVE_BLOCKED.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import london_day, now_london
from varma.controls.addendum_a import (
    ADDENDUM_A_LABEL,
    ADDENDUM_A_LIMITS,
    ADDENDUM_A_SET_BY,
    CURRENCY,
    EVALUATION_AUTO_SWITCH_LIVE,
    EVALUATION_REQUIRES_BOOK_PROFITABLE,
    EVALUATION_WIN_RATE_THRESHOLD,
    SIMULATED_CAPITAL,
    SUCCESSFUL_TRADE_DEFINITION,
    TIMEZONE,
)
from varma.db.models import (
    ControlState,
    Employee,
    EvaluationPolicy,
    MemoryEmployee,
    NumericLimit,
    PaperAccount,
    Permission,
    Routine,
    Skill,
    WatchlistItem,
)
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG

MI_SLUG = "market-intelligence-research"

# Board door/title lock. display_name is the office door label, not a person name.
BOARD_DOOR_NAMES = (
    (MI_SLUG, "Research"),
    (CEO_SLUG, "CEO"),
    (CHALLENGE_SLUG, "Challenge"),
    (RISK_SLUG, "Risk"),
)
RESEARCH_PERSON_NAME = "Asha Patel"

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
            display_name="Research",
            person_name="Asha Patel",
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
    _apply_board_door_names(session)

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

    seed_board_addendum_a(session)
    session.commit()


def seed_board_addendum_a(session: Session) -> None:
    """Write Board Addendum A 2026-08-27 into control tables.

    These are Board-set values, labelled as such. Not invented silent defaults.
    Does not write an execution allow-list. Does not switch trading_mode to PAPER
    or LIVE. Empty allow-list still denies orders.
    """
    now = now_london()
    for key, value, unit in ADDENDUM_A_LIMITS:
        row = session.get(NumericLimit, key)
        if row is None:
            session.add(
                NumericLimit(
                    key=key,
                    value=value,
                    unit=unit,
                    set_by=ADDENDUM_A_SET_BY,
                    set_at=now,
                    source=ADDENDUM_A_LABEL,
                )
            )
        elif row.value in (None, ""):
            row.value = value
            row.unit = unit
            row.set_by = ADDENDUM_A_SET_BY
            row.set_at = now
            row.source = ADDENDUM_A_LABEL

    policy = session.get(EvaluationPolicy, 1)
    if policy is None:
        session.add(
            EvaluationPolicy(
                id=1,
                currency=CURRENCY,
                timezone=TIMEZONE,
                successful_trade_definition=SUCCESSFUL_TRADE_DEFINITION,
                win_rate_threshold=str(EVALUATION_WIN_RATE_THRESHOLD),
                requires_book_profitable=EVALUATION_REQUIRES_BOOK_PROFITABLE,
                auto_switch_live=EVALUATION_AUTO_SWITCH_LIVE,
                paper_continues_until_board_approval=True,
                source=ADDENDUM_A_LABEL,
                set_by=ADDENDUM_A_SET_BY,
                set_at=now,
            )
        )

    account = session.get(PaperAccount, 1)
    if account is None:
        session.add(
            PaperAccount(
                id=1,
                currency=CURRENCY,
                timezone=TIMEZONE,
                simulated_capital=SIMULATED_CAPITAL,
                cash=SIMULATED_CAPITAL,
                equity_at_day_start=SIMULATED_CAPITAL,
                london_day=london_day(),
                source=ADDENDUM_A_LABEL,
                updated_at=now,
            )
        )

    session.flush()


def _apply_board_door_names(session: Session) -> None:
    """Board naming lock: doors/titles are CEO, Research, Challenge, Risk.

    slug stays stable. Asha Patel is an internal person_name only, not the door.
    """
    for slug, door in BOARD_DOOR_NAMES:
        emp = session.query(Employee).filter_by(slug=slug).one_or_none()
        if emp is None:
            continue
        emp.display_name = door
        if slug == MI_SLUG:
            emp.person_name = RESEARCH_PERSON_NAME
        elif not emp.person_name:
            emp.person_name = ""


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
