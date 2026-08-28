# Varma Corp — BUILD STATE (engineering handover)

Concise, current-state handover for the next engineering agent (including Grok Bot). Read this
FIRST, then `docs/PROJECT_MAP.md` and `docs/SPEC_INDEX.md`. Do not rescan the whole repository or
re-read Documents 00–18 unless a specific task requires it. The **source code is authoritative**; if
this file disagrees with the code, the code wins and this file must be corrected.

_Last updated: 2026-08-28._

## 0. RECOVERY / CONTINUATION INSTRUCTION
> Read `BUILD_STATE.md` first. Then read `PROJECT_MAP.md` and `SPEC_INDEX.md`. Do not rescan the
> entire repository unless required. Verify the current git state. Continue from the recorded NEXT
> STEP. Preserve all governance and safety rules.

## 1. CURRENT BUILD STATUS
- **Formal completion percentage: not established — do not invent one.** The project is the first
  vertical slice per Document 18; the company is CLOSED until Grand Opening (Board Addendum I).
- **Working:** FastAPI kernel; 7 durable AI employees; skills (brief, challenge, risk); on-demand
  routines (brief, challenge, risk-deny, 07:30 meeting, nightly memory filter, flatten, backup);
  four memory stores; durable DB handoffs; deterministic control engine; internal paper simulator;
  Board observability; 2D desktop UI; chat (Board-only); AI-usage measurement; context slimming and
  selective memory retrieval. Full test suite: **175 passing, 0 failures.**
- **Incomplete / not built:** first paper-trade path; Grand Opening (PAPER or LIVE); real LLM binding;
  live/broker execution; semantic memory summarisation; response caching; event-idempotency schema.
- **Deliberately closed/disabled:** `trading_mode=LIVE_BLOCKED`; PAPER execution CLOSED; BROKER_PAPER
  and LIVE ports UNLOADED; FakeLLM is the only LLM (no network); Talk/voice disabled.

## 2. COMPLETED WORK (this optimisation run + prior)
- **PR #1 — [#23] Safe Token-Efficiency Foundation** (branch `cursor/token-efficiency-foundation-280b`):
  project map (`docs/PROJECT_MAP.md`, `SPEC_INDEX.md`, `GLOSSARY.md`, `knowledge/index.json`) +
  non-invasive AI-usage measurement (`varma/observability/ai_usage.py`, `AICallLog` table, transparent
  `MeasuredLLM` wrapper, `ai_usage_summary`). 153 → 158 tests.
- **PR #2 — [#24] Evidence-Driven Context Slimming** (branch `cursor/context-slimming-280b`): replaced
  the verbose `ControlEngine.snapshot()` in AI context with a compact `constraints_hint()`; dropped
  duplicated lessons; added STATIC/PERSISTENT/DYNAMIC classifier (`varma/employees/context.py`). Brief
  context 21,000 → 4,694 chars. 158 → 165 tests.
- **PR #3–#8 — [#25] Master Runtime Optimisation** (branch `cursor/runtime-token-optimisation-280b`):
  Stage 1 bounded chat context; Stage 2 selective (recency) lesson retrieval; Stage 3 idempotent
  handoffs (no schema); Stages 6/7/9 deterministic-first guard + daily-operating-day simulation.
  Stages 4 (snapshot cache) and 5 (response caching) intentionally NOT implemented (safety). 165 → 173.
- **Board memory policy — [#26] Selective working + org memory** (branch `cursor/selective-memory-policy-280b`):
  recency-selective retrieval extended to working memory and org-memory titles; nothing deleted; full
  durable records preserved and Board-auditable. 173 → 175.

## 3. CURRENT BRANCH / REPOSITORY STATE
- **Current branch when this file was written:** `cursor/build-state-handover-280b` (docs only).
- **Stacked feature branches (each based on the previous), all AWAITING REVIEW — not merged to `main`:**
  `cursor/token-efficiency-foundation-280b` (#23) → `cursor/context-slimming-280b` (#24) →
  `cursor/runtime-token-optimisation-280b` (#25) → `cursor/selective-memory-policy-280b` (#26).
- **Latest functional commit:** `Selective retrieval for working + org memory (Board memory policy 2026-08-28)`.
- **Unrelated open PR:** `#22` adds `.cursor/environment.json` (Cloud Agent environment); independent of this work.
- Verify live state with `git log --oneline` and `git branch` before continuing.

## 4. ARCHITECTURE STATE (see `docs/PROJECT_MAP.md` for file-level detail)
- **Application:** FastAPI kernel `varma/kernel/app.py` (entry `varma/__main__.py`). Desktop UI is a
  projection; DB is the source of truth. No daemon/scheduler; routines are on-demand.
- **Database:** SQLAlchemy `varma/db/` (SQLite dev / Postgres via compose). Schema unchanged this run
  except the additive `AICallLog` table from PR #1.
- **Employee system:** 7 durable records (Document 03) in `varma/db/seed.py` + `varma/employees/brain.py`;
  runtime in `varma/employees/runtime.py`. Slugs/identities/roles unchanged.
- **Memory system:** four stores in `varma/memory/stores.py` (working, employee lessons, org knowledge,
  append-only evidence) + nightly filter. AI context now uses recency-selective retrieval for lessons,
  working memory and org titles; storage/semantics unchanged; nothing deleted.
- **Controls/governance:** deterministic `varma/controls/engine.py` (+ addenda A/C/E/F/I/J, LSE hold,
  kill switch, risk). Authoritative; AI never enforces controls. `constraints_hint()` is informational only.
- **Virtual office:** `desktop/` (2D office + right-hand Board panel; fetch-on-click, no polling).
- **Trading simulation:** internal paper fill simulator `varma/paper/` (not a broker). No fills while CLOSED.
- **AI/LLM boundary:** `varma/ports/llm.py` — `FakeLLM` default, wrapped by `MeasuredLLM`. Four task
  strings only: `prepare_daily_intelligence_brief`, `challenge_sample_thesis`, `review_unsafe_path`, `chat`.

## 5. AI / TOKEN-EFFICIENCY STATE
- **Implemented:** measurement (PR #1); compact control hint + context slimming (PR #2); bounded chat
  context, selective lesson retrieval, idempotent handoffs, deterministic-first discipline (PR #25);
  selective working/org-memory retrieval (PR #26).
- **Key measurements (FakeLLM; `estimated_tokens` = labelled chars/4 heuristic, NOT real provider tokens;
  no real model is connected):**
  - Brief AI context: **21,000 → 4,694 chars** (~−77.6%); est per-call tokens ~5,894 → ~1,818 (~−69.2%).
  - Bounded chat (100-msg history): **20,070 → 1,699 chars** (capped at 6 turns, constant as history grows).
  - Selective lessons (41): **2,702 → 504 chars** (8 sent).
  - Selective working+org (30 each): **2,490 → 672 chars** (~−73%).
  - Daily simulation: 4 AI calls (brief/challenge/risk/chat), 0 real-model calls; deterministic ops
    (meeting/filter/backup/deny) = 0 AI calls.
- **Remaining known token risks:** org/working retrieval is recency-only (no semantic relevance ranking);
  no response caching; a real model would still resend static scaffolding each call (acceptable, small).

## 6. GOVERNANCE / SAFETY STATE (explicit)
- `trading_mode = LIVE_BLOCKED`. **No live trading authorised.**
- PAPER trading **CLOSED** unless explicitly opened through existing Board governance (Grand Opening).
- BROKER_PAPER and LIVE adapters **UNLOADED**; no broker connection; no live-order path exists.
- Kill switch and deterministic control engine **preserved and authoritative**; AI does not enforce controls.
- Addenda A/C/E/F/I/J and the LSE fail-closed hold **unchanged**.
- **Board Member remains the sole human authority.** Silence is not approval.

## 7. CURRENT OPEN DECISIONS (Board — do not invent answers)
1. Semantic **rolling summary** of older chat turns (if/how; must never replace durable records).
2. Any **permanent memory summarisation/pruning/retention** policy (current limits are reversible dev defaults).
3. **Response caching** — requires a safe real-model binding + freshness + cache-invalidation policy.
4. **Event-idempotency** that skips duplicate AI reasoning — needs a schema key or routine-behaviour change.
5. Deterministic **task-relevance ranking** beyond recency (importance scoring) — a memory-policy decision.
6. Any **real LLM provider binding** and, separately, Grand Opening PAPER then (much later) LIVE.

## 8. CURRENT NEXT STEP
- Get the stacked PRs **#23 → #24 → #25 → #26 reviewed and merged in order** into `main` (human/Board
  review), or continue new work based on `cursor/selective-memory-policy-280b` (latest state).
- Do **not** implement any Section 7 item until the Board decides it.
- Optional safe code step (no Board decision needed): a **deterministic** task-relevance filter for
  lessons/working memory layered on top of recency (e.g. prefer entries whose key matches the current
  task), preserving all records. Measure with `ai_usage_summary` before/after.

## 9. IMPORTANT COMPATIBILITY RULES (Grok Bot)
Do NOT rename/delete/move or structurally change: employee **slugs/identities/roles/relationships**;
FakeLLM **task strings**; `get_llm()`/`FakeLLM`/`LLMPort` names and the `fake` default; DB **table and
column names** (schema is additive-only — do not alter existing tables); module/package names under
`varma/`; control-engine **deny reasons** and addenda labels; Documents 00–18 (authoritative, outside the
repo). Keep changes additive; keep the full test suite green.

## 10. HOW TO CONTINUE
Read this file, then `PROJECT_MAP.md` + `SPEC_INDEX.md` (+ `knowledge/index.json` for machine navigation
and `GLOSSARY.md` for terms). Verify git state. Run `python3 -m pytest` (expect 175 passing on the latest
branch). Continue from Section 8. Preserve every governance and safety rule in Section 6.
