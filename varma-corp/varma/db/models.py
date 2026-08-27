"""SQLAlchemy models. Source of truth is the database, not the desktop (Doc 14)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Employee(Base):
    """Persistent primary-agent identity. An LLM call is an invocation, not the employee."""

    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
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


class NumericLimit(Base):
    """Numeric paper/live limits. Missing ⇒ deny. Values are an OPEN BOARD DECISION."""

    __tablename__ = "numeric_limits"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    set_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
