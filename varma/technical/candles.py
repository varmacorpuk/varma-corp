"""Candlestick pattern detection plus opening-range break/failed break.

Uses the complete pandas_ta ``cdl_pattern`` set (62 recognised patterns)
plus two desk-custom additions: OR break and failed OR break.

Deterministic. No AI. No network.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandas_ta as ta


def compute_candlestick_patterns(df: pd.DataFrame) -> dict[str, Any]:
    """Return last-bar candlestick pattern signals + OR break signals.

    Each library pattern returns an int: positive = bullish, negative = bearish,
    zero = no signal. We report only non-zero signals on the last bar.
    """
    if df.empty or len(df) < 3:
        return {"patterns": [], "or_break": None}

    open_ = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    patterns_found: list[dict[str, Any]] = []

    all_patterns = ta.cdl_pattern(open_, high, low, close, name="all")
    if all_patterns is not None and not all_patterns.empty:
        last_row = all_patterns.iloc[-1]
        for col in all_patterns.columns:
            val = last_row[col]
            if val != 0:
                name = str(col).replace("CDL_", "").lower()
                patterns_found.append({
                    "pattern": name,
                    "signal": "bullish" if val > 0 else "bearish",
                    "value": int(val),
                    "description": _PATTERN_DESCRIPTIONS.get(name, ""),
                })

    or_break = _opening_range_break(df)

    return {
        "patterns": patterns_found,
        "or_break": or_break,
        "patterns_checked": all_patterns.shape[1] if all_patterns is not None else 0,
    }


def _opening_range_break(df: pd.DataFrame) -> dict[str, Any] | None:
    """Opening-range break and failed break detection.

    Uses the first bar as the opening range (OR). A break is when a
    subsequent bar closes above OR high or below OR low. A failed break
    is when a bar breaks intrabar but closes back inside OR.
    """
    if len(df) < 3:
        return None
    or_high = float(df["high"].iloc[0])
    or_low = float(df["low"].iloc[0])
    last_high = float(df["high"].iloc[-1])
    last_low = float(df["low"].iloc[-1])
    last_close = float(df["close"].iloc[-1])

    broke_above = last_high > or_high
    broke_below = last_low < or_low
    closed_above = last_close > or_high
    closed_below = last_close < or_low
    inside = or_low <= last_close <= or_high

    if closed_above:
        return {"type": "break_up", "or_high": or_high, "or_low": or_low, "close": last_close}
    if closed_below:
        return {"type": "break_down", "or_high": or_high, "or_low": or_low, "close": last_close}
    if broke_above and inside:
        return {"type": "failed_break_up", "or_high": or_high, "or_low": or_low, "close": last_close}
    if broke_below and inside:
        return {"type": "failed_break_down", "or_high": or_high, "or_low": or_low, "close": last_close}
    return {"type": "inside", "or_high": or_high, "or_low": or_low, "close": last_close}


_PATTERN_DESCRIPTIONS: dict[str, str] = {
    "2crows": "Two crows — bearish reversal after an uptrend.",
    "3blackcrows": "Three black crows — three consecutive long bearish candles.",
    "3inside": "Three inside up/down — reversal confirmed by a third candle.",
    "3linestrike": "Three-line strike — three same-direction then a large reversal.",
    "3outside": "Three outside up/down — engulfing + confirmation candle.",
    "3starsinsouth": "Three stars in the south — bullish reversal in a downtrend.",
    "3whitesoldiers": "Three white soldiers — three consecutive long bullish candles.",
    "abandonedbaby": "Abandoned baby — star gap reversal with isolated doji.",
    "advanceblock": "Advance block — weakening bullish momentum, possible reversal.",
    "belthold": "Belt hold — strong open at extreme, long body same direction.",
    "breakaway": "Breakaway — five-candle reversal breaking out of a trend.",
    "closingmarubozu": "Closing marubozu — strong close at the extreme, no tail.",
    "concealbabyswall": "Concealed baby swallow — rare four-candle bullish reversal.",
    "counterattack": "Counterattack — opposing candle closes at same price.",
    "darkcloudcover": "Dark cloud cover — bearish candle closes below midpoint of prior.",
    "doji": "Doji — open ≈ close, indecision/reversal signal.",
    "dojistar": "Doji star — gapped doji after a trend candle.",
    "dragonflydoji": "Dragonfly doji — long lower shadow, open/close at high; bullish.",
    "engulfing": "Engulfing — current body fully contains prior body.",
    "eveningdojistar": "Evening doji star — three-candle bearish reversal with doji.",
    "eveningstar": "Evening star — three-candle bearish top reversal.",
    "gapsidesidewhite": "Gap side-by-side white — continuation gap with parallel bodies.",
    "gravestonedoji": "Gravestone doji — long upper shadow, open/close at low; bearish.",
    "hammer": "Hammer — small body at top, long lower shadow; bullish reversal.",
    "hangingman": "Hanging man — hammer shape in an uptrend; bearish warning.",
    "harami": "Harami — small body inside prior large body; reversal.",
    "haramicross": "Harami cross — doji inside prior body; strong reversal signal.",
    "highwave": "High wave — small body with very long shadows; indecision.",
    "hikkake": "Hikkake — inside bar false breakout trap.",
    "hikkakemod": "Modified hikkake — confirmed inside bar trap.",
    "homingpigeon": "Homing pigeon — two small bullish candles; reversal.",
    "identical3crows": "Identical three crows — three crows opening at prior close.",
    "inneck": "In-neck — bearish continuation; close near prior low.",
    "inside": "Inside bar — current range fully within prior range.",
    "invertedhammer": "Inverted hammer — long upper shadow at bottom; bullish reversal.",
    "kicking": "Kicking — two marubozu in opposite directions with a gap.",
    "kickingbylength": "Kicking by length — kicking confirmed by relative candle size.",
    "ladderbottom": "Ladder bottom — five-candle bullish reversal at bottom.",
    "longleggeddoji": "Long-legged doji — extreme indecision, very long shadows.",
    "longline": "Long line — single long candle in the direction of the trend.",
    "marubozu": "Marubozu — full body with no shadows; strong conviction.",
    "matchinglow": "Matching low — two equal lows; bullish support.",
    "mathold": "Mat hold — five-candle bullish continuation.",
    "morningdojistar": "Morning doji star — three-candle bullish reversal with doji.",
    "morningstar": "Morning star — three-candle bullish bottom reversal.",
    "onneck": "On-neck — bearish continuation closing at prior low.",
    "piercing": "Piercing — bullish candle closes above midpoint of prior bearish.",
    "rickshawman": "Rickshaw man — doji with very long equal shadows.",
    "risefall3methods": "Rising/falling three methods — five-candle continuation.",
    "separatinglines": "Separating lines — same open, opposite direction; continuation.",
    "shootingstar": "Shooting star — long upper shadow at top; bearish reversal.",
    "shortline": "Short line — small candle body; low conviction.",
    "spinningtop": "Spinning top — small body between upper and lower shadows; indecision.",
    "stalledpattern": "Stalled pattern — weakening trend near a top.",
    "sticksandwich": "Stick sandwich — bullish reversal with matching closes.",
    "takuri": "Takuri — dragonfly doji variant with very long lower shadow.",
    "tasukigap": "Tasuki gap — continuation gap not fully closed.",
    "thrusting": "Thrusting — weak bullish attempt that doesn't close above midpoint.",
    "tristar": "Tri-star — three doji in a row; rare reversal.",
    "unique3river": "Unique three river — three-candle bullish reversal.",
    "upsidegap2crows": "Upside gap two crows — bearish reversal above a gap.",
    "xsidegap3methods": "X side gap three methods — continuation gap held.",
}
