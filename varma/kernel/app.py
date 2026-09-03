"""FastAPI company kernel. Office talks to this. Office is not the source of truth."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from varma import __version__
from varma.backup.job import run_company_backup
from varma.clock import (
    describe_0630_weekday_routine,
    describe_0730_company_meeting,
    describe_company_backup,
    describe_flatten_london_close,
    describe_flatten_us_close,
    describe_nightly_memory_filter,
    describe_paper_session,
    now_london,
)
from varma.controls.engine import ControlEngine
from varma.db.engine import get_session_factory, init_db, storage_from_url
from varma.db.models import (
    ChallengeReview,
    ChatMessage,
    Employee,
    IntelligenceBrief,
    MemoryFilterRun,
    MemoryWorking,
    MemoryWorkingArchive,
    RiskDecision,
    SampleThesis,
    WatchlistItem,
)
from varma.db.seed import MI_SLUG, seed_if_empty
from varma.employees.brain import EmployeeBrain
from varma.employees.runtime import NO_LIVE_APPROVAL_SLUGS, EmployeeRuntime
from varma.kernel.auth import Actor, parse_actor, require_board_member
from varma.meetings.handoff import CEO_SLUG, CHALLENGE_SLUG, RISK_SLUG, handoff_to_dict
from varma.ports.execution import ExecutionPort
from varma.memory.filter import filter_run_to_dict
from varma.observability.board import BoardObservability
from varma.routines.run_brief import run_brief
from varma.routines.run_challenge import run_challenge
from varma.routines.run_nightly_filter import run_nightly_filter
from varma.routines.run_risk_deny import run_risk_deny
from varma.routines.run_0730_meeting import run_0730_meeting
from varma.routines.run_flatten_us_close import run_flatten_us_close
from varma.routines.run_flatten_london_close import run_flatten_london_close
from varma.routines.run_paper_trade_path import run_paper_trade_path
from varma.routines.board_jobs import with_flatten_safety, with_job_safety, with_paper_trade_safety
from varma.controls.addendum_j import (
    EMPLOYEE_CANNOT_DOWNLOAD_SECRETS_REASON,
    SECRETS_ARE_NOT_DOWNLOADABLE_REASON,
)
from varma.skills.challenge_sample_thesis import challenge_review_to_dict
from varma.skills.prepare_daily_intelligence_brief import brief_to_dict
from varma.skills.prepare_sample_thesis import thesis_to_dict
from varma.skills.review_unsafe_path import risk_decision_to_dict


def _session() -> Session:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    session = get_session_factory()()
    try:
        seed_if_empty(session)
    finally:
        session.close()
    yield



class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class OrderIn(BaseModel):
    symbol: str
    side: str = "buy"
    quantity: float = 0
    notional_gbp: float | None = None
    execution_port: str = "SIMULATOR"


class KillSwitchIn(BaseModel):
    halt: bool = True


def create_app() -> FastAPI:
    app = FastAPI(
        title="Varma Corp. Kernel",
        version=__version__,
        description="Company kernel. Desktop is a projection. LIVE trading is blocked.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health(session: Session = Depends(_session)) -> dict[str, Any]:
        storage = storage_from_url()
        controls = ControlEngine(session).snapshot()
        return {
            "ok": True,
            "service": "varma-corp-kernel",
            "version": __version__,
            "timezone": "Europe/London",
            "now": now_london().isoformat(),
            "trading_mode": controls["trading_mode"],
            "live_adapter_loaded": controls["live_adapter_loaded"],
            "broker_paper_loaded": controls["broker_paper_loaded"],
            "storage_backend": storage.backend_name(),
            "storage_temporary": storage.is_temporary_dev_store(),
            "storage_note": storage.persistence_note(),
            "environment": "DEVELOPMENT — not production runtime",
            "nightly_filter": {
                "cadence": "nightly",
                "timezone": "Europe/London",
                "daemon": False,
                "cli": "python -m varma.routines.run_nightly_filter",
            },
        }

    @app.get("/auth/whoami")
    def whoami(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
    ) -> dict[str, str]:
        actor = parse_actor(authorization, x_varma_actor, x_varma_employee)
        return {
            "identity": actor.identity,
            "actor_type": actor.actor_type,
            "terminology": "Board Member (human). CEO is an AI employee. Never MD.",
        }

    @app.get("/controls")
    def controls(session: Session = Depends(_session)) -> dict[str, Any]:
        snap = ControlEngine(session).snapshot()
        snap["employees_cannot_write_this"] = True
        return snap

    @app.post("/controls/write")
    def controls_write(
        payload: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        actor = parse_actor(authorization, x_varma_actor, x_varma_employee)
        engine = ControlEngine(session)
        decision = engine.write_control(
            actor_id=actor.identity,
            actor_type=actor.actor_type,
            field=str(payload.get("field") or ""),
            value=payload.get("value"),
        )
        if not decision.allowed:
            raise HTTPException(403, decision.reason)
        return {"ok": True, "reason": decision.reason}

    @app.post("/controls/kill-switch")
    def kill_switch_halt(
        payload: KillSwitchIn = Body(default_factory=KillSwitchIn),
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        from varma.controls.kill_switch import trip_kill_switch
        from varma.ports.execution import BROKER_PAPER_LOADED as PAPER_LOADED
        from varma.ports.execution import LIVE_PORT_LOADED

        if payload.halt is False:
            raise HTTPException(400, "USE_RESET_ENDPOINT")
        result = trip_kill_switch(
            session,
            actor_id="board-member",
            reason="BOARD_MEMBER_HALT",
        )
        snap = ControlEngine(session).snapshot()
        result.update(
            {
                "ok": True,
                "halted": True,
                "trading_mode": snap["trading_mode"],
                "trading_mode_unchanged": snap["trading_mode"] == "LIVE_BLOCKED",
                "broker_paper_loaded": bool(PAPER_LOADED),
                "live_adapter_loaded": bool(LIVE_PORT_LOADED) or bool(snap["live_adapter_loaded"]),
                "ai_employee_not_required": True,
            }
        )
        return result

    @app.post("/controls/kill-switch/reset")
    def kill_switch_reset_endpoint(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        from varma.controls.kill_switch import reset_kill_switch

        actor = parse_actor(authorization, x_varma_actor, x_varma_employee)
        decision = reset_kill_switch(
            session,
            actor_id=actor.identity,
            actor_type=actor.actor_type,
        )
        if not decision.allowed:
            raise HTTPException(403, decision.reason)
        return {"ok": True, "halted": False, "reason": decision.reason}

    @app.get("/employees")
    def employees(session: Session = Depends(_session)) -> list[dict[str, Any]]:
        rows = session.query(Employee).all()
        return [_employee_public(e) for e in rows]

    @app.get("/employees/{slug}")
    def employee(slug: str, session: Session = Depends(_session)) -> dict[str, Any]:
        emp = _get_employee(session, slug)
        rt = EmployeeRuntime(session, emp)
        data = _employee_public(emp)
        data["brain"] = EmployeeBrain(session).record(emp)
        data["context"] = {
            "role": emp.role_title,
            "responsibilities": emp.responsibilities,
            "authority_boundaries": emp.authority_boundaries,
            "role_knowledge": data["brain"]["role_knowledge"],
            "memory_pointers": data["brain"]["memory_pointers"],
            "lessons": [m.content for m in rt.memory.employee_lessons(emp.id)],
        }
        return data

    @app.get("/employees/{slug}/brief/latest")
    def latest_brief(slug: str, session: Session = Depends(_session)) -> dict[str, Any]:
        emp = _get_employee(session, slug)
        brief = (
            session.query(IntelligenceBrief)
            .filter_by(employee_id=emp.id)
            .order_by(IntelligenceBrief.produced_at.desc())
            .first()
        )
        if brief is None:
            return {"brief": None, "note": "No brief stored yet. Run python -m varma.routines.run_brief"}
        return {"brief": brief_to_dict(brief)}

    @app.get("/employees/{slug}/inbox")
    def inbox(slug: str, session: Session = Depends(_session)) -> dict[str, Any]:
        emp = _get_employee(session, slug)
        rt = EmployeeRuntime(session, emp)
        items: list[dict[str, Any]] = []
        for h in rt.inbox():
            item = handoff_to_dict(h)
            item.update(_hydrate_handoff_artefact(session, h.artefact_type, h.artefact_id))
            items.append(item)
        return {
            "employee": emp.slug,
            "display_name": emp.display_name,
            "ceo_cannot_approve_live_trading": emp.slug == CEO_SLUG,
            "cannot_approve_live_trading": emp.slug in NO_LIVE_APPROVAL_SLUGS,
            "items": items,
        }

    @app.get("/employees/{slug}/work")
    def employee_work(slug: str, session: Session = Depends(_session)) -> dict[str, Any]:
        emp = _get_employee(session, slug)
        rt = EmployeeRuntime(session, emp)
        produced = rt.latest_brief()
        received_brief = rt.latest_received_brief()
        thesis = rt.latest_thesis() if emp.slug in {CHALLENGE_SLUG, RISK_SLUG} else None
        review = rt.latest_challenge_review() if emp.slug in {CHALLENGE_SLUG, RISK_SLUG} else None
        risk = rt.latest_risk_decision() if emp.slug == RISK_SLUG else None
        inbox_items: list[dict[str, Any]] = []
        for h in rt.inbox():
            item = handoff_to_dict(h)
            item.update(_hydrate_handoff_artefact(session, h.artefact_type, h.artefact_id))
            inbox_items.append(item)
        data = _employee_public(emp)
        data.update(
            {
                "brief": brief_to_dict(produced) if produced else None,
                "received_brief": brief_to_dict(received_brief) if received_brief else None,
                "thesis": thesis_to_dict(thesis) if thesis else None,
                "challenge_review": challenge_review_to_dict(review) if review else None,
                "risk_decision": risk_decision_to_dict(risk) if risk else None,
                "inbox": inbox_items,
            }
        )
        return data

    @app.post("/employees/{slug}/chat")
    def chat(
        slug: str,
        payload: ChatIn = Body(...),
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        emp = _get_employee(session, slug)
        rt = EmployeeRuntime(session, emp)
        reply = rt.chat(payload.message)
        return {
            "employee": emp.display_name,
            "reply": reply.body,
            "same_runtime": True,
            "talk_voice": "disabled — OPEN BOARD DECISION; Chat is required",
        }

    @app.get("/employees/{slug}/chat")
    def chat_history(
        slug: str,
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> list[dict[str, Any]]:
        emp = _get_employee(session, slug)
        rows = (
            session.query(ChatMessage)
            .filter_by(employee_id=emp.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        return [
            {
                "id": r.id,
                "from_role": r.from_role,
                "body": r.body,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    @app.post("/routines/run-brief")
    def api_run_brief(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_job_safety(session, run_brief(session))

    @app.post("/routines/run-challenge")
    def api_run_challenge(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_job_safety(session, run_challenge(session))

    @app.post("/routines/run-risk-deny")
    def api_run_risk_deny(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_job_safety(session, run_risk_deny(session))

    @app.post("/routines/run-nightly-filter")
    def api_run_nightly_filter(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_job_safety(session, run_nightly_filter(session))

    @app.post("/routines/run-0730-meeting")
    def api_run_0730_meeting(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_job_safety(session, run_0730_meeting(session, started_by="board-member"))

    @app.post("/routines/run-flatten-us-close")
    def api_run_flatten_us_close(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_flatten_safety(
            session,
            run_flatten_us_close(session, started_by="board-member"),
        )

    @app.post("/routines/run-flatten-london-close")
    def api_run_flatten_london_close(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_flatten_safety(
            session,
            run_flatten_london_close(session, started_by="board-member"),
        )

    @app.post("/routines/run-backup")
    def api_run_backup(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_job_safety(
            session,
            run_company_backup(session, started_by="board-member"),
        )

    @app.post("/routines/run-paper-trade-path")
    def api_run_paper_trade_path(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return with_paper_trade_safety(
            session,
            run_paper_trade_path(session, started_by="board-member"),
        )

    @app.get("/routines/backup-schedule")
    def backup_schedule() -> dict[str, Any]:
        return {
            "schedule": "daily after US close / end of London evening",
            "timezone": "Europe/London",
            "after": "US_REGULAR_CASH_CLOSE",
            "daemon": False,
            "encrypted_at_rest": True,
            "owner_display_name": "Owen Blake · Technology",
            "owner_slug": "technology",
            "github_is_code_only": True,
            "on_board_member_laptop": False,
            "system_of_record": "database",
            "included": [
                "paper_ledger",
                "evidence",
                "organisational_memory",
                "control_snapshots",
            ],
            "excluded": ["secrets", "live_broker_credentials"],
            "live_broker_credentials_exist": False,
            "employees_cannot_download_secrets": True,
            "description": describe_company_backup(),
            "cli": "python -m varma.routines.run_backup",
            "writes_controls": False,
            "fills": False,
            "paper_fills": False,
        }

    def _deny_secret_download(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
    ) -> dict[str, Any]:
        actor = parse_actor(authorization, x_varma_actor, x_varma_employee)
        if actor.actor_type != "board_member":
            raise HTTPException(403, EMPLOYEE_CANNOT_DOWNLOAD_SECRETS_REASON)
        raise HTTPException(403, SECRETS_ARE_NOT_DOWNLOADABLE_REASON)

    @app.get("/backup/secrets")
    def backup_secrets_denied(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
    ) -> dict[str, Any]:
        return _deny_secret_download(authorization, x_varma_actor, x_varma_employee)

    @app.get("/backup/key")
    def backup_key_denied(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
    ) -> dict[str, Any]:
        return _deny_secret_download(authorization, x_varma_actor, x_varma_employee)

    @app.get("/backup/download")
    def backup_download_denied(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
    ) -> dict[str, Any]:
        return _deny_secret_download(authorization, x_varma_actor, x_varma_employee)

    @app.get("/routines/flatten-us-close-schedule")
    def flatten_us_close_schedule() -> dict[str, Any]:
        return {
            "schedule": "before US regular cash close",
            "timezone": "Europe/London",
            "flatten_at": "US_REGULAR_CASH_CLOSE",
            "flatten_not_at": "LONDON_CLOSING_AUCTION",
            "venue_scope": "US",
            "split_flatten_clocks": True,
            "risk_02f_bound": True,
            "daemon": False,
            "overnight_holds": False,
            "us_after_hours": False,
            "extended_hours": False,
            "description": describe_flatten_us_close(),
            "session": describe_paper_session(),
            "cli": "python -m varma.routines.run_flatten_us_close",
            "writes_controls": False,
            "get_observability_flattens": False,
            "internal_simulator": True,
            "broker": False,
        }

    @app.get("/routines/flatten-london-close-schedule")
    def flatten_london_close_schedule() -> dict[str, Any]:
        return {
            "schedule": "London closing auction 16:30-16:35 Europe/London",
            "timezone": "Europe/London",
            "flatten_at": "LONDON_CLOSING_AUCTION",
            "flatten_not_at": "US_REGULAR_CASH_CLOSE",
            "venue_scope": "LSE",
            "split_flatten_clocks": True,
            "risk_02f_bound": True,
            "cannot_drop_independently": True,
            "daemon": False,
            "overnight_holds": False,
            "description": describe_flatten_london_close(),
            "session": describe_paper_session(),
            "cli": "python -m varma.routines.run_flatten_london_close",
            "writes_controls": False,
            "get_observability_flattens": False,
            "internal_simulator": True,
            "broker": False,
        }

    @app.get("/routines/0730-meeting-schedule")
    def company_meeting_schedule() -> dict[str, Any]:
        return {
            "schedule": "07:30 weekdays",
            "timezone": "Europe/London",
            "daemon": False,
            "is_trade": False,
            "is_live_approval": False,
            "cannot_start_live": True,
            "board_member_diary_invite": False,
            "board_member_calendar_invite": False,
            "board_member_email": False,
            "internal_staff_artefact": True,
            "description": describe_0730_company_meeting(),
            "cli": "python -m varma.routines.run_0730_meeting",
            "writes_controls": False,
        }

    @app.get("/routines/nightly-filter-schedule")
    def nightly_filter_schedule() -> dict[str, Any]:
        return {
            "schedule": "nightly",
            "timezone": "Europe/London",
            "daemon": False,
            "description": describe_nightly_memory_filter(),
            "cli": "python -m varma.routines.run_nightly_filter",
            "writes_controls": False,
            "deletes_evidence": False,
        }

    @app.get("/routines/brief-schedule")
    def brief_schedule() -> dict[str, str]:
        return {
            "schedule": "06:30 weekdays",
            "timezone": "Europe/London",
            "description": describe_0630_weekday_routine(),
            "cli": "python -m varma.routines.run_brief",
        }

    @app.get("/memory/filter/latest")
    def latest_memory_filter(session: Session = Depends(_session)) -> dict[str, Any]:
        row = session.query(MemoryFilterRun).order_by(MemoryFilterRun.ran_at.desc()).first()
        if row is None:
            return {
                "run": None,
                "note": "No nightly filter run stored yet. python -m varma.routines.run_nightly_filter",
            }
        archived = (
            session.query(MemoryWorkingArchive)
            .filter_by(filter_run_id=row.id)
            .all()
        )
        data = filter_run_to_dict(row)
        data["archived_keys"] = [
            {"employee_id": a.employee_id, "key": a.key} for a in archived
        ]
        data["working_remaining"] = session.query(MemoryWorking).count()
        return {"run": data}

    @app.post("/execution/place-order")
    def place_order(
        payload: OrderIn = Body(...),
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        actor = parse_actor(authorization, x_varma_actor, x_varma_employee)
        port = ExecutionPort(session)
        if actor.actor_type == "employee":
            actor_id = _resolve_employee_actor_id(session, actor)
            actor_type = "employee"
        elif actor.actor_type == "board_member":
            actor_id = actor.identity
            actor_type = "board_member"
        else:
            # Anonymous attempts still go through the engine as an employee-shaped deny.
            mi = session.query(Employee).filter_by(slug=MI_SLUG).one()
            actor_id = mi.id
            actor_type = "employee"
        decision = port.place_order(
            actor_id=actor_id,
            actor_type=actor_type,
            order=payload.model_dump(),
        )
        if not decision.allowed:
            raise HTTPException(403, detail={"reason": decision.reason, "allowed": False})
        return {"ok": True, "allowed": True, "reason": decision.reason, "details": decision.details}

    @app.get("/watchlist")
    def watchlist(session: Session = Depends(_session)) -> dict[str, Any]:
        rows = session.query(WatchlistItem).all()
        return {
            "label": "TEMPORARY DEVELOPMENT DEFAULT",
            "is_execution_allow_list": False,
            "gold": False,
            "items": [
                {
                    "symbol": r.symbol,
                    "name": r.name,
                    "venue": r.venue,
                    "asset_class": r.asset_class,
                    "label": r.label,
                }
                for r in rows
            ],
            "note": (
                "This watchlist is a TEMPORARY DEVELOPMENT DEFAULT so the brief skill "
                "has something to observe. Exact authorised instrument list is an "
                "OPEN BOARD DECISION. Empty allow-list ⇒ no execution. No gold."
            ),
        }

    @app.get("/office/state")
    def office_state(session: Session = Depends(_session)) -> dict[str, Any]:
        controls = ControlEngine(session).snapshot()
        employees = session.query(Employee).all()
        return {
            "trading_mode": controls["trading_mode"],
            "kill_switch": controls["kill_switch"],
            "office_is_source_of_truth": False,
            "talk_enabled": False,
            "chat_required": True,
            "employees": [_employee_public(e) for e in employees],
            "floor": {
                "width": 32,
                "height": 20,
                "tile": 16,
                "style": "pixel-art-2d",
                "rooms": [
                    {"id": "conference", "label": "Conference room"},
                    {"id": "kitchen", "label": "Kitchenette"},
                    {"id": "ceo", "label": "Corner office", "person": "Jordan Hale · CEO"},
                    {"id": "research", "label": "Open desks", "person": "Asha Patel · Research"},
                    {"id": "quant", "label": "Open desks", "person": "Nina Kapoor · Quant"},
                    {"id": "trader", "label": "Open desks", "person": "Chris Adeyemi · Trader"},
                    {"id": "break", "label": "Rec room"},
                    {"id": "technology", "label": "Technology room", "person": "Owen Blake · Technology"},
                    {"id": "challenge", "label": "Challenge room", "person": "Sam Okeke · Challenge"},
                    {"id": "risk", "label": "Risk room", "person": "Elena Voss · Risk"},
                ],
            },
            "board_observability": {
                "path": "/observability",
                "read_only": True,
                "source": "database",
                "writes_controls": False,
                "includes": [
                    "costs",
                    "evidence",
                    "nightly_filter",
                    "organisation_memory",
                    "meeting_pack",
                    "meeting_artefacts",
                    "status_bubbles",
                    "routines",
                    "missing_numeric_limits",
                    "numeric_limits",
                    "controls",
                    "paper_gate",
                    "execution_ports",
                    "company_meeting",
                    "runnable_jobs",
                    "kill_switch",
                    "evaluation",
                    "paper_ledger",
                    "paper_session",
                    "addendum_c",
                    "addendum_j",
                    "addendum_k",
                    "backup",
                ],
            },
        }

    @app.get("/observability")
    def observability(
        _board: Actor = Depends(require_board_member),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        return BoardObservability(session).snapshot()

    @app.post("/observability")
    def observability_write_denied(
        authorization: str | None = Header(default=None),
        x_varma_actor: str | None = Header(default=None),
        x_varma_employee: str | None = Header(default=None),
        session: Session = Depends(_session),
    ) -> dict[str, Any]:
        parse_actor(authorization, x_varma_actor, x_varma_employee)
        # Touch the session so tests can prove controls were not mutated.
        ControlEngine(session).snapshot()
        raise HTTPException(403, "OBSERVABILITY_IS_READ_ONLY")

    return app


def _hydrate_handoff_artefact(session: Session, artefact_type: str, artefact_id: str) -> dict[str, Any]:
    if artefact_type == "intelligence_brief":
        artefact = session.get(IntelligenceBrief, artefact_id)
        return {"brief": brief_to_dict(artefact) if artefact else None}
    if artefact_type == "sample_thesis":
        artefact = session.get(SampleThesis, artefact_id)
        return {"thesis": thesis_to_dict(artefact) if artefact else None}
    if artefact_type == "challenge_review":
        artefact = session.get(ChallengeReview, artefact_id)
        return {"challenge_review": challenge_review_to_dict(artefact) if artefact else None}
    if artefact_type == "risk_decision":
        artefact = session.get(RiskDecision, artefact_id)
        return {"risk_decision": risk_decision_to_dict(artefact) if artefact else None}
    return {}


def _resolve_employee_actor_id(session: Session, actor: Actor) -> str:
    emp = (
        session.query(Employee)
        .filter(or_(Employee.slug == actor.identity, Employee.id == actor.identity))
        .one_or_none()
    )
    return emp.id if emp else actor.identity


def _get_employee(session: Session, slug: str) -> Employee:
    emp = session.query(Employee).filter_by(slug=slug).one_or_none()
    if emp is None:
        raise HTTPException(404, "employee not found")
    return emp


def _employee_public(e: Employee) -> dict[str, Any]:
    return {
        "id": e.id,
        "slug": e.slug,
        "display_name": e.display_name,
        "person_name": e.person_name or "",
        "role_title": e.role_title,
        "department": e.department,
        "status": e.status,
        "status_bubble": e.status_bubble,
        "office_x": e.office_x,
        "office_y": e.office_y,
        "is_primary_agent": bool(e.is_primary_agent),
        "cannot_approve_live_trading": e.slug in NO_LIVE_APPROVAL_SLUGS,
        "is_meeting_brief_recipient": e.slug == CEO_SLUG,
    }


app = create_app()
