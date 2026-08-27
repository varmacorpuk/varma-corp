"""Nightly Europe/London working-context filter (Document 08).

On-demand. No 24/7 daemon. Archives working context. Evidence is append-only.
Does not write controls, trading_mode, allow-list, or permissions.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import describe_nightly_memory_filter, now_london
from varma.controls.engine import ControlEngine
from varma.db.models import (
    AllowListInstrument,
    ControlSetting,
    ControlState,
    Evidence,
    MemoryEmployee,
    MemoryFilterRun,
    MemoryOrg,
    MemoryWorking,
    MemoryWorkingArchive,
    NumericLimit,
    Permission,
)

FILTER_ACTOR = "nightly-memory-filter"
CADENCE = "nightly"
TIMEZONE = "Europe/London"


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


def _org_fingerprint(session: Session) -> list[tuple[str, str, str]]:
    rows = session.query(MemoryOrg).order_by(MemoryOrg.id).all()
    return [(r.id, r.title, r.promoted_by) for r in rows]


def _controls_guard(session: Session) -> dict[str, Any]:
    engine = ControlEngine(session)
    state = session.get(ControlState, 1)
    paper = session.get(ControlSetting, "paper_execution")
    return {
        "snapshot": engine.snapshot(),
        "trading_mode": state.trading_mode if state else None,
        "kill_switch": bool(state.kill_switch) if state else None,
        "allow_list": sorted(r.symbol for r in session.query(AllowListInstrument).all()),
        "permissions": _permission_fingerprint(session),
        "limits": _limit_fingerprint(session),
        "paper_execution": paper.value if paper is not None else None,
        "org": _org_fingerprint(session),
    }


def filter_run_to_dict(row: MemoryFilterRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "ran_at": row.ran_at.isoformat() if row.ran_at else None,
        "timezone": row.timezone,
        "cadence": row.cadence,
        "archived_count": row.archived_count,
        "evidence_count_before": row.evidence_count_before,
        "evidence_count_after": row.evidence_count_after,
        "trading_mode_before": row.trading_mode_before,
        "trading_mode_after": row.trading_mode_after,
        "controls_written": row.controls_written,
        "daemon": row.daemon,
        "notes": row.notes,
        "evidence_deleted": False,
        "live_still_blocked": row.trading_mode_after == "LIVE_BLOCKED",
    }


class NightlyMemoryFilter:
    """Archive working context. Never delete evidence. Never write controls."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self) -> dict[str, Any]:
        before = _controls_guard(self.session)
        evidence_ids_before = [r.id for r in self.session.query(Evidence).all()]
        lesson_ids_before = [r.id for r in self.session.query(MemoryEmployee).all()]

        run = MemoryFilterRun(
            ran_at=now_london(),
            timezone=TIMEZONE,
            cadence=CADENCE,
            archived_count=0,
            evidence_count_before=len(evidence_ids_before),
            evidence_count_after=len(evidence_ids_before),
            trading_mode_before=str(before["trading_mode"] or ""),
            trading_mode_after=str(before["trading_mode"] or ""),
            controls_written=False,
            daemon=False,
            notes=describe_nightly_memory_filter(),
        )
        self.session.add(run)
        self.session.flush()

        working = self.session.query(MemoryWorking).all()
        archived = 0
        for row in working:
            self.session.add(
                MemoryWorkingArchive(
                    filter_run_id=run.id,
                    employee_id=row.employee_id,
                    key=row.key,
                    value=row.value,
                    working_updated_at=row.updated_at,
                    archived_at=now_london(),
                )
            )
            self.session.delete(row)
            archived += 1

        self.session.add(
            Evidence(
                kind="nightly_filter_ran",
                actor=FILTER_ACTOR,
                payload=json.dumps(
                    {
                        "filter_run_id": run.id,
                        "archived_count": archived,
                        "controls_written": False,
                        "evidence_deleted": False,
                        "daemon": False,
                        "timezone": TIMEZONE,
                        "cadence": CADENCE,
                    }
                ),
                created_at=now_london(),
            )
        )
        self.session.flush()

        after = _controls_guard(self.session)
        if after["trading_mode"] != before["trading_mode"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_WRITE_CONTROLS")
        if after["kill_switch"] != before["kill_switch"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_WRITE_CONTROLS")
        if after["allow_list"] != before["allow_list"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_WRITE_CONTROLS")
        if after["permissions"] != before["permissions"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_WRITE_CONTROLS")
        if after["limits"] != before["limits"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_WRITE_CONTROLS")
        if after["paper_execution"] != before["paper_execution"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_WRITE_CONTROLS")
        if after["org"] != before["org"]:
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_MUTATE_ORG_KNOWLEDGE")

        evidence_ids_after = [r.id for r in self.session.query(Evidence).all()]
        if not set(evidence_ids_before).issubset(set(evidence_ids_after)):
            raise RuntimeError("EVIDENCE_IS_APPEND_ONLY")
        lesson_ids_after = [r.id for r in self.session.query(MemoryEmployee).all()]
        if set(lesson_ids_before) != set(lesson_ids_after):
            raise RuntimeError("NIGHTLY_FILTER_MUST_NOT_MUTATE_EMPLOYEE_LESSONS")

        run.archived_count = archived
        run.evidence_count_after = len(evidence_ids_after)
        run.trading_mode_after = str(after["trading_mode"] or "")
        run.controls_written = False
        self.session.commit()
        data = filter_run_to_dict(run)
        data["working_remaining"] = self.session.query(MemoryWorking).count()
        data["cli"] = "python -m varma.routines.run_nightly_filter"
        data["description"] = describe_nightly_memory_filter()
        return data
