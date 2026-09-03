"""US-open PAPER scanner + final 15-name universe."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import BOARD_HEADERS, SESSION_OPEN
from varma.config import CANONICAL_PAPER_OPEN_DB, operational_paper_open_db
from varma.controls.addendum_e import (
    ADDENDUM_E_COMMODITY_ETP_SYMBOLS,
    ADDENDUM_E_EQUITY_SYMBOLS,
    ADDENDUM_E_SYMBOLS,
    addendum_e_public,
    is_commodity_etp,
    is_gold_futures_symbol,
)
from varma.controls.addendum_l import addendum_l_public
from varma.controls.engine import LIVE_ADAPTER_LOADED, ControlEngine
from varma.db.models import AllowListInstrument, ControlState, Employee, PaperAccount, PaperFill
from varma.db.seed import MI_SLUG
from varma.paper.fx import FAKE_USDGBP_LAST
from varma.paper.quote import paper_order_economics
from varma.ports.execution import BROKER_PAPER_LOADED, LIVE_PORT_LOADED
from varma.scanner.bars import is_completed_bar, resolve_stop_target
from varma.scanner.opening import evaluate_symbol, run_us_open_scanner
from varma.scanner.plan import freeze_opening_plan

NY = ZoneInfo("America/New_York")
NY_OPEN = datetime(2026, 9, 3, 9, 30, tzinfo=NY)
MINUTE_2 = datetime(2026, 9, 3, 9, 32, 2, tzinfo=NY)
MINUTE_4 = datetime(2026, 9, 3, 9, 34, 0, tzinfo=NY)
MINUTE_5 = datetime(2026, 9, 3, 9, 35, 2, tzinfo=NY)

EXACT_15 = (
    "NVDA",
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "SPCX",
    "AVGO",
    "META",
    "TSLA",
    "BRK-B",
    "GLD",
    "SLV",
    "USO",
    "UNG",
    "CPER",
)


def _bar(
    symbol: str,
    index: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    volume: float = 120_000,
    timeframe: str = "1m",
    complete: bool = True,
) -> dict:
    minutes = 5 if timeframe == "5m" else 1
    start = NY_OPEN + timedelta(minutes=index * minutes)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "open_time": start,
        "close_time": start + timedelta(minutes=minutes),
        "exchange_tz": "America/New_York",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "complete": complete,
        "retrieved_at": start + timedelta(minutes=minutes),
        "source": "test-injected-ohlcv",
        "currency": "USD",
        "quote_unit": "USD",
    }


def _through_plan(symbol: str = "AAPL", level: float = 100.0) -> list[dict]:
    """Two completed 1m bars plus a next bar whose open is not the signal close."""
    return [
        _bar(symbol, 0, 99.0, 99.6, 98.4, 99.2),
        _bar(symbol, 1, 99.3, 101.8, 99.0, 101.4),  # close through 100
        _bar(symbol, 2, 102.2, 102.8, 101.6, 102.4),  # next open 102.2
    ]


def _plan(symbol: str = "AAPL", level: float = 100.0, stop: float = 98.0, target: float = 104.0):
    return freeze_opening_plan(
        [{"symbol": symbol, "side": "buy", "level": level, "stop": stop, "target": target, "notional_gbp": 50.0}]
    )


def test_exact_15_name_universe_and_no_extras(session):
    assert ADDENDUM_E_SYMBOLS == EXACT_15
    assert len(ADDENDUM_E_SYMBOLS) == 15
    assert len(ADDENDUM_E_EQUITY_SYMBOLS) == 10
    assert ADDENDUM_E_COMMODITY_ETP_SYMBOLS == ("GLD", "SLV", "USO", "UNG", "CPER")
    seeded = tuple(r.symbol for r in session.query(AllowListInstrument).all())
    assert set(seeded) == set(EXACT_15)
    assert len(seeded) == 15
    assert "SHEL.L" not in seeded
    assert "JPM" not in seeded
    assert "XAUUSD" not in seeded
    public = addendum_e_public()
    assert public["count"] == 15
    assert public["futures"] is False
    assert public["all_us_market"] is True
    l_pub = addendum_l_public()
    assert l_pub["count"] == 15
    assert l_pub["no_non_us_venues"] is True
    assert l_pub["futures_rollover"] is False
    engine = ControlEngine(session)
    assert set(engine.allow_list_symbols()) == set(EXACT_15)
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_commodity_etps_use_ordinary_usd_sizing_path(session):
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    from varma.db.models import Permission

    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    for symbol in ADDENDUM_E_COMMODITY_ETP_SYMBOLS:
        assert is_commodity_etp(symbol) is True
        assert is_gold_futures_symbol(symbol) is False
        row = {"symbol": symbol, "last": 100.0, "currency": "USD", "quote_unit": "USD"}
        econ = paper_order_economics(
            {"symbol": symbol, "side": "buy", "notional_gbp": 50.0},
            price_row=row,
        )
        assert econ.instrument_currency == "USD"
        assert econ.fx.pair == "USDGBP"
        assert econ.fx.rate == FAKE_USDGBP_LAST
        assert econ.quantity > 0
        assert econ.notional_gbp <= 50.0 + 1e-6
        d = ControlEngine(session).place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": symbol, "side": "buy", "notional_gbp": 50.0, "execution_port": "SIMULATOR"},
            at=SESSION_OPEN,
        )
        assert d.allowed is True, (symbol, d.reason)
        assert d.reason == "PAPER_FILL_SIMULATED"
        assert d.details["instrument_currency"] == "USD"
        assert d.details["fx"]["pair"] == "USDGBP"
        assert d.details["is_live"] is False
    assert is_gold_futures_symbol("XAUUSD") is True
    gold = ControlEngine(session).place_order(
        actor_id=emp.id,
        actor_type="employee",
        order={"symbol": "XAUUSD", "side": "buy", "quantity": 1, "execution_port": "SIMULATOR"},
        at=SESSION_OPEN,
    )
    assert gold.allowed is False
    assert gold.reason == "GOLD_NOT_AUTHORISED"


def test_incomplete_bars_are_excluded():
    from varma.scanner.bars import parse_bar

    unfinished = _bar("AAPL", 1, 99.3, 101.8, 99.0, 101.4, complete=False)
    bar = parse_bar(unfinished)
    assert is_completed_bar(bar, MINUTE_2) is False
    ev = evaluate_symbol(
        "AAPL",
        plan=_plan("AAPL"),
        now=MINUTE_2,
        bars_1m=[parse_bar(_bar("AAPL", 0, 99.0, 99.6, 98.4, 99.2)), bar],
        bars_5m=[],
    )
    assert ev["candidate"] is False
    assert ev["reason"] == "NEED_TWO_COMPLETED_1M_BARS"
    assert ev["completed_1m"] == 1


def test_minute_2_requires_two_completed_1m_bars_and_frozen_level():
    from varma.scanner.bars import parse_bar

    bars = [parse_bar(b) for b in _through_plan("AAPL")]
    frozen = _plan("AAPL", level=100.0)
    too_early = evaluate_symbol("AAPL", plan=frozen, now=datetime(2026, 9, 3, 9, 31, 2, tzinfo=NY), bars_1m=bars, bars_5m=[])
    assert too_early["candidate"] is False
    assert too_early["reason"] in {"BEFORE_MINUTE_2", "NEED_TWO_COMPLETED_1M_BARS"}

    one_bar = evaluate_symbol(
        "AAPL",
        plan=frozen,
        now=MINUTE_2,
        bars_1m=[parse_bar(_bar("AAPL", 0, 99.0, 99.6, 98.4, 101.4))],
        bars_5m=[],
    )
    assert one_bar["candidate"] is False
    assert one_bar["reason"] == "NEED_TWO_COMPLETED_1M_BARS"

    mutated = {"symbol": "AAPL", "side": "buy", "level": 100.0, "stop": 98.0, "target": 104.0}
    plan = freeze_opening_plan([mutated])
    mutated["level"] = 200.0  # later rewrite must not change the frozen copy
    ev = evaluate_symbol("AAPL", plan=plan, now=MINUTE_2, bars_1m=bars, bars_5m=[])
    assert ev["candidate"] is True
    assert ev["frozen_level"] == 100.0
    assert ev["frozen_level"] != 200.0
    assert ev["reason"] == "MINUTE_2_CLOSE_THROUGH_LEVEL"
    assert plan.frozen is True


def test_next_price_fill_not_signal_close():
    from varma.scanner.bars import parse_bar

    bars = [parse_bar(b) for b in _through_plan("AAPL")]
    ev = evaluate_symbol("AAPL", plan=_plan("AAPL"), now=MINUTE_2, bars_1m=bars, bars_5m=[])
    assert ev["candidate"] is True
    assert ev["signal_close"] == 101.4
    assert ev["fill_price"] == 102.2
    assert ev["fill_price"] != ev["signal_close"]
    assert ev["next_price_fill"] is True
    assert ev["fill_is_signal_close"] is False


def test_5m_opening_range_updates_from_minute_5():
    from varma.scanner.bars import parse_bar

    bars_1m = [parse_bar(b) for b in _through_plan("AAPL")]
    bars_5m = [
        parse_bar(_bar("AAPL", 0, 99.0, 103.5, 97.5, 101.0, timeframe="5m")),
        parse_bar(_bar("AAPL", 1, 101.0, 104.0, 100.5, 102.0, timeframe="5m")),
    ]
    before = evaluate_symbol("AAPL", plan=_plan("AAPL"), now=MINUTE_4, bars_1m=bars_1m, bars_5m=bars_5m)
    assert before["opening_range_5m"]["OR_high"] is None
    assert before.get("opening_range_5m_applied") is None

    after = evaluate_symbol("AAPL", plan=_plan("AAPL"), now=MINUTE_5, bars_1m=bars_1m, bars_5m=bars_5m)
    assert after["opening_range_5m"]["OR_high"] == 103.5
    assert after["opening_range_5m"]["OR_low"] == 97.5
    assert after["opening_range_5m_applied"] is True


def test_duplicate_entry_prevention(session):
    bars = _through_plan("AAPL")
    first = run_us_open_scanner(
        session,
        plan=_plan("AAPL"),
        at=MINUTE_2,
        bars_1m=bars,
        bars_5m=[],
        submit=True,
        max_concurrent_positions=1,
    )
    assert first["candidates"]
    assert first["submissions"]
    assert first["submissions"][0]["filled"] is True
    fills = session.query(PaperFill).count()
    second = run_us_open_scanner(
        session,
        plan=_plan("AAPL"),
        at=MINUTE_2,
        bars_1m=bars,
        bars_5m=[],
        submit=True,
        max_concurrent_positions=1,
    )
    aapl = next(row for row in second["evaluations"] if row["symbol"] == "AAPL")
    assert aapl["reason"] == "DUPLICATE_ENTRY_PREVENTED"
    assert aapl["candidate"] is False
    assert session.query(PaperFill).count() == fills


def test_exhausted_order_loss_cash_limits_block(session):
    bars = _through_plan("AAPL")
    emp = session.query(Employee).filter_by(slug=MI_SLUG).one()
    from varma.db.models import Permission

    session.query(Permission).filter_by(subject_id=emp.id, action="place_order").one().allowed = True
    session.commit()
    engine = ControlEngine(session)
    for _ in range(6):
        d = engine.place_order(
            actor_id=emp.id,
            actor_type="employee",
            order={"symbol": "MSFT", "side": "buy", "notional_gbp": 10.0, "execution_port": "SIMULATOR"},
            at=MINUTE_2,
        )
        assert d.allowed is True
    orders_blocked = run_us_open_scanner(
        session,
        plan=_plan("AAPL"),
        at=MINUTE_2,
        bars_1m=bars,
        bars_5m=[],
        submit=True,
    )
    assert any(row["reason"] == "MAX_ORDERS_PER_DAY" for row in orders_blocked["blocked"])
    assert not any(row.get("filled") for row in orders_blocked["submissions"])

    from varma.db.models import PaperOrder, PaperPosition

    for row in session.query(PaperFill).all():
        row.london_day = "1999-01-01"
    for row in session.query(PaperOrder).all():
        row.london_day = "1999-01-01"
    for pos in session.query(PaperPosition).all():
        session.delete(pos)
    acc = session.get(PaperAccount, 1)
    acc.cash = 1.0
    acc.equity_at_day_start = 1.0
    session.commit()

    cash_blocked = run_us_open_scanner(
        session,
        plan=_plan("AAPL"),
        at=MINUTE_2,
        bars_1m=bars,
        bars_5m=[],
        submit=True,
    )
    assert any(row["reason"] == "INSUFFICIENT_CASH" for row in cash_blocked["blocked"])

    acc = session.get(PaperAccount, 1)
    acc.cash = 900.0
    acc.equity_at_day_start = 1000.0
    session.commit()
    loss_blocked = run_us_open_scanner(
        session,
        plan=_plan("AAPL"),
        at=MINUTE_2,
        bars_1m=bars,
        bars_5m=[],
        submit=True,
    )
    assert any(row["reason"] == "MAX_DAILY_LOSS" for row in loss_blocked["blocked"])


def test_live_remains_blocked(session, client):
    result = run_us_open_scanner(
        session,
        plan=_plan("AAPL"),
        at=MINUTE_2,
        bars_1m=_through_plan("AAPL"),
        bars_5m=[],
        submit=True,
    )
    assert result["trading_mode"] == "LIVE_BLOCKED"
    assert result["live_fills"] is False
    assert result["broker_paper_loaded"] is False
    assert result["live_adapter_loaded"] is False
    assert LIVE_ADAPTER_LOADED is False
    assert BROKER_PAPER_LOADED is False
    assert LIVE_PORT_LOADED is False
    live = client.post(
        "/execution/place-order",
        headers=BOARD_HEADERS,
        json={"symbol": "AAPL", "side": "buy", "quantity": 1, "execution_port": "LIVE"},
    )
    assert live.status_code == 403
    assert live.json()["detail"]["reason"] in {"LIVE_BLOCKED", "LIVE_ADAPTER_NOT_LOADED"}
    assert session.get(ControlState, 1).trading_mode == "LIVE_BLOCKED"


def test_stop_and_target_same_bar_is_stop_first():
    from varma.scanner.bars import parse_bar

    bar = parse_bar(_bar("AAPL", 3, 102.0, 105.0, 97.0, 104.0))
    assert resolve_stop_target(bar, side="buy", stop=98.0, target=104.0) == "stop"


def test_scanner_evaluates_all_15_and_concurrent_cap_is_proposal(session):
    bars = []
    for symbol in EXACT_15:
        bars.extend(_through_plan(symbol))
    levels = [
        {"symbol": s, "side": "buy", "level": 100.0, "stop": 98.0, "target": 104.0, "notional_gbp": 50.0}
        for s in EXACT_15
    ]
    result = run_us_open_scanner(
        session,
        plan=freeze_opening_plan(levels),
        at=MINUTE_2,
        bars_1m=bars,
        bars_5m=[],
        submit=True,
        max_concurrent_positions=1,
    )
    assert result["evaluated_symbols"] == list(EXACT_15)
    assert result["universe_count"] == 15
    assert result["max_concurrent_is_proposal_not_control"] is True
    filled = [row for row in result["submissions"] if row.get("filled")]
    assert len(filled) == 1
    assert any(row["reason"] == "MAX_CONCURRENT_PROPOSAL" for row in result["blocked"])
    assert result["news_required"] is False
    assert result["indicator_unanimity_required"] is False
    assert result["hindsight_signal_close_fill"] is False


def test_canonical_ledger_path_is_not_created_by_config(tmp_path):
    assert str(CANONICAL_PAPER_OPEN_DB) == "/workspace/varma-canonical/varma_paper_open.db"
    # This PR must not create or overwrite the operational ledger.
    assert not CANONICAL_PAPER_OPEN_DB.is_file()
    path = operational_paper_open_db()
    assert path.name == "varma_paper_open.db"
    assert "varma-canonical" not in str(path) or CANONICAL_PAPER_OPEN_DB.is_file()


def test_board_scanner_job_does_not_open_live(client):
    r = client.post("/routines/run-us-open-scanner", headers=BOARD_HEADERS, json={})
    assert r.status_code == 200
    body = r.json()
    assert body["trading_mode"] == "LIVE_BLOCKED"
    assert body["live_fills"] is False
    assert body["universe_count"] == 15
    assert body["job_safety"]["live_fills"] is False
    assert body["job_safety"]["loads_broker_ports"] is False
    assert body["job_safety"]["changes_trading_mode"] is False
    assert client.get("/controls").json()["trading_mode"] == "LIVE_BLOCKED"
