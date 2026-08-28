"""Non-invasive AI-usage measurement (PR #1: Safe Token-Efficiency Foundation).

Observational only. This module wraps the existing ``LLMPort`` and records
deterministic metadata about each ``complete()`` call. It does NOT change prompts,
context, model selection, retries, or employee behaviour, and it adds no network
calls. FakeLLM remains the default.

Measurement value categories (kept explicitly distinct):
- REAL/DETERMINISTIC: ``input_chars`` / ``output_chars`` (exact serialized sizes),
  ``duration_ms`` (measured), ``provider`` (from the wrapped LLM).
- ESTIMATE: ``estimated_tokens`` = chars/4 heuristic. This is NOT a real vendor token
  count. ``estimate_is_heuristic`` is always True.
- FAKELLM UNIT: ``fake_cost_units`` mirrors the FakeLLM accounting unit, if present.
``is_real_model`` stays False while FakeLLM (or the unused optional stub) is active.
"""

from __future__ import annotations

import json
import time
from typing import Any

from varma.clock import now_london
from varma.db.engine import get_session_factory
from varma.db.models import AICallLog

# Providers that are NOT real, metered vendor models.
FAKE_PROVIDERS = frozenset({"fake", "", "none", "unused-optional"})

MEASUREMENT_NOTE = (
    "Observational only. Sizes are exact serialized character counts; "
    "estimated_tokens is a chars/4 heuristic, NOT a real vendor token count. "
    "FakeLLM is the default; no real model is connected."
)


def _safe_len(obj: Any) -> int:
    try:
        return len(json.dumps(obj, default=str))
    except Exception:
        try:
            return len(str(obj))
        except Exception:
            return 0


def estimate_tokens_from_chars(chars: int) -> int:
    """Deterministic, labelled heuristic. ~4 chars/token. Never claims real tokens."""
    if chars <= 0:
        return 0
    return max(1, chars // 4)


def record_ai_call(
    *,
    task: str,
    context: Any,
    result: Any,
    provider: str,
    duration_ms: int,
    session: Any | None = None,
) -> AICallLog | None:
    """Persist one AICallLog row. Best-effort: never raise into the caller."""
    input_chars = _safe_len(context)
    output_chars = _safe_len(result)

    emp: dict[str, Any] = {}
    if isinstance(context, dict):
        candidate = context.get("employee") or context.get("identity") or {}
        if isinstance(candidate, dict):
            emp = candidate
    employee_id = emp.get("id")
    employee_slug = emp.get("slug")

    fake_cost_units: int | None = None
    if isinstance(result, dict):
        cu = result.get("cost_units")
        if isinstance(cu, bool):
            cu = None
        if isinstance(cu, int):
            fake_cost_units = cu

    row = AICallLog(
        created_at=now_london(),
        task=str(task),
        employee_id=str(employee_id) if employee_id is not None else None,
        employee_slug=str(employee_slug) if employee_slug is not None else None,
        provider=str(provider),
        is_real_model=str(provider) not in FAKE_PROVIDERS,
        input_chars=input_chars,
        output_chars=output_chars,
        estimated_tokens=estimate_tokens_from_chars(input_chars + output_chars),
        estimate_is_heuristic=True,
        fake_cost_units=fake_cost_units,
        duration_ms=int(duration_ms),
        cache_hit=False,
        measurement_note=MEASUREMENT_NOTE,
    )

    own_session = session is None
    s = session or get_session_factory()()
    try:
        s.add(row)
        s.commit()
    finally:
        if own_session:
            s.close()
    return row


class MeasuredLLM:
    """Transparent observability wrapper around any ``LLMPort``.

    Flow is unchanged: caller -> MeasuredLLM.complete -> inner LLM -> result.
    Measurement is added around the call and can never alter the returned result.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def provider_name(self) -> str:
        return getattr(self._inner, "provider_name", "unknown")

    @property
    def inner(self) -> Any:
        return self._inner

    def complete(self, *, task: str, context: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        result = self._inner.complete(task=task, context=context)
        duration_ms = int(round((time.perf_counter() - start) * 1000))
        try:
            record_ai_call(
                task=task,
                context=context,
                result=result,
                provider=self.provider_name,
                duration_ms=duration_ms,
            )
        except Exception:
            # Measurement must never break or alter the AI call.
            pass
        return result


def ai_usage_summary(session: Any) -> dict[str, Any]:
    """Deterministic aggregation of recorded AI usage. No AI reasoning involved."""
    rows = session.query(AICallLog).all()
    by_task: dict[str, dict[str, int]] = {}
    for r in rows:
        bucket = by_task.setdefault(
            r.task,
            {"calls": 0, "input_chars": 0, "output_chars": 0, "estimated_tokens": 0, "fake_cost_units": 0},
        )
        bucket["calls"] += 1
        bucket["input_chars"] += int(r.input_chars or 0)
        bucket["output_chars"] += int(r.output_chars or 0)
        bucket["estimated_tokens"] += int(r.estimated_tokens or 0)
        bucket["fake_cost_units"] += int(r.fake_cost_units or 0)
    return {
        "total_calls": len(rows),
        "real_model_calls": sum(1 for r in rows if r.is_real_model),
        "total_input_chars": sum(int(r.input_chars or 0) for r in rows),
        "total_output_chars": sum(int(r.output_chars or 0) for r in rows),
        "total_estimated_tokens": sum(int(r.estimated_tokens or 0) for r in rows),
        "total_fake_cost_units": sum(int(r.fake_cost_units or 0) for r in rows),
        "by_task": by_task,
        "estimate_is_heuristic": True,
        "note": (
            "Deterministic measurement. estimated_tokens is a chars/4 heuristic, "
            "NOT a real vendor token count. FakeLLM is the default; no real model is connected."
        ),
    }
