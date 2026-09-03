"""Delayed OHLCV bars for the paper desk.

The existing feed is FakeMarketData (labelled delayed last prices). This
module turns those last prices into deterministic 1m/5m bars for the
open-scanner. No AI. No live quotes. Not a broker.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

import pandas as pd

from varma.clock import LONDON, as_london
from varma.controls.addendum_e import instrument_currency, instrument_quote_unit
from varma.ports.data import FakeMarketData

TIMEFRAME_MINUTES: dict[str, int] = {"1m": 1, "5m": 5}


class BarsProvider(Protocol):
    """Return OHLCV bars. Index is bar-open time, Europe/London, tz-aware."""

    def get_bars(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame: ...


def timeframe_minutes(timeframe: str) -> int:
    key = str(timeframe or "").strip().lower()
    if key not in TIMEFRAME_MINUTES:
        raise ValueError(f"unsupported timeframe {timeframe!r}")
    return TIMEFRAME_MINUTES[key]


def completed_bars(
    bars: pd.DataFrame,
    *,
    timeframe: str,
    as_of: datetime,
    latency_buffer_seconds: int,
) -> pd.DataFrame:
    """Keep only bars whose close + latency is at or before ``as_of``.

    Bar index is the open. A 1m bar opened at 14:31 completes at 14:32.
    """
    if bars is None or bars.empty:
        return bars if bars is not None else pd.DataFrame()
    minutes = timeframe_minutes(timeframe)
    as_of_l = as_london(as_of)
    complete_at = bars.index + pd.Timedelta(minutes=minutes) + pd.Timedelta(seconds=int(latency_buffer_seconds))
    return bars.loc[complete_at <= as_of_l].copy()


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "currency", "quote_unit"])


class ScriptedBars:
    """In-memory bar book for tests. Keys are (symbol, timeframe)."""

    def __init__(self, book: dict[tuple[str, str], pd.DataFrame] | None = None) -> None:
        self.book = book or {}

    def add(self, symbol: str, timeframe: str, bars: pd.DataFrame) -> None:
        self.book[(str(symbol), str(timeframe))] = bars

    def get_bars(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        df = self.book.get((str(symbol), str(timeframe)))
        if df is None or df.empty:
            return _empty_bars()
        out = df.sort_index()
        start_l = as_london(start)
        end_l = as_london(end)
        return out.loc[(out.index >= start_l) & (out.index <= end_l)].copy()


class FakeDelayedBars:
    """Deterministic delayed bars derived from FakeMarketData last prices.

    Labelled. Not live. Used by the on-demand scanner when no scripted
    book is injected. Same last prices as the paper quote path.
    """

    def __init__(self, *, data: FakeMarketData | None = None) -> None:
        self.data = data or FakeMarketData()

    def get_bars(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        minutes = timeframe_minutes(timeframe)
        start_l = as_london(start)
        end_l = as_london(end)
        if end_l < start_l:
            return _empty_bars()
        row = self.data.delayed_prices([symbol])[0]
        last = float(row.get("last") or 1.0)
        currency = str(row.get("currency") or instrument_currency(symbol))
        quote_unit = str(row.get("quote_unit") or instrument_quote_unit(symbol))
        step = timedelta(minutes=minutes)
        stamps: list[datetime] = []
        cursor = start_l.replace(second=0, microsecond=0)
        # Align to timeframe.
        cursor = cursor.replace(minute=(cursor.minute // minutes) * minutes)
        while cursor <= end_l:
            stamps.append(cursor)
            cursor = cursor + step
        if not stamps:
            return _empty_bars()
        opens: list[float] = []
        highs: list[float] = []
        lows: list[float] = []
        closes: list[float] = []
        volumes: list[float] = []
        for i, _ts in enumerate(stamps):
            # Quiet walk around last. Deterministic, no random, no AI.
            drift = 1.0 + ((i % 7) - 3) * 0.0004
            o = round(last * drift, 6)
            c = round(o * (1.0 + ((i % 5) - 2) * 0.0003), 6)
            h = round(max(o, c) * 1.0006, 6)
            lo = round(min(o, c) * 0.9994, 6)
            opens.append(o)
            highs.append(h)
            lows.append(lo)
            closes.append(c)
            volumes.append(float(10_000 + (i % 11) * 250))
        idx = pd.DatetimeIndex(stamps, tz=LONDON)
        return pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
                "currency": currency,
                "quote_unit": quote_unit,
            },
            index=idx,
        )


def bar_frame(
    stamps: list[datetime],
    rows: list[tuple[float, float, float, float, float]],
    *,
    currency: str = "USD",
    quote_unit: str = "USD",
) -> pd.DataFrame:
    """Helper for tests: rows are (open, high, low, close, volume)."""
    idx = pd.DatetimeIndex([as_london(ts) for ts in stamps], tz=LONDON)
    opens, highs, lows, closes, volumes = zip(*rows) if rows else ([], [], [], [], [])
    return pd.DataFrame(
        {
            "open": list(opens),
            "high": list(highs),
            "low": list(lows),
            "close": list(closes),
            "volume": list(volumes),
            "currency": currency,
            "quote_unit": quote_unit,
        },
        index=idx,
    )


def bars_to_public(df: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ts, row in df.iterrows():
        out.append(
            {
                "open_time": ts.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            }
        )
    return out
