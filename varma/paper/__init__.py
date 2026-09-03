"""Internal paper fill simulator and evaluation ledger (Document 12).

Not BROKER_PAPER. Not LIVE. No brokerage. Empty allow-list ⇒ no orders.
"""

from varma.paper.flatten import flatten_all_paper, flatten_lse_paper, flatten_run_to_dict
from varma.paper.ledger import PaperLedger, evaluation_snapshot
from varma.paper.simulator import PaperFillSimulator

__all__ = [
    "PaperFillSimulator",
    "PaperLedger",
    "evaluation_snapshot",
    "flatten_all_paper",
    "flatten_lse_paper",
    "flatten_run_to_dict",
]
