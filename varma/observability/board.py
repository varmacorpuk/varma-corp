"""Board Member read-only observability. Database is the ledger, not the desktop.

This view must not write controls, trading_mode, allow-list, or permissions.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import (
    describe_0630_weekday_routine,
    describe_0730_company_meeting,
    describe_flatten_us_close,
    describe_nightly_memory_filter,
    describe_paper_session,
)
from varma.controls.addendum_a import ADDENDUM_A_LABEL, CURRENCY, TIMEZONE, addendum_a_public
from varma.controls.addendum_c import ADDENDUM_C_LABEL, addendum_c_public
from varma.controls.addendum_e import ADDENDUM_E_LABEL, addendum_e_public
from varma.controls.addendum_f import ADDENDUM_F_LABEL, addendum_f_public
from varma.controls.addendum_i import ADDENDUM_I_LABEL, addendum_i_public
from varma.controls.engine import REQUIRED_LIMIT_KEYS, ControlEngine
from varma.controls.kill_switch import kill_switch_state
from varma.cost.ledger import CostLedger, TEMPORARY_BRIEF_COST_CAP_LABEL
from varma.paper.flatten import flatten_run_to_dict
from varma.paper.ledger import PaperLedger, evaluation_snapshot
from varma.paper.simulator import simulator_assumptions
from varma.ports.execution import execution_port_status
from varma.db.models import (
    BoardApproval,
    ChallengeReview,
    CompanyMeeting,
    CostEntry,
    Employee,
    Evidence,
    Handoff,
    IntelligenceBrief,
    MemoryFilterRun,
    MemoryOrg,
    PaperAccount,
    PaperFill,
    PaperFlattenRun,
    PaperOrder,
    PaperPosition,
    RiskDecision,
    Routine,
    SampleThesis,
)
from varma.meetings.handoff import CEO_SLUG
from varma.meetings.company_meeting import (
    ATTENDEE_SLUGS,
    attendees_for,
    latest_meeting_pack,
    meeting_to_dict,
)
from varma.memory.filter import filter_run_to_dict
from varma.memory.stores import MemoryStores
from varma.routines.board_jobs import runnable_jobs_catalog

DEFAULT_RECENT_LIMIT = 20

READ_ONLY_NOTE = (
    "Board Member observability. Read-only. Source is the database, not desktop disk. "
    "This view does not write controls, trading_mode, allow-list, or permissions."
)


def cost_entry_to_dict(row: CostEntry) -> dict[str, Any]:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "workflow": row.workflow,
        "kind": row.kind,
        "units": row.units,
        "note": row.note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def evidence_to_dict(row: Evidence) -> dict[str, Any]:
    return {
        "id": row.id,
        "kind": row.kind,
        "actor": row.actor,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def org_title_to_dict(row: MemoryOrg) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "promoted_by": row.promoted_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class BoardObservability:
    """Read path only. Instantiating or calling snapshot() must not mutate controls."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.costs = CostLedger(session)
        self.memory = MemoryStores(session)
        self.controls = ControlEngine(session)

    def snapshot(self, *, recent_limit: int = DEFAULT_RECENT_LIMIT) -> dict[str, Any]:
        limit = max(1, min(int(recent_limit), 100))
        control_snap = self.controls.snapshot()
        entries = self.costs.recent(limit=limit)
        evidence = self.memory.recent_evidence(limit=limit)
        return {
            "read_only": True,
            "writes_controls": False,
            "source": "database",
            "office_is_source_of_truth": False,
            "trading_mode": control_snap["trading_mode"],
            "allow_list_empty": control_snap["allow_list_empty"],
            "live_adapter_loaded": control_snap["live_adapter_loaded"],
            "broker_paper_loaded": control_snap.get("broker_paper_loaded", False),
            "employees_cannot_write_controls": True,
            "currency": control_snap.get("currency", CURRENCY),
            "timezone": control_snap.get("timezone", TIMEZONE),
            "addendum": control_snap.get("addendum") or addendum_a_public(),
            "addendum_c": control_snap.get("addendum_c") or addendum_c_public(),
            "addendum_e": control_snap.get("addendum_e") or addendum_e_public(),
            "addendum_f": control_snap.get("addendum_f") or addendum_f_public(),
            "addendum_i": control_snap.get("addendum_i") or addendum_i_public(),
            "paper_session": self._paper_session(control_snap),
            "missing_numeric_limits": self._missing_numeric_limits(control_snap),
            "numeric_limits": self._numeric_limits(control_snap),
            "kill_switch": self._kill_switch(control_snap),
            "evaluation": self._evaluation(),
            "paper_ledger": self._paper_ledger(control_snap),
            "paper_flatten": self._paper_flatten(),
            "controls": self._control_snapshot(control_snap),
            "paper_gate": self._paper_gate(control_snap),
            "execution_ports": self._execution_ports(control_snap),
            "cost_cap_units": self.costs.cap,
            "cost_cap_label": TEMPORARY_BRIEF_COST_CAP_LABEL,
            "cost_cap_is_board_budget": False,
            "costs": {
                "total_units": self.costs.total_units(),
                "recent_limit": limit,
                "entries": [cost_entry_to_dict(row) for row in entries],
            },
            "evidence": {
                "append_only": True,
                "recent_limit": limit,
                "entries": [evidence_to_dict(row) for row in evidence],
            },
            "nightly_filter": self._nightly_filter(),
            "organisation_memory": self._organisation_memory_titles(),
            "meeting_pack": self._meeting_pack(),
            "meeting_artefacts": self._meeting_artefacts(),
            "company_meeting": self._company_meeting(),
            "status_bubbles": self._status_bubbles(),
            "routines": self._routine_schedules(),
            "runnable_jobs": self._runnable_jobs(),
            "note": READ_ONLY_NOTE,
        }

    def _missing_numeric_limits(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        """Keys still unset. After Addendum A the required keys are Board-set."""
        unset_keys = list(control_snap.get("missing_numeric_limits") or self.controls.missing_limits())
        return {
            "read_only": True,
            "source": "database",
            "open_board_decision": False,
            "board_set": True,
            "addendum": ADDENDUM_A_LABEL,
            "values_invented": False,
            "values_shown": True,
            "required_keys": list(REQUIRED_LIMIT_KEYS),
            "unset_keys": unset_keys,
            "all_unset": len(unset_keys) == len(REQUIRED_LIMIT_KEYS) and bool(unset_keys),
            "deny_execution_when_missing": True,
            "note": (
                "Numeric paper limits are Board Addendum A 2026-08-27 (Board-set). "
                "Values are shown. Missing keys (if any) still DENY execution. "
                "Not invented silent defaults."
            ),
        }

    def _numeric_limits(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        items = list(control_snap.get("numeric_limits") or self.controls.limit_rows())
        return {
            "read_only": True,
            "source": "database",
            "board_set": True,
            "values_invented": False,
            "values_shown": True,
            "addendum": ADDENDUM_A_LABEL,
            "currency": CURRENCY,
            "timezone": TIMEZONE,
            "items": items,
            "unset_keys": list(control_snap.get("missing_numeric_limits") or []),
            "employees_cannot_write": True,
            "note": (
                "Board-set numeric limits (Board Addendum A 2026-08-27). "
                "Employees cannot write limits. Empty allow-list still denies execution. "
                "trading_mode stays LIVE_BLOCKED."
            ),
        }

    def _kill_switch(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        state = dict(control_snap.get("kill_switch_state") or kill_switch_state(self.session))
        state.update(
            {
                "read_only_status": True,
                "source": "database",
                "board_endpoint": "POST /controls/kill-switch",
                "reset_endpoint": "POST /controls/kill-switch/reset",
                "board_member_only": True,
            }
        )
        return state

    def _evaluation(self) -> dict[str, Any]:
        return evaluation_snapshot(self.session)

    def _paper_ledger(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        ledger = PaperLedger(self.session)
        acc = self.session.get(PaperAccount, 1)
        return {
            "read_only": True,
            "source": "database",
            "kind": "INTERNAL_PAPER_FILL_SIMULATOR",
            "broker": False,
            "broker_paper_loaded": bool(control_snap.get("broker_paper_loaded", False)),
            "live_loaded": bool(control_snap.get("live_adapter_loaded", False)),
            "currency": CURRENCY,
            "timezone": TIMEZONE,
            "simulated_capital_gbp": acc.simulated_capital if acc else None,
            "cash_gbp": acc.cash if acc else None,
            "equity_gbp": ledger.equity() if acc else None,
            "london_day": acc.london_day if acc else None,
            "london_day_pnl_gbp": ledger.london_day_pnl() if acc else 0,
            "open_positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost_gbp": p.avg_cost_gbp,
                }
                for p in self.session.query(PaperPosition).all()
            ],
            "fills": self.session.query(PaperFill).count(),
            "open_orders": self.session.query(PaperOrder).filter_by(status="OPEN").count(),
            "assumptions": simulator_assumptions(),
            "allow_list_empty": control_snap.get("allow_list_empty", True),
            "trading_mode": control_snap["trading_mode"],
            "does_not_switch_to_paper_mode": True,
            "simulated_capital_status": "FUTURE_PAPER_STARTING_BOOK_ONLY",
            "paper_execution_closed": True,
            "note": (
                "Internal paper ledger. Not a broker. £1000 is the FUTURE paper "
                "starting book only (Board Addendum I). PAPER execution is CLOSED. "
                "Do not fill. Allow-list E exists but cannot be used for fills until "
                "open. trading_mode stays LIVE_BLOCKED. Flatten ALL paper before US "
                "regular cash close (Board Addendum C) is a no-op while closed. "
                "Do not flatten-as-if-there-were-positions."
            ),
        }

    def _paper_session(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        addendum = dict(control_snap.get("addendum_c") or addendum_c_public())
        session_status = dict(control_snap.get("paper_session") or addendum.get("session") or {})
        settings = list(control_snap.get("control_settings") or self.controls.setting_rows())
        return {
            "read_only": True,
            "source": "database",
            "board_set": True,
            "values_invented": False,
            "addendum": ADDENDUM_C_LABEL,
            "company_clock": "Europe/London",
            "uk_cash_open": "08:00",
            "uk_cash_open_tz": "Europe/London",
            "us_regular_cash_close": "16:00",
            "us_regular_cash_close_tz": "America/New_York",
            "us_close_converted_not_hardcoded": True,
            "flatten_at": "US_REGULAR_CASH_CLOSE",
            "flatten_not_at": "LONDON_CASH_CLOSE",
            "flatten_at_london_cash_close": False,
            "overnight_holds": False,
            "us_after_hours": False,
            "extended_hours": False,
            "daemon": False,
            "get_observability_flattens": False,
            "empty_allow_list_denies_new_orders": True,
            "flatten_does_not_require_allow_list": True,
            "internal_simulator": True,
            "broker": False,
            "session": session_status,
            "control_settings": settings,
            "cli": "python -m varma.routines.run_flatten_us_close",
            "method": "POST",
            "path": "/routines/run-flatten-us-close",
            "description": describe_paper_session(),
            "flatten_description": describe_flatten_us_close(),
            "employees_cannot_write": True,
        }

    def _paper_flatten(self) -> dict[str, Any]:
        row = self.session.query(PaperFlattenRun).order_by(PaperFlattenRun.ran_at.desc()).first()
        data: dict[str, Any] = {
            "read_only": True,
            "source": "database",
            "writes_controls": False,
            "daemon": False,
            "get_observability_flattens": False,
            "flatten_at": "US_REGULAR_CASH_CLOSE",
            "flatten_not_at": "LONDON_CASH_CLOSE",
            "internal_simulator": True,
            "broker": False,
            "run": flatten_run_to_dict(row) if row else None,
        }
        if row is None:
            data["note"] = (
                "No flatten-before-US-close run stored yet. "
                "Board Member: POST /routines/run-flatten-us-close or "
                "python -m varma.routines.run_flatten_us_close"
            )
        else:
            data["note"] = (
                "Latest on-demand flatten-before-US-close from the database. "
                "Internal simulator only. GET /observability does not flatten."
            )
        return data

    def _control_snapshot(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        return {
            "read_only": True,
            "source": "database",
            "writes_controls": False,
            "employees_cannot_write_controls": True,
            "trading_mode": control_snap["trading_mode"],
            "kill_switch": control_snap["kill_switch"],
            "currency": control_snap.get("currency", CURRENCY),
            "timezone": control_snap.get("timezone", TIMEZONE),
            "addendum": ADDENDUM_A_LABEL,
            "numeric_limits_board_set": True,
            "allow_list": list(control_snap["allow_list"]),
            "allow_list_empty": control_snap["allow_list_empty"],
            "live_adapter_loaded": control_snap["live_adapter_loaded"],
            "broker_paper_loaded": control_snap.get("broker_paper_loaded", False),
            "live_gate": control_snap["live_gate"],
            "note": (
                "Board-only control snapshot. Employees cannot write controls. "
                "Empty allow-list cannot execute. BROKER_PAPER and LIVE remain UNLOADED. "
                "This view does not write trading_mode, allow-list, or permissions."
            ),
        }

    def _paper_gate(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        """PAPER execution CLOSED until Grand Opening. trading_mode stays LIVE_BLOCKED."""
        live_approvals = (
            self.session.query(BoardApproval)
            .filter_by(action="transition_to_live")
            .count()
        )
        paper_approvals = (
            self.session.query(BoardApproval)
            .filter_by(action="start_paper")
            .count()
        )
        evaluation = evaluation_snapshot(self.session)
        addendum_i = dict(control_snap.get("addendum_i") or addendum_i_public())
        return {
            "read_only": True,
            "source": "database",
            "writes_controls": False,
            "paper_status": (
                "CLOSED until Grand Opening PAPER (Board Addendum I). "
                "trading_mode LIVE_BLOCKED. £1000 is FUTURE paper starting book only."
            ),
            "paper_started": False,
            "paper_mode_switched": False,
            "paper_execution": "CLOSED",
            "paper_execution_closed": True,
            "paper_execution_implemented": False,
            "first_paper_trade_path_implemented": False,
            "internal_simulator": True,
            "firm_open": False,
            "grand_opening_paper": "not",
            "grand_opening_live": "not",
            "evaluation_status": "ledger ready (unused until open)",
            "live_trading_recommendation": "not",
            "board_review": "not",
            "explicit_board_approval": "not",
            "trading_mode": control_snap["trading_mode"],
            "execution": False,
            "live_adapter_loaded": control_snap["live_adapter_loaded"],
            "broker_paper_loaded": control_snap.get("broker_paper_loaded", False),
            "live_approvals": live_approvals,
            "paper_start_approvals": paper_approvals,
            "gate": control_snap["live_gate"],
            "silence_is_not_approval": True,
            "open_board_decision": False,
            "values_invented": False,
            "values_shown": True,
            "addendum": ADDENDUM_A_LABEL,
            "addendum_i": ADDENDUM_I_LABEL,
            "simulated_capital_status": "FUTURE_PAPER_STARTING_BOOK_ONLY",
            "addendum_a_unused_until_open": True,
            "successful_trade_definition": evaluation["successful_trade_definition"],
            "evaluation_win_rate_threshold": evaluation["win_rate_threshold"],
            "evaluation_requires_book_profitable": True,
            "evaluation_auto_switch_live": False,
            "evaluation_trigger_met": evaluation["evaluation_trigger_met"],
            "unset_open_keys": [
                "paper_duration_threshold",
            ],
            "note": (
                "Board Addendum I 2026-08-27: the company is CLOSED until Grand "
                "Opening. PAPER execution is CLOSED. Do not fill. Do not propose "
                "fills. Allow-list E exists but cannot be used for fills until Hari's "
                "explicit Grand Opening PAPER yes. LIVE still blocked. Never auto-switch. "
                "Silence is not approval. Addendum A numbers are stored but unused "
                "until open. First paper trade path is not implemented in this slice."
            ),
            "two_openings": addendum_i.get("two_openings"),
        }

    def _execution_ports(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        """BROKER_PAPER and LIVE remain UNLOADED. Status only. No fills."""
        status = execution_port_status()
        status["trading_mode"] = control_snap["trading_mode"]
        status["live_adapter_loaded"] = control_snap["live_adapter_loaded"]
        status["broker_paper_loaded"] = bool(control_snap.get("broker_paper_loaded", False))
        status["employees_cannot_write_controls"] = True
        return status

    def _nightly_filter(self) -> dict[str, Any]:
        row = self.session.query(MemoryFilterRun).order_by(MemoryFilterRun.ran_at.desc()).first()
        data: dict[str, Any] = {
            "read_only": True,
            "source": "database",
            "writes_controls": False,
            "daemon": False,
            "timezone": "Europe/London",
            "cadence": "nightly",
            "run": filter_run_to_dict(row) if row else None,
        }
        if row is None:
            data["note"] = (
                "No nightly filter run stored yet. python -m varma.routines.run_nightly_filter"
            )
        return data

    def _organisation_memory_titles(self) -> dict[str, Any]:
        rows = self.memory.org_titles()
        return {
            "read_only": True,
            "source": "database",
            "titles": [org_title_to_dict(row) for row in rows],
            "note": (
                "Organisation-memory titles only. Not Board-approved knowledge. "
                "Empty is valid. This view does not write org memory."
            ),
        }

    def _latest_meeting_rows(self) -> tuple[
        IntelligenceBrief | None,
        Employee | None,
        Handoff | None,
        SampleThesis | None,
        ChallengeReview | None,
        RiskDecision | None,
    ]:
        pack = latest_meeting_pack(self.session)
        return (
            pack["brief"],
            pack["ceo"],
            pack["handoff"],
            pack["thesis"],
            pack["review"],
            pack["risk"],
        )

    def _meeting_pack(self) -> dict[str, Any]:
        brief, _ceo, handoff, thesis, review, risk = self._latest_meeting_rows()
        if review is not None:
            challenge_status = str(review.verdict or "SAMPLE")
        elif thesis is not None:
            challenge_status = "SAMPLE"
        else:
            challenge_status = "not"
        risk_denied = bool(risk is not None and risk.decision == "DENIED")
        return {
            "read_only": True,
            "source": "database",
            "meeting": "07:30 Europe/London company meeting",
            "timezone": "Europe/London",
            "brief_headline": brief.headline if brief else None,
            "brief_id": brief.id if brief else None,
            "ceo_handoff_status": "DELIVERED" if (handoff and handoff.status == "DELIVERED") else "not",
            "challenge_sample_thesis": {
                "status": challenge_status,
                "present": thesis is not None,
                "label": thesis.label if thesis else None,
                "is_live_trade": bool(thesis.is_live_trade) if thesis else False,
                "sample_not_a_live_trade": True,
            },
            "risk_status": "DENIED" if risk_denied else "not",
            "risk_denied": risk_denied,
            "note": (
                "Read-only 07:30 meeting pack status from the database. "
                "Not a trade recommendation. Not an order."
            ),
        }

    def _meeting_artefacts(self) -> dict[str, Any]:
        brief, _ceo, handoff, thesis, review, risk = self._latest_meeting_rows()
        items: list[dict[str, Any]] = []
        if brief is not None:
            items.append(
                {
                    "kind": "intelligence_brief",
                    "id": brief.id,
                    "label": brief.headline,
                    "produced_at": brief.produced_at.isoformat() if brief.produced_at else None,
                    "verification_passed": brief.verification_passed,
                    "no_execution_authority": True,
                }
            )
        if handoff is not None:
            items.append(
                {
                    "kind": "handoff",
                    "id": handoff.id,
                    "artefact_type": handoff.artefact_type,
                    "status": handoff.status,
                    "to": CEO_SLUG,
                    "purpose": handoff.purpose,
                }
            )
        if thesis is not None:
            items.append(
                {
                    "kind": "sample_thesis",
                    "id": thesis.id,
                    "label": thesis.label,
                    "symbol": thesis.symbol,
                    "is_live_trade": False,
                    "no_execution_authority": True,
                }
            )
        if review is not None:
            items.append(
                {
                    "kind": "challenge_review",
                    "id": review.id,
                    "verdict": review.verdict,
                    "does_not_approve_live": True,
                    "no_execution_authority": True,
                }
            )
        if risk is not None:
            items.append(
                {
                    "kind": "risk_decision",
                    "id": risk.id,
                    "decision": risk.decision,
                    "cannot_approve_live": True,
                    "label": risk.label,
                }
            )
        return {
            "read_only": True,
            "source": "database",
            "meeting": "07:30 Europe/London company meeting",
            "timezone": "Europe/London",
            "items": items,
            "note": (
                "Read-only list of 07:30 meeting artefacts from the database. "
                "SAMPLE thesis is not a live trade. Risk cannot approve LIVE."
            ),
        }

    def _company_meeting(self) -> dict[str, Any]:
        row = self.session.query(CompanyMeeting).order_by(CompanyMeeting.ran_at.desc()).first()
        data: dict[str, Any] = {
            "read_only": True,
            "source": "database",
            "meeting": "07:30 Europe/London company meeting",
            "timezone": "Europe/London",
            "schedule": "07:30 weekdays",
            "daemon": False,
            "is_trade": False,
            "is_live_approval": False,
            "cannot_start_live": True,
            "writes_controls": False,
            "cli": "python -m varma.routines.run_0730_meeting",
            "run": meeting_to_dict(row, attendees_for(self.session, row.id)) if row else None,
            "attendee_slugs_documented": list(ATTENDEE_SLUGS),
            "not_a_twelve_employee_roster": True,
            "board_member_diary_invite": False,
            "board_member_calendar_invite": False,
            "board_member_email": False,
            "internal_staff_artefact": True,
        }
        if row is None:
            data["note"] = (
                "No 07:30 company meeting stored yet. Internal staff artefact. "
                "No diary invite to the Board Member. Must not email or calendar-invite Hari. "
                "Board Member: POST /routines/run-0730-meeting or python -m varma.routines.run_0730_meeting"
            )
        else:
            data["note"] = (
                "Latest on-demand 07:30 company meeting from the database. "
                "Internal staff artefact. No Board Member diary/calendar invite. No approval email. "
                "Not a trade. Not LIVE approval. Employees cannot start LIVE from a meeting."
            )
        return data

    def _status_bubbles(self) -> list[dict[str, Any]]:
        rows = self.session.query(Employee).order_by(Employee.slug.asc()).all()
        return [
            {
                "slug": e.slug,
                "display_name": e.display_name,
                "status_bubble": e.status_bubble,
                "status": e.status,
                "read_only": True,
            }
            for e in rows
        ]

    def _routine_schedules(self) -> dict[str, Any]:
        rows = self.session.query(Routine).order_by(Routine.name.asc()).all()
        return {
            "read_only": True,
            "source": "database",
            "daemon": False,
            "writes_controls": False,
            "timezone": "Europe/London",
            "items": [
                {
                    "name": row.name,
                    "schedule": row.schedule,
                    "timezone": row.timezone,
                    "skill_name": row.skill_name,
                    "enabled": bool(row.enabled),
                    "notes": row.notes,
                }
                for row in rows
            ],
            "documented": {
                "brief": {
                    "schedule": "06:30 weekdays",
                    "timezone": "Europe/London",
                    "daemon": False,
                    "method": "POST",
                    "path": "/routines/run-brief",
                    "cli": "python -m varma.routines.run_brief",
                    "description": describe_0630_weekday_routine(),
                },
                "nightly_filter": {
                    "schedule": "nightly",
                    "timezone": "Europe/London",
                    "daemon": False,
                    "writes_controls": False,
                    "method": "POST",
                    "path": "/routines/run-nightly-filter",
                    "cli": "python -m varma.routines.run_nightly_filter",
                    "description": describe_nightly_memory_filter(),
                },
                "company_meeting": {
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
                    "method": "POST",
                    "path": "/routines/run-0730-meeting",
                    "cli": "python -m varma.routines.run_0730_meeting",
                    "description": describe_0730_company_meeting(),
                },
                "flatten_us_close": {
                    "schedule": "before US regular cash close",
                    "timezone": "Europe/London",
                    "daemon": False,
                    "flatten_at": "US_REGULAR_CASH_CLOSE",
                    "flatten_not_at": "LONDON_CASH_CLOSE",
                    "overnight_holds": False,
                    "method": "POST",
                    "path": "/routines/run-flatten-us-close",
                    "cli": "python -m varma.routines.run_flatten_us_close",
                    "description": describe_flatten_us_close(),
                    "session": describe_paper_session(),
                    "get_observability_flattens": False,
                    "internal_simulator": True,
                    "broker": False,
                    "flatten_as_if_there_were_positions": False,
                },
            },
            "note": (
                "Board-only read of documented schedules. On-demand. No 24/7 daemon. "
                "Nightly filter has no invented clock hour. This view does not write controls. "
                "Board Member runs jobs via POST (right-hand panel), not GET /observability."
            ),
        }

    def _runnable_jobs(self) -> dict[str, Any]:
        """Listing only. GET /observability must not run these jobs."""
        catalog = runnable_jobs_catalog()
        catalog["read_only"] = True
        catalog["run_via"] = "POST"
        catalog["get_observability_runs_jobs"] = False
        return catalog
