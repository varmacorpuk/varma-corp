# Varma Corp — BUILD STATE (engineering handover)

Concise, current-state handover for the next engineering agent (including Grok Bot). Read this
FIRST, then `docs/PROJECT_MAP.md` and `docs/SPEC_INDEX.md`. Do not rescan the whole repository or
re-read Documents 00–18 unless a specific task requires it. Do not call AI for deterministic
operations. The **source code on the branch you have checked out is authoritative**; if this file
disagrees with that code, the code wins and this file must be corrected.

_Last updated: 2026-09-03._ Verified against GitHub (`gh pr list` / API) and `python3 -m pytest`
on this paper-trade-path branch: **183 passing, 0 failures**. Do not invent a percent-complete. Chat is
not the record.

## 0. RECOVERY / CONTINUATION INSTRUCTION
> Read `BUILD_STATE.md` first. Then read `PROJECT_MAP.md` and `SPEC_INDEX.md`. Do not rescan the
> entire repository unless required. Verify the current git state (`git log` / `git rev-parse HEAD`
> vs `origin/main`, and `gh pr list`). Continue from the recorded NEXT STEP. Preserve all governance
> and safety rules.

## 1. CURRENT BUILD STATUS
- **Formal completion percentage: not established — do not invent one.** The project is the first
  vertical slice per Document 18; the company is CLOSED until Grand Opening (Board Addendum I).
- **On default branch `main` (this landing of #24–#26 runtime):** FastAPI kernel; 7 durable AI
  employees; skills (brief, challenge, risk, Trader paper-ticket proposal); on-demand routines
  (brief, challenge, risk-deny, 07:30 meeting, nightly memory filter, flatten, backup,
  Trader paper-ticket proposal); four memory stores; durable DB handoffs;
  deterministic ControlEngine; internal paper simulator; Board observability; 2D desktop UI; chat
  (Board-only); FakeLLM default wrapped by MeasuredLLM; `AICallLog` + `ai_usage_summary`;
  token-efficiency runtime (`constraints_hint()`, STATIC/PERSISTENT/DYNAMIC context classes,
  bounded chat, selective lessons/working/org titles, idempotent handoffs, daily sim 0 AI on
  deterministic ops). Pytest: **183 passing, 0 failures** (measured 2026-09-03, includes the
  first paper-trade PATH tests; PAPER still CLOSED).
- **Incomplete / not built:** Grand Opening (PAPER or LIVE); real LLM
  binding; live/broker execution; semantic memory summarisation; response caching;
  event-idempotency schema.
- **Deliberately closed/disabled:** `trading_mode=LIVE_BLOCKED`; PAPER execution CLOSED (no fills;
  £1,000 is future paper start only); BROKER_PAPER and LIVE ports UNLOADED; FakeLLM is the only
  LLM (no network); Talk/voice disabled. Token-efficiency stages 4 (snapshot cache) and 5
  (response cache) are intentionally **not** implemented (safety: caches must never become
  authority for limits, kill switch, hours, or live/paper gates). Deterministic ControlEngine
  stays authority. The first paper-trade **PATH** exists (Trader proposal → ControlEngine →
  internal simulator) and is still gated CLOSED.

## 2. COMPLETED WORK (GitHub PR state, verified 2026-09-03)
Merged **into `main`:** PRs **#1–#20**, **#22**, **#23**, **#28**, and this PR landing the #24–#26
runtime. (#16 is merged — Addendum I company CLOSED until Grand Opening, not an unmerged close.)
PRs #24–#27 were GitHub-merged earlier onto stacked feature branches and did **not** reach `main`
until #28 (BUILD_STATE restore) and this PR (runtime).

| PR | On `main`? | What |
| --- | --- | --- |
| #1–#15, #17–#20 | yes | Kernel slice, observability, addenda A/C/E/F/I/J, brains + four stores, LSE fail-closed hold |
| #16 | yes | Addendum I: PAPER execution CLOSED until Grand Opening |
| #22 | yes | `.cursor/environment.json` (Cloud Agent install + start) |
| #23 | yes | Project map + non-invasive AI usage (`MeasuredLLM`, `AICallLog`, `ai_usage_summary`). 153 → 158 tests |
| #24 | **yes** (this PR) | `constraints_hint()` + STATIC/PERSISTENT/DYNAMIC classifier. 158 → 165 |
| #25 | **yes** (this PR) | Bounded chat (6 turns); selective lessons (8); idempotent handoffs; daily sim 0 AI on deterministic ops. Stages 4–5 **not** implemented. 165 → 173 |
| #26 | **yes** (this PR) | Selective working/org titles (8). 173 → 175 |
| #27 | docs only | Original `docs/BUILD_STATE.md` on the stacked tip `07495a3`. Restored and corrected onto `main` by #28. Not replayed as a runtime commit |
| #28 | yes | Restored BUILD_STATE on `main` and recorded that #24–#26 were not yet on default branch |

**Open (leave open):** PR **#21** only — LSE hold: deny SHEL.L / AZN.L / ULVR.L after London cash
close. Do **not** merge or rebase it. Do **not** encode a split-clock. Addendum C stays
flatten-at-US-close.

## 3. CURRENT BRANCH / REPOSITORY STATE
- **Default branch `main` immediately before this landing:** `c548856` — PR #28. Contained #1–#20,
  #22, #23, #28. Pytest was **158**. BUILD_STATE on that commit correctly said #24–#26 were
  GitHub-merged but not on `main`.
- **This landing:** replays the runtime commits from stacked PRs #24–#26 onto current `main`.
  Runtime files match stacked tip `4adc643` (the #26 merge). The #27 BUILD_STATE blob was **not**
  copied (it claimed the stack was already the working tree). `.cursor/environment.json` from #22
  is kept. Docs here are updated to the new truth.
- **Historical note:** #23–#27 were a stacked chain. Only #23 targeted `main` at the time. GitHub
  "MERGED" did not mean the commit was in a `main` checkout. That gap is closed for #24–#26 runtime.
- Verify live state with `git log --oneline origin/main` and `gh pr list --state all` before
  continuing.

## 4. ARCHITECTURE STATE (see `docs/PROJECT_MAP.md` for file-level detail)
- **Application:** FastAPI kernel `varma/kernel/app.py` (entry `varma/__main__.py`). Desktop UI is a
  projection; DB is the source of truth. No daemon/scheduler; routines are on-demand.
- **Database:** SQLAlchemy `varma/db/` (SQLite dev / Postgres via compose). Additive `AICallLog`
  table from #23 is on `main`.
- **Employee system:** 7 durable records (Document 03) in `varma/db/seed.py` + `varma/employees/brain.py`;
  runtime in `varma/employees/runtime.py`; context classes in `varma/employees/context.py`.
  Slugs/identities/roles unchanged. AI context uses compact `constraints_hint()`. Full
  `ControlEngine.snapshot()` remains for enforcement and observability; AI never enforces controls.
- **Memory system:** four stores in `varma/memory/stores.py` (working, employee lessons, org knowledge,
  append-only evidence) + nightly filter. Selective recency retrieval (#25/#26) is on `main`
  (lessons/working/org titles, limit 8). Nothing is deleted. Full durable records stay in the
  database and in Board observability. Limits are reversible dev defaults, not a retention policy.
- **Controls/governance:** deterministic `varma/controls/engine.py` (+ addenda A/C/E/F/I/J, LSE
  fail-closed hold, kill switch, risk). Authoritative; AI never enforces controls.
- **Virtual office:** `desktop/` (2D office + right-hand Board panel; fetch-on-click, no polling).
- **Trading simulation:** internal paper fill simulator `varma/paper/` (not a broker). First
  paper-trade PATH exists: Trader (Chris Adeyemi) proposes → ControlEngine permit/deny →
  simulator fill → paper ledger. Board-only on-demand job
  `python -m varma.routines.run_paper_trade_path` / POST `/routines/run-paper-trade-path`.
  PAPER execution is still CLOSED: no fills. Next human step is Board Grand Opening.
- **AI/LLM boundary:** `varma/ports/llm.py` — `FakeLLM` default, wrapped by `MeasuredLLM`. Four task
  strings only: `prepare_daily_intelligence_brief`, `challenge_sample_thesis`, `review_unsafe_path`, `chat`.
  Do not bind a real LLM.

## 5. AI / TOKEN-EFFICIENCY STATE
- **On `main`:** measurement (#23) plus runtime from #24–#26. Measure with `ai_usage_summary`
  before any further runtime token work. Do not call AI for deterministic ops (meeting / filter /
  backup / deny).
- Compact `constraints_hint()`; bounded chat (6 turns; full history stays append-only); selective
  lessons (8); idempotent handoffs (existing columns only); selective working/org titles (8);
  daily simulation 4 FakeLLM calls (brief/challenge/risk/chat) and 0 AI on deterministic ops.
- **Key measurements (FakeLLM; `estimated_tokens` = labelled chars/4 heuristic, NOT real provider
  tokens; no real model is connected):**
  - Brief AI context: **21,000 → 4,694 chars** (~−77.6%); est per-call tokens ~5,894 → ~1,818 (~−69.2%).
  - Bounded chat (100-msg history): **20,070 → 1,699 chars** (capped at 6 turns).
  - Selective lessons (41): **2,702 → 504 chars** (8 sent).
  - Selective working+org (30 each): **2,490 → 672 chars** (~−73%).
- **Intentionally not implemented (anywhere):** stage 4 snapshot cache; stage 5 response caching
  (safety). Remaining known risks: recency-only retrieval; a real model would still resend static
  scaffolding.

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
- **Do not implement token-efficiency stages 4–5.** Measure with `ai_usage_summary` before further
  runtime token work.
- **Next human step:** Board Grand Opening (PAPER). The paper-trade path is wired. PAPER
  execution is still CLOSED. Do not open the firm in code. Do not fill practice orders until
  Hari says Grand Opening. Flipping the existing CLOSED gate is then enough for a practice
  order to be able to fill (internal simulator only). LIVE remains later and forbidden.

## 9. IMPORTANT COMPATIBILITY RULES (Grok Bot)
Do NOT rename/delete/move or structurally change: employee **slugs/identities/roles/relationships**;
FakeLLM **task strings**; `get_llm()`/`FakeLLM`/`LLMPort` names and the `fake` default; DB **table and
column names** (schema is additive-only — do not alter existing tables); module/package names under
`varma/`; control-engine **deny reasons** and addenda labels; Documents 00–18 (authoritative, outside the
repo). Keep changes additive; keep the full test suite green.

## 10. HOW TO CONTINUE
Read this file, then `PROJECT_MAP.md` + `SPEC_INDEX.md` (+ `knowledge/index.json` for machine navigation
and `GLOSSARY.md` for terms). Verify git state. Run `python3 -m pytest` (expect **183** passing
on this paper-trade-path landing; **175** was main after #24–#26 runtime, before this path).
Continue from Section 8. Preserve every governance and safety rule in Section 6.
