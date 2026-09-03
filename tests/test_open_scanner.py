"""Deterministic NY-open scanner: completed bars, next-bar fill, 15 names, limits."""

from __future__ import annotations

from datetime import datetime, timedelta

from tests.conftest import BOARD_HEADERS
from varma.clock import LONDON, london_day
from varma.controls.addendum_e import ADDENDUM_E_SYMBOLS
from varma.controls.addendum_m import ADDENDUM_M_ETP_SYMBOLS
from varma.db.models import PaperFill, PaperOrder
from varma.paper.ledger import PaperLedger
from varma.ports.bars import ScriptedBars, bar_frame, completed_bars
from varma.routines.run_open_scanner import run_open_scanner
from varma.scanner.open_scanner import OpenScanner

AS_OF_DAY = datetime(2026, 9, 3, 15, 0, tzinfo=LONDON)
PRIOR = datetime(2026, 9, 2, 15, 0, tzinfo=LONDON)
OPEN = datetime(2026, 9, 3, 14, 30, tzinfo=LONDON)
TRIGGER = 100.0


def _ts(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 3, hour, minute, tzinfo=LONDON)


def _ohlc(close: float, *, open_: float | None = None, volume: float = 12000.0):
    o = close if open_ is None else open_
    hi = max(o, close) + 0.2
    lo = min(o, close) - 0.2
    return (o, hi, lo, close, volume)


def _crossing_1m(*, signal_close: float = 100.6, next_open: float = 101.4, extra: list | None = None):
    """Prior day + 14:30/14:31/14:32 (+ optional later bars). Index = bar open."""
    stamps = [PRIOR, _ts(14, 30), _ts(14, 31), _ts(14, 32)]
    rows = [
        _ohlc(99.2),
        _ohlc(99.4),
        _ohlc(signal_close),  # completes 14:32 — minute-2 cross of 100
        _ohlc(next_open + 0.1, open_=next_open),
    ]
    if extra:
        for ts, row in extra:
            stamps.append(ts)
            rows.append(row)
    return bar_frame(stamps, rows)


def _quiet_5m():
    stamps = [_ts(14, 30), _ts(14, 35), _ts(14, 40)]
    rows = [_ohlc(99.5), _ohlc(99.6), _ohlc(99.7)]
    return bar_frame(stamps, rows)


def _book_for_all(symbols=ADDENDUM_E_SYMBOLS, **kwargs) -> ScriptedBars:
    book = ScriptedBars()
    for sym in symbols:
        book.add(sym, "1m", _crossing_1m(**kwargs))
        book.add(sym, "5m", _quiet_5m())
    return book


def test_incomplete_candle_excluded(session):
    book = _book_for_all()
    scanner = OpenScanner(latency_buffer_seconds=60, meeting_trigger_levels={"AAPL": TRIGGER}, symbols=("AAPL",))
    # 14:32:30 with 60s buffer: the 14:31 bar completed at 14:32, usable only at 14:33.
    early = scanner.scan(session, bar_provider=book, as_of=_ts(14, 32) + timedelta(seconds=30))
    assert early == []
    later = scanner.scan(session, bar_provider=book, as_of=_ts(14, 33))
    assert len(later) == 1
    assert later[0]["symbol"] == "AAPL"


def test_next_bar_fill_not_signal_close(session):
    signal_close = 100.55
    next_open = 107.25
    book = _book_for_all(signal_close=signal_close, next_open=next_open)
    scanner = OpenScanner(latency_buffer_seconds=0, meeting_trigger_levels={"MSFT": TRIGGER}, symbols=("MSFT",))
    rows = scanner.scan(session, bar_provider=book, as_of=_ts(14, 33))
    assert len(rows) == 1
    assert rows[0]["entry_price"] == next_open
    assert rows[0]["entry_price"] != signal_close
    assert "next-bar open fill" in rows[0]["reason"]
    assert "not signal close" in rows[0]["reason"]


def test_all_fifteen_names_covered(session):
    """Each of the 15 names can trigger. Firm-wide 6-order cap is tested separately."""
    book = _book_for_all()
    got = []
    desks = []
    for sym in ADDENDUM_E_SYMBOLS:
        scanner = OpenScanner(
            latency_buffer_seconds=0,
            meeting_trigger_levels={sym: TRIGGER},
            symbols=(sym,),
        )
        rows = scanner.scan(session, bar_provider=book, as_of=_ts(14, 33))
        assert len(rows) == 1, f"{sym} produced {rows}"
        got.append(rows[0]["feed_symbol"])
        desks.append(rows[0]["symbol"])
        assert rows[0]["currency"] == "USD"
        assert 0 < rows[0]["gbp_notional"] <= 200.0
        assert rows[0]["trigger_time"].startswith("2026-09-03T14:32")
        assert rows[0]["stop"] is not None
        assert rows[0]["target"] is not None
    assert got == list(ADDENDUM_E_SYMBOLS)
    assert "BRK.B" in desks
    assert "BRK-B" not in desks
    for etp in ADDENDUM_M_ETP_SYMBOLS:
        assert etp in got


def test_duplicate_entry_prevention_per_name(session):
    extra = [
        (_ts(14, 40), _ohlc(99.1)),
        (_ts(14, 41), _ohlc(100.8)),  # second cross, completes 14:42
        (_ts(14, 42), _ohlc(101.0, open_=100.9)),
    ]
    book = ScriptedBars()
    book.add("NVDA", "1m", _crossing_1m(extra=extra))
    book.add("NVDA", "5m", _quiet_5m())
    scanner = OpenScanner(latency_buffer_seconds=0, meeting_trigger_levels={"NVDA": TRIGGER}, symbols=("NVDA",))
    rows = scanner.scan(session, bar_provider=book, as_of=_ts(14, 45))
    assert len(rows) == 1
    assert rows[0]["feed_symbol"] == "NVDA"


def test_limit_exhaustion_stops_new_candidates(session):
    book = _book_for_all()
    levels = {sym: TRIGGER for sym in ADDENDUM_E_SYMBOLS}
    as_of = _ts(14, 33)
    ledger = PaperLedger(session)
    ledger.ensure_account(at=as_of)
    for i in range(6):
        session.add(
            PaperOrder(
                symbol="AAPL",
                side="buy",
                quantity=0.01,
                notional_gbp=10.0,
                status="FILLED",
                london_day=london_day(as_of),
                created_at=as_of,
                actor_id="test",
                is_flatten=False,
            )
        )
    session.commit()
    scanner = OpenScanner(latency_buffer_seconds=0, meeting_trigger_levels=levels)
    assert scanner.scan(session, bar_provider=book, as_of=as_of) == []

    session.query(PaperOrder).delete()
    session.commit()
    for i in range(5):
        session.add(
            PaperOrder(
                symbol="AAPL",
                side="buy",
                quantity=0.01,
                notional_gbp=10.0,
                status="FILLED",
                london_day=london_day(as_of),
                created_at=as_of,
                actor_id="test",
                is_flatten=False,
            )
        )
    session.commit()
    rows = scanner.scan(session, bar_provider=book, as_of=as_of)
    assert len(rows) == 1


def test_daily_loss_limit_stops_candidates(session):
    book = _book_for_all()
    as_of = _ts(14, 33)
    ledger = PaperLedger(session)
    acc = ledger.ensure_account(at=as_of)
    acc.cash = 900.0
    acc.equity_at_day_start = 1000.0
    acc.london_day = london_day(as_of)
    session.commit()
    assert ledger.london_day_pnl(at=as_of) <= -50.0
    scanner = OpenScanner(
        latency_buffer_seconds=0,
        meeting_trigger_levels={sym: TRIGGER for sym in ADDENDUM_E_SYMBOLS},
    )
    assert scanner.scan(session, bar_provider=book, as_of=as_of) == []


def test_scanner_does_not_place_orders(session):
    book = _book_for_all()
    fills_before = session.query(PaperFill).count()
    result = run_open_scanner(
        session,
        started_by="cli",
        as_of=_ts(14, 33),
        latency_buffer_seconds=0,
        bar_provider=book,
        meeting_trigger_levels={sym: TRIGGER for sym in ADDENDUM_E_SYMBOLS},
    )
    assert result["places_orders"] is False
    assert result["candidate_count"] == 6  # Addendum A max_orders_per_day
    assert set(result["symbols_scanned"]) == set(ADDENDUM_E_SYMBOLS)
    assert result["daemon"] is False
    assert result["trading_mode"] == "LIVE_BLOCKED"
    assert session.query(PaperFill).count() == fills_before


def test_completed_bars_helper_drops_in_progress():
    bars = _crossing_1m()
    as_of = _ts(14, 32) + timedelta(seconds=30)
    kept = completed_bars(bars, timeframe="1m", as_of=as_of, latency_buffer_seconds=60)
    assert _ts(14, 31) not in kept.index
    later = completed_bars(bars, timeframe="1m", as_of=_ts(14, 33), latency_buffer_seconds=60)
    assert _ts(14, 31) in later.index


def test_or_break_from_minute_5(session):
    """No meeting-trigger cross; 1m close breaks completed 5m OR after 14:35."""
    # 1m: stay below trigger 100, then at 14:35 close above OR high.
    stamps = [PRIOR, _ts(14, 30), _ts(14, 31), _ts(14, 32), _ts(14, 33), _ts(14, 34), _ts(14, 35), _ts(14, 36)]
    rows = [
        _ohlc(90.0),
        _ohlc(90.1),
        _ohlc(90.2),
        _ohlc(90.3),
        _ohlc(90.4),
        _ohlc(90.5),
        _ohlc(96.0),  # completes 14:36, breaks OR high ~90.x
        _ohlc(96.2, open_=96.1),
    ]
    five = bar_frame(
        [_ts(14, 30), _ts(14, 35)],
        [_ohlc(90.2), _ohlc(90.4)],
    )
    book = ScriptedBars()
    book.add("GLD", "1m", bar_frame(stamps, rows))
    book.add("GLD", "5m", five)
    scanner = OpenScanner(latency_buffer_seconds=0, meeting_trigger_levels={"GLD": 200.0}, symbols=("GLD",))
    rows_out = scanner.scan(session, bar_provider=book, as_of=_ts(14, 37))
    assert len(rows_out) == 1
    assert rows_out[0]["feed_symbol"] == "GLD"
    assert "OR high" in rows_out[0]["reason"]


def test_board_open_scanner_job_does_not_fill(client):
    r = client.post("/routines/run-open-scanner", headers=BOARD_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["places_orders"] is False
    assert body["daemon"] is False
    assert body["job_safety"]["fills"] is False
    assert body["job_safety"]["trading_mode"] == "LIVE_BLOCKED"
