"""On-demand Trader paper-ticket proposal. No daemon.

Usage:
    python -m varma.routines.run_paper_trade_path

Chris Adeyemi · Trader proposes a legal allow-list paper buy. ControlEngine
permit/deny is authoritative. The internal paper simulator would fill after
Grand Opening PAPER. While PAPER execution is CLOSED the engine DENY
(PAPER_EXECUTION_CLOSED) and nothing fills. LIVE stays off. FakeLLM is not
called. Board-only via the API. GET /observability does not run this.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.addendum_f import TRADER_SLUG
from varma.db.engine import get_session_factory, init_db
from varma.db.seed import seed_if_empty
from varma.employees.runtime import EmployeeRuntime
from varma.meetings.handoff import get_employee


def run_paper_trade_path(session: Session, *, started_by: str = "cli", at=None) -> dict:
    trader = get_employee(session, TRADER_SLUG)
    return EmployeeRuntime(session, trader).propose_paper_ticket(
        at=at,
        started_by=started_by,
    )


def main() -> None:
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        seed_if_empty(session)
        print("Trader paper-ticket proposal — first paper-trade PATH")
        print("PAPER execution: CLOSED until Grand Opening")
        print("Daemon: False")
        print("AI called: False")
        print("Now Europe/London:", now_london().isoformat())
        result = run_paper_trade_path(session, started_by="cli")
        print("proposed:", result["proposed"])
        print("proposer:", result["proposer"]["display_name"])
        print("symbol:", result["order"]["symbol"])
        print("allowed:", result["allowed"])
        print("reason:", result["reason"])
        print("filled:", result["filled"])
        print("paper_fills:", result["paper_fills"])
        print("live_fills:", result["live_fills"])
        print("paper_execution:", result["paper_execution"])
        print("trading_mode:", result["trading_mode"])
        print("ai_called:", result["ai_called"])
        print("path_reached:", result["path"]["reached"])
    finally:
        session.close()


if __name__ == "__main__":
    main()
