# Varma Corp — BUILD STATE (engineering handover)

Concise, current-state handover for the next engineering agent (including Grok Bot). Read this
FIRST, then `docs/PROJECT_MAP.md` and `docs/SPEC_INDEX.md`. Do not rescan the whole repository or
re-read Documents 00–18 unless a specific task requires it. Do not call AI for deterministic
operations. The **source code on the branch you have checked out is authoritative**; if this file
disagrees with that code, the code wins and this file must be corrected.

_Last updated: 2026-09-03._ Grand Opening PAPER (Hari explicit yes, word: Open). LIVE still
blocked. Pytest: **198 passing, 0 failures**. Do not invent a percent-complete. Chat is not
the record.

## 0. RECOVERY / CONTINUATION INSTRUCTION
> Read `BUILD_STATE.md` first. Then read `PROJECT_MAP.md` and `SPEC_INDEX.md`. Do not rescan the
> entire repository unless required. Verify the current git state (`git log` / `git rev-parse HEAD`
> vs `origin/main`, and `gh pr list`). Continue from the recorded NEXT STEP. Preserve all governance
> and safety rules.

## 1. CURRENT BUILD STATUS
- **Formal completion percentage: not established — do not invent one.** The project is the first
  vertical slice per Document 18.
- **On current `main` plus this Grand Opening PAPER PR:** FastAPI kernel; 7 durable AI employees;
  skills (brief, challenge, risk, Trader paper-ticket proposal); on-demand routines (brief,
  challenge, risk-deny, 07:30 meeting, nightly memory filter, flatten, backup, Trader paper-ticket
  proposal); four memory stores; durable DB handoffs; deterministic ControlEngine; internal paper
  simulator; Board observability; 2D desktop UI; chat (Board-only); FakeLLM default wrapped by
  MeasuredLLM; `AICallLog` + `ai_usage_summary`; token-efficiency runtime; first paper-trade PATH;
  Board Addendum K; **Grand Opening PAPER**. Practice / paper only. A legal allow-list practice
  order can fill in the internal simulator on the £1,000 paper book when in session and within
  Addendum A limits. Named ticket PAPER-20260903-02 (SHEL.L BUY 5) runs on
  `data/varma_paper_open.db` only. LIVE stays BLOCKED. BROKER_PAPER and LIVE ports stay UNLOADED. No real broker.
  No real money. FakeLLM stays default. Do not call AI for permit/deny/fills.
- **Incomplete / not built:** Grand Opening LIVE; real LLM binding; live/broker execution;
  semantic memory summarisation; response caching; event-idempotency schema.
- **Deliberately closed/disabled:** `trading_mode=LIVE_BLOCKED`; BROKER_PAPER and LIVE ports
  UNLOADED; FakeLLM is the only LLM (no network); Talk/voice disabled. Token-efficiency stages 4
  (snapshot cache) and 5 (response cache) are intentionally **not** implemented. Deterministic
  ControlEngine stays authority.

## 2. COMPLETED WORK (GitHub PR state, verified 2026-09-03)
Merged **into `main`:** PRs **#1–#20**, **#22**, **#23**, **#28**, **#29**, **#30**.
(#16 is merged — Addendum I is the two-opening rule, not an unmerged close.)
#30 wired the first paper-trade PATH and encoded Board Addendum K. This PR is Grand Opening PAPER.

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
| this PR | not yet | Grand Opening PAPER. Practice / paper OPEN. LIVE still blocked. Pytest **196** |

**Board Grand Opening PAPER** (3 Sep 2026, Hari explicit yes, word: Open) is Board record,
encoded as a Board-only `write_control`. Silence was not this. Addendum I still exists as the
two-opening rule; paper opening has happened; live opening has not. Do **not** merge or rebase
PR **#21**. Leave **#21** open as leftover draft. Do not encode a split-clock. Addendum C stays
flatten-at-US-close. London cash close is not the flatten.

## 3. CURRENT BRANCH / REPOSITORY STATE
- **Default branch `main` HEAD at start of this PR:** `8992fad` — PR #30. First paper-trade PATH
  + Addendum K. Pytest was **188**. PAPER execution was CLOSED.
- **This PR:** Board-authorised Grand Opening PAPER. Fresh seed: paper OPEN, live BLOCKED,
  £1,000 starting paper capital, Addendum A limits, allow-list E, flatten US close (C), Addendum K.
  Opening is a Board-only control write. Employees cannot open or close the firm. LIVE stays
  unimplemented. FakeLLM remains default.
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
- **Controls/governance:** deterministic `varma/controls/engine.py` (+ addenda A/C/E/F/I/J/K, LSE
  after-London-cash-close session rule, kill switch, risk). Authoritative; AI never enforces controls.
  Board `write_control` can open or close paper. LIVE opening is not implemented.
- **Virtual office:** `desktop/` (2D office + right-hand Board panel; fetch-on-click, no polling).
- **Trading simulation:** internal paper fill simulator `varma/paper/` (not a broker). First
  paper-trade PATH exists: Trader (Chris Adeyemi) proposes → ControlEngine permit/deny →
  simulator fill → paper ledger. Board-only on-demand job
  `python -m varma.routines.run_paper_trade_path` / POST `/routines/run-paper-trade-path`.
  PAPER execution is OPEN for practice. LIVE stays blocked.
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
- `trading_mode = LIVE_BLOCKED`. **No live trading authorised.**
- PAPER trading **OPEN** for PRACTICE only (Grand Opening PAPER, Hari explicit yes 3 Sep 2026,
  word: Open). Internal simulator. £1,000 paper starting book. No real broker. No real money.
- BROKER_PAPER and LIVE adapters **UNLOADED**; no broker connection; no live-order path exists.
- Kill switch and deterministic control engine **preserved and authoritative**; AI does not enforce controls.
- Addenda A/C/E/F/I/J/K. Addendum I still exists as the two-opening rule. Paper opening has
  happened; live opening has not. Addendum C flatten remains US regular cash close; London cash
  close is **not** the flatten. Addendum K denies SHEL.L / AZN.L / ULVR.L only after London cash
  shuts. Dual-listed US lines SHEL/AZN/ULVR are not on the allow-list. Addendum A limits apply
  (£200 position, £50 daily loss, 6 orders/day, kill switch).
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
- Treat **this file on the branch** as the handover. Do not rescan the repo or re-read Documents 00–18
  unless a specific task requires it.
- **Do not merge PR #21.** Leave it open. Do not encode a split-clock. Addendum C stays flatten-at-US-close.
- **Do not bind a real LLM.** FakeLLM remains default.
- **Do not implement any Section 7 item** until the Board decides it.
- **Do not implement token-efficiency stages 4–5.** Measure with `ai_usage_summary` before further
  runtime token work.
- **Paper operation:** named ticket `PAPER-20260903-02` is SHEL.L BUY 5 on
  `data/varma_paper_open.db` only (`python -m varma.routines.run_paper_trade_path --ticket PAPER-20260903-02`).
  Never `data/varma.db`. LIVE stays blocked. Overnight off. Stop/target are desk-managed, not
  resting engine orders. Latest London 16:30 exit is a later job. GitHub remains code only
  (the paper book is gitignored).
- **Next human step:** further paper operation on the £1,000 book, then flatten-before-US-close
  as a later job. LIVE later only if the Board says so. Do not open live in code.

## 9. IMPORTANT COMPATIBILITY RULES (Grok Bot)
Do NOT rename/delete/move or structurally change: employee **slugs/identities/roles/relationships**;
FakeLLM **task strings**; `get_llm()`/`FakeLLM`/`LLMPort` names and the `fake` default; DB **table and
column names** (schema is additive-only — do not alter existing tables); module/package names under
`varma/`; control-engine **deny reasons** and addenda labels; Documents 00–18 (authoritative, outside the
repo). Keep changes additive; keep the full test suite green.

## 10. HOW TO CONTINUE
Read this file, then `PROJECT_MAP.md` + `SPEC_INDEX.md` (+ `knowledge/index.json` for machine navigation
and `GLOSSARY.md` for terms). Verify git state. Run `python3 -m pytest` (expect **198** passing
on this SHEL.L BUY 5 paper-ticket landing; **196** was Grand Opening PAPER). Continue from Section 8.
Preserve every governance and safety rule in Section 6.
