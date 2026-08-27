# Varma Corp. — first vertical slice

Company kernel plus a Board Member control-room desktop. This is DEVELOPMENT on this box, not production runtime, and not the Board Member Mac/Windows as the system of record.

Human user terminology: Board Member. The CEO is an AI employee (not built in this slice). Never MD.

## What this slice proves

1. FastAPI kernel: health, Board Member auth stub, control tables (permissions, empty allow-list, trading_mode=LIVE_BLOCKED). Employees cannot write those tables.
2. One persistent employee: Market Intelligence / Research Analyst (identity, role, four memory stores, skill, routine).
3. Skill prepare_daily_intelligence_brief. FakeLLM for tests. Optional LLM env is unused by default.
4. On-demand brief plus a documented 06:30 Europe/London weekday routine.
5. Independent verification of the brief (required fields, source+timestamp, freshness, TEMPORARY cost cap).
6. Brief stored in the database, not as source of truth on a desktop disk.
7. Desktop: 2D office, one employee sprite, click to right-hand panel with the latest brief; office remains visible; no covering overlay; status bubble; chat hits the same employee runtime. No Talk/voice.
8. pytest without paid APIs. Execution in LIVE mode is denied. Empty allow-list cannot execute.
9. TEMPORARY DEVELOPMENT DEFAULT watchlist of a few listed stocks. It is not the execution allow-list. No gold.

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

    cd /workspace/varma-corp
    python3 -m pip install -r requirements.txt
    cp -n .env.example .env
    make test
    python3 -m varma.routines.run_brief
    python3 -m varma

Health: http://127.0.0.1:8000/health

### Desktop

One client for Mac and Windows (Electron). Browser also works in development.

    python3 -m varma
    cd desktop && python3 -m http.server 5173 --bind 127.0.0.1

Then open http://127.0.0.1:5173

Click the employee. The right-hand panel shows the latest brief. Office stays visible. Chat uses the same employee runtime. Talk is disabled.

## 06:30 Europe/London routine

Documented weekday schedule: 06:30 Europe/London, output due before the 07:30 company meeting (Documents 02, 09, 18).

This slice does not start a 24/7 daemon scheduler. Run on demand:

    python3 -m varma.routines.run_brief

A later slice can attach the same skill to a Europe/London scheduler.

## Controls (not memory)

- trading_mode default: LIVE_BLOCKED
- Execution allow-list: empty, so no execution
- Numeric limits: unset, so deny (OPEN BOARD DECISION, not invented here)
- LIVE adapter: not loaded
- Employees cannot write control tables
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

## Next slice

CEO as meeting recipient of the intelligence brief (Document 18), then Challenge on a sample thesis, then Risk as a deny-path demo.

## Specs

See ARCHITECTURE.md. Authoritative documents 00-18 are not copied into git.

## Tests

    python3 -m pytest

Covers: LIVE mode denied; empty allow-list cannot execute; missing limits deny; employee cannot write controls; brief verification; watchlist is not the allow-list; office right-hand panel is not an overlay; FakeLLM only.
