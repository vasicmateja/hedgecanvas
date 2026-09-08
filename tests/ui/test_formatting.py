"""Tests for Decimal-safe UI input parsing and display formatting."""

from decimal import Decimal

from hedgecanvas.ui.formatting import format_percentage, format_quantity, format_usd, parse_decimal_input


def test_parse_decimal_input_from_clean_string() -> None:
    assert parse_decimal_input("0.55") == Decimal("0.55")


def test_parse_decimal_input_strips_whitespace() -> None:
    assert parse_decimal_input("  1.5  ") == Decimal("1.5")


def test_parse_decimal_input_rejects_empty_string() -> None:
    assert parse_decimal_input("") is None
    assert parse_decimal_input("   ") is None


def test_parse_decimal_input_rejects_garbage() -> None:
    assert parse_decimal_input("abc") is None
    assert parse_decimal_input("1,234") is None


def test_parse_decimal_input_accepts_int() -> None:
    assert parse_decimal_input(5) == Decimal("5")


def test_parse_decimal_input_none_is_none() -> None:
    assert parse_decimal_input(None) is None


def test_parse_decimal_input_never_returns_float_type() -> None:
    # A float, if it must be accepted at all, is converted via str() so it
    # never reaches the domain layer as a binary float value.
    result = parse_decimal_input(0.1)
    assert isinstance(result, Decimal)
    assert result == Decimal("0.1")


def test_format_usd_basic() -> None:
    assert format_usd(Decimal("1234.5")) == "$1,234.50"


def test_format_usd_negative() -> None:
    assert format_usd(Decimal("-500")) == "-$500.00"


def test_format_usd_sign_positive() -> None:
    assert format_usd(Decimal("500"), sign=True) == "+$500.00"


def test_format_quantity_trims_trailing_zeros() -> None:
    assert format_quantity(Decimal("0.500000000")) == "0.5"
    assert format_quantity(Decimal("1.00000000")) == "1"


def test_format_percentage_rounds_display_only() -> None:
    assert format_percentage(Decimal("40")) == "40.00%"
    assert format_percentage(Decimal("99.999999")) == "100.00%"
