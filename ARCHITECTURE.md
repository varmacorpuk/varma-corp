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
   Skills, Routines (on-demand; no 24/7 daemon)
   Memory (employee / organisation / evidence)
   Nightly Europe/London working-context filter (archive working; evidence append-only; no control writes)
   Meeting handoffs (MI brief → CEO; SAMPLE thesis → Challenge; challenge → Risk)
   Control engine + Risk deny-path (never LIVE)
   Observability, Cost ledger
        |
   LLMPort          DataPorts           ExecutionPort
   (FakeLLM)    (fake delayed/news)    (LIVE adapter not loaded)
```

The visual office is a projection. It is not the source of truth (Document 16).

CEO, Challenge, and Risk are AI employees. They cannot approve LIVE, place orders, or write controls. Human = Board Member.
