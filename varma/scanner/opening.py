"""Deterministic on-demand US-open PAPER scanner.

Operates on the final 15-name US book from New York open through the first
32 minutes. Completed 1m/5m bars only. Pre-agreed 14:00 plan levels. Next-bar
entry, never hindsight at the signal close. PAPER path only. LIVE stays blocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Iterable

from sqlalchemy.orm import Session

from varma.clock import now_london
from varma.controls.addendum_e import (
    ADDENDUM_E_COMMODITY_ETP_SYMBOLS,
    ADDENDUM_E_SYMBOLS,
    feed_symbol,
    instrument_asset_class,
    is_commodity_etp,
)
from varma.controls.addendum_f import TRADER_SLUG
from varma.controls.engine import BROKER_PAPER_LOADED, LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import Employee, Evidence
from varma.paper.ledger import PaperLedger
from varma.ports.data import FakeMarketData
from varma.scanner.bars import (
    DEFAULT_LATENCY_BUFFER,
    OhlcvBar,
    as_new_york,
    bars_to_frame_rows,
    completed_bars,
    in_us_open_scan_window,
    minutes_from_ny_open,
    next_available_bar,
    ny_scan_end,
    ny_session_open,
    opening_range,
    parse_bar,
    resolve_stop_target,
)
from varma.scanner.plan import NamePlan, OpeningPlan, freeze_opening_plan
from varma.scanner.state import ScannerBook

SCANNER_VERSION = "1.0.0"
SCAN_MINUTES = 32
MINUTE_2 = 2
MINUTE_5 = 5
DEFAULT_MAX_CONCURRENT = 1
DEFAULT_NOTIONAL_GBP = 50.0
EVIDENCE_KIND = "us_open_scanner_run"

# Concurrent-position cap is a scanner proposal default, not a ControlEngine lock.
# The engine still enforces £200/name, £50 daily loss, 6 orders, cash, LIVE_BLOCKED.


def _technical_context(bars: list[OhlcvBar]) -> dict[str, Any]:
    """Descriptive toolkit snapshot. Never a unanimity gate. Never requires news."""
    if len(bars) < 3:
        return {
            "available": False,
            "descriptive_only": True,
            "unanimity_required": False,
            "news_required": False,
            "note": "Insufficient completed bars for a toolkit snapshot.",
        }
    try:
        import pandas as pd

        from varma.technical import technical_snapshot

        rows = bars_to_frame_rows(bars)
        frame = pd.DataFrame(rows).set_index("timestamp")
        snap = technical_snapshot(bars[0].symbol, frame, timeframe=bars[0].timeframe)
        return {
            "available": True,
            "descriptive_only": True,
            "unanimity_required": False,
            "news_required": False,
            "snapshot": snap,
        }
    except Exception as exc:  # toolkit is context only — never block a valid trigger
        return {
            "available": False,
            "descriptive_only": True,
            "unanimity_required": False,
            "news_required": False,
            "error": str(exc),
        }


def _volume_context(bars: list[OhlcvBar]) -> dict[str, Any]:
    if not bars:
        return {"ok": False, "reason": "NO_VOLUME_CONTEXT", "volume": 0.0}
    last = bars[-1]
    if last.volume <= 0:
        return {"ok": False, "reason": "ZERO_VOLUME", "volume": 0.0}
    prior = [b.volume for b in bars[:-1] if b.volume > 0]
    avg = sum(prior) / len(prior) if prior else last.volume
    rel = last.volume / avg if avg else None
    return {
        "ok": True,
        "volume": last.volume,
        "avg_volume": avg,
        "relative_volume": None if rel is None else round(rel, 4),
        "liquidity_ok": last.volume > 0,
    }


def _structural_stop_ok(plan: NamePlan, signal: OhlcvBar, or_levels: dict[str, Any]) -> dict[str, Any]:
    if plan.stop <= 0:
        return {"ok": False, "reason": "MISSING_STRUCTURAL_STOP"}
    if plan.side == "buy":
        structure = signal.low
        or_low = or_levels.get("OR_low")
        if or_low is not None:
            structure = min(structure, float(or_low))
        if plan.stop >= plan.level:
            return {"ok": False, "reason": "STOP_NOT_BELOW_LEVEL", "stop": plan.stop}
        if plan.stop > structure:
            return {"ok": False, "reason": "STOP_ABOVE_STRUCTURE", "stop": plan.stop, "structure": structure}
    else:
        structure = signal.high
        or_high = or_levels.get("OR_high")
        if or_high is not None:
            structure = max(structure, float(or_high))
        if plan.stop <= plan.level:
            return {"ok": False, "reason": "STOP_NOT_ABOVE_LEVEL", "stop": plan.stop}
        if plan.stop < structure:
            return {"ok": False, "reason": "STOP_BELOW_STRUCTURE", "stop": plan.stop, "structure": structure}
    return {"ok": True, "stop": plan.stop, "side": plan.side}


def _close_through_level(bar: OhlcvBar, plan: NamePlan) -> bool:
    if plan.side == "buy":
        return bar.close > plan.level
    return bar.close < plan.level


def _cash_remaining(session: Session | None, at: datetime) -> float | None:
    if session is None:
        return None
    ledger = PaperLedger(session)
    acc = ledger.ensure_account(at=at)
    return float(acc.cash)


def _collect_bars(
    *,
    symbols: Iterable[str],
    timeframe: str,
    session_open: datetime,
    now: datetime,
    data: Any,
    injected: Iterable[OhlcvBar | dict[str, Any]] | None,
    count: int,
) -> list[OhlcvBar]:
    if injected is not None:
        out: list[OhlcvBar] = []
        wanted = set(symbols)
        for raw in injected:
            bar = raw if isinstance(raw, OhlcvBar) else parse_bar(raw)
            if bar.symbol in wanted and bar.timeframe == timeframe:
                out.append(bar)
        return out
    rows = data.ohlcv(
        list(symbols),
        timeframe=timeframe,
        session_open=session_open,
        now=now,
        count=count,
    )
    return [parse_bar(row) for row in rows]


def evaluate_symbol(
    symbol: str,
    *,
    plan: OpeningPlan,
    now: datetime,
    bars_1m: list[OhlcvBar],
    bars_5m: list[OhlcvBar],
    latency_buffer: timedelta = DEFAULT_LATENCY_BUFFER,
) -> dict[str, Any]:
    """Evaluate one name. Does not fill. Does not call AI."""
    name = feed_symbol(symbol)
    name_plan = plan.for_symbol(name)
    done_1m = completed_bars(bars_1m, now, latency_buffer=latency_buffer, symbol=name, timeframe="1m")
    done_5m = completed_bars(bars_5m, now, latency_buffer=latency_buffer, symbol=name, timeframe="5m")
    minutes = minutes_from_ny_open(now)
    or_5m_ready = minutes >= MINUTE_5 and bool(done_5m)
    or_5m = opening_range(done_5m) if or_5m_ready else {"OR_high": None, "OR_low": None, "bar_count": 0}
    result: dict[str, Any] = {
        "symbol": name,
        "desk_symbol": symbol,
        "asset_class": instrument_asset_class(name),
        "commodity_etp": is_commodity_etp(name),
        "in_universe": name in ADDENDUM_E_SYMBOLS,
        "candidate": False,
        "reason": "",
        "minutes_from_open": minutes,
        "completed_1m": len(done_1m),
        "completed_5m": len(done_5m),
        "opening_range_5m": or_5m,
        "opening_range_5m_applied": or_5m_ready,
        "frozen_level": None if name_plan is None else name_plan.level,
        "plan_frozen": bool(plan.frozen),
        "technical": _technical_context(done_1m),
        "news_required": False,
        "indicator_unanimity_required": False,
    }
    if name not in ADDENDUM_E_SYMBOLS:
        result["reason"] = "SYMBOL_NOT_IN_UNIVERSE"
        return result
    if name_plan is None:
        result["reason"] = "NO_FROZEN_PLAN_LEVEL"
        return result
    result["side"] = name_plan.side
    result["stop"] = name_plan.stop
    result["target"] = name_plan.target
    result["notional_gbp"] = name_plan.notional_gbp
    if minutes < MINUTE_2:
        result["reason"] = "BEFORE_MINUTE_2"
        return result
    if len(done_1m) < 2:
        result["reason"] = "NEED_TWO_COMPLETED_1M_BARS"
        return result
    signal = done_1m[1]
    if not _close_through_level(signal, name_plan):
        result["reason"] = "NO_CLOSE_THROUGH_FROZEN_LEVEL"
        result["signal_close"] = signal.close
        return result
    volume = _volume_context(done_1m[:2])
    result["volume"] = volume
    if not volume.get("ok"):
        result["reason"] = str(volume.get("reason") or "NO_VOLUME_CONTEXT")
        return result
    structure = _structural_stop_ok(name_plan, signal, or_5m if minutes >= MINUTE_5 else opening_range(done_1m[:2]))
    result["structural_stop"] = structure
    if not structure.get("ok"):
        result["reason"] = str(structure.get("reason") or "MISSING_STRUCTURAL_STOP")
        return result
    nxt = next_available_bar(bars_1m, signal)
    if nxt is None:
        result["reason"] = "NO_NEXT_BAR_FOR_FILL"
        result["signal_close"] = signal.close
        return result
    # Never fill at the signal-candle close. Next available price is the next bar open.
    fill_price = nxt.open
    result.update(
        {
            "candidate": True,
            "reason": "MINUTE_2_CLOSE_THROUGH_LEVEL",
            "signal_bar": signal.to_dict(),
            "signal_close": signal.close,
            "fill_bar": nxt.to_dict(),
            "fill_price": fill_price,
            "fill_is_signal_close": False,
            "next_price_fill": True,
        }
    )
    return result


def run_us_open_scanner(
    session: Session | None,
    *,
    plan: OpeningPlan | Iterable[dict[str, Any]],
    at: datetime | None = None,
    data: Any | None = None,
    bars_1m: Iterable[OhlcvBar | dict[str, Any]] | None = None,
    bars_5m: Iterable[OhlcvBar | dict[str, Any]] | None = None,
    submit: bool = False,
    max_concurrent_positions: int = DEFAULT_MAX_CONCURRENT,
    latency_buffer: timedelta = DEFAULT_LATENCY_BUFFER,
    started_by: str = "cli",
) -> dict[str, Any]:
    """Scan all 15 names. Optional submit through the sanctioned paper path."""
    now = at or now_london()
    ny_now = as_new_york(now)
    session_open = ny_session_open(ny_now)
    frozen = plan if isinstance(plan, OpeningPlan) else freeze_opening_plan(plan, as_of=now)
    feed = data or FakeMarketData()
    symbols = list(ADDENDUM_E_SYMBOLS)
    raw_1m = _collect_bars(
        symbols=symbols,
        timeframe="1m",
        session_open=session_open,
        now=ny_now,
        data=feed,
        injected=bars_1m,
        count=SCAN_MINUTES + 2,
    )
    raw_5m = _collect_bars(
        symbols=symbols,
        timeframe="5m",
        session_open=session_open,
        now=ny_now,
        data=feed,
        injected=bars_5m,
        count=max(1, (SCAN_MINUTES // 5) + 1),
    )
    book = ScannerBook(session, at=ny_now)
    evaluations: list[dict[str, Any]] = []
    submissions: list[dict[str, Any]] = []
    window_ok = in_us_open_scan_window(ny_now)
    for symbol in symbols:
        ev = evaluate_symbol(
            symbol,
            plan=frozen,
            now=ny_now,
            bars_1m=raw_1m,
            bars_5m=raw_5m,
            latency_buffer=latency_buffer,
        )
        if not window_ok:
            ev["candidate"] = False
            ev["reason"] = ev["reason"] or "OUTSIDE_US_OPEN_SCAN_WINDOW"
            ev["window"] = {
                "start": session_open.isoformat(),
                "end": ny_scan_end(ny_now).isoformat(),
            }
        if book.already_entered(symbol):
            ev["candidate"] = False
            ev["reason"] = "DUPLICATE_ENTRY_PREVENTED"
            ev["already_entered"] = True
            book.mark_blocked(symbol, "DUPLICATE_ENTRY_PREVENTED")
        evaluations.append(ev)

    candidates = [row for row in evaluations if row.get("candidate")]
    blocked: list[dict[str, Any]] = []
    engine = ControlEngine(session) if session is not None else None
    trading_mode = "LIVE_BLOCKED"
    if engine is not None:
        trading_mode = engine.state().trading_mode

    if submit and session is not None and engine is not None:
        trader = session.query(Employee).filter_by(slug=TRADER_SLUG).one()
        cash = _cash_remaining(session, now)
        ledger = PaperLedger(session)
        ledger.ensure_account(at=now)
        for row in candidates:
            if book.open_position_count() >= int(max_concurrent_positions):
                row["submitted"] = False
                row["submit_reason"] = "MAX_CONCURRENT_PROPOSAL"
                blocked.append({"symbol": row["symbol"], "reason": "MAX_CONCURRENT_PROPOSAL"})
                continue
            if book.already_entered(row["symbol"]):
                row["submitted"] = False
                row["submit_reason"] = "DUPLICATE_ENTRY_PREVENTED"
                blocked.append({"symbol": row["symbol"], "reason": "DUPLICATE_ENTRY_PREVENTED"})
                continue
            notional = float(row.get("notional_gbp") or DEFAULT_NOTIONAL_GBP)
            if cash is not None and cash < notional:
                row["submitted"] = False
                row["submit_reason"] = "INSUFFICIENT_CASH"
                blocked.append({"symbol": row["symbol"], "reason": "INSUFFICIENT_CASH", "cash_gbp": cash})
                continue
            orders_today = ledger.orders_today(at=now)
            max_orders = engine.limit_value("max_orders_per_day")
            if max_orders is not None and orders_today >= int(max_orders):
                row["submitted"] = False
                row["submit_reason"] = "MAX_ORDERS_PER_DAY"
                blocked.append({"symbol": row["symbol"], "reason": "MAX_ORDERS_PER_DAY"})
                continue
            pnl = ledger.london_day_pnl(at=now)
            max_loss = engine.limit_value("max_daily_loss")
            if max_loss is not None and pnl <= -abs(max_loss):
                row["submitted"] = False
                row["submit_reason"] = "MAX_DAILY_LOSS"
                blocked.append({"symbol": row["symbol"], "reason": "MAX_DAILY_LOSS", "pnl": pnl})
                continue
            fill_bar = row["fill_bar"]
            order = {
                "symbol": row["symbol"],
                "side": row["side"],
                "notional_gbp": notional,
                "execution_port": "SIMULATOR",
                "price_row": {
                    "symbol": row["symbol"],
                    "last": float(row["fill_price"]),
                    "currency": fill_bar.get("currency") or "USD",
                    "quote_unit": fill_bar.get("quote_unit") or "USD",
                },
                "scanner": "us_open",
                "signal_close": row["signal_close"],
                "next_price_fill": True,
            }
            decision = engine.place_order(
                actor_id=trader.id,
                actor_type="employee",
                order=order,
                at=now,
            )
            submitted = {
                "symbol": row["symbol"],
                "allowed": decision.allowed,
                "reason": decision.reason,
                "filled": bool(decision.allowed),
                "live_fills": False,
                "details": decision.details,
                "fill_price_native": row["fill_price"],
                "signal_close": row["signal_close"],
            }
            row["submitted"] = True
            row["submit_reason"] = decision.reason
            row["filled"] = bool(decision.allowed)
            if decision.allowed:
                book.mark_entered(
                    row["symbol"],
                    signal_close=float(row["signal_close"]),
                    fill_price=float(row["fill_price"]),
                    fill_order_id=str(decision.details.get("order_id") or ""),
                    opening_range=row.get("opening_range_5m") or {},
                )
                cash = _cash_remaining(session, now)
            else:
                blocked.append({"symbol": row["symbol"], "reason": decision.reason})
            submissions.append(submitted)

            # After a fill, later bars in the same injected series may print both
            # stop and target. Unknown intra-bar order ⇒ stop-first (desk note).
            if decision.allowed and row.get("stop") is not None:
                later = [
                    b
                    for b in raw_1m
                    if b.symbol == row["symbol"]
                    and b.open_time >= parse_bar(fill_bar).close_time
                ]
                for later_bar in later:
                    hit = resolve_stop_target(
                        later_bar,
                        side=row["side"],
                        stop=float(row["stop"]),
                        target=row.get("target"),
                    )
                    if hit:
                        row["exit_assumption"] = {
                            "hit": hit,
                            "bar": later_bar.to_dict(),
                            "rule": "adverse_stop_first_when_order_unknown",
                        }
                        break

    payload = {
        "scanner": "us_open_paper",
        "scanner_version": SCANNER_VERSION,
        "universe": list(ADDENDUM_E_SYMBOLS),
        "universe_count": len(ADDENDUM_E_SYMBOLS),
        "commodity_etp_symbols": list(ADDENDUM_E_COMMODITY_ETP_SYMBOLS),
        "evaluated_symbols": [row["symbol"] for row in evaluations],
        "plan": frozen.to_dict(),
        "at": now.isoformat(),
        "ny_now": ny_now.isoformat(),
        "ny_session_open": session_open.isoformat(),
        "scan_window_minutes": SCAN_MINUTES,
        "in_scan_window": window_ok,
        "latency_buffer_seconds": latency_buffer.total_seconds(),
        "completed_bars_only": True,
        "unfinished_candles_excluded": True,
        "next_price_fill": True,
        "hindsight_signal_close_fill": False,
        "indicator_unanimity_required": False,
        "news_required": False,
        "max_concurrent_positions": int(max_concurrent_positions),
        "max_concurrent_is_proposal_not_control": True,
        "submit": bool(submit),
        "evaluations": evaluations,
        "candidates": candidates,
        "submissions": submissions,
        "blocked": blocked,
        "name_state": {k: v.to_dict() for k, v in book.names.items()},
        "started_by": started_by,
        "ai_called": False,
        "daemon": False,
        "paper_only": True,
        "trading_mode": trading_mode,
        "live_fills": False,
        "broker_paper_loaded": bool(BROKER_PAPER_LOADED),
        "live_adapter_loaded": bool(LIVE_ADAPTER_LOADED),
        "futures": False,
        "note": (
            "On-demand US-open PAPER scanner. Completed 1m/5m bars only with "
            "exchange timestamps and a latency buffer. Minute-2 needs two "
            "completed 1m bars and a close through a frozen 14:00 level. "
            "Entry is the next available price, never the signal close. "
            "Technical toolkit is descriptive context. No news gate. "
            "One concurrent position is a proposal default, not a control. "
            "Fills use the sanctioned USD→GBP paper path. LIVE stays BLOCKED."
        ),
    }
    if session is not None:
        session.add(
            Evidence(
                kind=EVIDENCE_KIND,
                actor=started_by,
                payload=json.dumps(
                    {
                        "universe_count": payload["universe_count"],
                        "candidate_count": len(candidates),
                        "submission_count": len(submissions),
                        "submit": submit,
                        "trading_mode": trading_mode,
                        "live_fills": False,
                    },
                    default=str,
                ),
                created_at=now_london(),
            )
        )
        session.commit()
    return payload


def manage_open_exit(
    bar: OhlcvBar,
    *,
    side: str,
    stop: float,
    target: float | None,
) -> str | None:
    """Public helper: stop-first when both levels print in one OHLC bar."""
    return resolve_stop_target(bar, side=side, stop=stop, target=target)
