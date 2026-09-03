"""Deterministic technical indicator computation.

One compact ``technical_snapshot(symbol, bars_df)`` function so Research/Quant/
Challenge/Trader all read identical numbers. Multi-timeframe: call once per
timeframe with the appropriate bars DataFrame.

Every result is dated and stamped with the bar's timestamp. All data is
treated as delayed (labelled). No AI calls. No network at compute time.
No locks, no allow-list writes, no live path. Paper only.

Requires: pandas, pandas_ta.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import pandas_ta as ta

from varma.technical.structure import (
    compute_gap,
    compute_opening_range,
    compute_pivot_points,
    compute_prior_day_levels,
    compute_prior_week_levels,
    compute_relative_volume,
    compute_session_levels,
    compute_support_resistance_clusters,
    compute_swing_points,
)
from varma.technical.candles import compute_candlestick_patterns

# ---------------------------------------------------------------------------
# Signal reference (one line per signal for staff interpretation)
# ---------------------------------------------------------------------------
SIGNAL_REFERENCE: dict[str, str] = {
    "SMA": "Simple moving average — equal-weighted mean of the last N closes.",
    "EMA": "Exponential moving average — recent prices weighted more heavily.",
    "WMA": "Weighted moving average — linearly weighted toward recent prices.",
    "HMA": "Hull moving average — fast-tracking, reduced-lag smoothed average.",
    "MACD": "Moving average convergence/divergence — trend momentum from EMA spread.",
    "ADX": "Average directional index — trend strength regardless of direction.",
    "DMI+": "Positive directional indicator — upward trend pressure.",
    "DMI-": "Negative directional indicator — downward trend pressure.",
    "PSAR": "Parabolic SAR — trailing stop-and-reverse trend follower.",
    "Ichimoku": "Ichimoku cloud — support/resistance/trend via five averaged lines.",
    "SuperTrend": "Volatility-based trailing stop; above price = bearish, below = bullish.",
    "Aroon_Up": "Aroon up — bars since highest high as % of period; >70 = strong up.",
    "Aroon_Down": "Aroon down — bars since lowest low; >70 = strong down.",
    "RSI": "Relative strength index — 0–100 oscillator; >70 overbought, <30 oversold.",
    "Stochastic_K": "Stochastic %K — close position within the high-low range.",
    "Stochastic_D": "Stochastic %D — 3-period SMA of %K; signal line.",
    "StochRSI_K": "Stochastic RSI %K — RSI mapped to a 0–1 stochastic range.",
    "StochRSI_D": "Stochastic RSI %D — signal line of StochRSI %K.",
    "CCI": "Commodity channel index — deviation from statistical mean; ±100 = extreme.",
    "Williams_R": "Williams %R — overbought/oversold like inverse stochastic; −20/−80.",
    "ROC": "Rate of change — percentage change over N periods.",
    "MFI": "Money flow index — volume-weighted RSI; >80 overbought, <20 oversold.",
    "TSI": "True strength index — double-smoothed momentum; crossovers signal.",
    "AO": "Awesome oscillator — 5-period vs 34-period midpoint SMA difference.",
    "ATR": "Average true range — volatility as smoothed true range in price units.",
    "BB_upper": "Bollinger upper band — SMA + 2 standard deviations.",
    "BB_middle": "Bollinger middle band — 20-period SMA.",
    "BB_lower": "Bollinger lower band — SMA − 2 standard deviations.",
    "BB_width": "Bollinger bandwidth — (upper−lower)/middle as a fraction.",
    "KC_upper": "Keltner upper channel — EMA + 2 × ATR.",
    "KC_lower": "Keltner lower channel — EMA − 2 × ATR.",
    "Donchian_upper": "Donchian upper — highest high of the last N periods.",
    "Donchian_mid": "Donchian mid — average of upper and lower channels.",
    "Donchian_lower": "Donchian lower — lowest low of the last N periods.",
    "StdDev": "Rolling standard deviation of closes.",
    "HistVol": "Historical volatility — annualised standard deviation of log returns.",
    "VWAP": "Volume-weighted average price — session-anchored fair-value level.",
    "OBV": "On-balance volume — cumulative volume by price direction.",
    "AD": "Accumulation/distribution — volume-weighted close location within bar.",
    "CMF": "Chaikin money flow — 20-period average of AD volume ratio.",
    "Vol_vs_Avg20": "Current volume / 20-period average volume ratio.",
    "RelVol": "Relative volume — current bar volume vs same-bar historical average.",
    "OR_high": "Opening range high — high of the first N-minute bar(s) of the session.",
    "OR_low": "Opening range low — low of the first N-minute bar(s) of the session.",
    "PriorDay_high": "Previous session's high.",
    "PriorDay_low": "Previous session's low.",
    "PriorDay_close": "Previous session's close.",
    "PriorWeek_high": "Previous week's high.",
    "PriorWeek_low": "Previous week's low.",
    "PriorWeek_close": "Previous week's close.",
    "Gap": "Gap classification: up / down / inside relative to prior close.",
    "Pivot": "Classic pivot point — (prior H + L + C) / 3.",
    "S1": "Pivot support 1 — 2×Pivot − prior high.",
    "R1": "Pivot resistance 1 — 2×Pivot − prior low.",
    "SwingHigh": "Most recent confirmed swing high.",
    "SwingLow": "Most recent confirmed swing low.",
    "SR_clusters": "Support/resistance price clusters from local extremes.",
}


def _safe_last(series: pd.Series | pd.DataFrame | None) -> float | None:
    """Extract the last non-NaN scalar from a Series/DataFrame column."""
    if series is None:
        return None
    if isinstance(series, pd.DataFrame):
        if series.empty:
            return None
        series = series.iloc[:, 0]
    if series.empty:
        return None
    val = series.dropna()
    if val.empty:
        return None
    return round(float(val.iloc[-1]), 6)


def _safe_dict(series: pd.Series | pd.DataFrame | None, prefix: str = "") -> dict[str, float | None]:
    """Extract last values from a multi-column DataFrame result."""
    out: dict[str, float | None] = {}
    if series is None:
        return out
    if isinstance(series, pd.Series):
        out[prefix or series.name or "value"] = _safe_last(series)
        return out
    for col in series.columns:
        key = f"{prefix}_{col}" if prefix else str(col)
        out[key] = _safe_last(series[col])
    return out


def _compute_trend(df: pd.DataFrame) -> dict[str, Any]:
    """Trend indicators: SMA/EMA/WMA/HMA families, MACD, ADX/DMI, PSAR, Ichimoku, SuperTrend, Aroon."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    out: dict[str, Any] = {}

    for period in (9, 20, 50, 200):
        out[f"SMA_{period}"] = _safe_last(ta.sma(close, length=period))
        out[f"EMA_{period}"] = _safe_last(ta.ema(close, length=period))
    out["WMA_20"] = _safe_last(ta.wma(close, length=20))
    out["HMA_20"] = _safe_last(ta.hma(close, length=20))

    macd_result = ta.macd(close)
    out.update(_safe_dict(macd_result, "MACD"))

    adx_result = ta.adx(high, low, close)
    out.update(_safe_dict(adx_result, "ADX"))

    psar_result = ta.psar(high, low, close)
    out.update(_safe_dict(psar_result, "PSAR"))

    ichi = ta.ichimoku(high, low, close)
    if ichi is not None and isinstance(ichi, tuple) and len(ichi) >= 1:
        out.update(_safe_dict(ichi[0], "Ichimoku"))

    st = ta.supertrend(high, low, close)
    out.update(_safe_dict(st, "SuperTrend"))

    aroon_result = ta.aroon(high, low)
    out.update(_safe_dict(aroon_result, "Aroon"))

    return out


def _compute_momentum(df: pd.DataFrame) -> dict[str, Any]:
    """Momentum: RSI, Stoch, StochRSI, CCI, Williams %R, ROC, MFI, TSI, AO."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    out: dict[str, Any] = {}

    out["RSI_14"] = _safe_last(ta.rsi(close, length=14))

    stoch_result = ta.stoch(high, low, close)
    out.update(_safe_dict(stoch_result, "Stoch"))

    stochrsi_result = ta.stochrsi(close)
    out.update(_safe_dict(stochrsi_result, "StochRSI"))

    out["CCI_20"] = _safe_last(ta.cci(high, low, close, length=20))
    out["Williams_R_14"] = _safe_last(ta.willr(high, low, close, length=14))
    out["ROC_12"] = _safe_last(ta.roc(close, length=12))
    out["MFI_14"] = _safe_last(ta.mfi(high, low, close, volume, length=14))

    tsi_result = ta.tsi(close)
    out.update(_safe_dict(tsi_result, "TSI"))

    out["AO"] = _safe_last(ta.ao(high, low))

    return out


def _compute_volatility(df: pd.DataFrame) -> dict[str, Any]:
    """Volatility: ATR, Bollinger, Keltner, Donchian, StdDev, HistVol."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    out: dict[str, Any] = {}

    out["ATR_14"] = _safe_last(ta.atr(high, low, close, length=14))

    bb = ta.bbands(close)
    out.update(_safe_dict(bb, "BB"))

    kc = ta.kc(high, low, close)
    out.update(_safe_dict(kc, "KC"))

    don = ta.donchian(high, low)
    out.update(_safe_dict(don, "Donchian"))

    out["StdDev_20"] = _safe_last(ta.stdev(close, length=20))

    import numpy as _np
    log_ret = (close / close.shift(1)).apply(_np.log).dropna()
    if len(log_ret) >= 20:
        out["HistVol_20"] = round(float(log_ret.rolling(20).std().iloc[-1]) * (252 ** 0.5), 6)
    else:
        out["HistVol_20"] = None

    return out


def _compute_volume(df: pd.DataFrame) -> dict[str, Any]:
    """Volume: VWAP, OBV, A/D, CMF, volume vs 20-avg, relative volume."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    out: dict[str, Any] = {}

    vwap = ta.vwap(high, low, close, volume)
    out["VWAP"] = _safe_last(vwap)

    out["OBV"] = _safe_last(ta.obv(close, volume))
    out["AD"] = _safe_last(ta.ad(high, low, close, volume))
    out["CMF_20"] = _safe_last(ta.cmf(high, low, close, volume, length=20))

    vol_avg = volume.rolling(20).mean()
    if not vol_avg.empty and vol_avg.iloc[-1] and vol_avg.iloc[-1] > 0:
        out["Vol_vs_Avg20"] = round(float(volume.iloc[-1]) / float(vol_avg.iloc[-1]), 4)
    else:
        out["Vol_vs_Avg20"] = None

    out["RelVol"] = compute_relative_volume(df)

    return out


def technical_snapshot(
    symbol: str,
    bars: pd.DataFrame,
    *,
    timeframe: str = "1d",
    fetch_time: datetime | None = None,
    include_sections: set[str] | None = None,
    include_candlestick_patterns: bool = True,
) -> dict[str, Any]:
    """ONE compact snapshot per ticker per timeframe.

    ``bars`` must have columns: open, high, low, close, volume and a
    DatetimeIndex (or a 'date'/'datetime' column). Rows are oldest-first.

    Returns a flat dict of all indicator values, structure levels, candle
    patterns, metadata, and the signal reference. Deterministic: same
    bars in → same numbers out. No AI. No network.
    """
    include = include_sections or {
        "trend",
        "momentum",
        "volatility",
        "volume",
        "structure",
        "candles",
    }
    if bars.empty or len(bars) < 2:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars": 0,
            "error": "insufficient bars",
        }

    df = bars.copy()
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            raise ValueError(f"bars DataFrame missing required column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if not isinstance(df.index, pd.DatetimeIndex):
        for candidate in ("datetime", "date", "timestamp"):
            if candidate in df.columns:
                df.index = pd.DatetimeIndex(df[candidate])
                break

    last_bar_time = str(df.index[-1]) if isinstance(df.index, pd.DatetimeIndex) else None
    from varma.clock import now_london
    stamp = fetch_time or now_london()

    result: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": len(df),
        "last_bar": last_bar_time,
        "last_close": round(float(df["close"].iloc[-1]), 6),
        "fetch_time": stamp.isoformat(),
        "delayed_data": True,
        "deterministic": True,
        "ai_calls": 0,
    }

    if "trend" in include:
        result["trend"] = _compute_trend(df)
    if "momentum" in include:
        result["momentum"] = _compute_momentum(df)
    if "volatility" in include:
        result["volatility"] = _compute_volatility(df)
    if "volume" in include:
        result["volume"] = _compute_volume(df)
    if "structure" in include:
        result["structure"] = {
            "opening_range": compute_opening_range(df, timeframe=timeframe),
            "prior_day": compute_prior_day_levels(df),
            "prior_week": compute_prior_week_levels(df),
            "gap": compute_gap(df),
            "pivots": compute_pivot_points(df),
            "session_levels": compute_session_levels(df),
            "swing_points": compute_swing_points(df),
            "sr_clusters": compute_support_resistance_clusters(df),
        }
    if "candles" in include:
        result["candles"] = compute_candlestick_patterns(
            df, include_patterns=include_candlestick_patterns
        )
    result["signal_reference"] = SIGNAL_REFERENCE

    return result
