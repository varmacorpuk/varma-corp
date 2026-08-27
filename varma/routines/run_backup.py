"""On-demand company backup. Daily after US close / end of London evening. No daemon.

Usage:
    python -m varma.routines.run_backup

Board Addendum J 2026-08-27. Technology (Owen Blake · Technology) owns the job.
Board Member runs it. Encrypted artefact stays in the database. No fills.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.backup.job import run_company_backup
from varma.clock import describe_company_backup, now_london
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty


def run_backup(session: Session, *, started_by: str = "cli") -> dict:
    return run_company_backup(session, started_by=started_by)


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        print(describe_company_backup())
        print("Now Europe/London:", now_london().isoformat())
        print("Daemon: False")
        print("Owner: Owen Blake · Technology")
        print("Store: database")
        print("Encrypted at rest: True")
        result = run_backup(session, started_by="cli")
        print("backup_run_id:", result["id"])
        print("status:", result["status"])
        print("encrypted_at_rest:", result["encrypted_at_rest"])
        print("git_committed:", result["git_committed"])
        print("on_board_member_laptop:", result["on_board_member_laptop"])
        print("fills:", result["fills"])
        print("trading_mode:", result["trading_mode_after"])
        print("stored_in: database table backup_runs")
    finally:
        session.close()


if __name__ == "__main__":
    main()
