"""Employee AI-context categorisation (PR #2: evidence-driven context slimming).

This module documents and verifies the STATIC / PERSISTENT / DYNAMIC split of the
context assembled for an AI invocation. It does NOT change what is stored or how
memory works; it only classifies the keys that are delivered to the model so the
separation is explicit and testable.

- STATIC: stable identity/role/relationship scaffolding that rarely changes.
- PERSISTENT: values retrieved from Varma Corp memory stores (Document 08).
- DYNAMIC: information that genuinely changes between invocations (new market data,
  the current task artefact, a compact current-controls hint, inbox, etc.).

The compact controls hint (`controls_hint`) is DYNAMIC and informational only; the
authoritative deterministic ControlEngine remains the sole enforcement surface.
"""

from __future__ import annotations

from typing import Any

STATIC_KEYS: frozenset[str] = frozenset(
    {
        "identity",
        "employee",
        "role_knowledge",
        "professional_foundation",
        "authority_boundaries",
        "responsibilities",
        "memory_pointers",
        "skills",
        "relationships",
        "llm_call_is_invocation",
        "employee_is_not_a_prompt",
        "independent_of_employee_ids",
    }
)

PERSISTENT_KEYS: frozenset[str] = frozenset(
    {
        "lessons",
        "working",
        "org_knowledge_titles",
        "blank_prompt",
        "originator_beliefs_loaded",
        "excluded_originator_lessons",
    }
)

DYNAMIC_KEYS: frozenset[str] = frozenset(
    {
        "news",
        "prices",
        "watchlist_label",
        "controls_hint",
        "thesis",
        "proposed",
        "policy",
        "latest_brief",
        "produced_brief",
        "received_brief",
        "latest_thesis",
        "latest_challenge_review",
        "latest_risk_decision",
        "inbox",
        "message",
        "cannot_approve_live_trading",
    }
)


def classify(context: dict[str, Any]) -> dict[str, list[str]]:
    """Group a delivered context's top-level keys into static/persistent/dynamic.

    `other` holds any unclassified key so tests can assert full coverage (no
    silently-untracked context growth).
    """
    static: list[str] = []
    persistent: list[str] = []
    dynamic: list[str] = []
    other: list[str] = []
    for key in context:
        if key in STATIC_KEYS:
            static.append(key)
        elif key in PERSISTENT_KEYS:
            persistent.append(key)
        elif key in DYNAMIC_KEYS:
            dynamic.append(key)
        else:
            other.append(key)
    return {
        "static": sorted(static),
        "persistent": sorted(persistent),
        "dynamic": sorted(dynamic),
        "other": sorted(other),
    }
