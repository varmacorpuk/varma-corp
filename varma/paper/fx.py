"""Stamped FX quotes for the internal paper simulator.

Limits, cash, position value, and P&L are GBP (Board Addendum A).
US allow-list names are USD. LSE three are GBP and must not be FX-converted.

Do not call AI. Do not load LIVE or BROKER_PAPER. A fill stores the rate
it used (pair, rate, source, timestamp) so it is auditable and deterministic.

Never apply a silent unnamed USDGBP constant. Every conversion goes through
a stamped quote: source + quoted_at. Development default is FakeDelayedFx
(same pattern as FakeMarketData). If that source is unavailable, take a
stamped public ECB quote at run time and record it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from varma.clock import now_london

USDGBP_PAIR = "USDGBP"
GBPGBP_PAIR = "GBPGBP"
IDENTITY_SOURCE = "identity"
FAKE_FX_SOURCE = "fake-delayed-fx-snapshot"
PUBLIC_FX_SOURCE = "frankfurter.app/ECB"
PUBLIC_USDGBP_URL = "https://api.frankfurter.app/latest?from=USD&to=GBP"
PUBLIC_FX_TIMEOUT_SEC = 2.0

# Delayed fake last, labelled like FakeMarketData. Not a Board FX vendor.
# Not LIVE. Observed_at is stamped on the quote, never applied as a bare number.
FAKE_USDGBP_LAST = 0.7481


@dataclass(frozen=True)
class FxQuote:
    pair: str
    rate: float
    source: str
    quoted_at: datetime
    retrieved_at: datetime
    delay_label: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["quoted_at"] = self.quoted_at.isoformat()
        payload["retrieved_at"] = self.retrieved_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "FxQuote | None":
        if not raw:
            return None
        quoted = raw.get("quoted_at")
        retrieved = raw.get("retrieved_at")
        if isinstance(quoted, str):
            quoted = datetime.fromisoformat(quoted)
        if isinstance(retrieved, str):
            retrieved = datetime.fromisoformat(retrieved)
        if quoted is None or retrieved is None:
            return None
        return cls(
            pair=str(raw.get("pair") or USDGBP_PAIR),
            rate=float(raw["rate"]),
            source=str(raw.get("source") or ""),
            quoted_at=quoted,
            retrieved_at=retrieved,
            delay_label=str(raw.get("delay_label") or ""),
            note=str(raw.get("note") or ""),
        )


def identity_fx_quote(*, at: datetime | None = None) -> FxQuote:
    """GBP→GBP. Not a USD rate. Used so GBP names are not double-converted."""
    now = at or now_london()
    return FxQuote(
        pair=GBPGBP_PAIR,
        rate=1.0,
        source=IDENTITY_SOURCE,
        quoted_at=now,
        retrieved_at=now,
        delay_label="none — same-currency identity",
        note="GBP instrument. No FX. Do not apply USDGBP.",
    )


class FakeDelayedFx:
    """TEMPORARY DEVELOPMENT DEFAULT FX. Labelled. Not live. Not Board FX."""

    def __init__(self, *, stale: bool = False) -> None:
        self.stale = stale

    def usdgbp(self, *, at: datetime | None = None) -> FxQuote:
        now = at or now_london()
        observed = now - timedelta(hours=28 if self.stale else 4)
        return FxQuote(
            pair=USDGBP_PAIR,
            rate=float(FAKE_USDGBP_LAST),
            source=FAKE_FX_SOURCE,
            quoted_at=observed,
            retrieved_at=now,
            delay_label="DELAYED — TEMPORARY DEVELOPMENT DEFAULT",
            note=(
                "Fake delayed USDGBP last. Labelled source + timestamp. "
                "Not a silent unnamed constant. Not LIVE. Not a vendor contract."
            ),
        )


def fetch_public_usdgbp(*, at: datetime | None = None, timeout: float = PUBLIC_FX_TIMEOUT_SEC) -> FxQuote:
    """Stamped public USDGBP from Frankfurter (ECB). No AI. Records source + date."""
    now = at or now_london()
    with urlopen(PUBLIC_USDGBP_URL, timeout=timeout) as resp:  # noqa: S310 — public ECB JSON
        raw = resp.read()
    import json

    payload = json.loads(raw.decode("utf-8"))
    rate = float(payload["rates"]["GBP"])
    if rate <= 0:
        raise ValueError("public USDGBP rate must be positive")
    quoted_date = str(payload.get("date") or "")
    quoted_at = now
    if quoted_date:
        quoted_at = datetime.fromisoformat(quoted_date).replace(tzinfo=now.tzinfo)
    return FxQuote(
        pair=USDGBP_PAIR,
        rate=rate,
        source=PUBLIC_FX_SOURCE,
        quoted_at=quoted_at,
        retrieved_at=now,
        delay_label="public ECB reference (frankfurter.app)",
        note="Stamped public quote. Not AI. Not LIVE. Recorded on the fill.",
    )


def resolve_fx_quote(
    currency: str,
    *,
    at: datetime | None = None,
    injected: FxQuote | dict[str, Any] | None = None,
    allow_public: bool = False,
) -> FxQuote:
    """Return a stamped quote for converting *currency* into GBP.

    GBP → identity (rate 1, not USDGBP).
    USD → injected quote, else FakeDelayedFx, else a public stamped quote
    if ``allow_public`` and the fake source is unavailable.
    """
    ccy = str(currency or "GBP").upper()
    if ccy == "GBP":
        return identity_fx_quote(at=at)

    if injected is not None:
        quote = injected if isinstance(injected, FxQuote) else FxQuote.from_dict(injected)
        if quote is not None and quote.rate > 0 and quote.source:
            return quote

    try:
        return FakeDelayedFx().usdgbp(at=at)
    except Exception:
        if not allow_public:
            raise

    try:
        return fetch_public_usdgbp(at=at)
    except (URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
        raise RuntimeError("no stamped FX quote available") from exc


def convert_major_to_gbp(amount: float, currency: str, quote: FxQuote) -> float:
    """Convert major units to GBP. GBP is passed through (no USD rate)."""
    ccy = str(currency or "GBP").upper()
    if ccy == "GBP":
        return float(amount)
    if ccy != "USD":
        raise ValueError(f"unsupported instrument currency {ccy}")
    if quote.pair != USDGBP_PAIR or quote.rate <= 0 or not quote.source:
        raise ValueError("USD conversion requires a stamped USDGBP quote")
    return float(amount) * float(quote.rate)
