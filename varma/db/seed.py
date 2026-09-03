"""Seed persistent identities, Board Addenda A/C/E/F/I/J/K, and TEMPORARY watchlist.

Numeric limits are Board Addendum A 2026-08-27 (Board-set).
Paper session is Board Addendum C 2026-08-27 (UK open through US close).
PAPER allow-list is Board Addendum E 2026-08-27 (Board-set).
Staff display is Board Addendum F 2026-08-27 (person · department).
Company CLOSED until Grand Opening: Board Addendum I 2026-08-27
(two-opening rule). Grand Opening PAPER 2026-09-03 (Hari explicit yes).
Encrypted company backup: Board Addendum J 2026-08-27 (database artefact; not git).
LSE after London cash close: Board Addendum K 2026-09-03 (Hari explicit yes).
seed_if_empty reconciles those Board-encoded rows onto a stale SQLite copy.
trading_mode stays LIVE_BLOCKED. LIVE and BROKER_PAPER remain UNLOADED.
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
from varma.controls.addendum_c import (
    ADDENDUM_C_LABEL,
    ADDENDUM_C_SET_BY,
    ADDENDUM_C_SETTINGS,
)
from varma.controls.addendum_e import (
    ADDENDUM_E_INSTRUMENTS,
    ADDENDUM_E_LABEL,
    ADDENDUM_E_SET_BY,
)
from varma.controls.addendum_f import (
    QUANT_SLUG,
    TECH_SLUG,
    TRADER_SLUG,
    format_staff_display,
    staff_display_for_slug,
)
from varma.controls.addendum_i import (
    ADDENDUM_I_LABEL,
    ADDENDUM_I_SET_BY,
    ADDENDUM_I_SETTINGS,
)
from varma.controls.addendum_j import (
    ADDENDUM_J_LABEL,
    ADDENDUM_J_SET_BY,
    ADDENDUM_J_SETTINGS,
    BACKUP_ROUTINE_NAME,
    BACKUP_SCHEDULE,
    BACKUP_SKILL_NAME,
    BACKUP_TIMEZONE,
)
from varma.controls.addendum_k import (
    ADDENDUM_K_LABEL,
    ADDENDUM_K_SET_BY,
    ADDENDUM_K_SETTINGS,
)
from varma.db.models import (
    AllowListInstrument,
    ControlSetting,
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
from varma.employees.brain import seed_employee_brains
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG

MI_SLUG = "market-intelligence-research"

# Door/role stays the job title. display_name is "First Last · Department" (Addendum F).
BOARD_DOOR_NAMES = (
    (MI_SLUG, "Research"),
    (CEO_SLUG, "CEO"),
    (CHALLENGE_SLUG, "Challenge"),
    (RISK_SLUG, "Risk"),
    (TRADER_SLUG, "Trader"),
    (QUANT_SLUG, "Quant"),
    (TECH_SLUG, "Technology"),
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
    """Reconcile Board-encoded defaults. Safe on a stale SQLite copy.

    Always applies Addenda A/C/E/F/I/J and the seven named employees, even when
    control_state already exists. Does not start a 24/7 daemon. trading_mode
    stays LIVE_BLOCKED. Kill switch is not reset. Trader may propose paper
    tickets; paper may fill after Grand Opening PAPER. LIVE stays blocked.
    """
    now = now_london()
    state = session.get(ControlState, 1)
    if state is None:
        session.add(
            ControlState(
                id=1,
                trading_mode="LIVE_BLOCKED",
                kill_switch=False,
                updated_at=now,
                updated_by="system-seed",
            )
        )
    elif state.trading_mode != "LIVE_BLOCKED":
        state.trading_mode = "LIVE_BLOCKED"
        state.updated_at = now
        state.updated_by = "board-reconcile"

    mi = session.query(Employee).filter_by(slug=MI_SLUG).one_or_none()
    if mi is None:
        mi = Employee(
            slug=MI_SLUG,
            display_name=staff_display_for_slug(MI_SLUG),
            person_name=RESEARCH_PERSON_NAME,
            role_title="Market Intelligence / Research Analyst",
            department="Research",
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
        session.add(
            Permission(
                subject_type="employee",
                subject_id=mi.id,
                action="download_secrets",
                allowed=False,
            )
        )
        session.add(
            Permission(
                subject_type="employee",
                subject_id=mi.id,
                action="open_firm",
                allowed=False,
            )
        )

    _seed_ceo(session)
    _seed_challenge(session)
    _seed_risk(session)
    _seed_trader(session)
    _seed_quant(session)
    _seed_technology(session)
    _apply_addendum_f_display(session)

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
    seed_board_addendum_c(session)
    seed_board_addendum_e(session)
    seed_board_addendum_k(session)
    seed_board_addendum_i(session)
    seed_board_addendum_j(session)
    seed_employee_brains(session)
    _reconcile_employee_locks(session)
    session.commit()


def seed_board_addendum_a(session: Session) -> None:
    """Write Board Addendum A 2026-08-27 into control tables.

    These are Board-set values, labelled as such. Not invented silent defaults.
    Does not switch trading_mode to PAPER or LIVE. PAPER allow-list is Addendum E.
    Unknown tickers still deny. Gold still denies.
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


def seed_board_addendum_c(session: Session) -> None:
    """Write Board Addendum C 2026-08-27 into control tables.

    Paper desk: UK cash open through US regular cash close (Europe/London clock).
    Flatten ALL paper before US regular cash close. Do NOT flatten at London close.
    Does not write an execution allow-list. Does not switch trading_mode.
    """
    now = now_london()
    for key, value, unit in ADDENDUM_C_SETTINGS:
        row = session.get(ControlSetting, key)
        if row is None:
            session.add(
                ControlSetting(
                    key=key,
                    value=value,
                    unit=unit,
                    set_by=ADDENDUM_C_SET_BY,
                    set_at=now,
                    source=ADDENDUM_C_LABEL,
                )
            )
        elif row.value in (None, ""):
            row.value = value
            row.unit = unit
            row.set_by = ADDENDUM_C_SET_BY
            row.set_at = now
            row.source = ADDENDUM_C_LABEL
    session.flush()


def seed_board_addendum_k(session: Session) -> None:
    """Write Board Addendum K 2026-09-03 LSE-after-London-cash-close rule.

    Hari explicit yes. Does not rewrite Addendum C flatten. Does not invent
    US listings. Employees cannot write this. LIVE stays blocked.
    Always reconciles onto a stale UNSET row so main gets one coherent path.
    """
    now = now_london()
    for key, value, unit in ADDENDUM_K_SETTINGS:
        row = session.get(ControlSetting, key)
        if row is None:
            session.add(
                ControlSetting(
                    key=key,
                    value=value,
                    unit=unit,
                    set_by=ADDENDUM_K_SET_BY,
                    set_at=now,
                    source=ADDENDUM_K_LABEL,
                )
            )
        else:
            row.value = value
            row.unit = unit
            row.set_by = ADDENDUM_K_SET_BY
            row.set_at = now
            row.source = ADDENDUM_K_LABEL
    session.flush()


def seed_lse_session_hold(session: Session) -> None:
    """Alias: Addendum K is the Board-set LSE session rule."""
    seed_board_addendum_k(session)


def seed_board_addendum_i(session: Session) -> None:
    """Write Board Addendum I plus authorised Grand Opening PAPER default.

    Addendum I remains the two-opening rule. Fresh seed: paper OPEN, live
    BLOCKED. Employees including the CEO cannot write it. Does not open LIVE.
    Does not load brokers.
    """
    now = now_london()
    for key, value, unit in ADDENDUM_I_SETTINGS:
        row = session.get(ControlSetting, key)
        if row is None:
            session.add(
                ControlSetting(
                    key=key,
                    value=value,
                    unit=unit,
                    set_by=ADDENDUM_I_SET_BY,
                    set_at=now,
                    source=ADDENDUM_I_LABEL,
                )
            )
        else:
            row.value = value
            row.unit = unit
            row.set_by = ADDENDUM_I_SET_BY
            row.set_at = now
            row.source = ADDENDUM_I_LABEL
    session.flush()


def seed_board_addendum_j(session: Session) -> None:
    """Write Board Addendum J 2026-08-27 backup ownership and exclusions.

    Encrypted artefact stays in the database. GitHub is code only.
    Technology owns the job. Employees cannot download secrets.
    Does not fill. Does not open the firm.
    """
    now = now_london()
    for key, value, unit in ADDENDUM_J_SETTINGS:
        row = session.get(ControlSetting, key)
        if row is None:
            session.add(
                ControlSetting(
                    key=key,
                    value=value,
                    unit=unit,
                    set_by=ADDENDUM_J_SET_BY,
                    set_at=now,
                    source=ADDENDUM_J_LABEL,
                )
            )
        elif row.value in (None, ""):
            row.value = value
            row.unit = unit
            row.set_by = ADDENDUM_J_SET_BY
            row.set_at = now
            row.source = ADDENDUM_J_LABEL
    tech = session.query(Employee).filter_by(slug=TECH_SLUG).one_or_none()
    if tech is not None:
        tech.responsibilities = (
            "Technology and self-maintenance of the company kernel. "
            "Owns the company backup job (Board Addendum J). "
            "Cannot write control tables, allow-list, or trading_mode. "
            "Cannot open the firm. Cannot download secrets. Cannot approve LIVE."
        )
        tech.authority_boundaries = (
            "No live-trading approval — Board Member only (Document 11). "
            "No execution. No control writes. Cannot write trading_mode or "
            "allow-list. Cannot open the firm. Cannot download secrets. "
            "No Mac installers in this slice."
        )
        if (
            session.query(Skill)
            .filter_by(employee_id=tech.id, name=BACKUP_SKILL_NAME)
            .one_or_none()
            is None
        ):
            session.add(
                Skill(
                    name=BACKUP_SKILL_NAME,
                    version="0.1.0",
                    employee_id=tech.id,
                    description=(
                        "Encrypted company backup into the database. "
                        "Paper ledger, evidence, organisational memory, control snapshots. "
                        "No secrets. No live broker credentials."
                    ),
                    active=True,
                )
            )
        if (
            session.query(Routine)
            .filter_by(employee_id=tech.id, name=BACKUP_ROUTINE_NAME)
            .one_or_none()
            is None
        ):
            session.add(
                Routine(
                    name=BACKUP_ROUTINE_NAME,
                    employee_id=tech.id,
                    skill_name=BACKUP_SKILL_NAME,
                    schedule=BACKUP_SCHEDULE,
                    timezone=BACKUP_TIMEZONE,
                    enabled=True,
                    notes=(
                        "Board Addendum J 2026-08-27. Daily after US close / end of "
                        "London evening. On-demand via python -m varma.routines.run_backup. "
                        "No daemon scheduler in this slice. Encrypted at rest in the "
                        "database. Not in GitHub. Not on the Board Member laptop."
                    ),
                )
            )
        for action in ("download_secrets", "open_firm", "write_allow_list"):
            perm = (
                session.query(Permission)
                .filter_by(subject_type="employee", subject_id=tech.id, action=action)
                .one_or_none()
            )
            if perm is None:
                session.add(
                    Permission(
                        subject_type="employee",
                        subject_id=tech.id,
                        action=action,
                        allowed=False,
                    )
                )
            else:
                perm.allowed = False
    session.flush()


def seed_board_addendum_e(session: Session) -> None:
    """Write Board Addendum E 2026-08-27 PAPER execution allow-list.

    Board-set. Employees including the CEO cannot write this list.
    Does not load LIVE or BROKER_PAPER. Does not switch trading_mode.
    Recodes listing venues onto a stale copy (JPM/JNJ are NYSE).
    Addendum I: the list exists but cannot be used for fills until open.
    """
    now = now_london()
    for symbol, venue in ADDENDUM_E_INSTRUMENTS:
        row = session.query(AllowListInstrument).filter_by(symbol=symbol).one_or_none()
        if row is None:
            session.add(
                AllowListInstrument(
                    symbol=symbol,
                    venue=venue,
                    approved_by=ADDENDUM_E_SET_BY,
                    approved_at=now,
                )
            )
        elif row.venue != venue:
            # Recode listing venue onto a stale copy. Encoding only. Does not fill.
            row.venue = venue
            row.approved_by = ADDENDUM_E_SET_BY
            row.approved_at = now
    session.flush()


def _apply_addendum_f_display(session: Session) -> None:
    """Board Addendum F: display_name is person · department, not a job-only label.

    Door/role stays the job title (department). person_name is the person.
    """
    from varma.controls.addendum_f import STAFF_PEOPLE

    for slug, (person, department) in STAFF_PEOPLE.items():
        emp = session.query(Employee).filter_by(slug=slug).one_or_none()
        if emp is None:
            continue
        emp.person_name = person
        emp.department = department
        emp.display_name = format_staff_display(person, department)


def _apply_board_door_names(session: Session) -> None:
    _apply_addendum_f_display(session)


def _seed_ceo(session: Session) -> None:
    """Persistent CEO identity. Meeting recipient of the MI brief. Cannot approve LIVE."""
    ceo = session.query(Employee).filter_by(slug=CEO_SLUG).one_or_none()
    if ceo is not None:
        return
    ceo = Employee(
        slug=CEO_SLUG,
        display_name=staff_display_for_slug(CEO_SLUG),
        person_name="Jordan Hale",
        role_title="Chief Executive Officer",
        department="CEO",
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


def _upsert_permission(session: Session, employee_id: str, action: str, allowed: bool) -> None:
    row = (
        session.query(Permission)
        .filter_by(subject_type="employee", subject_id=employee_id, action=action)
        .one_or_none()
    )
    if row is None:
        session.add(
            Permission(
                subject_type="employee",
                subject_id=employee_id,
                action=action,
                allowed=allowed,
            )
        )
    else:
        row.allowed = allowed


def _deny_live_and_execution(session: Session, employee_id: str, extra: tuple[tuple[str, bool], ...] = ()) -> None:
    actions = {
        "place_order": False,
        "write_controls": False,
        "approve_live": False,
        "transition_to_live": False,
        "download_secrets": False,
        "open_firm": False,
    }
    actions.update(dict(extra))
    for action, allowed in actions.items():
        _upsert_permission(session, employee_id, action, allowed)


def _reconcile_employee_locks(session: Session) -> None:
    """Trader may propose paper tickets. Nobody writes locks or opens the firm."""
    for emp in session.query(Employee).all():
        may_propose = emp.slug == TRADER_SLUG
        _upsert_permission(session, emp.id, "place_order", may_propose)
        for action in ("write_controls", "approve_live", "transition_to_live", "open_firm", "download_secrets"):
            _upsert_permission(session, emp.id, action, False)


def _seed_challenge(session: Session) -> None:
    """Persistent Challenge identity. Challenges a SAMPLE thesis. Not a live trade."""
    emp = session.query(Employee).filter_by(slug=CHALLENGE_SLUG).one_or_none()
    if emp is not None:
        return
    emp = Employee(
        slug=CHALLENGE_SLUG,
        display_name=staff_display_for_slug(CHALLENGE_SLUG),
        person_name="Sam Okeke",
        role_title="Challenge",
        department="Challenge",
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
        display_name=staff_display_for_slug(RISK_SLUG),
        person_name="Elena Voss",
        role_title="Risk",
        department="Risk",
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
                "Unsafe paths are denied. LIVE is blocked. PAPER allow-list is Board Addendum E. "
                "Gold is FUTURE SCOPE ONLY. A SAMPLE thesis is not an order. "
                "Risk cannot approve live trading. Risk is independent of Trader."
            ),
            created_at=now_london(),
        )
    )
    _deny_live_and_execution(
        session,
        emp.id,
        extra=(("run_skill:review_unsafe_path", True),),
    )


def _seed_trader(session: Session) -> None:
    """Persistent Trader identity. May propose paper tickets. Cannot write locks or approve LIVE."""
    emp = session.query(Employee).filter_by(slug=TRADER_SLUG).one_or_none()
    if emp is None:
        emp = Employee(
            slug=TRADER_SLUG,
            display_name=staff_display_for_slug(TRADER_SLUG),
            person_name="Chris Adeyemi",
            role_title="Trader",
            department="Trader",
            personality=(
                "Execution-minded, stays inside Board locks. Does not approve live trading. "
                "Personality never overrides controls."
            ),
            responsibilities=(
                "Paper-desk execution proposals inside Board locks. "
                "May propose paper tickets. After Grand Opening PAPER the engine "
                "may fill a legal allow-list practice order in the simulator. "
                "Cannot write control tables, allow-list, limits, or trading_mode. "
                "Cannot approve LIVE. Cannot open the firm. Risk stays independent of Trader."
            ),
            authority_boundaries=(
                "No live-trading approval — Board Member only (Document 11). "
                "No control writes. No allow-list writes. Cannot open the firm. "
                "Risk is independent of Trader. LIVE and BROKER_PAPER remain UNLOADED. "
                "Proposing a paper ticket is not LIVE. LIVE and BROKER_PAPER remain UNLOADED."
            ),
            status="AVAILABLE",
            status_bubble="AVAILABLE",
            office_x=160,
            office_y=160,
            is_primary_agent=1,
            created_at=now_london(),
        )
        session.add(emp)
        session.flush()
        session.add(
            MemoryEmployee(
                employee_id=emp.id,
                kind="lesson",
                content=(
                    "Trader may propose paper tickets. After Grand Opening PAPER "
                    "the engine may fill a legal allow-list practice order. Cannot "
                    "write locks or approve LIVE. Risk is independent of Trader. "
                    "Paper allow-list is Board Addendum E."
                ),
                created_at=now_london(),
            )
        )
    else:
        emp.responsibilities = (
            "Paper-desk execution proposals inside Board locks. "
                "May propose paper tickets. After Grand Opening PAPER the engine "
                "may fill a legal allow-list practice order in the simulator. "
                "Cannot write control tables, allow-list, limits, or trading_mode. "
            "Cannot approve LIVE. Cannot open the firm. Risk stays independent of Trader."
        )
        emp.authority_boundaries = (
            "No live-trading approval — Board Member only (Document 11). "
            "No control writes. No allow-list writes. Cannot open the firm. "
            "Risk is independent of Trader. LIVE and BROKER_PAPER remain UNLOADED. "
            "Proposing a paper ticket is not LIVE."
        )
    _deny_live_and_execution(session, emp.id, extra=(("place_order", True),))


def _seed_quant(session: Session) -> None:
    """Persistent Quant identity. Cannot write locks or approve LIVE. Challenge stays independent."""
    emp = session.query(Employee).filter_by(slug=QUANT_SLUG).one_or_none()
    if emp is not None:
        return
    emp = Employee(
        slug=QUANT_SLUG,
        display_name=staff_display_for_slug(QUANT_SLUG),
        person_name="Nina Kapoor",
        role_title="Quant/Strategy",
        department="Quant",
        personality=(
            "Model-first, distinguishes a sample from an order. Does not approve live trading. "
            "Personality never overrides controls."
        ),
        responsibilities=(
            "Quant/Strategy analysis. Cannot write control tables or the allow-list. "
            "Cannot approve LIVE. Challenge stays independent of Quant."
        ),
        authority_boundaries=(
            "No live-trading approval — Board Member only (Document 11). "
            "No control writes. Challenge is independent of Quant and does not "
            "report through this seat."
        ),
        status="AVAILABLE",
        status_bubble="AVAILABLE",
        office_x=120,
        office_y=40,
        is_primary_agent=1,
        created_at=now_london(),
    )
    session.add(emp)
    session.flush()
    session.add(
        MemoryEmployee(
            employee_id=emp.id,
            kind="lesson",
            content=(
                "Quant cannot write locks or approve LIVE. "
                "Challenge stays independent of Quant."
            ),
            created_at=now_london(),
        )
    )
    _deny_live_and_execution(session, emp.id)


def _seed_technology(session: Session) -> None:
    """Persistent Technology identity. Cannot write locks or approve LIVE."""
    emp = session.query(Employee).filter_by(slug=TECH_SLUG).one_or_none()
    if emp is not None:
        return
    emp = Employee(
        slug=TECH_SLUG,
        display_name=staff_display_for_slug(TECH_SLUG),
        person_name="Owen Blake",
        role_title="Technology",
        department="Technology",
        personality=(
            "Systems-first, keeps the kernel maintainable. Does not approve live trading. "
            "Personality never overrides controls."
        ),
        responsibilities=(
            "Technology and self-maintenance of the company kernel. "
            "Owns the company backup job (Board Addendum J). "
            "Cannot write control tables, allow-list, or trading_mode. "
            "Cannot open the firm. Cannot download secrets. Cannot approve LIVE."
        ),
        authority_boundaries=(
            "No live-trading approval — Board Member only (Document 11). "
            "No execution. No control writes. Cannot write trading_mode or "
            "allow-list. Cannot open the firm. Cannot download secrets. "
            "No Mac installers in this slice."
        ),
        status="AVAILABLE",
        status_bubble="AVAILABLE",
        office_x=250,
        office_y=120,
        is_primary_agent=1,
        created_at=now_london(),
    )
    session.add(emp)
    session.flush()
    session.add(
        MemoryEmployee(
            employee_id=emp.id,
            kind="lesson",
            content=(
                "Technology owns the encrypted company backup. "
                "Cannot write trading_mode, allow-list, or open the firm. "
                "Cannot download secrets. The office is a projection. "
                "The database is the ledger. GitHub is code only."
            ),
            created_at=now_london(),
        )
    )
    _deny_live_and_execution(session, emp.id)
