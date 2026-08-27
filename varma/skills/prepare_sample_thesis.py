"""SAMPLE thesis for Challenge. Not a live trade. Not an order."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.engine import ControlEngine
from varma.db.models import SampleThesis

SAMPLE_LABEL = "SAMPLE — not a live trade"
SAMPLE_SYMBOL = "AAPL"  # TEMPORARY DEVELOPMENT DEFAULT watchlist item, not allow-list


def thesis_to_dict(row: SampleThesis) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "statement": row.statement,
        "symbol": row.symbol,
        "venue": row.venue,
        "asset_class": row.asset_class,
        "label": row.label,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "trading_mode_at_creation": row.trading_mode_at_creation,
        "no_execution_authority": row.no_execution_authority,
        "is_live_trade": row.is_live_trade,
        "notes": row.notes,
    }


def create_sample_thesis(session: Session) -> SampleThesis:
    state = ControlEngine(session).snapshot()
    row = SampleThesis(
        title="SAMPLE thesis — delayed AAPL snapshot is not an execution case",
        statement=(
            "SAMPLE only, not a live trade: AAPL appears on the TEMPORARY DEVELOPMENT DEFAULT "
            "watchlist. A delayed fake snapshot exists. Challenge should stress-test whether this "
            "could ever be treated as an order. It must not. Watchlist is not the allow-list. "
            "trading_mode is LIVE_BLOCKED. Numeric limits are unset. Gold is not in this thesis."
        ),
        symbol=SAMPLE_SYMBOL,
        venue="NASDAQ",
        asset_class="listed_equity",
        label=SAMPLE_LABEL,
        created_by="sample-demo",
        created_at=now_london(),
        trading_mode_at_creation=state["trading_mode"],
        no_execution_authority=True,
        is_live_trade=False,
        notes=(
            "TEMPORARY SAMPLE artefact so Challenge has something to challenge. "
            "Not Board-approved universe membership. Not paper. Not LIVE."
        ),
    )
    session.add(row)
    session.commit()
    return row
