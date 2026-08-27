# Varma Corp. — kernel + Board Member control room

Company kernel plus a Board Member control-room desktop. This is DEVELOPMENT on this box, not production runtime, and not the Board Member Mac/Windows as the system of record.

Human user terminology: Board Member. The CEO is an AI employee. Never MD.

## What this slice proves

1. FastAPI kernel: health, Board Member auth stub, control tables (permissions, empty allow-list, trading_mode=LIVE_BLOCKED). Employees cannot write those tables.
2. Four persistent employees: Market Intelligence / Research Analyst (Asha Patel), CEO, Challenge, and Risk. LLM calls are invocations, not the employee.
3. Skill prepare_daily_intelligence_brief. FakeLLM for tests. Optional LLM env is unused by default.
4. On-demand brief plus a documented 06:30 Europe/London weekday routine.
5. Independent verification of the brief (required fields, source+timestamp, freshness, TEMPORARY cost cap).
6. Brief stored in the database, then handed off to the CEO as the 07:30 meeting recipient (Document 18). Handoff artefact lives in the database, not on a desktop disk.
7. Challenge reviews a SAMPLE thesis (not a live trade). Thesis and challenge review are database artefacts, handed to Risk.
8. Risk deny-path demo: reviews an unsafe/out-of-policy LIVE-gold path and DENIES it. Risk cannot approve LIVE.
9. Desktop: 2D office, four employee sprites, click to right-hand panel; office remains visible; no covering overlay; status bubble; chat hits the same employee runtime. No Talk/voice.
10. pytest without paid APIs. Execution in LIVE mode is denied. Empty allow-list cannot execute.
11. TEMPORARY DEVELOPMENT DEFAULT watchlist of a few listed stocks. It is not the execution allow-list. No gold.
12. Nightly Europe/London memory filter (on-demand): archives working context in the database; evidence stays append-only; filter does not write controls.
13. Board Member read-only observability in the right-hand panel: cost ledger + recent evidence from the database. Visible without clicking an employee, and via a Board observability entry. This view does not write controls, trading_mode, allow-list, or permissions.
14. Same Board observability panel also shows: latest nightly memory-filter run; organisation-memory titles; 07:30 meeting pack status (MI brief headline, CEO handoff DELIVERED/not, Challenge SAMPLE thesis status, Risk DENIED/not); Board-only employee status bubbles. Click still opens the person in the right-hand panel. Chat stays hidden on observability.
15. Same panel lists 07:30 meeting artefacts from the database (brief, CEO handoff, SAMPLE thesis, challenge review, Risk decision). Read-only. SAMPLE is not a live trade. Risk cannot approve LIVE.

## System separation

- GitHub (varmacorpuk/varma-corp): source code only. Never commit .env, DB volumes, memories, keys.
- This box: DEVELOPMENT. Persistent org data in a database.
- Board Member Mac/Windows: desktop client only. Local storage = cache/settings. Not the company ledger.
- Production 24/7: backend is designed so it can later run off the Board Member PC. Not deployed now.

Secrets: copy .env.example to .env. No live brokerage.

## Storage

Docker is optional. If Postgres is not running, the kernel uses TEMPORARY SQLite under data/ (gitignored) through a StoragePort. Postgres via docker-compose.yml replaces SQLite without redesigning the company.

## Run

Python 3.12+ (this box may be 3.13; that is fine).

From the repository root:

    python3 -m pip install -r requirements.txt
    cp -n .env.example .env
    make test
    python3 -m varma.routines.run_brief
    python3 -m varma.routines.run_challenge
    python3 -m varma.routines.run_risk_deny
    python3 -m varma.routines.run_nightly_filter
    python3 -m varma

Health: http://127.0.0.1:8000/health

### Desktop

One client for Mac and Windows (Electron). Browser also works in development.

    python3 -m varma
    cd desktop && python3 -m http.server 5173 --bind 127.0.0.1

Then open http://127.0.0.1:5173

Click Asha Patel, the CEO, Challenge, or Risk. The right-hand panel shows work (produced brief, meeting inbox, SAMPLE thesis, challenge review, or Risk DENY). Board observability (cost ledger, recent evidence, nightly filter, organisation-memory titles, 07:30 meeting pack status, status bubbles) loads in that same panel without clicking an employee, and via the Board observability entry. Office stays visible. Chat uses the same employee runtime. Talk is disabled. CEO, Challenge, and Risk cannot approve LIVE. Observability is read-only.

## 06:30 Europe/London routine

Documented weekday schedule: 06:30 Europe/London, output due before the 07:30 company meeting (Documents 02, 09, 18). The CEO is the meeting recipient of that pack.

This slice does not start a 24/7 daemon scheduler. Run on demand:

    python3 -m varma.routines.run_brief

A later slice can attach the same skill to a Europe/London scheduler.

## Controls (not memory)

- trading_mode default: LIVE_BLOCKED
- Execution allow-list: empty, so no execution
- Numeric limits: unset, so deny (OPEN BOARD DECISION, not invented here)
- LIVE adapter: not loaded
- Employees cannot write control tables
- CEO, Challenge, and Risk cannot approve live trading (Board Member only)
- Paper and live trading are not implemented in this slice

Gate: PAPER then EVALUATION then recommendation then Board review then explicit Board approval then LIVE. Silence is not approval.

## TEMPORARY defaults (not Board-permanent)

These exist so development can run. They are not Board-approved universe membership, budgets, or limits.

- Watchlist: AAPL, MSFT, SHEL.L, AZN.L — TEMPORARY DEVELOPMENT DEFAULT. Not the allow-list. Listed equities only.
- Brief cost cap: 100 units — TEMPORARY DEVELOPMENT DEFAULT. Not a budget.
- News freshness window: 18 hours — TEMPORARY DEVELOPMENT DEFAULT
- Price freshness window: 26 hours — TEMPORARY DEVELOPMENT DEFAULT
- Auth stub: see .env.example — DEVELOPMENT only
- SQLite path: data/varma.db — TEMPORARY until Postgres
- Fake delayed prices and news: in-process FakeMarketData — not a vendor contract

OPEN BOARD DECISIONS left unset (must not be invented): numeric paper limits; paper duration/success thresholds; Talk/voice required?; UK legal advice; exact authorised instrument list; material-cost approval thresholds.

## Challenge and Risk (this slice)

On demand, not a 24/7 daemon:

    python3 -m varma.routines.run_challenge
    python3 -m varma.routines.run_risk_deny

- Challenge receives a SAMPLE thesis (AAPL from the TEMPORARY watchlist). It is labelled SAMPLE — not a live trade, not an order, not allow-list membership.
- Challenge writes a CHALLENGED review to the database and hands it to Risk.
- Risk reviews an unsafe/out-of-policy path (LIVE execution of gold, treating the SAMPLE thesis as an order) and records DENIED. The control engine is consulted. Risk cannot approve LIVE.

## Nightly Europe/London memory filter

On demand, not a 24/7 daemon:

    python3 -m varma.routines.run_nightly_filter

- Cadence: nightly, timezone Europe/London (Document 08).
- Working context is archived to `memory_working_archive` and cleared from `memory_working`.
- Evidence is append-only and is never deleted or overwritten.
- The filter does not write controls, `trading_mode`, allow-list, or permissions.
- Filter run is a database artefact (`memory_filter_runs`), not a desktop file.

## Board observability (this slice)

The right-hand panel is a Board Member projection of the database, not a ledger of its own.

- Cost ledger and recent evidence are read from the kernel (`GET /observability`).
- Latest nightly memory-filter run and organisation-memory titles (titles only) are read from the database.
- 07:30 meeting pack status: latest MI brief headline, CEO handoff DELIVERED/not, Challenge SAMPLE thesis status, Risk DENIED/not.
- 07:30 meeting artefact list (read-only): latest brief, CEO handoff, SAMPLE thesis, challenge review, Risk decision.
- Board-only employee status bubbles. Click an employee (floor or bubble name) to open that person in the same right-hand panel.
- Visible without clicking an employee. A Board observability entry returns to this view.
- Read-only. It does not write controls, `trading_mode`, allow-list, or permissions. Chat is hidden on this view.
- Cost cap remains a TEMPORARY DEVELOPMENT DEFAULT. It is not a Board-approved budget (Document 17 OPEN: material-cost thresholds).
- Evidence stays append-only.

## Next slice

Load selected-employee chat history from the database into the right-hand panel when an employee is opened (GET already exists; desktop currently does not load it). No new employees. Still no paper/live execution and no 12-employee roster.

## Specs

See ARCHITECTURE.md. Authoritative documents 00-18 are not copied into git.

## Tests

    python3 -m pytest

Covers: LIVE mode denied; empty allow-list cannot execute; missing limits deny; employee cannot write controls; CEO/Challenge/Risk cannot approve LIVE; brief verification and handoff to CEO; SAMPLE thesis challenge; Risk deny-path; nightly memory filter archives working context without deleting evidence or writing controls; Board can read cost ledger, recent evidence, nightly filter run, organisation-memory titles, 07:30 meeting pack status, meeting artefact list, and status bubbles; employees cannot use observability to write controls; watchlist is not the allow-list; office right-hand panel is not an overlay; FakeLLM only.
