# Architecture pointer

Varma Corp. is specified in Documents **00-18** (authoritative Markdown package).

Those documents live **outside this GitHub repository** (source code only). On the development box they are at:

`/workspace/varma-corp-specs/authoritative/`

Do not copy the spec PDFs into this repo.

| Doc | Subject |
| --- | --- |
| 00 | Master Document Roadmap |
| 01 | Vision |
| 02 | Trading Organisation and Operating Model |
| 03 | AI Employee Architecture |
| 04 | Trading Strategy and Investment Approach |
| 05 | Trading Workflow and Decision Process |
| 06 | Trading Strategy and Market Universe |
| 07 | Trade Lifecycle and Decision-Making |
| 08 | AI Employee Behaviour, Memory and Learning |
| 09 | Meetings, Communication and Office Interaction |
| 10 | CEO, Management and Governance |
| 11 | Risk, Compliance, Controls and Human Approval |
| 12 | Paper Trading, Evaluation and Live Trading Transition |
| 13 | Technology, IT and Self-Maintenance |
| 14 | MVP Technical Architecture |
| 15 | Data, Market Intelligence and External Tools |
| 16 | Virtual Office and User Experience |
| 17 | Resource, Cost and Operational Sustainability |
| 18 | Final Varma Corp. Build Package |

Kernel sketch (Document 14):

```
Board Member UI  (office canvas + RIGHT-HAND PANEL + approvals)
   Chat  -->  same employee runtime   (Talk is an OPEN BOARD DECISION; off in this slice)
        |
Company Kernel
   Identity, Employees (MI, CEO, Challenge, Risk)
   Permissions, trading_mode=LIVE_BLOCKED, empty allow_list
   Skills, Routines (on-demand via Board panel POST / CLI; no 24/7 daemon)
   Memory (employee / organisation / evidence)
   Nightly Europe/London working-context filter (archive working; evidence append-only; no control writes)
   Meeting handoffs (MI brief → CEO; SAMPLE thesis → Challenge; challenge → Risk)
   On-demand 07:30 company meeting record (from existing handoffs; four-employee attendance; not a trade; not LIVE)
   Control engine + Risk deny-path (never LIVE)
   Observability, Cost ledger (Board GET /observability is read-only; database is the ledger)
   Board-only POST job runs from the right-hand panel (brief, SAMPLE challenge, Risk deny-path, 07:30 meeting, nightly filter; not GET /observability)
   Nightly filter run + organisation-memory titles + 07:30 meeting pack status + artefact list + status bubbles + documented routine schedules
   Board Addendum A 2026-08-27 numeric limits (Board-set VALUES shown; missing ⇒ deny)
   Control snapshot (trading_mode=LIVE_BLOCKED, empty allow-list, employees cannot write)
   Kill switch (Board Member POST halt/reset; employees cannot reset; cancel open PAPER only)
   Paper-gate status (LIVE_BLOCKED; internal simulator ledger; empty allow-list ⇒ no orders)
   Evaluation ledger (closed trades, P&L, win rate; zero fills valid; no auto-LIVE)
   Execution-port status (BROKER_PAPER and LIVE UNLOADED; internal simulator is the paper ledger)
        |
   LLMPort          DataPorts           ExecutionPort
   (FakeLLM)    (fake delayed/news)    (BROKER_PAPER and LIVE not loaded; internal simulator)
```

The visual office is a projection. It is not the source of truth (Document 16).

CEO, Challenge, and Risk are AI employees. They cannot approve LIVE, place orders, or write controls. Human = Board Member.

Board Member observability (cost ledger, recent evidence, nightly filter, organisation-memory titles, 07:30 meeting pack status and artefact list, latest 07:30 company meeting record, status bubbles, documented routine schedules, Board Addendum A numeric-limit VALUES, kill-switch state, evaluation ledger, control snapshot, paper-gate status, UNLOADED BROKER_PAPER and LIVE execution ports, internal paper ledger) is a right-hand panel view of the database. GET /observability is read-only and does not run jobs. Board Member runs existing on-demand jobs via POST from that panel (brief, SAMPLE challenge, Risk deny-path, 07:30 meeting, nightly filter) and can halt/reset the kill switch. Employees are denied. Running a job does not load broker ports, change trading_mode, or fill paper/live orders. After a run the panel refreshes from the database. CLI entry points still work. Numeric limits are Board Addendum A 2026-08-27 (Board-set, not invented silent defaults). trading_mode stays LIVE_BLOCKED. Empty allow-list ⇒ no orders. It is not stored on the desktop disk. Constructing or using BROKER_PAPER or LIVE is denied. The 07:30 meeting record is not a trade and cannot start LIVE.
