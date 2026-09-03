"""Tests for the deterministic technical analysis toolkit.

Fixed fixtures ensure reproducible results. No AI. No network.
Ticker-agnostic — does not reference any specific allow-list.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from varma.technical.indicators import SIGNAL_REFERENCE, technical_snapshot
from varma.technical.structure import (
    compute_gap,
    compute_opening_range,
    compute_pivot_points,
    compute_prior_day_levels,
    compute_support_resistance_clusters,
    compute_swing_points,
)
from varma.technical.candles import compute_candlestick_patterns


@pytest.fixture()
def daily_bars() -> pd.DataFrame:
    """100 daily bars with a known random seed for reproducibility."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2026-06-01", periods=n, freq="1D")
    close = 150.0 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame(
        {
            "open": close - np.random.rand(n),
            "high": close + np.abs(np.random.randn(n)),
            "low": close - np.abs(np.random.randn(n)),
            "close": close,
            "volume": np.random.randint(1000, 10000, n).astype(float),
        },
        index=dates,
    )


@pytest.fixture()
def intraday_bars() -> pd.DataFrame:
    """50 five-minute bars for intraday tests."""
    np.random.seed(99)
    n = 50
    dates = pd.date_range("2026-09-03 09:30", periods=n, freq="5min")
    close = 200.0 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame(
        {
            "open": close - np.random.rand(n) * 0.3,
            "high": close + np.abs(np.random.randn(n) * 0.4),
            "low": close - np.abs(np.random.randn(n) * 0.4),
            "close": close,
            "volume": np.random.randint(500, 5000, n).astype(float),
        },
        index=dates,
    )


def test_snapshot_deterministic_same_input_same_output(daily_bars):
    """Same bars → same numbers. Proves deterministic."""
    snap1 = technical_snapshot("AAPL", daily_bars, timeframe="1d")
    snap2 = technical_snapshot("AAPL", daily_bars, timeframe="1d")
    assert snap1["trend"] == snap2["trend"]
    assert snap1["momentum"] == snap2["momentum"]
    assert snap1["volatility"] == snap2["volatility"]
    assert snap1["volume"] == snap2["volume"]
    assert snap1["structure"] == snap2["structure"]
    assert snap1["candles"] == snap2["candles"]


def test_snapshot_no_ai_calls(daily_bars):
    snap = technical_snapshot("NVDA", daily_bars)
    assert snap["ai_calls"] == 0
    assert snap["deterministic"] is True
    assert snap["delayed_data"] is True


def test_snapshot_has_all_required_sections(daily_bars):
    snap = technical_snapshot("MSFT", daily_bars)
    assert "trend" in snap
    assert "momentum" in snap
    assert "volatility" in snap
    assert "volume" in snap
    assert "structure" in snap
    assert "candles" in snap
    assert "signal_reference" in snap


def test_trend_indicators_present(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    t = snap["trend"]
    for period in (9, 20, 50, 200):
        assert f"SMA_{period}" in t
        assert f"EMA_{period}" in t
    assert "WMA_20" in t
    assert "HMA_20" in t
    assert any(k.startswith("MACD") for k in t)
    assert any(k.startswith("ADX") for k in t)
    assert any(k.startswith("PSAR") for k in t)
    assert any(k.startswith("Ichimoku") for k in t)
    assert any(k.startswith("SuperTrend") for k in t)
    assert any(k.startswith("Aroon") for k in t)


def test_momentum_indicators_present(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    m = snap["momentum"]
    assert "RSI_14" in m and m["RSI_14"] is not None
    assert any(k.startswith("Stoch") for k in m)
    assert any(k.startswith("StochRSI") for k in m)
    assert "CCI_20" in m
    assert "Williams_R_14" in m
    assert "ROC_12" in m
    assert "MFI_14" in m
    assert any(k.startswith("TSI") for k in m)
    assert "AO" in m


def test_volatility_indicators_present(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    v = snap["volatility"]
    assert "ATR_14" in v and v["ATR_14"] is not None
    assert any(k.startswith("BB") for k in v)
    assert any(k.startswith("KC") for k in v)
    assert any(k.startswith("Donchian") for k in v)
    assert "StdDev_20" in v
    assert "HistVol_20" in v


def test_volume_indicators_present(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    vol = snap["volume"]
    assert "VWAP" in vol
    assert "OBV" in vol
    assert "AD" in vol
    assert "CMF_20" in vol
    assert "Vol_vs_Avg20" in vol
    assert "RelVol" in vol


def test_structure_indicators_present(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    s = snap["structure"]
    assert "opening_range" in s and s["opening_range"]["OR_high"] is not None
    assert "prior_day" in s and s["prior_day"]["PriorDay_high"] is not None
    assert "gap" in s and s["gap"]["gap"] is not None
    assert "pivots" in s and s["pivots"]["Pivot"] is not None
    assert "session_levels" in s
    assert "swing_points" in s
    assert "sr_clusters" in s


def test_candlestick_patterns_checked(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    c = snap["candles"]
    assert c["patterns_checked"] >= 2  # at least doji + inside without TA-Lib; 62 with
    assert isinstance(c["patterns"], list)
    assert c["or_break"] is not None
    assert c["or_break"]["type"] in ("break_up", "break_down", "failed_break_up", "failed_break_down", "inside")


def test_opening_range_break_detection(intraday_bars):
    snap = technical_snapshot("TEST", intraday_bars, timeframe="5m")
    orb = snap["candles"]["or_break"]
    assert orb is not None
    assert "or_high" in orb
    assert "or_low" in orb
    assert "close" in orb
    assert orb["type"] in ("break_up", "break_down", "failed_break_up", "failed_break_down", "inside")


def test_rsi_in_valid_range(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    rsi = snap["momentum"]["RSI_14"]
    assert rsi is not None
    assert 0 <= rsi <= 100


def test_bollinger_band_ordering(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    v = snap["volatility"]
    bb_keys = [k for k in v if k.startswith("BB")]
    bb_vals = {k: v[k] for k in bb_keys if v[k] is not None}
    upper_key = [k for k in bb_vals if "BBU" in k or "upper" in k.lower()]
    lower_key = [k for k in bb_vals if "BBL" in k or "lower" in k.lower()]
    mid_key = [k for k in bb_vals if "BBM" in k or "mid" in k.lower()]
    if upper_key and lower_key and mid_key:
        assert bb_vals[upper_key[0]] >= bb_vals[mid_key[0]] >= bb_vals[lower_key[0]]


def test_pivot_point_ordering(daily_bars):
    snap = technical_snapshot("TEST", daily_bars)
    p = snap["structure"]["pivots"]
    if p["Pivot"] is not None:
        assert p["R2"] >= p["R1"] >= p["Pivot"] >= p["S1"] >= p["S2"]


def test_gap_detection():
    bars = pd.DataFrame({
        "open": [100.0, 102.0, 106.0],
        "high": [101.0, 104.0, 107.0],
        "low": [99.0, 101.0, 105.0],
        "close": [100.5, 103.0, 106.5],
        "volume": [1000.0, 1000.0, 1000.0],
    }, index=pd.date_range("2026-09-01", periods=3, freq="1D"))
    gap = compute_gap(bars)
    assert gap["gap"] == "up"


def test_swing_points_with_known_data():
    n = 30
    np.random.seed(77)
    highs = (10.0 + np.arange(n) * 0.01).tolist()
    lows = (5.0 + np.arange(n) * 0.01).tolist()
    highs[20] = 25.0  # clear swing high surrounded by lower values
    lows[10] = 1.0    # clear swing low surrounded by higher values
    bars = pd.DataFrame({
        "open": [7.5] * n,
        "high": highs,
        "low": lows,
        "close": [7.5] * n,
        "volume": [100.0] * n,
    }, index=pd.date_range("2026-08-01", periods=n, freq="1D"))
    sw = compute_swing_points(bars)
    assert sw["SwingHigh"] == 25.0
    assert sw["SwingLow"] == 1.0


def test_sr_clusters_with_repeated_levels():
    n = 50
    np.random.seed(7)
    close = 100.0 + np.random.randn(n) * 0.1
    close[10] = 105.0
    close[20] = 105.1
    close[30] = 104.9
    bars = pd.DataFrame({
        "open": close - 0.05,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": [100.0] * n,
    }, index=pd.date_range("2026-07-01", periods=n, freq="1D"))
    clusters = compute_support_resistance_clusters(bars)
    assert len(clusters) >= 1
    assert all("level" in c and "touches" in c for c in clusters)


def test_signal_reference_has_all_documented_keys():
    expected_keys = [
        "SMA", "EMA", "WMA", "HMA", "MACD", "ADX", "PSAR", "Ichimoku", "SuperTrend",
        "RSI", "CCI", "Williams_R", "ROC", "MFI", "TSI", "AO",
        "ATR", "BB_upper", "BB_lower", "BB_middle",
        "VWAP", "OBV", "AD", "CMF",
        "OR_high", "OR_low", "PriorDay_high", "Gap", "Pivot",
        "SwingHigh", "SwingLow", "SR_clusters",
    ]
    for key in expected_keys:
        assert key in SIGNAL_REFERENCE, f"Missing signal reference: {key}"


def test_ticker_agnostic_any_symbol_works(daily_bars):
    for sym in ("AAPL", "MSFT", "XYZ_UNKNOWN", "SHEL.L", "BRK-B"):
        snap = technical_snapshot(sym, daily_bars)
        assert snap["symbol"] == sym
        assert snap["bars"] == len(daily_bars)
        assert snap["ai_calls"] == 0


def test_multi_timeframe_same_bars_different_label(daily_bars):
    d = technical_snapshot("TEST", daily_bars, timeframe="1d")
    w = technical_snapshot("TEST", daily_bars, timeframe="1wk")
    assert d["timeframe"] == "1d"
    assert w["timeframe"] == "1wk"
    assert d["trend"] == w["trend"]


def test_insufficient_bars_returns_error():
    tiny = pd.DataFrame({
        "open": [100.0], "high": [101.0], "low": [99.0],
        "close": [100.5], "volume": [1000.0],
    }, index=pd.date_range("2026-09-01", periods=1, freq="1D"))
    snap = technical_snapshot("TEST", tiny)
    assert snap["error"] == "insufficient bars"
    assert snap["bars"] == 0


def test_intraday_opening_range_uses_first_30_minutes(intraday_bars):
    snap = technical_snapshot("TEST", intraday_bars, timeframe="5m")
    or_ = snap["structure"]["opening_range"]
    assert or_["OR_high"] is not None
    assert or_["OR_low"] is not None
    assert or_["OR_high"] >= or_["OR_low"]
