# Varma Corp — Project Map

Read `docs/BUILD_STATE.md` first. Then use this map. **Do not rescan the whole repository. Do not
re-read Documents 00–18 unless a specific task requires it. Do not call AI for deterministic ops.**

Navigation aid for coding agents. The source code is authoritative. If this map disagrees with the
code, the code wins and this map must be corrected. Nothing here changes runtime behaviour.

Authoritative specifications are **Documents 00–18**, which live **outside this repository**
(see `ARCHITECTURE.md`). This map does not restate them; see `docs/SPEC_INDEX.md` for pointers.

## Top-level layout

| Path | What it is |
| --- | --- |
| `varma/` | Python package: the company kernel and all domain logic |
| `desktop/` | Static 2D "virtual office" UI (Electron/browser). Projection only, not source of truth |
| `tests/` | Pytest suite: Grand Opening PAPER on #30 main (practice OPEN, LIVE blocked). Do not invent a percent-complete. |
| `scripts/` | Dev helper scripts (`dev.sh`) |
| `docs/` | `BUILD_STATE.md` (read first — current handover), this map, spec index, glossary, `knowledge/index.json` (navigation only) |
| `data/` | Practice paper-OPEN book `varma_paper_open.db` plus tracked `paper_open_ledger.json`. Never empty `varma.db` |
| `docker-compose.yml` | Optional Postgres for the same StoragePort |
| `README.md`, `ARCHITECTURE.md` | Overview + pointer to Documents 00–18 |
| `Makefile`, `pyproject.toml`, `requirements.txt`, `.env.example` | Build / config |

## Architecture layers

```
desktop/ (UI projection)  ──HTTP──>  varma/kernel/app.py (FastAPI)
                                          │
        deterministic domain logic ───────┼──> ports (LLM / data / execution)
                                          │
                                     varma/db (SQLAlchemy → SQLite/Postgres)
```

The database is the source of truth. The office UI is a projection. There is no scheduler/daemon;
routines are on-demand (Board-only POST endpoints or CLI). Runtime AI is `FakeLLM` (deterministic,
no network) by default. `BROKER_PAPER` and `LIVE` execution ports are UNLOADED; trading_mode is
`LIVE_BLOCKED`; PAPER execution is OPEN for practice after Grand Opening PAPER.

## Components (location · purpose · key deps · key dependants)

### Backend / kernel
- `varma/kernel/app.py` — FastAPI app; all HTTP endpoints (health, employees, chat, routines,
  controls, observability). Depends on nearly every domain module. Entry point: `varma/__main__.py`.
- `varma/kernel/auth.py` — Board Member vs employee actor parsing; `require_board_member`.
- `varma/config.py` — pydantic-settings (`VARMA_*` env). Defaults: `llm_provider="fake"`, SQLite.

### Frontend / desktop UI
- `desktop/index.html`, `desktop/src/office.js`, `desktop/src/styles.css` — 2D office + right-hand
  Board panel; fetches kernel on user action (no polling). `electron-main.js`, `preload.js` wrap it.

### Database / storage
- `varma/db/models.py` — all SQLAlchemy tables (source of truth schema).
- `varma/db/engine.py` — StoragePort (SQLite now, Postgres later); `init_db`, `get_session_factory`.
- `varma/db/seed.py` — seeds/reconciles employees, controls, addenda onto stale SQLite.

### AI employee components
- `varma/employees/brain.py` — `EmployeeBrain`: durable employee record + `invocation()` context
  (identity, role knowledge, lessons, working memory, org titles). Document 03. Selective recency
  retrieval for lessons/working/org titles (limit 8); nothing deleted.
- `varma/employees/context.py` — STATIC / PERSISTENT / DYNAMIC context classes for AI payloads.
- `varma/employees/runtime.py` — `EmployeeRuntime`: `context_pack()` + `chat()` +
  `propose_paper_ticket()` (Trader only; no AI). Bounded chat context (6 turns) for the model;
  full history stays append-only.
- `varma/ports/llm.py` — `LLMPort`, `FakeLLM` (default), `get_llm()`. An LLM call is an invocation.

### Skills (one AI call each, wrapped in deterministic work)
- `varma/skills/prepare_daily_intelligence_brief.py` — Research brief. Deps: `ports/data`,
  `verification/brief`, `cost/ledger`, `meetings/handoff`.
- `varma/skills/prepare_sample_thesis.py` — SAMPLE thesis (no AI call; artefact builder).
- `varma/skills/challenge_sample_thesis.py` — Challenge review; hands off to Risk.
- `varma/skills/review_unsafe_path.py` — Risk deny-path (decision is deterministic; AI writes prose).
- `varma/skills/propose_paper_ticket.py` — Trader paper-ticket proposal (no AI call; engine permit/deny).

### Market intelligence / data
- `varma/ports/data.py` — `FakeMarketData` (delayed fake news + prices). No paid vendor. Equities only.
- `varma/verification/brief.py` — deterministic freshness + required-field verification.

### Trading / paper-trading components
- `varma/paper/simulator.py` — internal paper fill simulator (not a broker). Fill only after
  ControlEngine allows. After Grand Opening PAPER a legal allow-list practice order may fill.
- `varma/paper/ledger.py` — paper account/positions/P&L, evaluation snapshot.
- `varma/paper/persist.py` — git-tracked practice ledger JSON; hydrates the paper-OPEN book.
- `varma/paper/flatten.py` — venue-aware flatten (LSE London auction / US close; 02F bound).
- `varma/skills/propose_paper_ticket.py` — Trader (Chris Adeyemi) paper-ticket proposal.
  Deterministic. No AI. ControlEngine is authoritative.
- `varma/routines/run_paper_trade_path.py` — Board-only on-demand job that invokes the Trader
  proposal. No daemon. After Grand Opening PAPER a legal ticket may fill. Named ticket
  `PAPER-20260903-02` (SHEL.L BUY 5) uses `data/varma_paper_open.db` only and never
  `data/varma.db`.
- `varma/ports/execution.py` — ExecutionPort; BROKER_PAPER + LIVE remain UNLOADED.

### Risk / controls / governance
- `varma/controls/engine.py` — deterministic `ControlEngine`: permit/deny orders, `snapshot()`,
  compact informational `constraints_hint()` for AI context, `write_control`. Authoritative.
  AI never enforces controls.
- `varma/controls/addendum_a.py` (numeric limits), `addendum_c.py` (paper session),
  `addendum_e.py` (PAPER allow-list), `addendum_f.py` (named staff/slugs), `addendum_i.py`
  (two-opening rule + Grand Opening PAPER Board write), `addendum_j.py` (backup),
  `addendum_k.py` (LSE after London cash close), `lse_session.py` (Addendum K time window
  + UNSET fail-closed fallback), `venue_flatten.py` (CEO desk 02F bound LSE London-auction
  / US-close clocks), `risk.py` (RiskPolicy), `kill_switch.py` (Board-only halt/reset).

### Memory systems (four stores, Document 08)
- `varma/memory/stores.py` — working, employee lessons, org knowledge (governed promotion),
  append-only evidence.
- `varma/memory/filter.py` — nightly Europe/London working-context archive; never writes controls.

### Meetings / communication
- `varma/meetings/handoff.py` — durable DB handoff artefacts (Research→CEO, Challenge→Risk).
  Idempotent insert (deterministic dedup, existing columns only).
- `varma/meetings/company_meeting.py` — on-demand 07:30 meeting record from existing handoffs (no AI).

### Orchestration / routines (on-demand; no daemon)
- `varma/routines/run_brief.py`, `run_challenge.py`, `run_risk_deny.py`, `run_nightly_filter.py`,
  `run_0730_meeting.py`, `run_flatten_us_close.py`, `run_flatten_london_close.py`, `run_backup.py`, `run_paper_trade_path.py` —
  CLI + called by kernel POSTs.
- `varma/routines/board_jobs.py` — Board-only job catalog + safety flag wrappers.

### Observability / cost / measurement
- `varma/observability/board.py` — read-only Board observability snapshot (database projection).
- `varma/cost/ledger.py` — fake cost-unit ledger (development accounting, not real tokens).
- `varma/observability/ai_usage.py` — **non-invasive** AI-call measurement (#23). Wraps `LLMPort`
  (`MeasuredLLM`), records `AICallLog` rows (deterministic sizes + estimates), and
  `ai_usage_summary()`. Does not change prompts, context, model selection, or employee behaviour.
  **Measure here before further runtime token work.** Token-efficiency stages from PRs #24–#26
  (`constraints_hint()`, bounded chat, selective lessons/working/org, idempotent handoffs, daily
  sim 0 AI on deterministic ops) **are on `main`**. Stages 4 (snapshot cache) and 5 (response
  cache) are intentionally **not** implemented (safety).

### Backup
- `varma/backup/job.py`, `varma/backup/crypto.py` — encrypted-at-rest company backup (Technology owns).

### Clock
- `varma/clock.py` — Europe/London time helpers + descriptive schedule text. No live scheduler.

## Where things live (quick reference)
- Agent/employee definitions: `varma/db/seed.py` + `varma/employees/brain.py` (`ROLE_KNOWLEDGE`).
- Configuration: `varma/config.py`, `.env` / `.env.example` (default SQLite `data/varma_paper_open.db`).
- Database/schema: `varma/db/models.py`.
- Memory/data: `varma/memory/`, `data/` (dev SQLite).
- Tests: `tests/` (one file per addendum/feature).
- Specs: Documents 00–18 (outside repo); pointers in `docs/SPEC_INDEX.md`.
- Handover: `docs/BUILD_STATE.md` (read first; Grand Opening PAPER done; LIVE still blocked).
