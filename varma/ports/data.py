"""Data ports. Fake delayed prices + news + OHLCV. No paid vendor."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol

from varma.clock import now_london


class DataPort(Protocol):
    def news(self, symbols: list[str]) -> list[dict[str, Any]]: ...

    def delayed_prices(self, symbols: list[str]) -> list[dict[str, Any]]: ...

    def ohlcv(
        self,
        symbols: list[str],
        *,
        timeframe: str,
        session_open: datetime,
        now: datetime | None = None,
        count: int = 32,
    ) -> list[dict[str, Any]]: ...


class FakeMarketData:
    """TEMPORARY DEVELOPMENT DEFAULT data. Labelled. Not live. Not gold."""

    def __init__(self, *, stale: bool = False) -> None:
        self.stale = stale

    def news(self, symbols: list[str]) -> list[dict[str, Any]]:
        now = now_london()
        published = now - timedelta(hours=26 if self.stale else 3)
        items = [
            {
                "headline": "US listed tech mixed in delayed session wrap",
                "summary": "Commentary only. Not an execution instruction.",
                "source": "fake-wire://overnight-wrap",
                "published_at": published.isoformat(),
                "symbols": [s for s in symbols if s in {"AAPL", "MSFT"}],
                "retrieved_at": now.isoformat(),
            },
            {
                "headline": "London-listed energy and pharma: routine overnight notes",
                "summary": "No material corporate action in this fake feed.",
                "source": "fake-wire://lse-overnight",
                "published_at": (published if not self.stale else now - timedelta(hours=30)).isoformat(),
                "symbols": [s for s in symbols if s.endswith(".L")],
                "retrieved_at": now.isoformat(),
            },
        ]
        return items

    def delayed_prices(self, symbols: list[str]) -> list[dict[str, Any]]:
        now = now_london()
        observed = now - timedelta(hours=28 if self.stale else 4)
        last_px: dict[str, float] = {
            # --- Addendum E/L final strategy (15 US names, all USD) ---
            "NVDA": 120.0,
            "AAPL": 190.0,
            "GOOGL": 160.0,
            "MSFT": 410.0,
            "AMZN": 180.0,
            "SPCX": 149.0,
            "AVGO": 349.0,
            "META": 618.0,
            "TSLA": 380.0,
            "BRK-B": 507.0,
            # --- Addendum L commodity ETP proxies (US-listed, USD) ---
            "GLD": 230.0,
            "SLV": 28.0,
            "USO": 75.0,
            "UNG": 14.0,
            "CPER": 28.0,
            # --- Legacy LSE names (historical paper book, GBP) ---
            # 3409.3p delayed ≈ 34.093 GBP.
            "SHEL.L": 34.093,
            "AZN.L": 112.0,
            "ULVR.L": 45.0,
            # --- Former Addendum E names kept for test backward compat ---
            "JPM": 200.0,
            "JNJ": 150.0,
        }
        out = []
        for s in symbols:
            out.append(
                {
                    "symbol": s,
                    "last": last_px.get(s, 1.0),
                    "currency": "GBP" if s.endswith(".L") else "USD",
                    # LSE last above is already pounds (pence/100). quote_unit GBP
                    # prevents a second /100. A GBX last (e.g. 3281p) converts separately.
                    "quote_unit": "GBP" if s.endswith(".L") else "USD",
                    "source": "fake-delayed-snapshot",
                    "observed_at": observed.isoformat(),
                    "delay_label": "DELAYED — TEMPORARY DEVELOPMENT DEFAULT",
                    "not_an_execution_quote": True,
                }
            )
        return out

    def ohlcv(
        self,
        symbols: list[str],
        *,
        timeframe: str,
        session_open: datetime,
        now: datetime | None = None,
        count: int = 32,
    ) -> list[dict[str, Any]]:
        """Deterministic delayed 1m/5m OHLCV. Not live. Not a vendor contract.

        Bars carry explicit America/New_York exchange timestamps. Completeness
        is decided by the scanner (close_time + latency buffer), never here
        by wall-clock guesswork on an unfinished candle.
        """
        clock = now or now_london()
        minutes = 5 if str(timeframe) == "5m" else 1
        last_px = {row["symbol"]: float(row["last"]) for row in self.delayed_prices(symbols)}
        out: list[dict[str, Any]] = []
        for symbol in symbols:
            mid = last_px.get(symbol, 1.0)
            open_at = session_open
            for i in range(max(1, int(count))):
                close_at = open_at + timedelta(minutes=minutes)
                # Tiny deterministic variation so bars are not identical.
                drift = ((i % 5) - 2) * 0.0004 * mid
                o = mid + drift
                c = mid + drift * 0.5
                high = max(o, c) + 0.0008 * mid
                low = min(o, c) - 0.0008 * mid
                volume = 100_000 + (i * 1_250)
                out.append(
                    {
                        "symbol": symbol,
                        "timeframe": "5m" if minutes == 5 else "1m",
                        "open_time": open_at,
                        "close_time": close_at,
                        "exchange_tz": "America/New_York",
                        "open": round(o, 6),
                        "high": round(high, 6),
                        "low": round(low, 6),
                        "close": round(c, 6),
                        "volume": float(volume),
                        "complete": close_at <= clock,
                        "retrieved_at": clock,
                        "source": "fake-delayed-ohlcv",
                        "delay_label": "DELAYED — TEMPORARY DEVELOPMENT DEFAULT",
                        "currency": "GBP" if symbol.endswith(".L") else "USD",
                        "quote_unit": "GBP" if symbol.endswith(".L") else "USD",
                    }
                )
                open_at = close_at
        return out
