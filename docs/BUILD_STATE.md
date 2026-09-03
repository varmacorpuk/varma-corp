# Varma Corp — BUILD STATE (engineering handover)

Concise, current-state handover for the next engineering agent (including Grok Bot). Read this
FIRST, then `docs/PROJECT_MAP.md` and `docs/SPEC_INDEX.md`. Do not rescan the whole repository or
re-read Documents 00–18 unless a specific task requires it. Do not call AI for deterministic
operations. The **source code on the branch you have checked out is authoritative**; if this file
disagrees with that code, the code wins and this file must be corrected.

_Last updated: 2026-09-03._ Verified against GitHub (`gh pr list` / API) and a `main` checkout.
Do not invent a percent-complete. Chat is not the record.

## 0. RECOVERY / CONTINUATION INSTRUCTION
> Read `BUILD_STATE.md` first. Then read `PROJECT_MAP.md` and `SPEC_INDEX.md`. Do not rescan the
> entire repository unless required. Verify the current git state (`git log` / `git rev-parse HEAD`
> vs `origin/main`, and `gh pr list`). Continue from the recorded NEXT STEP. Preserve all governance
> and safety rules.

## 1. CURRENT BUILD STATUS
- **Formal completion percentage: not established — do not invent one.** The project is the first
  vertical slice per Document 18; the company is CLOSED until Grand Opening (Board Addendum I).
- **On default branch `main` (this file's home after 2026-09-03):** FastAPI kernel; 7 durable AI
  employees; skills (brief, challenge, risk); on-demand routines (brief, challenge, risk-deny,
  07:30 meeting, nightly memory filter, flatten, backup); four memory stores; durable DB handoffs;
  deterministic ControlEngine; internal paper simulator; Board observability; 2D desktop UI; chat
  (Board-only); FakeLLM default wrapped by MeasuredLLM; `AICallLog` + `ai_usage_summary`.
  Pytest on `main`: **158 passing, 0 failures** (measured 2026-09-03).
- **GitHub-merged but not on `main`:** PRs #24–#26 (context slimming, bounded chat, selective
  lessons/working/org retrieval, idempotent handoffs, daily-sim 0 AI on deterministic ops) plus
  the original #27 BUILD_STATE. Those commits live on stacked feature branches (tip
  `07495a328a1754e86d2ee1c1bfab121deccf04dd`). That stack reported **175** passing tests. A
  `main` checkout does **not** contain `constraints_hint()`, `varma/employees/context.py`, or
  those extra tests. This PR restores BUILD_STATE onto `main` as documentation only; it does
  **not** land that runtime.
- **Incomplete / not built:** first paper-trade path; Grand Opening (PAPER or LIVE); real LLM
  binding; live/broker execution; semantic memory summarisation; response caching;
  event-idempotency schema.
- **Deliberately closed/disabled:** `trading_mode=LIVE_BLOCKED`; PAPER execution CLOSED (no fills;
  £1,000 is future paper start only); BROKER_PAPER and LIVE ports UNLOADED; FakeLLM is the only
  LLM (no network); Talk/voice disabled. Token-efficiency stages 4 (snapshot cache) and 5
  (response cache) are intentionally **not** implemented (safety).

## 2. COMPLETED WORK (GitHub PR state, verified 2026-09-03)
Merged **into `main`:** PRs **#1–#20**, **#22**, **#23**. (#16 is merged — Addendum I company
CLOSED until Grand Opening, not an unmerged close.)

| PR | On `main`? | What |
| --- | --- | --- |
| #1–#15, #17–#20 | yes | Kernel slice, observability, addenda A/C/E/F/I/J, brains + four stores, LSE fail-closed hold |
| #16 | yes | Addendum I: PAPER execution CLOSED until Grand Opening |
| #22 | yes | `.cursor/environment.json` (Cloud Agent install + start) |
| #23 | yes | Project map + non-invasive AI usage (`MeasuredLLM`, `AICallLog`, `ai_usage_summary`). 153 → 158 tests |
| #24 | **no** (merged into `cursor/token-efficiency-foundation-280b`) | `constraints_hint()` + STATIC/PERSISTENT/DYNAMIC classifier. 158 → 165 on that stack |
| #25 | **no** (merged into `cursor/context-slimming-280b`) | Bounded chat (6 turns); selective lessons (8); idempotent handoffs; daily sim 0 AI on deterministic ops. Stages 4–5 **not** implemented. 165 → 173 on that stack |
| #26 | **no** (merged into `cursor/runtime-token-optimisation-280b`) | Selective working/org titles (8). 173 → 175 on that stack |
| #27 | **no** (merged into `cursor/selective-memory-policy-280b` at `07495a3`) | Original `docs/BUILD_STATE.md`. Was 404 on raw `main`. Restored and corrected by this PR |

**Open (leave open):** PR **#21** only — LSE hold: deny SHEL.L / AZN.L / ULVR.L after London cash
close. Do **not** merge or rebase it. Do **not** encode a split-clock. Addendum C stays
flatten-at-US-close.

## 3. CURRENT BRANCH / REPOSITORY STATE
- **Default branch `main` HEAD (2026-09-03 fetch):** `90d18d1` — PR #23 merge. Contains #1–#20,
  #22, #23. Does **not** contain #24–#27 runtime or the original BUILD_STATE blob.
- **Why BUILD_STATE 404'd on `main`:** #23–#27 were a stacked chain. Only #23 targeted `main`.
  #24–#27 GitHub-merged into the previous feature branch, so `docs/BUILD_STATE.md` existed at
  merge commit `07495a328a1754e86d2ee1c1bfab121deccf04dd` and not at default-branch HEAD.
  This PR puts BUILD_STATE on `main`.
- **Stale claim this file used to make:** §3 said #23–#26 were awaiting merge and #22 was open.
  Those PRs **are** GitHub-MERGED. They are **not** all on `main`. #21 remains the only open PR.
- Verify live state with `git log --oneline origin/main` and `gh pr list --state all` before
  continuing. Do not assume GitHub "MERGED" means the commit is in a `main` checkout.

## 4. ARCHITECTURE STATE (see `docs/PROJECT_MAP.md` for file-level detail)
- **Application:** FastAPI kernel `varma/kernel/app.py` (entry `varma/__main__.py`). Desktop UI is a
  projection; DB is the source of truth. No daemon/scheduler; routines are on-demand.
- **Database:** SQLAlchemy `varma/db/` (SQLite dev / Postgres via compose). Additive `AICallLog`
  table from #23 is on `main`.
- **Employee system:** 7 durable records (Document 03) in `varma/db/seed.py` + `varma/employees/brain.py`;
  runtime in `varma/employees/runtime.py`. Slugs/identities/roles unchanged. On `main`, AI context
  still uses `ControlEngine.snapshot()` (verbose). `constraints_hint()` exists only on the #24 stack.
- **Memory system:** four stores in `varma/memory/stores.py` (working, employee lessons, org knowledge,
  append-only evidence) + nightly filter. Selective retrieval (#25/#26) is on the stacked branches,
  not on `main`. Nothing is deleted in either place.
- **Controls/governance:** deterministic `varma/controls/engine.py` (+ addenda A/C/E/F/I/J, LSE
  fail-closed hold, kill switch, risk). Authoritative; AI never enforces controls.
- **Virtual office:** `desktop/` (2D office + right-hand Board panel; fetch-on-click, no polling).
- **Trading simulation:** internal paper fill simulator `varma/paper/` (not a broker). No fills while CLOSED.
- **AI/LLM boundary:** `varma/ports/llm.py` — `FakeLLM` default, wrapped by `MeasuredLLM`. Four task
  strings only: `prepare_daily_intelligence_brief`, `challenge_sample_thesis`, `review_unsafe_path`, `chat`.
  Do not bind a real LLM.

## 5. AI / TOKEN-EFFICIENCY STATE
- **On `main`:** measurement only (#23). Measure with `ai_usage_summary` before any further runtime
  token work. Do not call AI for deterministic ops (meeting / filter / backup / deny).
- **On stacked branches #24–#26 (not `main`):** compact `constraints_hint()`; bounded chat (6 turns);
  selective lessons (8); idempotent handoffs; selective working/org titles (8); daily simulation
  4 FakeLLM calls (brief/challenge/risk/chat) and 0 AI on deterministic ops.
- **Key measurements (FakeLLM on the stack; `estimated_tokens` = labelled chars/4 heuristic, NOT
  real provider tokens; no real model is connected):**
  - Brief AI context: **21,000 → 4,694 chars** (~−77.6%); est per-call tokens ~5,894 → ~1,818 (~−69.2%).
  - Bounded chat (100-msg history): **20,070 → 1,699 chars** (capped at 6 turns).
  - Selective lessons (41): **2,702 → 504 chars** (8 sent).
  - Selective working+org (30 each): **2,490 → 672 chars** (~−73%).
- **Intentionally not implemented (anywhere):** stage 4 snapshot cache; stage 5 response caching
  (safety). Remaining known risks if that stack lands: recency-only retrieval; a real model would
  still resend static scaffolding.

## 6. GOVERNANCE / SAFETY STATE (explicit)
- `trading_mode = LIVE_BLOCKED`. **No live trading authorised.**
- PAPER trading **CLOSED** unless explicitly opened through existing Board governance (Grand Opening).
  No fills. £1,000 is future paper start only.
- BROKER_PAPER and LIVE adapters **UNLOADED**; no broker connection; no live-order path exists.
- Kill switch and deterministic control engine **preserved and authoritative**; AI does not enforce controls.
- Addenda A/C/E/F/I/J and the LSE fail-closed hold **unchanged**. Do not rewrite Addendum C.
- **Board Member remains the sole human authority.** Silence is not approval. Do not write Board
  policy into chat comments. GitHub is code only: never paper book, secrets, or employee memory.
- Specs Documents 00–18 live **outside** the repo (see `ARCHITECTURE.md`). Do not copy the full spec set in.

## 7. CURRENT OPEN DECISIONS (Board — do not invent answers)
1. Semantic **rolling summary** of older chat turns (if/how; must never replace durable records).
2. Any **permanent memory summarisation/pruning/retention** policy (stack limits are reversible dev defaults).
3. **Response caching** — requires a safe real-model binding + freshness + cache-invalidation policy.
4. **Event-idempotency** that skips duplicate AI reasoning — needs a schema key or routine-behaviour change.
5. Deterministic **task-relevance ranking** beyond recency (importance scoring) — a memory-policy decision.
6. Any **real LLM provider binding** and, separately, Grand Opening PAPER then (much later) LIVE.

## 8. CURRENT NEXT STEP
- Treat **this file on `main`** as the handover. Do not rescan the repo or re-read Documents 00–18
  unless a specific task requires it.
- **Do not merge PR #21.** Leave it open. Do not encode a split-clock.
- **Do not bind a real LLM.** FakeLLM remains default.
- **Do not implement any Section 7 item** until the Board decides it.
- Landing #24–#26 onto `main` is a **separate runtime PR**, not docs work. Until then, a `main`
  checkout will not show 175 tests or `constraints_hint()`. If that stack is landed, update this
  file and `PROJECT_MAP.md` test counts from pytest — do not invent a percent.
- Measure with `ai_usage_summary` before further runtime token work. Stages 4–5 stay unimplemented.

## 9. IMPORTANT COMPATIBILITY RULES (Grok Bot)
Do NOT rename/delete/move or structurally change: employee **slugs/identities/roles/relationships**;
FakeLLM **task strings**; `get_llm()`/`FakeLLM`/`LLMPort` names and the `fake` default; DB **table and
column names** (schema is additive-only — do not alter existing tables); module/package names under
`varma/`; control-engine **deny reasons** and addenda labels; Documents 00–18 (authoritative, outside the
repo). Keep changes additive; keep the full test suite green.

## 10. HOW TO CONTINUE
Read this file, then `PROJECT_MAP.md` + `SPEC_INDEX.md` (+ `knowledge/index.json` for machine navigation
and `GLOSSARY.md` for terms). Verify git state. Run `python3 -m pytest` (expect **158** passing on
current `main`; **175** was the token-efficiency stack, not default-branch HEAD). Continue from
Section 8. Preserve every governance and safety rule in Section 6.
