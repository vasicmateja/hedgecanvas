"""Tests for portfolio quantity/value conversion."""

from decimal import Decimal

import pytest

from hedgecanvas.ui.portfolio import portfolio_value_from_quantity, quantity_from_portfolio_value


def test_quantity_from_portfolio_value_basic() -> None:
    Q = quantity_from_portfolio_value(Decimal("30000"), Decimal("60000"))
    assert Q == Decimal("0.5")


def test_quantity_from_portfolio_value_exact_decimal() -> None:
    Q = quantity_from_portfolio_value(Decimal("10000"), Decimal("40000"))
    assert Q == Decimal("0.25")


def test_quantity_from_portfolio_value_rejects_non_positive_s0() -> None:
    with pytest.raises(ValueError):
        quantity_from_portfolio_value(Decimal("10000"), Decimal("0"))


def test_quantity_from_portfolio_value_rejects_non_positive_value() -> None:
    with pytest.raises(ValueError):
        quantity_from_portfolio_value(Decimal("0"), Decimal("60000"))


def test_portfolio_value_from_quantity_roundtrip() -> None:
    S0 = Decimal("65000")
    Q = quantity_from_portfolio_value(Decimal("32500"), S0)
    value = portfolio_value_from_quantity(Q, S0)
    assert value == Decimal("32500")
