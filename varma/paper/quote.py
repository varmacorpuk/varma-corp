"""Paper quote conversion and notional sizing.

GBP exposure is the sizing unit. Day-trading desk: open and close in session.
Do not size by whole-share count. Do not call AI.

LSE pence (GBX): 3281p = £32.81. GBP names must not be FX-converted and must
not be divided by 100 when the feed last is already in pounds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from varma.controls.addendum_e import instrument_currency, instrument_quote_unit
from varma.paper.fx import FxQuote, convert_major_to_gbp, resolve_fx_quote
from varma.ports.data import FakeMarketData

PENCE_PER_POUND = 100.0
QTY_DECIMALS = 6
# Pence quote unit tokens. Yahoo uses "GBp" for pence.
# Important: `GBp` (pence) must not be conflated with `GBP` (pounds).
PENCE_UNITS = frozenset({"GBX", "GBp", "GBPENCE", "PENCE", "P"})

# Spread/slippage copied as numbers so quote.py does not import simulator.
# Must stay in lockstep with varma.paper.simulator ADVERSE_BPS (10).
ADVERSE_BPS = 10.0


def floor_qty(value: float) -> float:
    """Round quantity down so a notional size cannot creep over the cap."""
    qty = float(value)
    if qty <= 0:
        return 0.0
    factor = 10 ** QTY_DECIMALS
    return math.floor(qty * factor + 1e-12) / factor


def is_pence_unit(quote_unit: str | None) -> bool:
    """True for pence tokens (GBp, GBX, etc.). False for GBP (pounds).

    The feed's own currency/quote_unit field drives this — never assumed
    from the ticker suffix. Yahoo uses ``GBp`` for pence; ``GBP`` is pounds.
    """
    token = str(quote_unit or "").strip()
    if not token:
        return False
    if token == "GBP":
        return False
    if token in PENCE_UNITS:
        return True
    return token.upper() in {u.upper() for u in PENCE_UNITS} and token.upper() != "GBP"


def major_units(last: float, quote_unit: str | None) -> float:
    """Convert a native last to major currency units.

    3281p (GBX) → 32.81. A last already in GBP is left alone.
    """
    native = float(last)
    if is_pence_unit(quote_unit):
        return native / PENCE_PER_POUND
    return native


def pence_to_gbp(pence: float) -> float:
    return float(pence) / PENCE_PER_POUND


def delayed_price_row(symbol: str) -> dict[str, Any]:
    rows = FakeMarketData().delayed_prices([symbol])
    return rows[0] if rows else {"symbol": symbol, "last": 1.0, "currency": "GBP", "quote_unit": "GBP"}


def quote_unit_for_row(symbol: str, row: dict[str, Any]) -> str:
    """Prefer the feed's unit so a GBP last is not treated as pence."""
    raw = row.get("quote_unit")
    if raw not in (None, ""):
        return str(raw)
    return instrument_quote_unit(symbol)


def mid_gbp_from_row(
    symbol: str,
    row: dict[str, Any],
    *,
    at: datetime | None = None,
    fx_quote: FxQuote | dict[str, Any] | None = None,
) -> tuple[float, float, str, str, FxQuote]:
    """Return (native_last, mid_gbp, quote_currency, quote_unit, fx)."""
    native_last = float(row.get("last") or 0) or 1.0
    quote_ccy = str(row.get("currency") or instrument_currency(symbol)).upper()
    unit = quote_unit_for_row(symbol, row)
    major = major_units(native_last, unit)
    fx = resolve_fx_quote(quote_ccy, at=at, injected=fx_quote)
    mid = convert_major_to_gbp(major, quote_ccy, fx)
    if mid <= 0:
        mid = 1.0
    return native_last, mid, quote_ccy, unit, fx


def mark_gbp(symbol: str, *, at: datetime | None = None, fx_quote: FxQuote | None = None) -> float:
    _native, mid, _ccy, _unit, _fx = mid_gbp_from_row(
        symbol, delayed_price_row(symbol), at=at, fx_quote=fx_quote
    )
    return mid


@dataclass(frozen=True)
class PaperOrderEconomics:
    symbol: str
    side: str
    instrument_currency: str
    quote_currency: str
    quote_unit: str
    native_mid: float
    mid_gbp: float
    fill_price_gbp: float
    native_fill_price: float
    quantity: float
    notional_gbp: float
    sized_from_notional: bool
    requested_notional_gbp: float | None
    cap_check_gbp: float
    fx: FxQuote

    def to_audit(self) -> dict[str, Any]:
        return {
            "instrument_currency": self.instrument_currency,
            "quote_currency": self.quote_currency,
            "quote_unit": self.quote_unit,
            "native_mid": self.native_mid,
            "mid_gbp": self.mid_gbp,
            "fill_price_gbp": self.fill_price_gbp,
            "native_fill_price": self.native_fill_price,
            "quantity": self.quantity,
            "notional_gbp": self.notional_gbp,
            "sized_from_notional": self.sized_from_notional,
            "fx": self.fx.to_dict(),
        }


def paper_order_economics(
    order: dict[str, Any],
    *,
    at: datetime | None = None,
    price_row: dict[str, Any] | None = None,
    fx_quote: FxQuote | dict[str, Any] | None = None,
    max_position_gbp: float | None = None,
) -> PaperOrderEconomics:
    """GBP mid, fill, and quantity for a paper order.

    A target ``notional_gbp`` produces a fractional quantity. An explicit
    fractional ``quantity`` is honoured. After conversion the GBP notional
    is floored so it does not exceed a supplied cap.
    """
    symbol = str(order.get("symbol") or "")
    side = str(order.get("side") or "buy").lower()
    row = price_row or order.get("price_row") or delayed_price_row(symbol)
    injected = fx_quote if fx_quote is not None else order.get("fx_quote")
    native_mid, mid_gbp, quote_ccy, quote_unit, fx = mid_gbp_from_row(
        symbol, row, at=at, fx_quote=injected
    )
    ccy = instrument_currency(symbol)
    if side == "buy":
        fill_gbp = mid_gbp * (1.0 + ADVERSE_BPS / 10000.0)
    else:
        fill_gbp = mid_gbp * (1.0 - ADVERSE_BPS / 10000.0)
    fill_gbp = round(fill_gbp, 6)
    if quote_ccy == "GBP":
        native_fill = fill_gbp
    else:
        native_fill = round(native_mid * (1.0 + (ADVERSE_BPS if side == "buy" else -ADVERSE_BPS) / 10000.0), 6)

    raw_notional = order.get("notional_gbp")
    requested = abs(float(raw_notional)) if raw_notional not in (None, "") else None
    quantity = abs(float(order.get("quantity") or 0))
    sized_from_notional = False
    if quantity == 0 and requested:
        target = requested
        if max_position_gbp is not None:
            target = min(target, float(max_position_gbp))
        quantity = floor_qty(target / fill_gbp) if fill_gbp > 0 else 0.0
        sized_from_notional = True
    else:
        quantity = floor_qty(quantity) if quantity else 0.0

    notional = round(quantity * fill_gbp, 6)
    if sized_from_notional and requested is not None and notional > requested:
        quantity = floor_qty(requested / fill_gbp) if fill_gbp > 0 else 0.0
        notional = round(quantity * fill_gbp, 6)
    if max_position_gbp is not None and notional > float(max_position_gbp):
        quantity = floor_qty(float(max_position_gbp) / fill_gbp) if fill_gbp > 0 else 0.0
        notional = round(quantity * fill_gbp, 6)

    cap_check = notional
    if requested is not None:
        cap_check = max(requested, notional)

    return PaperOrderEconomics(
        symbol=symbol,
        side=side,
        instrument_currency=ccy,
        quote_currency=quote_ccy,
        quote_unit=quote_unit,
        native_mid=native_mid,
        mid_gbp=mid_gbp,
        fill_price_gbp=fill_gbp,
        native_fill_price=native_fill,
        quantity=quantity,
        notional_gbp=notional,
        sized_from_notional=sized_from_notional,
        requested_notional_gbp=requested,
        cap_check_gbp=cap_check,
        fx=fx,
    )
