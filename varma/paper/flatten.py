"""Flatten ALL paper before US regular cash close (Board Addendum C 2026-08-27).

Internal PAPER FILL SIMULATOR only. Not BROKER_PAPER. Not LIVE.
Board Addendum I: do not run flatten-as-if-there-were-positions. While PAPER
execution is CLOSED there are no positions to flatten; this is a no-op.
GET /observability must not call this.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import describe_flatten_us_close, now_london
from varma.controls.addendum_c import (
    ADDENDUM_C_LABEL,
    FLATTEN_AT,
    FLATTEN_NOT_AT,
    addendum_c_public,
    us_regular_cash_close_london,
)
from varma.controls.addendum_i import ADDENDUM_I_LABEL, paper_execution_is_closed
from varma.controls.engine import BROKER_PAPER_LOADED, LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import Evidence, PaperFlattenRun, PaperPosition
from varma.paper.ledger import PaperLedger
from varma.paper.simulator import PaperFillSimulator
from varma.ports.execution import LIVE_PORT_LOADED


def flatten_all_paper(
    session: Session,
    *,
    actor_id: str,
    at: datetime | None = None,
    started_by: str = "board-member",
) -> dict[str, Any]:
    """Cancel open paper orders and close open paper positions via the simulator.

    Does not load BROKER_PAPER or LIVE. Does not write trading_mode or allow-list.
    Does not require allow-list membership.
    Board Addendum I: do not run flatten-as-if-there-were-positions. While
    PAPER execution is CLOSED this is a no-op (no fills).
    """
    now = at or now_london()
    engine = ControlEngine(session)
    before_mode = engine.state().trading_mode
    before_allow = engine.allow_list_symbols()
    ledger = PaperLedger(session)
    ledger.ensure_account(at=now)
    cancelled = ledger.cancel_open_paper_orders(
        reason="FLATTEN_BEFORE_US_REGULAR_CASH_CLOSE",
        at=now,
    )
    closed_symbols: list[str] = []
    flatten_fills = 0
    firm_closed = paper_execution_is_closed(session)
    if not firm_closed:
        sim = PaperFillSimulator(session)
        for pos in list(session.query(PaperPosition).all()):
            if pos.quantity == 0:
                continue
            side = "sell" if pos.quantity > 0 else "buy"
            qty = abs(pos.quantity)
            decision = sim.fill(
                actor_id=actor_id,
                order={
                    "symbol": pos.symbol,
                    "side": side,
                    "quantity": qty,
                    "execution_port": "SIMULATOR",
                },
                at=now,
                is_flatten=True,
            )
            if decision.allowed:
                flatten_fills += 1
                closed_symbols.append(pos.symbol)
            else:
                session.add(
                    Evidence(
                        kind="paper_flatten_fill_denied",
                        actor=actor_id,
                        payload=json.dumps(
                            {"symbol": pos.symbol, "reason": decision.reason},
                            default=str,
                        ),
                        created_at=now,
                    )
                )
    remaining = session.query(PaperPosition).filter(PaperPosition.quantity != 0).count()
    after_mode = engine.state().trading_mode
    run = PaperFlattenRun(
        ran_at=now,
        timezone="Europe/London",
        flatten_at=FLATTEN_AT,
        flatten_not_at=FLATTEN_NOT_AT,
        cancelled_open_paper_orders=cancelled,
        closed_positions=len(closed_symbols),
        flatten_fills=flatten_fills,
        positions_remaining=remaining,
        trading_mode_before=before_mode,
        trading_mode_after=after_mode,
        allow_list_empty=len(before_allow) == 0,
        daemon=False,
        writes_controls=False,
        broker_paper_loaded=bool(BROKER_PAPER_LOADED),
        live_loaded=bool(LIVE_ADAPTER_LOADED) or bool(LIVE_PORT_LOADED),
        started_by=started_by,
        notes=describe_flatten_us_close(),
    )
    session.add(run)
    session.flush()
    session.add(
        Evidence(
            kind="paper_flatten_us_close",
            actor=actor_id,
            payload=json.dumps(
                {
                    "run_id": run.id,
                    "flatten_at": FLATTEN_AT,
                    "flatten_not_at": FLATTEN_NOT_AT,
                    "cancelled_open_paper_orders": cancelled,
                    "closed_positions": len(closed_symbols),
                    "closed_symbols": closed_symbols,
                    "flatten_fills": flatten_fills,
                    "positions_remaining": remaining,
                    "us_regular_cash_close_london": us_regular_cash_close_london(now).isoformat(),
                    "broker": False,
                    "live_loaded": False,
                    "paper_execution_closed": firm_closed,
                    "flatten_as_if_there_were_positions": False,
                    "source": ADDENDUM_C_LABEL,
                    "addendum_i": ADDENDUM_I_LABEL,
                },
                default=str,
            ),
            created_at=now,
        )
    )
    session.commit()
    return flatten_run_to_dict(run, extra={
        "closed_symbols": closed_symbols,
        "addendum": addendum_c_public(now),
        "broker": False,
        "loads_broker_ports": False,
        "changes_trading_mode": after_mode != before_mode,
        "live_fills": False,
        "internal_simulator_flatten": True,
        "allow_list_unchanged": engine.allow_list_symbols() == before_allow,
        "trading_mode": after_mode,
        "paper_execution_closed": firm_closed,
        "flatten_as_if_there_were_positions": False,
        "description": describe_flatten_us_close(),
    })


def flatten_run_to_dict(row: PaperFlattenRun, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": row.id,
        "ran_at": row.ran_at.isoformat() if row.ran_at else None,
        "timezone": row.timezone,
        "flatten_at": row.flatten_at,
        "flatten_not_at": row.flatten_not_at,
        "flatten_at_london_cash_close": False,
        "cancelled_open_paper_orders": row.cancelled_open_paper_orders,
        "closed_positions": row.closed_positions,
        "flatten_fills": row.flatten_fills,
        "positions_remaining": row.positions_remaining,
        "trading_mode_before": row.trading_mode_before,
        "trading_mode_after": row.trading_mode_after,
        "allow_list_empty": bool(row.allow_list_empty),
        "daemon": bool(row.daemon),
        "writes_controls": bool(row.writes_controls),
        "broker_paper_loaded": bool(row.broker_paper_loaded),
        "live_loaded": bool(row.live_loaded),
        "started_by": row.started_by,
        "notes": row.notes,
        "source": ADDENDUM_C_LABEL,
        "is_live": False,
        "broker": False,
    }
    if extra:
        data.update(extra)
    return data
