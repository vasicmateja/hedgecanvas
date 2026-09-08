"""Portfolio input mode: Underlying Quantity vs Portfolio Value (USD).

Both modes resolve to the same domain quantity Q. The USD-value mode's
conversion (Q = portfolio_value / S0) is kept here, transparent and
testable, rather than inlined in Streamlit widget callbacks.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum


class PortfolioInputMode(Enum):
    UNDERLYING_QUANTITY = "UNDERLYING_QUANTITY"
    PORTFOLIO_VALUE_USD = "PORTFOLIO_VALUE_USD"


def quantity_from_portfolio_value(portfolio_value_usd: Decimal, S0: Decimal) -> Decimal:
    """Q = portfolio_value / S0. Raises ValueError for a non-positive S0."""
    if S0 <= 0:
        raise ValueError("S0 must be > 0 to derive Q from a USD portfolio value")
    if portfolio_value_usd <= 0:
        raise ValueError("portfolio_value_usd must be > 0")
    return portfolio_value_usd / S0


def portfolio_value_from_quantity(Q: Decimal, S0: Decimal) -> Decimal:
    """Current USD portfolio value implied by Q at the current index price S0."""
    return Q * S0
