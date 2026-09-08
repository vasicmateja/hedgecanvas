"""Tests for stored-metric presentation formatting (no recomputation)."""

import pandas as pd

from hedgecanvas.ui.historical_view_models import (
    build_metrics_table,
    format_net_premium_cost,
    format_percentage_metric,
    format_ratio_metric,
    format_upside_shortfall,
)
from tests.historical.helpers import metrics_row


def test_stored_metric_values_returned_unchanged_via_table() -> None:
    rows = [metrics_row(asset="BTC", strategy="BENCHMARK", cumulative_return=0.2345)]
    df = pd.DataFrame(rows)
    table = build_metrics_table(df)
    assert table.loc[0, "Cumulative Return"] == "23.45%"


def test_percentage_formatting_is_display_only() -> None:
    assert format_percentage_metric(0.679201157477) == "67.92%"


def test_ratio_formatting() -> None:
    assert format_ratio_metric(2.00645603082) == "2.01"


def test_positive_net_premium_is_cost() -> None:
    text = format_net_premium_cost(1.5)
    assert text.startswith("Cost:")
    assert "1.500000" in text


def test_negative_net_premium_presented_as_credit_without_changing_value() -> None:
    text = format_net_premium_cost(-2.25)
    assert text.startswith("Credit:")
    assert "2.250000" in text  # magnitude shown, sign carried by the word "Credit"


def test_zero_net_premium() -> None:
    assert format_net_premium_cost(0.0) == "0.000000 coin/unit notional (cumulative)"


def test_net_premium_wording_never_says_annualized_or_average() -> None:
    for value in (1.5, -2.25, 0.0):
        text = format_net_premium_cost(value)
        assert "annualized" not in text.lower()
        assert "average" not in text.lower()
        assert "cumulative" in text.lower()


def test_upside_shortfall_is_cumulative_not_averaged_or_annualized() -> None:
    text = format_upside_shortfall(2.23048382043)
    assert "cumulative" in text.lower()
    assert "annualized" not in text.lower()
    assert "average" not in text.lower()
    assert "%" not in text
    assert "2.230484" in text


def test_build_metrics_table_uses_friendly_strategy_labels() -> None:
    rows = [
        metrics_row(asset="BTC", strategy="BENCHMARK"),
        metrics_row(asset="BTC", strategy="COLLAR95_105"),
    ]
    table = build_metrics_table(pd.DataFrame(rows))
    assert list(table["Strategy"]) == ["Unhedged Benchmark", "Collar 95/105"]


def test_build_metrics_table_contains_all_eight_canonical_metric_columns() -> None:
    rows = [metrics_row(asset="BTC", strategy="BENCHMARK")]
    table = build_metrics_table(pd.DataFrame(rows))
    expected_labels = {
        "Cumulative Return",
        "Annualized Return",
        "Annualized Volatility",
        "Max Monthly Drawdown",
        "Downside Deviation (ann.)",
        "Sortino Ratio",
        "Net Premium Cost (coin/unit notional, cumulative)",
        "Upside Shortfall — Positive Benchmark Months (cumulative)",
    }
    assert expected_labels <= set(table.columns)
