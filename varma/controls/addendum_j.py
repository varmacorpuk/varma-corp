"""Board Addendum J 2026-08-27.

Hari asked the Founding Architect to encode: company records are not on the
Board Member's laptop and not in GitHub. These are Board-set control-table
values, labelled Board Addendum J 2026-08-27. They are not invented silent
defaults.

GitHub remains source code only. The system of record remains the database
(Postgres when the kernel is pointed at it; TEMPORARY SQLite via StoragePort
otherwise). Do not invent a second store.

Technology (Owen Blake · Technology) owns the backup job. Board Member runs
it on-demand like other Board jobs. Default documented schedule: daily
Europe/London, after US close / end of London evening. Not a 24/7 daemon.

Backups are encrypted at rest. Included: paper ledger, evidence,
organisational memory, control snapshots. Excluded: secrets, live broker
credentials (which must not exist yet). Employees including the CEO cannot
download secrets. Owen cannot write trading_mode, allow-list, or open the firm.

PAPER execution stays CLOSED. trading_mode stays LIVE_BLOCKED. This slice
does not implement paper fills or Grand Opening.
"""

from __future__ import annotations

from typing import Any

from varma.controls.addendum_f import TECH_SLUG, staff_display_for_slug

ADDENDUM_J_LABEL = "Board Addendum J 2026-08-27"
ADDENDUM_J_SET_BY = "board-member"

BACKUP_OWNER_SLUG = TECH_SLUG
BACKUP_OWNER_DISPLAY = staff_display_for_slug(TECH_SLUG)
BACKUP_SKILL_NAME = "run_company_backup"
BACKUP_ROUTINE_NAME = "daily_backup_after_us_close"

BACKUP_SCHEDULE = "daily after US close / end of London evening"
BACKUP_TIMEZONE = "Europe/London"
BACKUP_AFTER = "US_REGULAR_CASH_CLOSE"
BACKUP_STORE = "database"

BACKUP_INCLUDED: tuple[str, ...] = (
    "paper_ledger",
    "evidence",
    "organisational_memory",
    "control_snapshots",
)
BACKUP_EXCLUDED: tuple[str, ...] = (
    "secrets",
    "live_broker_credentials",
)

EMPLOYEE_CANNOT_DOWNLOAD_SECRETS_REASON = "EMPLOYEE_CANNOT_DOWNLOAD_SECRETS"
SECRETS_ARE_NOT_DOWNLOADABLE_REASON = "SECRETS_ARE_NOT_DOWNLOADABLE"
BACKUP_ARTEFACT_NOT_ON_LAPTOP_REASON = "BACKUP_ARTEFACT_NOT_ON_BOARD_MEMBER_LAPTOP"
BACKUP_ARTEFACT_NOT_IN_GITHUB_REASON = "BACKUP_ARTEFACT_NOT_IN_GITHUB"

ADDENDUM_J_SETTINGS: tuple[tuple[str, str, str], ...] = (
    ("backup_owner_slug", BACKUP_OWNER_SLUG, "slug"),
    ("backup_encrypted_at_rest", "true", "flag"),
    ("backup_includes_secrets", "false", "flag"),
    ("backup_includes_live_broker_credentials", "false", "flag"),
    ("live_broker_credentials_exist", "false", "flag"),
    ("backup_store", BACKUP_STORE, "label"),
    ("backup_github_is_code_only", "true", "flag"),
    ("backup_on_board_member_laptop", "false", "flag"),
)

BACKUP_WRITE_FIELDS = frozenset(
    {
        "addendum_j",
        "backup_encryption_key",
        "backup_secrets",
        "live_broker_credentials",
    }
)


def live_broker_credentials_exist() -> bool:
    """LIVE broker credentials must not exist in this slice."""
    return False


def addendum_j_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_J_LABEL,
        "set_by": ADDENDUM_J_SET_BY,
        "board_set": True,
        "values_invented": False,
        "github_is_code_only": True,
        "on_board_member_laptop": False,
        "in_github": False,
        "system_of_record": BACKUP_STORE,
        "second_store_invented": False,
        "owner_slug": BACKUP_OWNER_SLUG,
        "owner_display_name": BACKUP_OWNER_DISPLAY,
        "owner_cannot_write_trading_mode": True,
        "owner_cannot_write_allow_list": True,
        "owner_cannot_open_the_firm": True,
        "schedule": BACKUP_SCHEDULE,
        "timezone": BACKUP_TIMEZONE,
        "after": BACKUP_AFTER,
        "after_us_close": True,
        "end_of_london_evening": True,
        "clock_hour_invented": False,
        "daemon": False,
        "encrypted_at_rest": True,
        "included": list(BACKUP_INCLUDED),
        "excluded": list(BACKUP_EXCLUDED),
        "secrets_included": False,
        "live_broker_credentials_exist": False,
        "live_broker_credentials_included": False,
        "employees_cannot_download_secrets": True,
        "ceo_cannot_download_secrets": True,
        "technology_cannot_download_secrets": True,
        "paper_execution_stays": "CLOSED",
        "trading_mode_stays": "LIVE_BLOCKED",
        "does_not_fill": True,
        "does_not_open_the_firm": True,
        "grand_opening_implemented": False,
        "note": (
            "Company records live in the database, not on the Board Member's laptop "
            "and not in GitHub. GitHub is code only. Backups are encrypted at rest "
            "in the same database. Technology (Owen Blake · Technology) owns the "
            "job. Board Member runs it on-demand. Daily after US close / end of "
            "London evening. No 24/7 daemon. Secrets and live broker credentials "
            "are excluded. Live broker credentials must not exist yet."
        ),
    }
