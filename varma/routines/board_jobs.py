"""Board-only on-demand jobs. POST endpoints, not GET /observability.

CLI entry points remain. Running a job must not load broker ports and must
not change trading_mode. Paper-path and flatten jobs may use the internal
simulator after Grand Opening PAPER. LIVE stays off.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.controls.engine import ControlEngine
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED, execution_port_status

JOB_SAFETY_FLAGS: dict[str, Any] = {
    "loads_broker_ports": False,
    "changes_trading_mode": False,
    "fills": False,
    "paper_fills": False,
    "live_fills": False,
    "writes_controls": False,
    "not_get_observability": True,
    "board_only": True,
    "employees_denied": True,
    "cli_still_works": True,
    "daemon": False,
}

BOARD_JOBS: tuple[dict[str, Any], ...] = (
    {
        "id": "run-brief",
        "label": "Run morning intelligence brief",
        "method": "POST",
        "path": "/routines/run-brief",
        "cli": "python -m varma.routines.run_brief",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
    },
    {
        "id": "run-challenge",
        "label": "Run SAMPLE challenge",
        "method": "POST",
        "path": "/routines/run-challenge",
        "cli": "python -m varma.routines.run_challenge",
        "sample": True,
        "is_live_trade": False,
        "is_live_approval": False,
    },
    {
        "id": "run-risk-deny",
        "label": "Run Risk deny-path",
        "method": "POST",
        "path": "/routines/run-risk-deny",
        "cli": "python -m varma.routines.run_risk_deny",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "cannot_approve_live": True,
    },
    {
        "id": "run-0730-meeting",
        "label": "Run 07:30 meeting record",
        "method": "POST",
        "path": "/routines/run-0730-meeting",
        "cli": "python -m varma.routines.run_0730_meeting",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "cannot_start_live": True,
    },
    {
        "id": "run-nightly-filter",
        "label": "Run nightly memory filter",
        "method": "POST",
        "path": "/routines/run-nightly-filter",
        "cli": "python -m varma.routines.run_nightly_filter",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
    },
    {
        "id": "run-flatten-us-close",
        "label": "Flatten paper before US cash close",
        "method": "POST",
        "path": "/routines/run-flatten-us-close",
        "cli": "python -m varma.routines.run_flatten_us_close",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "internal_simulator_flatten": True,
        "flatten_at": "US_REGULAR_CASH_CLOSE",
        "flatten_not_at": "LONDON_CLOSING_AUCTION",
        "venue_scope": "US",
        "split_flatten_clocks": True,
        "paper_fills": False,
        "fills": False,
        "allow_list_not_required_for_flatten": True,
        "flatten_as_if_there_were_positions": False,
        "daemon": False,
    },
    {
        "id": "run-flatten-london-close",
        "label": "Flatten LSE paper in London closing auction",
        "method": "POST",
        "path": "/routines/run-flatten-london-close",
        "cli": "python -m varma.routines.run_flatten_london_close",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "internal_simulator_flatten": True,
        "flatten_at": "LONDON_CLOSING_AUCTION",
        "flatten_not_at": "US_REGULAR_CASH_CLOSE",
        "venue_scope": "LSE",
        "split_flatten_clocks": True,
        "risk_02f_bound": True,
        "paper_fills": False,
        "fills": False,
        "allow_list_not_required_for_flatten": True,
        "flatten_as_if_there_were_positions": False,
        "daemon": False,
    },
    {
        "id": "run-backup",
        "label": "Run company backup now",
        "method": "POST",
        "path": "/routines/run-backup",
        "cli": "python -m varma.routines.run_backup",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "owner_slug": "technology",
        "owner_display_name": "Owen Blake · Technology",
        "encrypted_at_rest": True,
        "git_committed": False,
        "on_board_member_laptop": False,
        "secrets_included": False,
        "live_broker_credentials_exist": False,
        "paper_fills": False,
        "fills": False,
        "daemon": False,
    },
    {
        "id": "run-us-open-scanner",
        "label": "Run US-open PAPER scanner",
        "method": "POST",
        "path": "/routines/run-us-open-scanner",
        "cli": "python -m varma.routines.run_us_open_scanner",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "internal_simulator": True,
        "paper_execution_closed": False,
        "fills_while_closed": False,
        "paper_fills": True,
        "fills": True,
        "live_fills": False,
        "ai_called": False,
        "daemon": False,
        "scanner": "us_open",
        "universe_count": 15,
        "completed_bars_only": True,
        "max_concurrent_is_proposal_not_control": True,
        "grand_opening_paper_done": True,
    },
    {
        "id": "run-paper-trade-path",
        "label": "Run Trader paper-ticket proposal",
        "method": "POST",
        "path": "/routines/run-paper-trade-path",
        "cli": "python -m varma.routines.run_paper_trade_path",
        "sample": False,
        "is_live_trade": False,
        "is_live_approval": False,
        "proposer_slug": "trader",
        "proposer_display_name": "Chris Adeyemi · Trader",
        "first_paper_trade_path_implemented": True,
        "internal_simulator": True,
        "paper_execution_closed": False,
        "fills_while_closed": False,
        "paper_fills": True,
        "fills": True,
        "live_fills": False,
        "ai_called": False,
        "daemon": False,
        "grand_opening_not_performed": False,
        "grand_opening_paper_done": True,
    },
)


def runnable_jobs_catalog() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for job in BOARD_JOBS:
        item = dict(job)
        item.update(JOB_SAFETY_FLAGS)
        if job["id"] == "run-flatten-us-close":
            item["paper_fills"] = False
            item["fills"] = False
            item["internal_simulator_flatten"] = True
            item["broker_fills"] = False
            item["allow_list_not_required_for_flatten"] = True
            item["flatten_as_if_there_were_positions"] = False
            item["flatten_at"] = "US_REGULAR_CASH_CLOSE"
            item["flatten_not_at"] = "LONDON_CLOSING_AUCTION"
            item["venue_scope"] = "US"
            item["split_flatten_clocks"] = True
            item["daemon"] = False
        if job["id"] == "run-flatten-london-close":
            item["paper_fills"] = False
            item["fills"] = False
            item["internal_simulator_flatten"] = True
            item["broker_fills"] = False
            item["allow_list_not_required_for_flatten"] = True
            item["flatten_as_if_there_were_positions"] = False
            item["flatten_at"] = "LONDON_CLOSING_AUCTION"
            item["flatten_not_at"] = "US_REGULAR_CASH_CLOSE"
            item["venue_scope"] = "LSE"
            item["split_flatten_clocks"] = True
            item["risk_02f_bound"] = True
            item["daemon"] = False
        if job["id"] == "run-backup":
            item["paper_fills"] = False
            item["fills"] = False
            item["encrypted_at_rest"] = True
            item["git_committed"] = False
            item["on_board_member_laptop"] = False
            item["in_github"] = False
            item["secrets_included"] = False
            item["live_broker_credentials_exist"] = False
            item["owner_slug"] = "technology"
            item["owner_display_name"] = "Owen Blake · Technology"
            item["daemon"] = False
        if job["id"] == "run-paper-trade-path":
            item["paper_fills"] = True
            item["fills"] = True
            item["live_fills"] = False
            item["fills_while_closed"] = False
            item["first_paper_trade_path_implemented"] = True
            item["internal_simulator"] = True
            item["paper_execution_closed"] = False
            item["ai_called"] = False
            item["proposer_slug"] = "trader"
            item["proposer_display_name"] = "Chris Adeyemi · Trader"
            item["grand_opening_not_performed"] = False
            item["grand_opening_paper_done"] = True
            item["daemon"] = False
        if job["id"] == "run-us-open-scanner":
            item["paper_fills"] = True
            item["fills"] = True
            item["live_fills"] = False
            item["fills_while_closed"] = False
            item["internal_simulator"] = True
            item["ai_called"] = False
            item["scanner"] = "us_open"
            item["completed_bars_only"] = True
            item["max_concurrent_is_proposal_not_control"] = True
            item["grand_opening_paper_done"] = True
            item["daemon"] = False
        items.append(item)
    catalog = {
        "read_only_list": True,
        "source": "kernel",
        "items": items,
        "note": (
            "Board Member can run these on-demand jobs via POST from the right-hand "
            "panel or the API. Not GET /observability. Employees are denied. CLI "
            "entry points still work. Running a job does not load BROKER_PAPER or "
            "LIVE, does not change trading_mode, and does not fill against a broker. "
            "Flatten-before-US-close uses the internal paper simulator for US names. "
            "LSE names flatten in the London closing auction (CEO desk 02F; "
            "split_flatten_clocks true). "
            "The Trader paper-ticket path exists; after Grand Opening PAPER that "
            "job may fill in the internal simulator. LIVE stays off. After a run, "
            "the same panel refreshes from the database."
        ),
    }
    catalog.update(JOB_SAFETY_FLAGS)
    catalog["fills"] = False
    return catalog


def with_job_safety(session: Session, result: dict[str, Any]) -> dict[str, Any]:
    """Attach safety flags. Does not load broker ports or write controls."""
    snap = ControlEngine(session).snapshot()
    ports = execution_port_status()
    out = dict(result)
    out["job_safety"] = {
        "loads_broker_ports": False,
        "changes_trading_mode": False,
        "fills": False,
        "paper_fills": False,
        "live_fills": False,
        "writes_controls": False,
        "not_get_observability": True,
        "trading_mode": snap["trading_mode"],
        "trading_mode_unchanged": snap["trading_mode"] == "LIVE_BLOCKED",
        "allow_list_empty": snap["allow_list_empty"],
        "broker_paper_loaded": bool(BROKER_PAPER_LOADED) or bool(snap.get("broker_paper_loaded")),
        "live_adapter_loaded": bool(LIVE_PORT_LOADED) or bool(snap.get("live_adapter_loaded")),
        "broker_paper_status": ports["broker_paper"]["status"],
        "live_status": ports["live"]["status"],
    }
    return out


def with_scanner_safety(session: Session, result: dict[str, Any]) -> dict[str, Any]:
    """Safety flags for the US-open scanner. Simulator fills only if submitted and allowed."""
    out = with_job_safety(session, result)
    filled = any(bool(row.get("filled")) for row in result.get("submissions") or [])
    out["job_safety"]["fills"] = filled
    out["job_safety"]["paper_fills"] = filled
    out["job_safety"]["live_fills"] = False
    out["job_safety"]["fills_while_closed"] = False
    out["job_safety"]["internal_simulator"] = True
    out["job_safety"]["ai_called"] = False
    out["job_safety"]["scanner"] = "us_open"
    out["job_safety"]["completed_bars_only"] = True
    out["job_safety"]["loads_broker_ports"] = False
    out["job_safety"]["changes_trading_mode"] = False
    out["job_safety"]["writes_controls"] = False
    return out


def with_paper_trade_safety(session: Session, result: dict[str, Any]) -> dict[str, Any]:
    """Safety flags for the Trader paper-ticket path. Simulator fills only if allowed."""
    out = with_job_safety(session, result)
    filled = bool(result.get("filled"))
    closed = bool(result.get("paper_execution_closed"))
    out["job_safety"]["fills"] = filled
    out["job_safety"]["paper_fills"] = filled
    out["job_safety"]["live_fills"] = False
    out["job_safety"]["fills_while_closed"] = False
    out["job_safety"]["first_paper_trade_path_implemented"] = True
    out["job_safety"]["internal_simulator"] = True
    out["job_safety"]["ai_called"] = False
    out["job_safety"]["proposer_slug"] = "trader"
    out["job_safety"]["loads_broker_ports"] = False
    out["job_safety"]["changes_trading_mode"] = False
    out["job_safety"]["writes_controls"] = False
    out["job_safety"]["grand_opening_not_performed"] = False
    out["job_safety"]["grand_opening_paper_done"] = True
    out["job_safety"]["paper_execution_closed"] = closed
    return out


def with_flatten_safety(session: Session, result: dict[str, Any]) -> dict[str, Any]:
    """Safety flags for the US-close flatten job. Internal simulator only."""
    out = with_job_safety(session, result)
    out["job_safety"]["fills"] = False
    out["job_safety"]["paper_fills"] = False
    out["job_safety"]["live_fills"] = False
    out["job_safety"]["internal_simulator_flatten"] = True
    out["job_safety"]["broker_fills"] = False
    out["job_safety"]["allow_list_not_required"] = True
    out["job_safety"]["flatten_as_if_there_were_positions"] = False
    out["job_safety"]["flatten_at"] = result.get("flatten_at") or "US_REGULAR_CASH_CLOSE"
    out["job_safety"]["flatten_not_at"] = result.get("flatten_not_at")
    out["job_safety"]["venue_scope"] = result.get("venue_scope")
    out["job_safety"]["split_flatten_clocks"] = True
    out["job_safety"]["risk_02f_bound"] = True
    out["job_safety"]["loads_broker_ports"] = False
    out["job_safety"]["changes_trading_mode"] = False
    return out
