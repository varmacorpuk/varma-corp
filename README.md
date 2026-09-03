# Varma Corp. — kernel + Board Member control room

Company kernel plus a Board Member control-room desktop. This is DEVELOPMENT on this box, not production runtime, and not the Board Member Mac/Windows as the system of record.

Human user terminology: Board Member. The CEO is an AI employee. Never MD.

## What this slice proves

1. FastAPI kernel: health, Board Member auth stub, control tables (permissions, Board Addendum E PAPER allow-list, Board Addendum I PAPER execution CLOSED, trading_mode=LIVE_BLOCKED). Employees cannot write those tables.
2. Seven persistent employees shown as person · department (Board Addendum F): Asha Patel · Research, Jordan Hale · CEO, Sam Okeke · Challenge, Elena Voss · Risk, Chris Adeyemi · Trader, Nina Kapoor · Quant, Owen Blake · Technology. Door/role stays the job title. Talk is disabled.
3. Skill prepare_daily_intelligence_brief. FakeLLM for tests. Optional LLM env is unused by default.
4. On-demand brief plus a documented 06:30 Europe/London weekday routine.
5. Independent verification of the brief (required fields, source+timestamp, freshness, TEMPORARY cost cap).
6. Brief stored in the database, then handed off to the CEO as the 07:30 meeting recipient (Document 18). Handoff artefact lives in the database, not on a desktop disk.
7. Challenge reviews a SAMPLE thesis (not a live trade). Thesis and challenge review are database artefacts, handed to Risk.
8. Risk deny-path demo: reviews an unsafe/out-of-policy LIVE-gold path and DENIES it. Risk cannot approve LIVE.
9. Desktop: 2D pixel-art office (rooms, desks, plants, conference table, rec room), seven Varma staff sprites labelled person · department, click to right-hand panel; office remains visible; no covering overlay; status bubble; chat hits the same employee runtime. Chat history is loaded from the database. No Talk/voice.
10. pytest without paid APIs. Execution in LIVE mode is denied. Empty allow-list cannot execute.
11. TEMPORARY DEVELOPMENT DEFAULT watchlist of a few listed stocks. It is not the execution allow-list. No gold.
12. Nightly Europe/London memory filter (on-demand): archives working context in the database; evidence stays append-only; filter does not write controls.
13. Board Member read-only observability in the right-hand panel: cost ledger + recent evidence from the database. Visible without clicking an employee, and via a Board observability entry. This view does not write controls, trading_mode, allow-list, or permissions.
14. Same Board observability panel also shows: latest nightly memory-filter run; organisation-memory titles; 07:30 meeting pack status (MI brief headline, CEO handoff DELIVERED/not, Challenge SAMPLE thesis status, Risk DENIED/not); Board-only employee status bubbles. Click still opens the person in the right-hand panel. Chat stays hidden on observability.
15. Same panel lists 07:30 meeting artefacts from the database (brief, CEO handoff, SAMPLE thesis, challenge review, Risk decision). Read-only. SAMPLE is not a live trade. Risk cannot approve LIVE.
16. Board-only documented routine schedules in the same panel (06:30 weekday brief; nightly Europe/London filter). On-demand. No 24/7 daemon. No invented nightly clock hour.
17. Same panel: Board-set numeric limits from **Board Addendum A 2026-08-27** (VALUES shown: simulated_capital 1000 GBP, max_position 200 GBP, max_daily_loss 50 GBP, max_orders_per_day 6, kill-switch floors 800 / -50 GBP). Not invented silent defaults. Employees cannot write limits. A missing key still DENIES execution.
18. Same panel: Board-only control snapshot (trading_mode=LIVE_BLOCKED, Grand Opening PAPER OPEN for practice, employees cannot write controls). Read-only except the Board-only kill switch.
19. Same panel: Board-only paper-gate status — Grand Opening PAPER done (Hari explicit yes, 3 Sep 2026). Practice / paper only. PAPER execution OPEN. First paper-trade PATH exists (Trader proposal → ControlEngine → internal simulator). trading_mode stays LIVE_BLOCKED. £1000 is the paper starting book. LIVE still blocked. Never auto-switch. Paper duration remains an OPEN BOARD DECISION.
20. Same panel: Board-only confirmation that BROKER_PAPER and LIVE execution ports remain UNLOADED. No broker fills. Constructing or using those ports is denied. Internal simulator may fill a legal allow-list practice order after Grand Opening PAPER.
21. On-demand 07:30 Europe/London company meeting record: Board Member API or documented CLI writes a meeting artefact to the database from existing handoffs (MI brief, CEO pack, Challenge SAMPLE, Risk DENY). Shown read-only in Board observability. Not a trade. Not LIVE approval. Not a daemon. Employees cannot start LIVE from a meeting.
22. Latest 07:30 meeting attendance list: the four existing employees only (MI, CEO, Challenge, Risk). Not a 12-employee roster. Read-only in Board observability.
23. Board Member can run the existing on-demand jobs from the right-hand Board observability panel (POST, not GET /observability): morning intelligence brief, SAMPLE challenge, Risk deny-path, 07:30 meeting record, nightly memory filter, company backup, Trader paper-ticket proposal. Employees are denied. Running a job does not load broker ports or change trading_mode. After Grand Opening PAPER the Trader path may fill in the internal simulator. LIVE stays off. After a run the same panel refreshes from the database. CLI entry points still work.
24. Board-usable kill switch (Board Member only): halt if paper equity <= 800 GBP OR London-day P&L <= -50 GBP, or when the Board Member triggers halt without an AI employee. Addendum A numbers apply after Grand Opening PAPER. On halt: cancel open PAPER orders only; never load LIVE; never flatten live (there is no live). Employees cannot reset it.
25. Evaluation ledger tables exist (closed trades, P&L, win rate of profitable closes). Zero fills is valid.
26. Board Addendum I 2026-08-27 is the two-opening rule. Grand Opening PAPER happened (Hari explicit yes, 3 Sep 2026, word: Open). Practice / paper only. LIVE has not opened. The first paper-trade PATH exists (Trader proposal → ControlEngine → internal simulator). No 07:30 diary invite to the Board Member; 07:30 may exist as an internal staff artefact and must not email or calendar-invite Hari. Do not flatten-as-if-there-were-positions.
27. Board Addendum J 2026-08-27: company records are not on the Board Member's laptop and not in GitHub. GitHub is code only. System of record remains the database. Board-visible backup status (last successful backup time, last failure, included: paper ledger / evidence / organisational memory / control snapshots; excluded: secrets / live broker credentials which must not exist yet). Board-only job to run a backup now. Default schedule: daily Europe/London after US close / end of London evening. Encrypted at rest. Technology (Owen Blake · Technology) owns the job and cannot write trading_mode, allow-list, or open the firm. Employees including the CEO cannot download secrets. The backup job does not fill orders.
28. Documents 03 and 08: each employee is a durable database record (identity, role knowledge, authority boundaries, memory pointers, skills, relationships), not an LLM prompt. An LLM call is an invocation of that person. Four memory stores: working context, employee persistent memory, shared organisational knowledge (governed promotion only), append-only evidence. Learning writes memory only, never controls. The next job for the same employee loads lessons from the database and changes behaviour. Challenge stays independent of Quant; Risk stays independent of Trader (originator “I believe this” is not loaded as their own belief). FakeLLM may simulate retrieval; the memory API is the database.
29. Board Addendum K 2026-09-03 (Hari explicit yes): after London cash market shuts, deny paper orders in SHEL.L, AZN.L, ULVR.L only. CEO desk 02F (bound in ControlEngine): those three flatten in the London closing auction 16:30–16:35 and cannot be held to New York. US names still flatten at US regular cash close. Firm day still runs to NY close. split_flatten_clocks true. Dual-listed US lines SHEL/AZN/ULVR are not on the allow-list. LIVE_BLOCKED. Employees cannot write this lock. PR #21 leftover draft: leave open.

## System separation

- GitHub (varmacorpuk/varma-corp): source code only. Never commit .env, DB volumes, memories, keys.
- This box: DEVELOPMENT. Persistent org data in a database. Kernel startup reconciles Board-encoded seed (seven named employees, Addendum A numbers, Addendum E allow-list, Addendum I two-opening rule with Grand Opening PAPER OPEN) onto a stale SQLite copy. Does not start a 24/7 daemon.
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
    python3 -m varma.routines.run_0730_meeting
    python3 -m varma.routines.run_backup
    python3 -m varma.routines.run_paper_trade_path
    python3 -m varma.routines.run_paper_trade_path --ticket PAPER-20260903-02
    python3 -m varma

Health: http://127.0.0.1:8000/health

### Desktop

One client for Mac and Windows (Electron). Browser also works in development.

    python3 -m varma
    cd desktop && python3 -m http.server 5173 --bind 127.0.0.1

Then open http://127.0.0.1:5173

Click Research, the CEO, Challenge, or Risk. The right-hand panel shows work (produced brief, meeting inbox, SAMPLE thesis, challenge review, or Risk DENY). Board observability (on-demand job runs, Board Addendum A limits, kill switch, paper ledger, evaluation ledger, control snapshot, paper-gate status, UNLOADED BROKER_PAPER and LIVE execution ports, latest 07:30 company meeting record, cost ledger, recent evidence, nightly filter, organisation-memory titles, 07:30 meeting pack status, status bubbles) loads in that same panel without clicking an employee, and via the Board observability entry. Board Member can run the existing on-demand jobs from that panel and can halt/reset the kill switch. Office stays visible. Chat uses the same employee runtime. Talk is disabled. CEO, Challenge, and Risk cannot approve LIVE. GET /observability is read-only. Job runs and the kill switch are Board-only POST endpoints.

## 06:30 Europe/London routine

Documented weekday schedule: 06:30 Europe/London, output due before the 07:30 company meeting (Documents 02, 09, 18). The CEO is the meeting recipient of that pack.

This slice does not start a 24/7 daemon scheduler. Run on demand from the Board observability panel, or:

    python3 -m varma.routines.run_brief

A later slice can attach the same skill to a Europe/London scheduler.

## Controls (not memory)

- trading_mode: LIVE_BLOCKED (internal paper fill simulator is the paper ledger; PAPER execution is OPEN after Grand Opening PAPER; do not load LIVE or BROKER_PAPER)
- PAPER execution: OPEN (Board Grand Opening PAPER 2026-09-03). Employees including the CEO cannot write this flag or open/close the firm. LIVE still blocked.
- Execution allow-list: Board Addendum E 2026-08-27 PAPER membership (AAPL, MSFT, NVDA, AMZN, GOOGL on NASDAQ; JPM, JNJ on NYSE; SHEL.L, AZN.L, ULVR.L on LSE). After Grand Opening PAPER these names may fill in the simulator. Unknown tickers deny. Gold denies. Employees including the CEO cannot write the list.
- Numeric limits: Board Addendum A 2026-08-27 (Board-set, VALUES stored, in use after paper open)
  - simulated_capital = 1000 GBP (paper starting book)
  - max_position = 200 GBP (one paper trade)
  - max_daily_loss = 50 GBP
  - max_orders_per_day = 6
  - kill switch: halt if paper equity <= 800 GBP OR London-day P&L <= -50 GBP
- Currency GBP. Timezone Europe/London.
- LIVE adapter: not loaded
- BROKER_PAPER and LIVE execution ports: UNLOADED (no broker fills)
- Internal PAPER FILL SIMULATOR may fill a legal allow-list practice order after Grand Opening PAPER. First paper-trade PATH exists (Trader proposal → ControlEngine → simulator). LIVE stays blocked.
- Paper session (Board Addendum C 2026-08-27): UK cash open through US regular cash close. CEO desk 02F: LSE names flatten in the London closing auction 16:30–16:35; US names flatten at US close. split_flatten_clocks true. Do not flatten-as-if-there-were-positions.
- Employees cannot write control tables, allow-list, limits, trading_mode, PAPER execution, or approve LIVE. CEO may recommend allow-list adds; cannot write them; cannot open the firm.
- Board Member can trigger the kill switch without an AI employee. On halt: cancel open PAPER orders only; never load LIVE; never flatten live. Employees cannot reset it.

Gate: Grand Opening PAPER happened (Hari explicit yes, 3 Sep 2026). Practice on the £1000 book, then EVALUATION then recommendation then Board review then explicit Grand Opening LIVE yes. Silence is not approval. Never auto-switch. LIVE opening is not implemented.

## Internal paper fill simulator (Document 12)

Not a broker. Assumptions (labelled INTERNAL, not a vendor contract):

- Spread: 10 bps of mid. Half-spread + 5 bps slippage = 10 bps adverse vs mid.
- Commission: 5 bps of fill notional.
- Fake delayed last prices are treated as GBP notional (no FX vendor in this slice).
- Currency GBP. Timezone Europe/London.

Evaluation ledger tables (`closed_paper_trades`, fills, P&L, win rate) exist. Zero fills is valid.

## TEMPORARY defaults (not Board-permanent)

These exist so development can run. They are not Board-approved universe membership, budgets, or limits.

- Watchlist: AAPL, MSFT, SHEL.L, AZN.L — TEMPORARY DEVELOPMENT DEFAULT. Not the allow-list. Listed equities only.
- Brief cost cap: 100 units — TEMPORARY DEVELOPMENT DEFAULT. Not a budget.
- News freshness window: 18 hours — TEMPORARY DEVELOPMENT DEFAULT
- Price freshness window: 26 hours — TEMPORARY DEVELOPMENT DEFAULT
- Auth stub: see .env.example — DEVELOPMENT only
- SQLite path: data/varma_paper_open.db — paper-OPEN practice book (TEMPORARY until Postgres). Do not use empty data/varma.db.
- Fake delayed prices and news: in-process FakeMarketData — not a vendor contract
- Simulator FX: none — last treated as GBP (INTERNAL ASSUMPTION)

OPEN BOARD DECISIONS left unset (must not be invented): paper duration threshold; Talk/voice required?; UK legal advice; exact authorised instrument list; material-cost approval thresholds.

## Challenge and Risk (this slice)

On demand, not a 24/7 daemon. Board Member right-hand panel, API, or documented CLI:

    python3 -m varma.routines.run_challenge
    python3 -m varma.routines.run_risk_deny

- Challenge receives a SAMPLE thesis (AAPL from the TEMPORARY watchlist). It is labelled SAMPLE — not a live trade, not an order, not allow-list membership.
- Challenge writes a CHALLENGED review to the database and hands it to Risk.
- Risk reviews an unsafe/out-of-policy path (LIVE execution of gold, treating the SAMPLE thesis as an order) and records DENIED. The control engine is consulted. Risk cannot approve LIVE.

## Nightly Europe/London memory filter

On demand, not a 24/7 daemon. Board Member right-hand panel, API, or documented CLI:

    python3 -m varma.routines.run_nightly_filter

- Cadence: nightly, timezone Europe/London (Document 08).
- Working context is archived to `memory_working_archive` and cleared from `memory_working`.
- Evidence is append-only and is never deleted or overwritten.
- The filter does not write controls, `trading_mode`, allow-list, or permissions.
- Filter run is a database artefact (`memory_filter_runs`), not a desktop file.

## 07:30 Europe/London company meeting

On demand, not a 24/7 daemon. Board Member right-hand panel, API, or documented CLI:

    python3 -m varma.routines.run_0730_meeting

- Cadence: 07:30 weekdays, timezone Europe/London (Documents 02, 09, 18).
- Writes a meeting artefact (`company_meetings`) from existing handoffs: MI brief, CEO pack, Challenge SAMPLE, Risk DENY.
- Not a trade. Not LIVE approval. Does not write controls. Does not start LIVE.
- Internal staff artefact. No 07:30 diary invite to the Board Member. Must not email or calendar-invite Hari.
- Employees cannot start LIVE from a meeting. Research/CEO/Challenge/Risk cannot run the meeting via the API.
- Latest meeting is shown read-only in Board observability. Artefact lives in the database, not on the desktop.
- Attendance is the four existing employees only (Research, CEO, Challenge, Risk). Not a 12-employee roster. Board Member is the human, not an employee attendee.

## Company backup (Board Addendum J)

On demand, not a 24/7 daemon. Board Member right-hand panel, API, or documented CLI:

    python3 -m varma.routines.run_backup

- Cadence: daily Europe/London, after US close / end of London evening. No invented clock hour.
- Technology (Owen Blake · Technology) owns the job. Board Member runs it. Owen cannot write `trading_mode`, allow-list, or open the firm.
- Encrypted artefact stays in the database (`backup_runs`). Same StoragePort. Not a second store. Not in GitHub. Not on the Board Member laptop.
- Included: paper ledger, evidence, organisational memory, control snapshots.
- Excluded: secrets, live broker credentials (which must not exist yet). Employees including the CEO cannot download secrets.
- Does not fill orders. PAPER execution stays a Board control. LIVE stays blocked.

## Board observability (this slice)

The right-hand panel is a Board Member projection of the database, not a ledger of its own.

- Cost ledger and recent evidence are read from the kernel (`GET /observability`).
- Latest nightly memory-filter run and organisation-memory titles (titles only) are read from the database.
- 07:30 meeting pack status: latest MI brief headline, CEO handoff DELIVERED/not, Challenge SAMPLE thesis status, Risk DENIED/not.
- 07:30 meeting artefact list (read-only): latest brief, CEO handoff, SAMPLE thesis, challenge review, Risk decision.
- Board-only documented routine schedules: 06:30 weekday brief, nightly Europe/London filter, and daily backup after US close / end of London evening (on-demand, no daemon, no invented backup clock hour).
- Board-only missing numeric-limit keys (empty after Addendum A) and Board-set VALUES (simulated_capital 1000 GBP, max_position 200 GBP, max_daily_loss 50 GBP, max_orders_per_day 6, kill-switch floors). Not invented silent defaults.
- Board-only control snapshot: `trading_mode=LIVE_BLOCKED`, PAPER execution OPEN after Grand Opening PAPER, employees cannot write controls. Read-only except Board-only kill switch POST.
- Board-only paper-gate status: Grand Opening PAPER done. Practice / paper only. PAPER execution OPEN. First paper-trade PATH exists. £1000 paper starting book. LIVE still blocked. Silence is not approval.
- Board-only execution-port status: BROKER_PAPER and LIVE remain UNLOADED. No broker fills. Internal simulator may fill a legal allow-list practice order.
- Board-only kill switch status and Board Member halt/reset. On halt: cancel open PAPER orders only. Employees cannot reset it. Addendum A numbers apply after paper open.
- Board-only evaluation ledger (closed trades, P&L, win rate) — zero fills is valid.
- Latest on-demand 07:30 company meeting record (read-only): internal staff artefact; no Board Member diary/calendar invite; not a trade, not LIVE approval, employees cannot start LIVE from it. Attendance is the four existing employees only — not a 12-employee roster.
- Board-only on-demand job runs from this same panel: morning intelligence brief, SAMPLE challenge, Risk deny-path, 07:30 meeting record, nightly memory filter, company backup, Trader paper-ticket proposal. POST `/routines/run-*`, not GET `/observability`. Employees are denied. Running a job does not load BROKER_PAPER or LIVE and does not change `trading_mode`. After Grand Opening PAPER the Trader path may fill in the internal simulator. After a run the panel refreshes from the database. CLI entry points still work.
- Board-only backup status (Board Addendum J): last successful backup time, last failure, included (paper ledger, evidence, organisational memory, control snapshots), excluded (secrets, live broker credentials which must not exist yet). Encrypted at rest in the database. Not in GitHub. Not on the Board Member laptop. Technology (Owen Blake · Technology) owns the job and cannot write trading_mode, allow-list, or open the firm. Employees including the CEO cannot download secrets.
- Board-only employee status bubbles. Click an employee (floor or bubble name) to open that person in the same right-hand panel.
- Visible without clicking an employee. A Board observability entry returns to this view.
- Read-only. It does not write controls, `trading_mode`, allow-list, or permissions. Chat is hidden on this view.
- Cost cap remains a TEMPORARY DEVELOPMENT DEFAULT. It is not a Board-approved budget (Document 17 OPEN: material-cost thresholds).
- Evidence stays append-only.

## Next slice

Practice / paper is open. Grand Opening PAPER happened (Hari explicit yes, 3 Sep 2026). LIVE stays blocked. BROKER_PAPER and LIVE remain UNLOADED. £1,000 fake money on the internal simulator. No Mac installers. Approve LIVE remains impossible until Hari's explicit Grand Opening LIVE yes after paper evidence.

## Specs

See ARCHITECTURE.md. Authoritative documents 00-18 are not copied into git.

## Tests

    python3 -m pytest

Covers: no fills while PAPER execution is CLOSED, even for allow-listed tickers; first paper-trade PATH (Trader proposal → ControlEngine → simulator) exists and is still gated CLOSED; LIVE denied; BROKER_PAPER UNLOADED; gold denied; employees cannot open the firm; CEO cannot open the firm; Board Addendum I CLOSED gate; Board Addendum J encrypted company backup in the database (not git, not the laptop; last success/failure visible; secrets and live broker credentials excluded; Technology owns the job and cannot write trading_mode, allow-list, or open the firm; employees including CEO cannot download secrets; backup job does not fill orders); Board Addendum A limits are Board-set and shown (unused until open); kill switch remains Board-only; employees cannot write limits or reset the kill switch; CEO/Challenge/Risk cannot approve LIVE; brief verification and handoff to CEO; SAMPLE thesis challenge; Risk deny-path; nightly memory filter archives working context without deleting evidence or writing controls; on-demand 07:30 company meeting record from existing handoffs (internal staff artefact; no Board Member diary/calendar invite; not a trade, not LIVE approval) with attendance of the four existing employees only; Board can read cost ledger, recent evidence, nightly filter run, organisation-memory titles, 07:30 meeting pack status, meeting artefact list, latest company meeting, status bubbles, documented routine schedules, Board-set numeric-limit VALUES, kill-switch state, evaluation ledger (zero fills valid), control snapshot, paper-gate status (CLOSED), UNLOADED BROKER_PAPER and LIVE execution ports, backup status, and employee chat history; Board Member can run the on-demand jobs from the right-hand panel via POST (employees denied; GET /observability does not run jobs; running a job does not load broker ports, change trading_mode, or fill orders); constructing or using BROKER_PAPER/LIVE is denied; flatten-as-if-there-were-positions is a no-op while closed; employees cannot use observability to write controls; watchlist is not the allow-list; office right-hand panel is not an overlay; display names stay First Last · Department; Talk off; FakeLLM only; durable employees (Documents 03/08) with four memory stores; sequential jobs load lessons from the database; Challenge/Risk do not load originator belief; learning never writes controls.
