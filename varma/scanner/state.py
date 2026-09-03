"""Per-name US-open scanner state and duplicate-entry prevention.

State is in-memory for one scan plus Evidence for the same NY session so a
later on-demand run does not re-enter a name that already fired.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.db.models import Evidence, PaperPosition
from varma.scanner.bars import ny_session_open

EVIDENCE_KIND = "us_open_scanner_name_state"


@dataclass
class NameState:
    symbol: str
    entered: bool = False
    signal_close: float | None = None
    fill_price: float | None = None
    fill_order_id: str | None = None
    reason: str = ""
    opening_range: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "entered": self.entered,
            "signal_close": self.signal_close,
            "fill_price": self.fill_price,
            "fill_order_id": self.fill_order_id,
            "reason": self.reason,
            "opening_range": dict(self.opening_range),
        }


class ScannerBook:
    """Per-name book for one NY session. Duplicate entries are refused."""

    def __init__(self, session: Session | None = None, *, at: datetime | None = None) -> None:
        self.session = session
        self.at = at or now_london()
        self.names: dict[str, NameState] = {}
        if session is not None:
            self._hydrate(session, self.at)

    def session_key(self, at: datetime | None = None) -> str:
        return ny_session_open(at or self.at).isoformat()

    def state(self, symbol: str) -> NameState:
        row = self.names.get(symbol)
        if row is None:
            row = NameState(symbol=symbol)
            self.names[symbol] = row
        return row

    def already_entered(self, symbol: str) -> bool:
        if self.state(symbol).entered:
            return True
        if self.session is None:
            return False
        pos = self.session.get(PaperPosition, symbol)
        return bool(pos is not None and pos.quantity != 0)

    def open_position_count(self) -> int:
        return sum(1 for row in self.names.values() if row.entered)

    def mark_entered(
        self,
        symbol: str,
        *,
        signal_close: float,
        fill_price: float,
        fill_order_id: str | None,
        opening_range: dict[str, Any] | None = None,
    ) -> NameState:
        row = self.state(symbol)
        row.entered = True
        row.signal_close = signal_close
        row.fill_price = fill_price
        row.fill_order_id = fill_order_id
        row.reason = "ENTERED"
        if opening_range:
            row.opening_range = dict(opening_range)
        if self.session is not None:
            self._persist(self.session, row)
        return row

    def mark_blocked(self, symbol: str, reason: str) -> NameState:
        row = self.state(symbol)
        row.reason = reason
        return row

    def _hydrate(self, session: Session, at: datetime) -> None:
        key = self.session_key(at)
        rows = (
            session.query(Evidence)
            .filter(Evidence.kind == EVIDENCE_KIND)
            .order_by(Evidence.created_at.asc())
            .all()
        )
        for ev in rows:
            try:
                payload = json.loads(ev.payload)
            except json.JSONDecodeError:
                continue
            if payload.get("ny_session") != key:
                continue
            symbol = str(payload.get("symbol") or "")
            if not symbol:
                continue
            self.names[symbol] = NameState(
                symbol=symbol,
                entered=bool(payload.get("entered")),
                signal_close=payload.get("signal_close"),
                fill_price=payload.get("fill_price"),
                fill_order_id=payload.get("fill_order_id"),
                reason=str(payload.get("reason") or ""),
                opening_range=dict(payload.get("opening_range") or {}),
            )

    def _persist(self, session: Session, row: NameState) -> None:
        payload = {
            **row.to_dict(),
            "ny_session": self.session_key(),
            "exchange_tz": "America/New_York",
            "paper_only": True,
            "live": False,
        }
        session.add(
            Evidence(
                kind=EVIDENCE_KIND,
                actor="us-open-scanner",
                payload=json.dumps(payload, default=str),
                created_at=now_london(),
            )
        )
        session.commit()
