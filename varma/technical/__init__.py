"""Deterministic technical analysis toolkit for the paper desk.

Offline, no AI calls at read time. Uses pandas-ta over bar data.
Ticker-agnostic — does not hardcode to any specific allow-list.
"""

from varma.technical.indicators import technical_snapshot

__all__ = ["technical_snapshot"]
