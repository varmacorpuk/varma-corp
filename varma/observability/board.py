"""Board Member read-only observability. Database is the ledger, not the desktop.

This view must not write controls, trading_mode, allow-list, or permissions.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import describe_0630_weekday_routine, describe_nightly_memory_filter
from varma.controls.engine import REQUIRED_LIMIT_KEYS, ControlEngine
from varma.cost.ledger import CostLedger, TEMPORARY_BRIEF_COST_CAP_LABEL
from varma.db.models import (
    BoardApproval,
    ChallengeReview,
    CostEntry,
    Employee,
    Evidence,
    Handoff,
    IntelligenceBrief,
    MemoryFilterRun,
    MemoryOrg,
    RiskDecision,
    Routine,
    SampleThesis,
)
from varma.meetings.handoff import CEO_SLUG
from varma.memory.filter import filter_run_to_dict
from varma.memory.stores import MemoryStores

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
            "employees_cannot_write_controls": True,
            "missing_numeric_limits": self._missing_numeric_limits(control_snap),
            "controls": self._control_snapshot(control_snap),
            "paper_gate": self._paper_gate(control_snap),
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
            "status_bubbles": self._status_bubbles(),
            "routines": self._routine_schedules(),
            "note": READ_ONLY_NOTE,
        }

    def _missing_numeric_limits(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        """Keys only. Values are OPEN BOARD DECISIONS and must not be invented here."""
        unset_keys = list(control_snap.get("missing_numeric_limits") or self.controls.missing_limits())
        return {
            "read_only": True,
            "source": "database",
            "open_board_decision": True,
            "values_invented": False,
            "values_shown": False,
            "required_keys": list(REQUIRED_LIMIT_KEYS),
            "unset_keys": unset_keys,
            "all_unset": unset_keys == list(REQUIRED_LIMIT_KEYS),
            "deny_execution_when_missing": True,
            "note": (
                "Keys that are unset. Numeric paper/live limit VALUES are OPEN BOARD "
                "DECISIONS and are not invented here. Missing limits DENY execution."
            ),
        }

    def _control_snapshot(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        return {
            "read_only": True,
            "source": "database",
            "writes_controls": False,
            "employees_cannot_write_controls": True,
            "trading_mode": control_snap["trading_mode"],
            "kill_switch": control_snap["kill_switch"],
            "allow_list": list(control_snap["allow_list"]),
            "allow_list_empty": control_snap["allow_list_empty"],
            "live_adapter_loaded": control_snap["live_adapter_loaded"],
            "live_gate": control_snap["live_gate"],
            "note": (
                "Board-only control snapshot. Employees cannot write controls. "
                "Empty allow-list cannot execute. LIVE adapter is not loaded. "
                "This view does not write trading_mode, allow-list, or permissions."
            ),
        }

    def _paper_gate(self, control_snap: dict[str, Any]) -> dict[str, Any]:
        """PAPER not started. No paper/live execution. Do not invent duration/success numbers."""
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
        return {
            "read_only": True,
            "source": "database",
            "writes_controls": False,
            "paper_status": "not started",
            "paper_started": False,
            "paper_execution_implemented": False,
            "evaluation_status": "not",
            "live_trading_recommendation": "not",
            "board_review": "not",
            "explicit_board_approval": "not",
            "trading_mode": control_snap["trading_mode"],
            "execution": False,
            "live_adapter_loaded": control_snap["live_adapter_loaded"],
            "live_approvals": live_approvals,
            "paper_start_approvals": paper_approvals,
            "gate": control_snap["live_gate"],
            "silence_is_not_approval": True,
            "open_board_decision": True,
            "values_invented": False,
            "values_shown": False,
            "unset_open_keys": [
                "paper_duration_threshold",
                "paper_success_threshold",
            ],
            "note": (
                "PAPER is not started. trading_mode=LIVE_BLOCKED. No paper/live execution "
                "in this slice. Paper duration/success thresholds are OPEN BOARD DECISIONS "
                "and are not invented here. Silence is not approval."
            ),
        }

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
        brief = (
            self.session.query(IntelligenceBrief)
            .order_by(IntelligenceBrief.produced_at.desc())
            .first()
        )
        ceo = self.session.query(Employee).filter_by(slug=CEO_SLUG).one_or_none()
        handoff = None
        if brief is not None and ceo is not None:
            handoff = (
                self.session.query(Handoff)
                .filter_by(
                    to_employee_id=ceo.id,
                    artefact_type="intelligence_brief",
                    artefact_id=brief.id,
                )
                .order_by(Handoff.created_at.desc())
                .first()
            )
        thesis = (
            self.session.query(SampleThesis).order_by(SampleThesis.created_at.desc()).first()
        )
        review = None
        if thesis is not None:
            review = (
                self.session.query(ChallengeReview)
                .filter_by(thesis_id=thesis.id)
                .order_by(ChallengeReview.produced_at.desc())
                .first()
            )
        risk = (
            self.session.query(RiskDecision).order_by(RiskDecision.produced_at.desc()).first()
        )
        return brief, ceo, handoff, thesis, review, risk

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
                    "cli": "python -m varma.routines.run_brief",
                    "description": describe_0630_weekday_routine(),
                },
                "nightly_filter": {
                    "schedule": "nightly",
                    "timezone": "Europe/London",
                    "daemon": False,
                    "writes_controls": False,
                    "cli": "python -m varma.routines.run_nightly_filter",
                    "description": describe_nightly_memory_filter(),
                },
            },
            "note": (
                "Board-only read of documented schedules. On-demand. No 24/7 daemon. "
                "Nightly filter has no invented clock hour. This view does not write controls."
            ),
        }
