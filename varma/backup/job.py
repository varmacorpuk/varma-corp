"""On-demand company backup. Encrypted artefact lives in the database.

Does not fill orders. Does not write trading_mode, allow-list, or open the firm.
Does not commit artefacts to git. Does not put records on the Board Member laptop.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from varma.backup.crypto import encrypt_bytes, key_fingerprint, load_or_create_backup_key
from varma.clock import now_london
from varma.controls.addendum_j import (
    ADDENDUM_J_LABEL,
    BACKUP_AFTER,
    BACKUP_EXCLUDED,
    BACKUP_INCLUDED,
    BACKUP_OWNER_DISPLAY,
    BACKUP_OWNER_SLUG,
    BACKUP_SCHEDULE,
    BACKUP_STORE,
    BACKUP_TIMEZONE,
    addendum_j_public,
    live_broker_credentials_exist,
)
from varma.controls.engine import ControlEngine
from varma.db.models import (
    BackupRun,
    ClosedPaperTrade,
    ControlSetting,
    ControlState,
    Evidence,
    MemoryOrg,
    NumericLimit,
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperPosition,
)
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED, execution_port_status


def backup_run_to_dict(row: BackupRun | None) -> dict[str, Any] | None:
    if row is None:
        return None
    included = json.loads(row.included_json or "[]")
    excluded = json.loads(row.excluded_json or "[]")
    return {
        "id": row.id,
        "ran_at": row.ran_at.isoformat() if row.ran_at else None,
        "timezone": row.timezone,
        "schedule": row.schedule,
        "after": row.after,
        "status": row.status,
        "failure_reason": row.failure_reason or None,
        "included": included,
        "excluded": excluded,
        "encrypted_at_rest": bool(row.encrypted_at_rest),
        "key_fingerprint": row.key_fingerprint,
        "ciphertext_shown": False,
        "encryption_key_shown": False,
        "owner_slug": row.owner_slug,
        "owner_display_name": row.owner_display_name,
        "started_by": row.started_by,
        "daemon": bool(row.daemon),
        "writes_controls": bool(row.writes_controls),
        "fills": bool(row.fills),
        "paper_fills": bool(row.paper_fills),
        "live_fills": bool(row.live_fills),
        "git_committed": bool(row.git_committed),
        "on_board_member_laptop": bool(row.on_board_member_laptop),
        "in_github": bool(row.in_github),
        "secrets_included": bool(row.secrets_included),
        "live_broker_credentials_exist": bool(row.live_broker_credentials_exist),
        "live_broker_credentials_included": bool(row.live_broker_credentials_included),
        "store": row.store,
        "trading_mode_before": row.trading_mode_before,
        "trading_mode_after": row.trading_mode_after,
        "artefact_bytes": row.artefact_bytes,
        "notes": row.notes,
        "addendum": ADDENDUM_J_LABEL,
    }


def _row_public(row: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in fields:
        value = getattr(row, name)
        if hasattr(value, "isoformat"):
            out[name] = value.isoformat()
        else:
            out[name] = value
    return out


def _snapshot_payload(session: Session) -> dict[str, Any]:
    engine = ControlEngine(session)
    snap = engine.snapshot()
    account = session.get(PaperAccount, 1)
    paper_ledger = {
        "account": (
            _row_public(
                account,
                (
                    "id",
                    "currency",
                    "timezone",
                    "simulated_capital",
                    "cash",
                    "equity_at_day_start",
                    "london_day",
                    "source",
                    "updated_at",
                ),
            )
            if account
            else None
        ),
        "positions": [
            _row_public(row, ("symbol", "quantity", "avg_cost_gbp", "updated_at"))
            for row in session.query(PaperPosition).all()
        ],
        "orders": [
            _row_public(
                row,
                ("id", "symbol", "side", "quantity", "notional_gbp", "status", "london_day", "is_live"),
            )
            for row in session.query(PaperOrder).all()
        ],
        "fills": [
            _row_public(
                row,
                ("id", "order_id", "symbol", "side", "quantity", "price", "notional_gbp", "london_day", "is_live"),
            )
            for row in session.query(PaperFill).all()
        ],
        "closed_trades": [
            _row_public(
                row,
                ("id", "symbol", "quantity", "pnl_gbp", "profit_positive", "london_day", "is_paper", "is_live"),
            )
            for row in session.query(ClosedPaperTrade).all()
        ],
    }
    evidence = [
        _row_public(row, ("id", "kind", "actor", "payload", "created_at"))
        for row in session.query(Evidence).order_by(Evidence.created_at.asc()).all()
    ]
    org = [
        _row_public(row, ("id", "title", "content", "promoted_by", "created_at"))
        for row in session.query(MemoryOrg).order_by(MemoryOrg.created_at.asc()).all()
    ]
    state = session.get(ControlState, 1)
    control_snapshots = {
        "trading_mode": state.trading_mode if state else None,
        "kill_switch": bool(state.kill_switch) if state else False,
        "allow_list": list(snap.get("allow_list") or []),
        "paper_execution": snap.get("paper_execution"),
        "numeric_limits": [
            _row_public(row, ("key", "value", "unit", "set_by", "source"))
            for row in session.query(NumericLimit).all()
        ],
        "control_settings": [
            _row_public(row, ("key", "value", "unit", "set_by", "source"))
            for row in session.query(ControlSetting).all()
        ],
        "addendum_j": addendum_j_public(),
    }
    return {
        "included": list(BACKUP_INCLUDED),
        "paper_ledger": paper_ledger,
        "evidence": evidence,
        "organisational_memory": org,
        "control_snapshots": control_snapshots,
        "excluded": list(BACKUP_EXCLUDED),
        "secrets_included": False,
        "live_broker_credentials_exist": live_broker_credentials_exist(),
        "live_broker_credentials_included": False,
    }


_SECRET_KEYS = frozenset(
    {
        "llm_api_key",
        "board_member_stub_token",
        "backup_encryption_key",
        "live_broker_credential",
        "live_broker_credentials",
        "broker_api_key",
        "broker_password",
        "ibkr_password",
        "alpaca_key",
        "alpaca_secret",
    }
)


def _walk_secret_keys(obj: Any) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            if lowered in _SECRET_KEYS and value not in (None, "", False, "false"):
                raise RuntimeError(f"BACKUP_WOULD_INCLUDE_SECRET:{key}")
            _walk_secret_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            _walk_secret_keys(item)


def _assert_payload_excludes_secrets(payload: dict[str, Any]) -> None:
    if payload.get("secrets_included"):
        raise RuntimeError("BACKUP_WOULD_INCLUDE_SECRETS")
    if payload.get("live_broker_credentials_included") or payload.get("live_broker_credentials_exist"):
        raise RuntimeError("BACKUP_WOULD_INCLUDE_LIVE_BROKER_CREDENTIALS")
    _walk_secret_keys(payload)


def _persist_run(session: Session, row: BackupRun) -> BackupRun:
    session.add(row)
    session.add(
        Evidence(
            kind="backup_run",
            actor=row.started_by,
            payload=json.dumps(
                {
                    "id": row.id,
                    "status": row.status,
                    "encrypted_at_rest": bool(row.encrypted_at_rest),
                    "git_committed": False,
                    "on_board_member_laptop": False,
                    "fills": False,
                    "addendum": ADDENDUM_J_LABEL,
                    "failure_reason": row.failure_reason or None,
                },
                default=str,
            ),
            created_at=row.ran_at,
        )
    )
    session.commit()
    session.refresh(row)
    return row


def run_company_backup(session: Session, *, started_by: str = "board-member") -> dict[str, Any]:
    """Snapshot included records, encrypt, store in the same database. No fills."""
    engine = ControlEngine(session)
    before = engine.snapshot()
    fills_before = session.query(PaperFill).count()
    now = now_london()
    ports = execution_port_status()
    try:
        if live_broker_credentials_exist():
            raise RuntimeError("LIVE_BROKER_CREDENTIALS_MUST_NOT_EXIST")
        payload = _snapshot_payload(session)
        _assert_payload_excludes_secrets(payload)
        plaintext = json.dumps(payload, default=str, sort_keys=True).encode("utf-8")
        key = load_or_create_backup_key()
        ciphertext = encrypt_bytes(plaintext, key)
        if ciphertext == plaintext.decode("utf-8"):
            raise RuntimeError("BACKUP_NOT_ENCRYPTED")
        after = engine.snapshot()
        if after["trading_mode"] != before["trading_mode"]:
            raise RuntimeError("BACKUP_CHANGED_TRADING_MODE")
        if session.query(PaperFill).count() != fills_before:
            raise RuntimeError("BACKUP_FILLED_ORDERS")
        row = BackupRun(
            ran_at=now,
            timezone=BACKUP_TIMEZONE,
            schedule=BACKUP_SCHEDULE,
            after=BACKUP_AFTER,
            status="success",
            failure_reason="",
            included_json=json.dumps(list(BACKUP_INCLUDED)),
            excluded_json=json.dumps(list(BACKUP_EXCLUDED)),
            ciphertext=ciphertext,
            key_fingerprint=key_fingerprint(key),
            encrypted_at_rest=True,
            owner_slug=BACKUP_OWNER_SLUG,
            owner_display_name=BACKUP_OWNER_DISPLAY,
            started_by=started_by,
            daemon=False,
            writes_controls=False,
            fills=False,
            paper_fills=False,
            live_fills=False,
            git_committed=False,
            on_board_member_laptop=False,
            in_github=False,
            secrets_included=False,
            live_broker_credentials_exist=False,
            live_broker_credentials_included=False,
            store=BACKUP_STORE,
            trading_mode_before=before["trading_mode"],
            trading_mode_after=after["trading_mode"],
            artefact_bytes=len(ciphertext.encode("ascii")),
            notes=(
                "Encrypted backup artefact stored in the database. "
                "Not in GitHub. Not on the Board Member laptop. No fills."
            ),
        )
        row = _persist_run(session, row)
    except Exception as exc:
        after = engine.snapshot()
        row = BackupRun(
            ran_at=now,
            timezone=BACKUP_TIMEZONE,
            schedule=BACKUP_SCHEDULE,
            after=BACKUP_AFTER,
            status="failure",
            failure_reason=str(exc)[:240],
            included_json=json.dumps(list(BACKUP_INCLUDED)),
            excluded_json=json.dumps(list(BACKUP_EXCLUDED)),
            ciphertext="",
            key_fingerprint="",
            encrypted_at_rest=True,
            owner_slug=BACKUP_OWNER_SLUG,
            owner_display_name=BACKUP_OWNER_DISPLAY,
            started_by=started_by,
            daemon=False,
            writes_controls=False,
            fills=False,
            paper_fills=False,
            live_fills=False,
            git_committed=False,
            on_board_member_laptop=False,
            in_github=False,
            secrets_included=False,
            live_broker_credentials_exist=live_broker_credentials_exist(),
            live_broker_credentials_included=False,
            store=BACKUP_STORE,
            trading_mode_before=before["trading_mode"],
            trading_mode_after=after["trading_mode"],
            artefact_bytes=0,
            notes="Backup failed. Failure is recorded for Board status. No fills.",
        )
        row = _persist_run(session, row)
    data = backup_run_to_dict(row) or {}
    data.update(
        {
            "ok": row.status == "success",
            "addendum": addendum_j_public(),
            "paper_fills_unchanged": session.query(PaperFill).count() == fills_before,
            "paper_fill_count": session.query(PaperFill).count(),
            "broker_paper_loaded": bool(BROKER_PAPER_LOADED),
            "live_adapter_loaded": bool(LIVE_PORT_LOADED),
            "broker_paper_status": ports["broker_paper"]["status"],
            "live_status": ports["live"]["status"],
            "employees_cannot_download_secrets": True,
            "ceo_cannot_download_secrets": True,
        }
    )
    return data


def backup_status(session: Session) -> dict[str, Any]:
    """Board-visible backup status. No ciphertext. No encryption key."""
    success = (
        session.query(BackupRun)
        .filter_by(status="success")
        .order_by(BackupRun.ran_at.desc())
        .first()
    )
    failure = (
        session.query(BackupRun)
        .filter_by(status="failure")
        .order_by(BackupRun.ran_at.desc())
        .first()
    )
    pub = addendum_j_public()
    data: dict[str, Any] = {
        "read_only": True,
        "source": "database",
        "writes_controls": False,
        "addendum": pub,
        "label": ADDENDUM_J_LABEL,
        "owner_slug": BACKUP_OWNER_SLUG,
        "owner_display_name": BACKUP_OWNER_DISPLAY,
        "owner_cannot_write_trading_mode": True,
        "owner_cannot_write_allow_list": True,
        "owner_cannot_open_the_firm": True,
        "schedule": BACKUP_SCHEDULE,
        "timezone": BACKUP_TIMEZONE,
        "after": BACKUP_AFTER,
        "daemon": False,
        "encrypted_at_rest": True,
        "system_of_record": BACKUP_STORE,
        "second_store_invented": False,
        "github_is_code_only": True,
        "on_board_member_laptop": False,
        "in_github": False,
        "git_committed": False,
        "included": list(BACKUP_INCLUDED),
        "excluded": list(BACKUP_EXCLUDED),
        "secrets_included": False,
        "live_broker_credentials_exist": False,
        "live_broker_credentials_included": False,
        "employees_cannot_download_secrets": True,
        "ceo_cannot_download_secrets": True,
        "ciphertext_shown": False,
        "encryption_key_shown": False,
        "last_successful_backup_at": success.ran_at.isoformat() if success and success.ran_at else None,
        "last_failure_at": failure.ran_at.isoformat() if failure and failure.ran_at else None,
        "last_failure_reason": (failure.failure_reason or None) if failure else None,
        "last_success": backup_run_to_dict(success),
        "last_failure": backup_run_to_dict(failure),
        "cli": "python -m varma.routines.run_backup",
        "method": "POST",
        "path": "/routines/run-backup",
        "get_observability_runs_backup": False,
        "fills": False,
        "paper_fills": False,
        "live_fills": False,
        "paper_execution_stays": "CLOSED",
        "trading_mode_stays": "LIVE_BLOCKED",
        "note": pub["note"],
    }
    if success is None and failure is None:
        data["note"] = (
            "No backup run stored yet. Board Member: POST /routines/run-backup "
            "or python -m varma.routines.run_backup. Encrypted artefact stays "
            "in the database. Not in GitHub. Not on the Board Member laptop."
        )
    return data
