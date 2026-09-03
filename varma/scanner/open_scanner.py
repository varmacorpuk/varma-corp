"""Deterministic NY-open scanner. On-demand. Paper only. No daemon.

Window: 14:32–15:00 Europe/London (first ~30 minutes after 14:30 NY open).

Trigger rules:
- Evaluate ONLY completed 1m/5m bars after an explicit latency buffer.
- Minute-2 (14:32) narrow early trigger: a completed 1m close crossing a
  pre-agreed meeting trigger level. Default level is PriorDay_close from
  ``technical_snapshot`` (not re-derived).
- From minute 5 (14:35) onward, also accept a completed 5m opening-range
  high/low break. News and indicator unanimity are not required.
- Fill: next 1m bar's open after the signal candle completes. Never the
  signal candle's own close.
- One candidate per name. Stop emitting once Addendum A book/order limits
  are exhausted. Does not place orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from varma.clock import LONDON, as_london, now_london
from varma.controls.addendum_a import MAX_DAILY_LOSS, MAX_ORDERS_PER_DAY, MAX_POSITION
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS, canonical_feed_symbol, desk_symbol
from varma.db.models import PaperPosition
from varma.paper.ledger import PaperLedger
from varma.paper.quote import mark_gbp, paper_order_economics
from varma.ports.bars import BarsProvider, completed_bars, timeframe_minutes
from varma.technical import technical_snapshot
from varma.technical.structure import compute_opening_range

SCAN_START = time(14, 32)
SCAN_END = time(15, 0)
US_OPEN_LONDON = time(14, 30)
DEFAULT_LATENCY_SECONDS = 60
DEFAULT_NOTIONAL_GBP = 150.0
SCANNER_SECTIONS = {"structure", "volume", "candles"}


@dataclass(frozen=True)
class OpenScannerCandidate:
    symbol: str
    feed_symbol: str
    side: str
    trigger_time: str
    entry_price: float
    stop: float | None
    target: float
    currency: str
    gbp_notional: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "feed_symbol": self.feed_symbol,
            "side": self.side,
            "trigger_time": self.trigger_time,
            "entry_price": self.entry_price,
            "stop": self.stop,
            "target": self.target,
            "currency": self.currency,
            "gbp_notional": self.gbp_notional,
            "reason": self.reason,
        }


def scan_window_for(as_of: datetime) -> tuple[datetime, datetime, datetime]:
    """Return (session_open, window_start, window_end) on the as-of London day."""
    d = as_london(as_of)
    session_open = datetime(d.year, d.month, d.day, US_OPEN_LONDON.hour, US_OPEN_LONDON.minute, tzinfo=LONDON)
    window_start = datetime(d.year, d.month, d.day, SCAN_START.hour, SCAN_START.minute, tzinfo=LONDON)
    window_end = datetime(d.year, d.month, d.day, SCAN_END.hour, SCAN_END.minute, tzinfo=LONDON)
    return session_open, window_start, window_end


def _crossing(prev_close: float, curr_close: float, level: float) -> str | None:
    if prev_close <= level < curr_close:
        return "buy"
    if prev_close >= level > curr_close:
        return "sell"
    return None


def _snapshot(symbol: str, bars, *, timeframe: str) -> dict[str, Any]:
    return technical_snapshot(
        symbol,
        bars,
        timeframe=timeframe,
        include_sections=SCANNER_SECTIONS,
        include_candlestick_patterns=False,
    )


class OpenScanner:
    """On-demand open-scanner. Deterministic. Does not place orders."""

    def __init__(
        self,
        *,
        latency_buffer_seconds: int = DEFAULT_LATENCY_SECONDS,
        notional_gbp: float = DEFAULT_NOTIONAL_GBP,
        meeting_trigger_levels: dict[str, float] | None = None,
        symbols: tuple[str, ...] | None = None,
    ) -> None:
        self.latency_buffer_seconds = int(latency_buffer_seconds)
        self.notional_gbp = float(notional_gbp)
        self.meeting_trigger_levels = {
            canonical_feed_symbol(k): float(v) for k, v in (meeting_trigger_levels or {}).items()
        }
        self.symbols = tuple(canonical_feed_symbol(s) for s in (symbols or ADDENDUM_E_SYMBOLS))

    def scan(
        self,
        session: Session,
        *,
        bar_provider: BarsProvider,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = as_london(as_of or now_london())
        session_open, window_start, window_end = scan_window_for(now)
        minute5 = session_open + timedelta(minutes=5)

        ledger = PaperLedger(session)
        ledger.ensure_account(at=now)
        orders_today = ledger.orders_today(at=now)
        pnl = ledger.london_day_pnl(at=now)

        stopped_reason: str | None = None
        if orders_today >= int(MAX_ORDERS_PER_DAY):
            stopped_reason = "MAX_ORDERS_PER_DAY"
        elif pnl <= -abs(float(MAX_DAILY_LOSS)):
            stopped_reason = "MAX_DAILY_LOSS"
        if stopped_reason:
            return []

        remaining = int(MAX_ORDERS_PER_DAY) - orders_today
        out: list[dict[str, Any]] = []
        emitted: set[str] = set()

        lookback_start = session_open - timedelta(days=1)
        one_m_end = window_end + timedelta(minutes=2)
        five_m_end = window_end + timedelta(minutes=5)

        for feed_symbol in self.symbols:
            if remaining <= 0:
                break
            if feed_symbol in emitted:
                continue
            if self._name_at_cap(session, feed_symbol):
                continue

            raw_1m = bar_provider.get_bars(
                symbol=feed_symbol,
                timeframe="1m",
                start=lookback_start,
                end=one_m_end,
            )
            raw_5m = bar_provider.get_bars(
                symbol=feed_symbol,
                timeframe="5m",
                start=session_open,
                end=five_m_end,
            )
            done_1m = completed_bars(
                raw_1m, timeframe="1m", as_of=now, latency_buffer_seconds=self.latency_buffer_seconds
            )
            done_5m = completed_bars(
                raw_5m, timeframe="5m", as_of=now, latency_buffer_seconds=self.latency_buffer_seconds
            )
            if done_1m is None or len(done_1m) < 2:
                continue

            trigger = self._trigger_level(feed_symbol, done_1m)
            if trigger is None:
                continue

            candidate = self._first_setup(
                feed_symbol=feed_symbol,
                done_1m=done_1m,
                raw_1m=raw_1m,
                done_5m=done_5m,
                trigger=trigger,
                window_start=window_start,
                window_end=window_end,
                minute5=minute5,
                as_of=now,
            )
            if candidate is None:
                continue
            out.append(candidate)
            emitted.add(feed_symbol)
            remaining -= 1

        return out

    def _trigger_level(self, feed_symbol: str, bars_1m) -> float | None:
        if feed_symbol in self.meeting_trigger_levels:
            return self.meeting_trigger_levels[feed_symbol]
        desk = desk_symbol(feed_symbol)
        if desk in self.meeting_trigger_levels:
            return self.meeting_trigger_levels[desk]
        snap = _snapshot(feed_symbol, bars_1m, timeframe="1m")
        level = snap.get("structure", {}).get("prior_day", {}).get("PriorDay_close")
        if level is None:
            return None
        return float(level)

    def _name_at_cap(self, session: Session, feed_symbol: str) -> bool:
        pos = session.get(PaperPosition, feed_symbol)
        if pos is None or pos.quantity == 0:
            return False
        existing = abs(float(pos.quantity)) * mark_gbp(feed_symbol)
        return existing >= float(MAX_POSITION) - 1e-9

    def _first_setup(
        self,
        *,
        feed_symbol: str,
        done_1m,
        raw_1m,
        done_5m,
        trigger: float,
        window_start: datetime,
        window_end: datetime,
        minute5: datetime,
        as_of: datetime,
    ) -> dict[str, Any] | None:
        one_min = timeframe_minutes("1m")
        for i in range(1, len(done_1m)):
            t_open = done_1m.index[i]
            t_complete = t_open + timedelta(minutes=one_min)
            if t_complete < window_start or t_complete > window_end:
                continue
            prev_close = float(done_1m["close"].iloc[i - 1])
            curr_close = float(done_1m["close"].iloc[i])
            side: str | None = None
            reasons: list[str] = []

            cross = _crossing(prev_close, curr_close, trigger)
            if cross:
                side = cross
                reasons.append(
                    f"1m close crossed meeting trigger {trigger:.6f} "
                    f"({prev_close:.6f} → {curr_close:.6f})"
                )

            if t_complete >= minute5 and done_5m is not None and not done_5m.empty:
                five_upto = done_5m.loc[done_5m.index + pd.Timedelta(minutes=5) <= t_complete]
                if five_upto.empty:
                    five_upto = done_5m
                # Toolkit OR: compute_opening_range works on the first completed 5m bar.
                # technical_snapshot needs ≥2 bars; fall back to the same toolkit helper.
                or_levels = compute_opening_range(five_upto, timeframe="5m")
                or_high = or_levels.get("OR_high")
                or_low = or_levels.get("OR_low")
                or_break = None
                if len(five_upto) >= 2:
                    snap5 = _snapshot(feed_symbol, five_upto, timeframe="5m")
                    or_break = snap5.get("candles", {}).get("or_break")
                    struct_or = snap5.get("structure", {}).get("opening_range") or {}
                    or_high = struct_or.get("OR_high", or_high)
                    or_low = struct_or.get("OR_low", or_low)
                if or_high is not None and curr_close > float(or_high):
                    side = side or "buy"
                    reasons.append(f"1m close broke 5m OR high {float(or_high):.6f}")
                elif or_low is not None and curr_close < float(or_low):
                    side = side or "sell"
                    reasons.append(f"1m close broke 5m OR low {float(or_low):.6f}")
                elif isinstance(or_break, dict) and or_break.get("type") in {"break_up", "break_down"}:
                    side = side or ("buy" if or_break["type"] == "break_up" else "sell")
                    reasons.append(f"5m opening-range {or_break['type']}")

            if side is None:
                continue

            next_open, next_ts = _next_bar_open(raw_1m, t_open, as_of)
            if next_open is None or next_ts is None:
                continue

            upto = done_1m.iloc[: i + 1]
            snap1 = _snapshot(feed_symbol, upto, timeframe="1m")
            or_high_1 = snap1.get("structure", {}).get("opening_range", {}).get("OR_high")
            or_low_1 = snap1.get("structure", {}).get("opening_range", {}).get("OR_low")
            rel_vol = snap1.get("volume", {}).get("RelVol")
            stop = float(or_low_1) if side == "buy" and or_low_1 is not None else (
                float(or_high_1) if side == "sell" and or_high_1 is not None else None
            )

            currency = str(done_1m["currency"].iloc[i]) if "currency" in done_1m.columns else "USD"
            quote_unit = str(done_1m["quote_unit"].iloc[i]) if "quote_unit" in done_1m.columns else "USD"
            econ = paper_order_economics(
                {
                    "symbol": feed_symbol,
                    "side": side,
                    "notional_gbp": min(self.notional_gbp, float(MAX_POSITION)),
                },
                at=next_ts,
                price_row={"last": float(next_open), "currency": currency, "quote_unit": quote_unit},
                max_position_gbp=float(MAX_POSITION),
            )
            if econ.cap_check_gbp > float(MAX_POSITION) + 1e-9:
                continue
            if econ.notional_gbp <= 0:
                continue

            entry = float(next_open)
            if stop is None or (side == "buy" and stop >= entry) or (side == "sell" and stop <= entry):
                stop = entry * (0.995 if side == "buy" else 1.005)
            risk = abs(entry - float(stop))
            target = entry + risk if side == "buy" else entry - risk

            reasons.append(f"RelVol={rel_vol}")
            reasons.append(f"structural stop={stop:.6f}")
            reasons.append(f"next-bar open fill at {next_ts.isoformat()} (not signal close {curr_close:.6f})")

            cand = OpenScannerCandidate(
                symbol=desk_symbol(feed_symbol),
                feed_symbol=feed_symbol,
                side=side,
                trigger_time=t_complete.isoformat(),
                entry_price=round(entry, 6),
                stop=round(float(stop), 6),
                target=round(float(target), 6),
                currency=str(econ.quote_currency),
                gbp_notional=float(econ.notional_gbp),
                reason="; ".join(reasons),
            )
            return cand.to_dict()
        return None


def _next_bar_open(raw_1m, signal_open: datetime, as_of: datetime) -> tuple[float | None, datetime | None]:
    """Next 1m bar's open after the signal bar. Open may be from an unfinished bar."""
    if raw_1m is None or raw_1m.empty:
        return None, None
    later = raw_1m.loc[raw_1m.index > signal_open]
    if later.empty:
        return None, None
    next_ts = later.index[0]
    if as_london(next_ts) > as_london(as_of):
        return None, None
    return float(later["open"].iloc[0]), as_london(next_ts)


def scan_result_envelope(
    candidates: list[dict[str, Any]],
    *,
    as_of: datetime,
    latency_buffer_seconds: int,
) -> dict[str, Any]:
    session_open, window_start, window_end = scan_window_for(as_of)
    return {
        "daemon": False,
        "paper_only": True,
        "live_blocked": True,
        "places_orders": False,
        "fills": False,
        "futures": False,
        "as_of": as_london(as_of).isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "session_open": session_open.isoformat(),
        "latency_buffer_seconds": int(latency_buffer_seconds),
        "symbols_scanned": list(ADDENDUM_E_SYMBOLS),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "note": (
            "On-demand NY-open scanner. Completed bars only. Next-bar open fill. "
            "Does not place orders. LIVE stays BLOCKED."
        ),
    }
