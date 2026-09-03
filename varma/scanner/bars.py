"""Completed-bar helpers for the US-open PAPER scanner.

Evaluate finished 1m/5m candles only. Every bar must carry an explicit
America/New_York exchange timestamp. A latency buffer sits after close
before the bar is eligible. Unfinished candles are never used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
DEFAULT_LATENCY_BUFFER = timedelta(seconds=2)
ONE_MINUTE = timedelta(minutes=1)
FIVE_MINUTES = timedelta(minutes=5)
SCAN_WINDOW = timedelta(minutes=32)
NY_OPEN = (9, 30)


def as_new_york(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=NEW_YORK)
    return dt.astimezone(NEW_YORK)


def ny_session_open(dt: datetime) -> datetime:
    """09:30 America/New_York on the calendar day of *dt* (converted to NY)."""
    ny = as_new_york(dt)
    hour, minute = NY_OPEN
    return datetime(ny.year, ny.month, ny.day, hour, minute, tzinfo=NEW_YORK)


def ny_scan_end(dt: datetime) -> datetime:
    return ny_session_open(dt) + SCAN_WINDOW


def in_us_open_scan_window(dt: datetime) -> bool:
    now = as_new_york(dt)
    start = ny_session_open(now)
    return start <= now <= ny_scan_end(now)


def minutes_from_ny_open(dt: datetime) -> float:
    now = as_new_york(dt)
    start = ny_session_open(now)
    return (now - start).total_seconds() / 60.0


def timeframe_delta(timeframe: str) -> timedelta:
    return FIVE_MINUTES if str(timeframe) == "5m" else ONE_MINUTE


@dataclass(frozen=True)
class OhlcvBar:
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    exchange_tz: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    complete: bool
    retrieved_at: datetime
    source: str
    currency: str = "USD"
    quote_unit: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open_time": self.open_time.isoformat(),
            "close_time": self.close_time.isoformat(),
            "exchange_tz": self.exchange_tz,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "complete": self.complete,
            "retrieved_at": self.retrieved_at.isoformat(),
            "source": self.source,
            "currency": self.currency,
            "quote_unit": self.quote_unit,
        }

    def price_row(self, *, last: float | None = None) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "last": float(self.open if last is None else last),
            "currency": self.currency,
            "quote_unit": self.quote_unit,
        }


def parse_bar(raw: dict[str, Any]) -> OhlcvBar:
    open_time = _as_dt(raw["open_time"])
    close_time = _as_dt(raw["close_time"])
    retrieved = _as_dt(raw.get("retrieved_at") or close_time)
    return OhlcvBar(
        symbol=str(raw["symbol"]),
        timeframe=str(raw.get("timeframe") or "1m"),
        open_time=as_new_york(open_time),
        close_time=as_new_york(close_time),
        exchange_tz=str(raw.get("exchange_tz") or "America/New_York"),
        open=float(raw["open"]),
        high=float(raw["high"]),
        low=float(raw["low"]),
        close=float(raw["close"]),
        volume=float(raw.get("volume") or 0),
        complete=bool(raw.get("complete", False)),
        retrieved_at=retrieved,
        source=str(raw.get("source") or "unknown"),
        currency=str(raw.get("currency") or "USD"),
        quote_unit=str(raw.get("quote_unit") or "USD"),
    )


def _as_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def is_completed_bar(
    bar: OhlcvBar,
    now: datetime,
    *,
    latency_buffer: timedelta = DEFAULT_LATENCY_BUFFER,
) -> bool:
    """True only when the exchange close is in the past plus the latency buffer.

    An unfinished candle (close_time in the future, or complete=False) is
    never eligible, even if a feed marked it complete by mistake.
    """
    clock = as_new_york(now)
    if not bar.complete:
        return False
    if bar.close_time > clock:
        return False
    return clock >= bar.close_time + latency_buffer


def completed_bars(
    bars: Iterable[OhlcvBar | dict[str, Any]],
    now: datetime,
    *,
    latency_buffer: timedelta = DEFAULT_LATENCY_BUFFER,
    timeframe: str | None = None,
    symbol: str | None = None,
) -> list[OhlcvBar]:
    out: list[OhlcvBar] = []
    for raw in bars:
        bar = raw if isinstance(raw, OhlcvBar) else parse_bar(raw)
        if symbol is not None and bar.symbol != symbol:
            continue
        if timeframe is not None and bar.timeframe != timeframe:
            continue
        if is_completed_bar(bar, now, latency_buffer=latency_buffer):
            out.append(bar)
    out.sort(key=lambda b: b.close_time)
    return out


def next_available_bar(
    bars: Iterable[OhlcvBar],
    signal: OhlcvBar,
) -> OhlcvBar | None:
    """First bar whose open is at/after the signal close. Never the signal itself."""
    later = [
        bar
        for bar in bars
        if bar.symbol == signal.symbol
        and bar.timeframe == signal.timeframe
        and bar.open_time >= signal.close_time
        and bar.open_time != signal.open_time
    ]
    later.sort(key=lambda b: b.open_time)
    return later[0] if later else None


def opening_range(bars: Iterable[OhlcvBar]) -> dict[str, float | None]:
    rows = list(bars)
    if not rows:
        return {"OR_high": None, "OR_low": None, "bar_count": 0}
    return {
        "OR_high": max(b.high for b in rows),
        "OR_low": min(b.low for b in rows),
        "bar_count": len(rows),
    }


def resolve_stop_target(
    bar: OhlcvBar,
    *,
    side: str,
    stop: float,
    target: float | None,
) -> str | None:
    """If stop and target both print in one OHLC bar, assume adverse/stop-first."""
    direction = str(side or "buy").lower()
    hit_stop = bar.low <= stop if direction == "buy" else bar.high >= stop
    hit_target = False
    if target is not None:
        hit_target = bar.high >= target if direction == "buy" else bar.low <= target
    if hit_stop and hit_target:
        return "stop"
    if hit_stop:
        return "stop"
    if hit_target:
        return "target"
    return None


def bars_to_frame_rows(bars: Iterable[OhlcvBar]) -> list[dict[str, Any]]:
    """Rows suitable for a DatetimeIndex OHLCV frame (technical toolkit)."""
    rows = []
    for bar in bars:
        rows.append(
            {
                "timestamp": bar.close_time,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
        )
    return rows
