"""LLMPort. FakeLLM is the default. Optional paid LLM env is unused by default."""

from __future__ import annotations

from typing import Any, Protocol

from varma.config import get_settings


class LLMPort(Protocol):
    provider_name: str

    def complete(self, *, task: str, context: dict[str, Any]) -> dict[str, Any]: ...


class FakeLLM:
    """Deterministic stand-in. No network. No paid API."""

    provider_name = "fake"

    def complete(self, *, task: str, context: dict[str, Any]) -> dict[str, Any]:
        if task == "prepare_daily_intelligence_brief":
            return self._brief(context)
        if task == "chat":
            return self._chat(context)
        return {"text": "Unsupported task for FakeLLM.", "cost_units": 1}

    def _brief(self, context: dict[str, Any]) -> dict[str, Any]:
        news = context.get("news") or []
        prices = context.get("prices") or []
        items = []
        for n in news:
            items.append(
                {
                    "claim": n.get("headline", ""),
                    "detail": n.get("summary", ""),
                    "source": n.get("source", ""),
                    "published_at": n.get("published_at", ""),
                    "symbols": n.get("symbols") or [],
                    "material": True,
                    "kind": "news",
                }
            )
        for p in prices:
            items.append(
                {
                    "claim": f"Delayed last for {p.get('symbol')} is {p.get('last')}.",
                    "detail": "Delayed snapshot; not a live quote and not an execution signal.",
                    "source": p.get("source", ""),
                    "published_at": p.get("observed_at", ""),
                    "symbols": [p.get("symbol")],
                    "material": True,
                    "kind": "price",
                }
            )
        headline = "Overnight listed-equity developments for the company meeting"
        if news:
            headline = f"Brief: {news[0].get('headline', headline)}"
        return {
            "headline": headline[:240],
            "summary": (
                "Structured intelligence brief for the 07:30 Europe/London meeting. "
                "Research only. Watchlist items are TEMPORARY DEVELOPMENT DEFAULTS "
                "and are not the execution allow-list. No trade is proposed. "
                "trading_mode remains LIVE_BLOCKED."
            ),
            "items": items,
            "intended_recipient": "company_meeting",
            "no_execution_authority": True,
            "cost_units": 2,
        }

    def _chat(self, context: dict[str, Any]) -> dict[str, Any]:
        employee = context.get("employee") or {}
        message = (context.get("message") or "").strip()
        brief = context.get("latest_brief")
        name = employee.get("display_name", "Research")
        role = employee.get("role_title", "Market Intelligence / Research Analyst")
        if brief:
            reply = (
                f"{name} ({role}). Latest verified brief headline: "
                f"{brief.get('headline')}. Freshness: {brief.get('freshness_flag')}. "
                f"I can discuss the brief; I cannot place orders or change controls. "
                f"You asked: {message[:280]}"
            )
        else:
            reply = (
                f"{name} ({role}). I have no verified brief stored yet. "
                f"Run the 06:30 routine or `python -m varma.routines.run_brief`. "
                f"I cannot place orders. You asked: {message[:280]}"
            )
        return {"text": reply, "cost_units": 1}


class UnusedOptionalLLM:
    """Present so an env can be set later. Not used unless provider != fake.

    This class refuses to run without an explicit opt-in and still does not
    ship a vendor client. Paid APIs are out of scope for this slice.
    """

    provider_name = "unused-optional"

    def complete(self, *, task: str, context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(
            "Optional LLM env is unused by default. Tests and this slice use FakeLLM. "
            "Do not call paid APIs from pytest."
        )


def get_llm() -> LLMPort:
    settings = get_settings()
    if settings.llm_provider in ("fake", "", "none"):
        return FakeLLM()
    # Even if someone sets a provider name, this slice does not bind a paid client.
    return UnusedOptionalLLM()
