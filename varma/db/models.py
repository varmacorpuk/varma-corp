"""SQLAlchemy models. Source of truth is the database, not the desktop (Doc 14)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Employee(Base):
    """Persistent primary-agent identity. An LLM call is an invocation, not the employee.

    display_name is person · department (Board Addendum F), e.g. "Jordan Hale · CEO".
    person_name is the person. department/door is the job title.
    """

    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    person_name: Mapped[str] = mapped_column(String(120), default="")
    role_title: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    personality: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[str] = mapped_column(Text, default="")
    authority_boundaries: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="AVAILABLE")
    status_bubble: Mapped[str] = mapped_column(String(48), default="AVAILABLE")
    office_x: Mapped[int] = mapped_column(Integer, default=80)
    office_y: Mapped[int] = mapped_column(Integer, default=90)
    is_primary_agent: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ControlState(Base):
    """Singleton control plane. Employees cannot write this table."""

    __tablename__ = "control_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trading_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="LIVE_BLOCKED")
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[str] = mapped_column(String(80), default="system-seed")


class Permission(Base):
    """Permissions live here, not in memory (Documents 08, 11, 14)."""

    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "action", name="uq_perm"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, default=False)


class AllowListInstrument(Base):
    """Execution allow-list. Empty ⇒ no execution. OPEN BOARD DECISION for membership."""

    __tablename__ = "allow_list_instruments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    venue: Mapped[str] = mapped_column(String(32), default="")
    approved_by: Mapped[str] = mapped_column(String(80), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ControlSetting(Base):
    """Board-set non-numeric control-table values (Addendum C session locks).

    Employees cannot write this table. Values are labelled, not invented silent defaults.
    """

    __tablename__ = "control_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="")
    set_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)


class PaperFlattenRun(Base):
    """On-demand flatten-before-US-close run. Database artefact. Not a daemon."""

    __tablename__ = "paper_flatten_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    flatten_at: Mapped[str] = mapped_column(String(40), default="US_REGULAR_CASH_CLOSE")
    flatten_not_at: Mapped[str] = mapped_column(String(40), default="LONDON_CASH_CLOSE")
    cancelled_open_paper_orders: Mapped[int] = mapped_column(Integer, default=0)
    closed_positions: Mapped[int] = mapped_column(Integer, default=0)
    flatten_fills: Mapped[int] = mapped_column(Integer, default=0)
    positions_remaining: Mapped[int] = mapped_column(Integer, default=0)
    trading_mode_before: Mapped[str] = mapped_column(String(32), nullable=False)
    trading_mode_after: Mapped[str] = mapped_column(String(32), nullable=False)
    allow_list_empty: Mapped[bool] = mapped_column(Boolean, default=True)
    daemon: Mapped[bool] = mapped_column(Boolean, default=False)
    writes_controls: Mapped[bool] = mapped_column(Boolean, default=False)
    broker_paper_loaded: Mapped[bool] = mapped_column(Boolean, default=False)
    live_loaded: Mapped[bool] = mapped_column(Boolean, default=False)
    started_by: Mapped[str] = mapped_column(String(80), default="board-member")
    notes: Mapped[str] = mapped_column(Text, default="")


class NumericLimit(Base):
    """Numeric paper/live limits. Missing ⇒ deny.

    Values in this slice are Board Addendum A 2026-08-27 (Board-set), not invented
    silent defaults. Employees cannot write this table.
    """

    __tablename__ = "numeric_limits"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str] = mapped_column(String(16), default="")
    set_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)


class EvaluationPolicy(Base):
    """Board Addendum A evaluation rules. Do not auto-switch LIVE."""

    __tablename__ = "evaluation_policy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), default="GBP")
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    successful_trade_definition: Mapped[str] = mapped_column(Text, default="")
    win_rate_threshold: Mapped[str] = mapped_column(String(16), default="0.5")
    requires_book_profitable: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_switch_live: Mapped[bool] = mapped_column(Boolean, default=False)
    paper_continues_until_board_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(120), default="")
    set_by: Mapped[str] = mapped_column(String(80), default="board-member")
    set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaperAccount(Base):
    """Internal paper ledger singleton. Not a broker account. Currency GBP."""

    __tablename__ = "paper_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency: Mapped[str] = mapped_column(String(8), default="GBP")
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    simulated_capital: Mapped[float] = mapped_column(Float, default=0)
    cash: Mapped[float] = mapped_column(Float, default=0)
    equity_at_day_start: Mapped[float] = mapped_column(Float, default=0)
    london_day: Mapped[str] = mapped_column(String(16), default="")
    source: Mapped[str] = mapped_column(String(120), default="")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaperOrder(Base):
    """Internal simulator paper order. Not BROKER_PAPER. Not LIVE."""

    __tablename__ = "paper_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    notional_gbp: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    london_day: Mapped[str] = mapped_column(String(16), nullable=False)
    mid_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread_bps: Mapped[float] = mapped_column(Float, default=0)
    slippage_bps: Mapped[float] = mapped_column(Float, default=0)
    commission_gbp: Mapped[float] = mapped_column(Float, default=0)
    actor_id: Mapped[str] = mapped_column(String(80), default="")
    execution_port: Mapped[str] = mapped_column(String(32), default="SIMULATOR")
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_flatten: Mapped[bool] = mapped_column(Boolean, default=False)


class PaperFill(Base):
    """Internal simulator fill. Never a broker fill."""

    __tablename__ = "paper_fills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(String(36), ForeignKey("paper_orders.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    price: Mapped[float] = mapped_column(Float, default=0)
    notional_gbp: Mapped[float] = mapped_column(Float, default=0)
    commission_gbp: Mapped[float] = mapped_column(Float, default=0)
    london_day: Mapped[str] = mapped_column(String(16), nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)


class PaperPosition(Base):
    """Open paper position on the internal simulator ledger."""

    __tablename__ = "paper_positions"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    avg_cost_gbp: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClosedPaperTrade(Base):
    """A CLOSED paper trade. Successful iff profit > 0 (Board Addendum A)."""

    __tablename__ = "closed_paper_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    entry_price: Mapped[float] = mapped_column(Float, default=0)
    exit_price: Mapped[float] = mapped_column(Float, default=0)
    pnl_gbp: Mapped[float] = mapped_column(Float, default=0)
    profit_positive: Mapped[bool] = mapped_column(Boolean, default=False)
    london_day: Mapped[str] = mapped_column(String(16), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)


class BoardApproval(Base):
    """Append-only Board Member approval records. Silence is not approval."""

    __tablename__ = "board_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    board_member_identity: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    scope_json: Mapped[str] = mapped_column(Text, default="{}")
    recommendation_hash: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    skill_name: Mapped[str] = mapped_column(String(80), nullable=False)
    schedule: Mapped[str] = mapped_column(String(160), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class MemoryWorking(Base):
    __tablename__ = "memory_working"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MemoryWorkingArchive(Base):
    """Archived working context. Nightly Europe/London filter writes here, not controls."""

    __tablename__ = "memory_working_archive"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filter_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("memory_filter_runs.id"))
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    working_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MemoryFilterRun(Base):
    """On-demand nightly Europe/London filter run. Database artefact. Not a daemon."""

    __tablename__ = "memory_filter_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    cadence: Mapped[str] = mapped_column(String(40), default="nightly")
    archived_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count_before: Mapped[int] = mapped_column(Integer, default=0)
    evidence_count_after: Mapped[int] = mapped_column(Integer, default=0)
    trading_mode_before: Mapped[str] = mapped_column(String(32), nullable=False)
    trading_mode_after: Mapped[str] = mapped_column(String(32), nullable=False)
    controls_written: Mapped[bool] = mapped_column(Boolean, default=False)
    daemon: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class MemoryEmployee(Base):
    __tablename__ = "memory_employee"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MemoryOrg(Base):
    __tablename__ = "memory_org"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    promoted_by: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Evidence(Base):
    """Append-only evidence. Original never overwritten (Documents 08, 11, 14)."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntelligenceBrief(Base):
    """Daily intelligence brief artefact. Database is source of truth, not disk/desktop."""

    __tablename__ = "intelligence_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    headline: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    items_json: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    freshness_flag: Mapped[str] = mapped_column(String(16), nullable=False)
    freshness_notes: Mapped[str] = mapped_column(Text, default="")
    intended_recipient: Mapped[str] = mapped_column(String(80), default="company_meeting")
    trading_mode_at_production: Mapped[str] = mapped_column(String(32), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(32), nullable=False)
    cost_units: Mapped[int] = mapped_column(Integer, default=0)
    verification_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_notes: Mapped[str] = mapped_column(Text, default="")
    no_execution_authority: Mapped[bool] = mapped_column(Boolean, default=True)


class CompanyMeeting(Base):
    """On-demand 07:30 Europe/London company meeting record. Database artefact. Not a trade."""

    __tablename__ = "company_meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/London")
    schedule: Mapped[str] = mapped_column(String(80), default="07:30 weekdays")
    daemon: Mapped[bool] = mapped_column(Boolean, default=False)
    started_by: Mapped[str] = mapped_column(String(80), nullable=False)
    brief_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ceo_handoff_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    thesis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    challenge_review_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    risk_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    brief_headline: Mapped[str | None] = mapped_column(String(240), nullable=True)
    ceo_handoff_status: Mapped[str] = mapped_column(String(32), default="not")
    challenge_status: Mapped[str] = mapped_column(String(32), default="not")
    risk_status: Mapped[str] = mapped_column(String(32), default="not")
    trading_mode_at_run: Mapped[str] = mapped_column(String(32), nullable=False)
    is_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    is_live_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    cannot_start_live: Mapped[bool] = mapped_column(Boolean, default=True)
    live_started: Mapped[bool] = mapped_column(Boolean, default=False)
    writes_controls: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class CompanyMeetingAttendee(Base):
    """Attendance for a 07:30 meeting. The four existing employees only. Not a 12-person roster."""

    __tablename__ = "company_meeting_attendees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("company_meetings.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role_title: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    cannot_approve_live: Mapped[bool] = mapped_column(Boolean, default=True)
    is_board_member: Mapped[bool] = mapped_column(Boolean, default=False)


class Handoff(Base):
    """Meeting / workflow handoff artefact. Database is source of truth, not the desktop."""

    __tablename__ = "handoffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    from_employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    to_employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    artefact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    artefact_id: Mapped[str] = mapped_column(String(36), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="DELIVERED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(Text, default="")


class CostEntry(Base):
    __tablename__ = "cost_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    workflow: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    units: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    from_role: Mapped[str] = mapped_column(String(32), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WatchlistItem(Base):
    """TEMPORARY DEVELOPMENT DEFAULT watchlist. NOT the execution allow-list. No gold."""

    __tablename__ = "watchlist_items"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    venue: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(32), default="listed_equity")
    label: Mapped[str] = mapped_column(String(80), default="TEMPORARY DEVELOPMENT DEFAULT")


class SampleThesis(Base):
    """SAMPLE thesis for Challenge. Not a live trade. Not an order. Not allow-list membership."""

    __tablename__ = "sample_theses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), default="")
    venue: Mapped[str] = mapped_column(String(32), default="")
    asset_class: Mapped[str] = mapped_column(String(32), default="listed_equity")
    label: Mapped[str] = mapped_column(String(80), default="SAMPLE — not a live trade")
    created_by: Mapped[str] = mapped_column(String(80), default="sample-demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    trading_mode_at_creation: Mapped[str] = mapped_column(String(32), nullable=False)
    no_execution_authority: Mapped[bool] = mapped_column(Boolean, default=True)
    is_live_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")


class ChallengeReview(Base):
    """Challenge output on a SAMPLE thesis. Not execution authority."""

    __tablename__ = "challenge_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    thesis_id: Mapped[str] = mapped_column(String(36), ForeignKey("sample_theses.id"))
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    objections_json: Mapped[str] = mapped_column(Text, nullable=False)
    no_execution_authority: Mapped[bool] = mapped_column(Boolean, default=True)
    does_not_approve_live: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_name: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(32), nullable=False)
    cost_units: Mapped[int] = mapped_column(Integer, default=0)


class RiskDecision(Base):
    """Risk review artefact. This slice is a deny-path demo. Risk cannot approve LIVE."""

    __tablename__ = "risk_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    path_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    proposed_json: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    control_engine_reason: Mapped[str] = mapped_column(String(80), default="")
    thesis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    challenge_review_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    no_execution_authority: Mapped[bool] = mapped_column(Boolean, default=True)
    cannot_approve_live: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_name: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[str] = mapped_column(String(80), default="DENY-PATH DEMO")
