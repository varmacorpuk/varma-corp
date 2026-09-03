"""Data ports. Fake delayed prices + news. No paid vendor. Stocks/equities only."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Protocol

from varma.clock import now_london


class DataPort(Protocol):
    def news(self, symbols: list[str]) -> list[dict[str, Any]]: ...

    def delayed_prices(self, symbols: list[str]) -> list[dict[str, Any]]: ...


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
            # --- Addendum E final strategy (ten US names, all USD) ---
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
            # --- Addendum M US-listed commodity ETPs (USD, equity/ETP path) ---
            "GLD": 232.0,
            "SLV": 27.5,
            "USO": 71.0,
            "UNG": 14.2,
            "CPER": 26.8,
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
