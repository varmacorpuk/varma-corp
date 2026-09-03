"""LSE session module still exists; Board Addendum K is the SET rule.

The required Addendum K cases live in tests/test_addendum_k.py.
"""

from tests.conftest import LONDON_CASH_CLOSE, SESSION_OPEN
from varma.controls.addendum_k import ADDENDUM_K_LABEL, ADDENDUM_K_LSE_SYMBOLS
from varma.controls.lse_session import (
    LSE_HOLD_LABEL,
    LSE_HOLD_SYMBOLS,
    london_cash_is_shut,
)


def test_lse_session_module_uses_addendum_k():
    assert LSE_HOLD_SYMBOLS == ADDENDUM_K_LSE_SYMBOLS
    assert LSE_HOLD_LABEL == ADDENDUM_K_LABEL
    assert london_cash_is_shut(SESSION_OPEN) is False
    assert london_cash_is_shut(LONDON_CASH_CLOSE) is True
