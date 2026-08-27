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
        if task == "challenge_sample_thesis":
            return self._challenge(context)
        if task == "review_unsafe_path":
            return self._risk(context)
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
                "Recipient: CEO (AI employee). Research only. "
                "Watchlist items are TEMPORARY DEVELOPMENT DEFAULTS "
                "and are not the execution allow-list. No trade is proposed. "
                "trading_mode remains LIVE_BLOCKED. CEO cannot approve live trading."
            ),
            "items": items,
            "intended_recipient": "ceo",
            "no_execution_authority": True,
            "cost_units": 2,
        }

    def _challenge(self, context: dict[str, Any]) -> dict[str, Any]:
        thesis = context.get("thesis") or {}
        return {
            "verdict": "CHALLENGED",
            "summary": (
                "SAMPLE thesis challenged. It is not an order. Watchlist is not the allow-list. "
                "Delayed fake data is not an execution quote. trading_mode is LIVE_BLOCKED. "
                "Challenge cannot approve live trading."
            ),
            "objections": [
                {
                    "id": "not_an_order",
                    "claim": "This is a SAMPLE thesis, not a live trade and not an order.",
                },
                {
                    "id": "watchlist_is_not_allow_list",
                    "claim": (
                        f"Symbol {thesis.get('symbol') or 'AAPL'} is a TEMPORARY DEVELOPMENT DEFAULT "
                        "watchlist item, not execution-allow-list membership."
                    ),
                },
                {
                    "id": "live_blocked",
                    "claim": "trading_mode is LIVE_BLOCKED. PAPER allow-list is Board Addendum E. Gold is not authorised.",
                },
                {
                    "id": "no_gold",
                    "claim": "Gold is FUTURE SCOPE ONLY and is not an execution universe.",
                },
            ],
            "no_execution_authority": True,
            "does_not_approve_live": True,
            "cost_units": 1,
        }

    def _risk(self, context: dict[str, Any]) -> dict[str, Any]:
        policy = context.get("policy") or {}
        reasons = policy.get("reasons") or [policy.get("reason") or "RISK_DENIED"]
        return {
            "decision": "DENIED",
            "summary": (
                "DENIED. Unsafe/out-of-policy path. LIVE gold execution treating a SAMPLE thesis "
                f"as an order is refused. Reasons: {', '.join(str(r) for r in reasons)}. "
                "Risk cannot approve live trading. Board Member is the human authority."
            ),
            "cannot_approve_live": True,
            "cost_units": 1,
        }

    def _chat(self, context: dict[str, Any]) -> dict[str, Any]:
        employee = context.get("employee") or {}
        message = (context.get("message") or "").strip()
        brief = context.get("latest_brief") or context.get("received_brief")
        name = employee.get("display_name", "Employee")
        role = employee.get("role_title", "")
        slug = employee.get("slug") or ""
        if slug == "ceo":
            if brief:
                reply = (
                    f"{name} ({role}). I am the meeting recipient of the Market Intelligence brief. "
                    f"Latest pack headline: {brief.get('headline')}. "
                    f"Freshness: {brief.get('freshness_flag')}. "
                    f"I cannot approve live trading. That is a Board Member action. "
                    f"I cannot place orders or write controls. You asked: {message[:280]}"
                )
            else:
                reply = (
                    f"{name} ({role}). I have no meeting pack yet. "
                    f"Market Intelligence must run the 06:30 brief first. "
                    f"I cannot approve live trading. I cannot place orders. "
                    f"You asked: {message[:280]}"
                )
            return {"text": reply, "cost_units": 1}
        if slug == "challenge":
            thesis = context.get("latest_thesis") or {}
            review = context.get("latest_challenge_review") or {}
            reply = (
                f"{name} ({role}). I challenge SAMPLE theses, not live trades. "
                f"Latest thesis: {thesis.get('title') or 'none yet'}. "
                f"Verdict: {review.get('verdict') or 'none yet'}. "
                f"A SAMPLE thesis is not an order. I cannot approve live trading. "
                f"I cannot place orders or write controls. You asked: {message[:280]}"
            )
            return {"text": reply, "cost_units": 1}
        if slug == "risk":
            decision = context.get("latest_risk_decision") or {}
            reply = (
                f"{name} ({role}). Deny-path: {decision.get('decision') or 'no decision yet'}. "
                f"I deny unsafe and out-of-policy paths. I cannot approve live trading. "
                f"LIVE is blocked. PAPER allow-list is Board Addendum E. Gold is not authorised. "
                f"A SAMPLE thesis is not an order. Risk is independent of Trader. "
                f"You asked: {message[:280]}"
            )
            return {"text": reply, "cost_units": 1}
        if slug == "trader":
            reply = (
                f"{name} ({role}). I cannot write locks or approve live trading. "
                f"Risk stays independent of Trader. LIVE and BROKER_PAPER remain UNLOADED. "
                f"You asked: {message[:280]}"
            )
            return {"text": reply, "cost_units": 1}
        if slug == "quant-strategy":
            reply = (
                f"{name} ({role}). I cannot write locks or approve live trading. "
                f"Challenge stays independent of Quant. A sample is not an order. "
                f"You asked: {message[:280]}"
            )
            return {"text": reply, "cost_units": 1}
        if slug == "technology":
            reply = (
                f"{name} ({role}). I cannot write locks or approve live trading. "
                f"The office is a projection. The database is the ledger. "
                f"You asked: {message[:280]}"
            )
            return {"text": reply, "cost_units": 1}
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
