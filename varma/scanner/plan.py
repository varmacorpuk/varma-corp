"""Pre-agreed US-open plan levels from the 14:00 Europe/London meeting.

Levels are frozen at accept time. The scanner must not mutate them, chase
a later print, or invent a level that was not on the meeting plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from varma.clock import LONDON, as_london, now_london
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS, feed_symbol

MEETING_LABEL = "14:00 Europe/London opening plan"
MEETING_HOUR = 14
MEETING_MINUTE = 0


@dataclass(frozen=True)
class NamePlan:
    symbol: str
    side: str
    level: float
    stop: float
    target: float | None = None
    notional_gbp: float = 50.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "level": self.level,
            "stop": self.stop,
            "target": self.target,
            "notional_gbp": self.notional_gbp,
            "frozen": True,
        }


@dataclass(frozen=True)
class OpeningPlan:
    as_of: datetime
    levels: tuple[NamePlan, ...]
    meeting: str = MEETING_LABEL
    timezone: str = "Europe/London"
    frozen: bool = True
    source: str = "14:00-meeting"

    def for_symbol(self, symbol: str) -> NamePlan | None:
        key = feed_symbol(symbol)
        for row in self.levels:
            if row.symbol == key or row.symbol == symbol:
                return row
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "meeting": self.meeting,
            "timezone": self.timezone,
            "as_of": self.as_of.isoformat(),
            "frozen": self.frozen,
            "source": self.source,
            "levels": [row.to_dict() for row in self.levels],
            "symbols": [row.symbol for row in self.levels],
        }


def freeze_opening_plan(
    levels: Iterable[Mapping[str, Any] | NamePlan],
    *,
    as_of: datetime | None = None,
    universe: Iterable[str] = ADDENDUM_E_SYMBOLS,
) -> OpeningPlan:
    """Copy and freeze meeting levels. Names outside the 15-name book are dropped."""
    allowed = {feed_symbol(s) for s in universe}
    frozen: list[NamePlan] = []
    seen: set[str] = set()
    for raw in levels:
        row = raw if isinstance(raw, NamePlan) else _parse_name_plan(raw)
        symbol = feed_symbol(row.symbol)
        if symbol not in allowed or symbol in seen:
            continue
        if row.level <= 0 or row.stop <= 0:
            continue
        side = row.side if row.side in {"buy", "sell"} else "buy"
        frozen.append(
            NamePlan(
                symbol=symbol,
                side=side,
                level=float(row.level),
                stop=float(row.stop),
                target=None if row.target is None else float(row.target),
                notional_gbp=float(row.notional_gbp),
            )
        )
        seen.add(symbol)
    when = as_london(as_of or now_london())
    return OpeningPlan(as_of=when, levels=tuple(frozen), frozen=True)


def _parse_name_plan(raw: Mapping[str, Any]) -> NamePlan:
    target = raw.get("target")
    return NamePlan(
        symbol=str(raw.get("symbol") or ""),
        side=str(raw.get("side") or "buy").lower(),
        level=float(raw.get("level") or 0),
        stop=float(raw.get("stop") or 0),
        target=None if target in (None, "") else float(target),
        notional_gbp=float(raw.get("notional_gbp") or 50.0),
    )


def fourteen_hundred_london(dt: datetime | None = None) -> datetime:
    d = as_london(dt or now_london())
    return datetime(d.year, d.month, d.day, MEETING_HOUR, MEETING_MINUTE, tzinfo=LONDON)
