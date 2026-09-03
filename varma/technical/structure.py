"""Structure-level indicators: session levels, pivots, gaps, S/R clusters.

Deterministic. No AI. No network. Ticker-agnostic.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def compute_opening_range(
    df: pd.DataFrame, *, timeframe: str = "1d", minutes: int = 30
) -> dict[str, float | None]:
    """Opening range high/low from the first N minutes of the session.

    For daily bars the first bar IS the opening range.
    For intraday, take bars within the first ``minutes`` of each session.
    """
    if df.empty:
        return {"OR_high": None, "OR_low": None}
    if timeframe in ("1d", "1wk", "1mo"):
        return {
            "OR_high": round(float(df["high"].iloc[0]), 6),
            "OR_low": round(float(df["low"].iloc[0]), 6),
        }
    if isinstance(df.index, pd.DatetimeIndex):
        session_start = df.index[0]
        cutoff = session_start + pd.Timedelta(minutes=minutes)
        opening = df.loc[df.index <= cutoff]
        if opening.empty:
            opening = df.iloc[:1]
        return {
            "OR_high": round(float(opening["high"].max()), 6),
            "OR_low": round(float(opening["low"].min()), 6),
        }
    return {
        "OR_high": round(float(df["high"].iloc[0]), 6),
        "OR_low": round(float(df["low"].iloc[0]), 6),
    }


def compute_prior_day_levels(df: pd.DataFrame) -> dict[str, float | None]:
    """Prior-day high/low/close. Requires ≥2 daily bars or intraday grouped by date."""
    if len(df) < 2:
        return {"PriorDay_high": None, "PriorDay_low": None, "PriorDay_close": None}
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
        unique_dates = sorted(set(dates))
        if len(unique_dates) >= 2:
            prev_date = unique_dates[-2]
            prev = df[dates == prev_date]
            return {
                "PriorDay_high": round(float(prev["high"].max()), 6),
                "PriorDay_low": round(float(prev["low"].min()), 6),
                "PriorDay_close": round(float(prev["close"].iloc[-1]), 6),
            }
    return {
        "PriorDay_high": round(float(df["high"].iloc[-2]), 6),
        "PriorDay_low": round(float(df["low"].iloc[-2]), 6),
        "PriorDay_close": round(float(df["close"].iloc[-2]), 6),
    }


def compute_prior_week_levels(df: pd.DataFrame) -> dict[str, float | None]:
    """Prior-week high/low/close."""
    if len(df) < 6:
        return {"PriorWeek_high": None, "PriorWeek_low": None, "PriorWeek_close": None}
    if isinstance(df.index, pd.DatetimeIndex):
        weeks = df.index.isocalendar().week
        unique_weeks = sorted(set(zip(df.index.isocalendar().year, weeks)))
        if len(unique_weeks) >= 2:
            prev_year, prev_week = unique_weeks[-2]
            iso = df.index.isocalendar()
            mask = (iso.year == prev_year) & (iso.week == prev_week)
            prev = df[mask.values]
            if not prev.empty:
                return {
                    "PriorWeek_high": round(float(prev["high"].max()), 6),
                    "PriorWeek_low": round(float(prev["low"].min()), 6),
                    "PriorWeek_close": round(float(prev["close"].iloc[-1]), 6),
                }
    last_5 = df.iloc[-10:-5] if len(df) >= 10 else df.iloc[:max(1, len(df) - 5)]
    if last_5.empty:
        return {"PriorWeek_high": None, "PriorWeek_low": None, "PriorWeek_close": None}
    return {
        "PriorWeek_high": round(float(last_5["high"].max()), 6),
        "PriorWeek_low": round(float(last_5["low"].min()), 6),
        "PriorWeek_close": round(float(last_5["close"].iloc[-1]), 6),
    }


def compute_gap(df: pd.DataFrame) -> dict[str, Any]:
    """Gap up/down/inside classification relative to prior close."""
    if len(df) < 2:
        return {"gap": None, "gap_size": None}
    prior_close = float(df["close"].iloc[-2])
    current_open = float(df["open"].iloc[-1])
    prior_high = float(df["high"].iloc[-2])
    prior_low = float(df["low"].iloc[-2])

    if current_open > prior_high:
        return {"gap": "up", "gap_size": round(current_open - prior_close, 6)}
    if current_open < prior_low:
        return {"gap": "down", "gap_size": round(current_open - prior_close, 6)}
    return {"gap": "inside", "gap_size": round(current_open - prior_close, 6)}


def compute_pivot_points(df: pd.DataFrame) -> dict[str, float | None]:
    """Classic pivot points from the prior bar's H/L/C."""
    if len(df) < 2:
        return {"Pivot": None, "S1": None, "S2": None, "R1": None, "R2": None}
    h = float(df["high"].iloc[-2])
    l = float(df["low"].iloc[-2])
    c = float(df["close"].iloc[-2])
    pivot = (h + l + c) / 3
    return {
        "Pivot": round(pivot, 6),
        "S1": round(2 * pivot - h, 6),
        "S2": round(pivot - (h - l), 6),
        "R1": round(2 * pivot - l, 6),
        "R2": round(pivot + (h - l), 6),
    }


def compute_session_levels(df: pd.DataFrame) -> dict[str, float | None]:
    """Current session high/low/open."""
    if df.empty:
        return {"session_high": None, "session_low": None, "session_open": None}
    if isinstance(df.index, pd.DatetimeIndex):
        today = df.index[-1].date()
        session = df[df.index.date == today]
        if not session.empty:
            return {
                "session_high": round(float(session["high"].max()), 6),
                "session_low": round(float(session["low"].min()), 6),
                "session_open": round(float(session["open"].iloc[0]), 6),
            }
    return {
        "session_high": round(float(df["high"].iloc[-1]), 6),
        "session_low": round(float(df["low"].iloc[-1]), 6),
        "session_open": round(float(df["open"].iloc[-1]), 6),
    }


def compute_swing_points(df: pd.DataFrame, lookback: int = 5) -> dict[str, float | None]:
    """Most recent confirmed swing high and swing low."""
    if len(df) < lookback * 2 + 1:
        return {"SwingHigh": None, "SwingLow": None}
    highs = df["high"].values
    lows = df["low"].values
    swing_high = None
    swing_low = None
    for i in range(len(highs) - lookback - 1, lookback - 1, -1):
        if swing_high is None:
            if all(highs[i] >= highs[i - lookback : i]) and all(
                highs[i] >= highs[i + 1 : i + lookback + 1]
            ):
                swing_high = round(float(highs[i]), 6)
        if swing_low is None:
            if all(lows[i] <= lows[i - lookback : i]) and all(
                lows[i] <= lows[i + 1 : i + lookback + 1]
            ):
                swing_low = round(float(lows[i]), 6)
        if swing_high is not None and swing_low is not None:
            break
    return {"SwingHigh": swing_high, "SwingLow": swing_low}


def compute_support_resistance_clusters(
    df: pd.DataFrame, n_clusters: int = 5, lookback: int = 50
) -> list[dict[str, Any]]:
    """Simple S/R clustering from local extremes in the last ``lookback`` bars."""
    if len(df) < 10:
        return []
    window = df.iloc[-lookback:] if len(df) >= lookback else df
    extremes: list[float] = []
    highs = window["high"].values
    lows = window["low"].values
    for i in range(2, len(highs) - 2):
        if highs[i] >= highs[i - 1] and highs[i] >= highs[i + 1]:
            extremes.append(float(highs[i]))
        if lows[i] <= lows[i - 1] and lows[i] <= lows[i + 1]:
            extremes.append(float(lows[i]))
    if not extremes:
        return []
    extremes.sort()
    clusters: list[dict[str, Any]] = []
    used: list[bool] = [False] * len(extremes)
    threshold = (extremes[-1] - extremes[0]) * 0.02 if extremes[-1] != extremes[0] else 1.0
    for i, price in enumerate(extremes):
        if used[i]:
            continue
        group = [price]
        used[i] = True
        for j in range(i + 1, len(extremes)):
            if not used[j] and abs(extremes[j] - price) <= threshold:
                group.append(extremes[j])
                used[j] = True
        clusters.append({
            "level": round(sum(group) / len(group), 6),
            "touches": len(group),
        })
    clusters.sort(key=lambda c: c["touches"], reverse=True)
    return clusters[:n_clusters]


def compute_relative_volume(df: pd.DataFrame, lookback: int = 20) -> float | None:
    """Current bar volume vs same-bar-of-day average over ``lookback`` sessions."""
    if len(df) < lookback or "volume" not in df.columns:
        return None
    vol = df["volume"]
    if vol.iloc[-1] == 0:
        return None
    avg = vol.iloc[-lookback:].mean()
    if avg == 0:
        return None
    return round(float(vol.iloc[-1]) / float(avg), 4)
