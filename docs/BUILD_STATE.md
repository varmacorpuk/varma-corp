# Varma Corp — BUILD STATE (engineering handover)

Concise, current-state handover for the next engineering agent (including Grok Bot). Read this
FIRST, then `docs/PROJECT_MAP.md` and `docs/SPEC_INDEX.md`. Do not rescan the whole repository or
re-read Documents 00–18 unless a specific task requires it. Do not call AI for deterministic
operations. The **source code on the branch you have checked out is authoritative**; if this file
disagrees with that code, the code wins and this file must be corrected.

_Last updated: 2026-09-03._ Grand Opening PAPER (Hari explicit yes, word: Open). LIVE still
blocked. CEO desk 02F is bound in ControlEngine: `split_flatten_clocks` true. Paper-OPEN book is
`data/varma_paper_open.db`. LIVE_BLOCKED. Kernel down / no daemon. Pytest **204**. Do not invent
a percent-complete. Chat is not the record.

## 0. RECOVERY / CONTINUATION INSTRUCTION
> Read `BUILD_STATE.md` first. Then read `PROJECT_MAP.md` and `SPEC_INDEX.md`. Do not rescan the
> entire repository unless required. Verify the current git state (`git log` / `git rev-parse HEAD`
> vs `origin/main`, and `gh pr list`). Continue from the recorded NEXT STEP. Preserve all governance
> and safety rules.

## 1. CURRENT BUILD STATUS
- **Formal completion percentage: not established — do not invent one.** The project is the first
  vertical slice per Document 18.
- **On current `main` (02F bound, PR #34):** FastAPI kernel; 7 durable AI employees;
  skills (brief, challenge, risk, Trader paper-ticket proposal); on-demand routines (brief,
  challenge, risk-deny, 07:30 meeting, nightly memory filter, US flatten, London-auction flatten,
  backup, Trader paper-ticket proposal); four memory stores; durable DB handoffs; deterministic
  ControlEngine with bound 02F; internal paper simulator; Board observability; 2D desktop UI; chat
  (Board-only); FakeLLM default wrapped by MeasuredLLM; `AICallLog` + `ai_usage_summary`;
  token-efficiency runtime; first paper-trade PATH; Board Addendum K; Grand Opening PAPER;
  Addendum E JPM/JNJ NYSE. Practice / paper only. LIVE stays BLOCKED. BROKER_PAPER and LIVE ports
  stay UNLOADED. No real broker. No real money. FakeLLM stays default. Do not call AI for
  permit/deny/fills. Kernel is down; do not start it for this encoding.
- **Incomplete / not built:** Grand Opening LIVE; real LLM binding; live/broker execution;
  semantic memory summarisation; response caching; event-idempotency schema.
- **Deliberately closed/disabled:** `trading_mode=LIVE_BLOCKED`; BROKER_PAPER and LIVE ports
  UNLOADED; FakeLLM is the only LLM (no network); Talk/voice disabled. Token-efficiency stages 4
  (snapshot cache) and 5 (response cache) are intentionally **not** implemented. Deterministic
  ControlEngine stays authority.

## 2. COMPLETED WORK (GitHub PR state, verified 2026-09-03)
Merged **into `main`:** PRs **#1–#20**, **#22**, **#23**, **#28**, **#29**, **#30**, **#31**, **#32**, **#34**, **#35**.
(#16 is merged — Addendum I is the two-opening rule, not an unmerged close.)
#32 recoded Addendum E listing venues (JPM/JNJ NYSE). #34 binds CEO desk 02F in ControlEngine.
#35 records that landing on `main`.

| PR | On `main`? | What |
| --- | --- | --- |
| #1–#15, #17–#20 | yes | Kernel slice, observability, addenda A/C/E/F/I/J, brains + four stores, LSE fail-closed hold (UNSET until K) |
| #16 | yes | Addendum I: two-opening rule (CLOSED gate until Grand Opening) |
| #22 | yes | `.cursor/environment.json` (Cloud Agent install + start) |
| #23 | yes | Project map + non-invasive AI usage (`MeasuredLLM`, `AICallLog`, `ai_usage_summary`). 153 → 158 tests |
| #24–#26 | yes (#29) | Token-efficiency runtime. 158 → 175 |
| #28 | yes | Restored BUILD_STATE on `main` |
| #29 | yes | Landed #24–#26 runtime onto `main` at `f9adb0e`. Pytest **175** |
| #30 | yes | First paper-trade PATH + Board Addendum K. Pytest **188**. PAPER was still CLOSED |
| #31 | yes | Grand Opening PAPER. Practice / paper OPEN. LIVE still blocked. Pytest **196** |
| #32 | yes | Addendum E listing venues: JPM and JNJ recoded NASDAQ → NYSE. Encoding only. Pytest **198** |
| #34 | yes | CEO desk 02F bound in ControlEngine. Venue-split flatten clocks. Pytest **204** |
| #35 | yes | BUILD_STATE record of #34 on `main` (02F bound, LIVE_BLOCKED, kernel down) |

**Board Grand Opening PAPER** (3 Sep 2026, Hari explicit yes, word: Open) is Board record,
encoded as a Board-only `write_control`. Silence was not this. Addendum I still exists as the
two-opening rule; paper opening has happened; live opening has not. Do **not** merge or rebase
PR **#21**. Leave **#21** open as leftover draft.

**02F bound:** `split_flatten_clocks` is **true**. SHEL.L, AZN.L, ULVR.L flatten in the London
closing auction 16:30–16:35 Europe/London. That exit cannot be dropped independently of the
opening buy. Do not hold those three to New York. US names still flatten at US regular cash close.
Firm day still runs to NY close. Risk reads `engine.snapshot()["risk_02f"]` (`bound: true`) to
re-clear. Not a Board tap. Not a Hari card. LIVE_BLOCKED. paper OPEN.

## 3. CURRENT BRANCH / REPOSITORY STATE
- **Default branch `main`:** PR **#34** is merged (encoding commit `079b267`, merge `2e03dbe`).
  CEO desk 02F bound. Venue-split flatten clocks. `split_flatten_clocks` **true**. Pytest **204**.
  PAPER execution OPEN. LIVE_BLOCKED. Kernel down / no daemon. JPM/JNJ NYSE (from #32). Capital
  £1,000 and Addendum A limits unchanged. Allow-list membership unchanged. Kill switch unchanged.
  FakeLLM remains default. No fills on the paper-OPEN book. Do not start the office kernel.
- **Paper-OPEN book:** `data/varma_paper_open.db`. Never empty `data/varma.db`. Never reset/wipe a
  different sqlite file.
- Verify live state with `git log --oneline origin/main` and `gh pr list --state all` before
  continuing.

## 4. ARCHITECTURE STATE (see `docs/PROJECT_MAP.md` for file-level detail)
- **Application:** FastAPI kernel `varma/kernel/app.py` (entry `varma/__main__.py`). Desktop UI is a
  projection; DB is the source of truth. No daemon/scheduler; routines are on-demand. Kernel down
  for this encoding.
- **Database:** SQLAlchemy `varma/db/` (SQLite dev / Postgres via compose). Paper-OPEN practice
  book is `data/varma_paper_open.db`. Additive `AICallLog` table from #23 is on `main`.
- **Employee system:** 7 durable records (Document 03) in `varma/db/seed.py` + `varma/employees/brain.py`;
  runtime in `varma/employees/runtime.py`; context classes in `varma/employees/context.py`.
  Slugs/identities/roles unchanged. AI context uses compact `constraints_hint()` (includes
  `risk_02f_bound` / `split_flatten_clocks`). Full `ControlEngine.snapshot()` remains for
  enforcement and observability; AI never enforces controls.
- **Memory system:** four stores in `varma/memory/stores.py` (working, employee lessons, org knowledge,
  append-only evidence) + nightly filter. Selective recency retrieval (#25/#26) is on `main`
  (lessons/working/org titles, limit 8). Nothing is deleted. Full durable records stay in the
  database and in Board observability. Limits are reversible dev defaults, not a retention policy.
- **Controls/governance:** deterministic `varma/controls/engine.py` (+ addenda A/C/E/F/I/J/K, LSE
  after-London-cash-close session rule, CEO desk 02F venue flatten, kill switch, risk).
  Authoritative; AI never enforces controls. Board `write_control` can open or close paper. LIVE
  opening is not implemented.
- **Virtual office:** `desktop/` (2D office + right-hand Board panel; fetch-on-click, no polling).
- **Trading simulation:** internal paper fill simulator `varma/paper/` (not a broker). First
  paper-trade PATH exists: Trader (Chris Adeyemi) proposes → ControlEngine permit/deny →
  simulator fill → paper ledger. Bound session exit is attached on permit. Board-only on-demand
  jobs `run_flatten_london_close` (LSE) and `run_flatten_us_close` (US). PAPER execution is OPEN
  for practice. LIVE stays blocked.
- **AI/LLM boundary:** `varma/ports/llm.py` — `FakeLLM` default, wrapped by `MeasuredLLM`. Four task
  strings only: `prepare_daily_intelligence_brief`, `challenge_sample_thesis`, `review_unsafe_path`, `chat`.
  Do not bind a real LLM.

## 5. AI / TOKEN-EFFICIENCY STATE
- **On `main`:** measurement (#23) plus runtime from #24–#26. Measure with `ai_usage_summary`
  before any further runtime token work. Do not call AI for deterministic ops (meeting / filter /
  backup / deny / permit / fills).
- Compact `constraints_hint()`; bounded chat (6 turns; full history stays append-only); selective
  lessons (8); idempotent handoffs (existing columns only); selective working/org titles (8);
  daily simulation 4 FakeLLM calls (brief/challenge/risk/chat) and 0 AI on deterministic ops.
- **Intentionally not implemented (anywhere):** stage 4 snapshot cache; stage 5 response caching
  (safety). Remaining known risks: recency-only retrieval; a real model would still resend static
  scaffolding.

## 6. GOVERNANCE / SAFETY STATE (explicit)
- `trading_mode = LIVE_BLOCKED`. **No live trading authorised.** Kernel down.
- PAPER trading **OPEN** for PRACTICE only (Grand Opening PAPER, Hari explicit yes 3 Sep 2026,
  word: Open). Internal simulator. £1,000 paper starting book. No real broker. No real money.
  Paper-OPEN book: `data/varma_paper_open.db`. Do not use empty `data/varma.db`.
- BROKER_PAPER and LIVE adapters **UNLOADED**; no broker connection; no live-order path exists.
- Kill switch and deterministic control engine **preserved and authoritative**; AI does not enforce controls.
- Addenda A/C/E/F/I/J/K. Addendum I still exists as the two-opening rule. Paper opening has
  happened; live opening has not. **02F is bound:** `split_flatten_clocks` true. LSE three flatten
  in the London closing auction 16:30–16:35; US names flatten at US regular cash close. Firm day
  still runs to NY close. Overnight off. Addendum K still denies new SHEL.L / AZN.L / ULVR.L
  tickets after London cash shuts. Dual-listed US lines SHEL/AZN/ULVR are not on the allow-list.
  Addendum A limits apply (£200 position, £50 daily loss, 6 orders/day, kill switch). Addendum E
  listing venues: JPM and JNJ NYSE; US tech NASDAQ; LSE three LSE. Capital and allow-list
  membership were not rewritten.
- Employees including the CEO **cannot** open or close the firm or write locks.
- **Board Member remains the sole human authority.** Silence is not approval. Do not write Board
  policy into chat comments. GitHub is code only: never paper book, secrets, or employee memory.
- Specs Documents 00–18 live **outside** the repo (see `ARCHITECTURE.md`). Do not copy the full spec set in.

## 7. CURRENT OPEN DECISIONS (Board — do not invent answers)
1. Semantic **rolling summary** of older chat turns (if/how; must never replace durable records).
2. Any **permanent memory summarisation/pruning/retention** policy (stack limits are reversible dev defaults).
3. **Response caching** — requires a safe real-model binding + freshness + cache-invalidation policy.
4. **Event-idempotency** that skips duplicate AI reasoning — needs a schema key or routine-behaviour change.
5. Deterministic **task-relevance ranking** beyond recency (importance scoring) — a memory-policy decision.
6. Any **real LLM provider binding** and, separately, Grand Opening LIVE (much later, only if Board says so).

## 8. CURRENT NEXT STEP
- Treat **this file on `main`** as the handover. Do not rescan the repo or re-read Documents 00–18
  unless a specific task requires it.
- **Do not merge PR #21.** Leave it open.
- **Do not bind a real LLM.** FakeLLM remains default.
- **Do not implement any Section 7 item** until the Board decides it.
- **Do not implement token-efficiency stages 4–5.** Measure with `ai_usage_summary` before further
  runtime token work.
- **Do not start the office kernel. Do not place paper orders. Do not fill.**
- **Next human step:** paper operation (practice on the £1,000 book in `data/varma_paper_open.db`).
  LIVE later only if the Board says so. Do not open live in code. Risk can re-clear 02F from
  engine state (`risk_02f.bound` / `split_flatten_clocks`).

## 9. IMPORTANT COMPATIBILITY RULES (Grok Bot)
Do NOT rename/delete/move or structurally change: employee **slugs/identities/roles/relationships**;
FakeLLM **task strings**; `get_llm()`/`FakeLLM`/`LLMPort` names and the `fake` default; DB **table and
column names** (schema is additive-only — do not alter existing tables); module/package names under
`varma/`; control-engine **deny reasons** and addenda labels; Documents 00–18 (authoritative, outside the
repo). Keep changes additive; keep the full test suite green.

## 10. HOW TO CONTINUE
Read this file, then `PROJECT_MAP.md` + `SPEC_INDEX.md` (+ `knowledge/index.json` for machine navigation
and `GLOSSARY.md` for terms). Verify git state. Run `python3 -m pytest` (expect **204** on `main`
after #34; **198** was main after #32). Continue from Section 8. Preserve every governance and
safety rule in Section 6.
