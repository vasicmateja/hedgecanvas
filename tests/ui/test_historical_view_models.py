"""Tests for stored-metric presentation formatting (no recomputation)."""

import pandas as pd
import pytest

from hedgecanvas.historical.keys import (
    HistoricalView,
    PRIMARY_STRATEGIES,
    ROBUSTNESS_STRATEGIES,
    strategies_for_view,
)
from hedgecanvas.ui.historical_view_models import (
    MAIN_STRATEGIES_LABEL,
    WIDER_STRIKE_SETTINGS_LABEL,
    build_metrics_table,
    format_net_premium_cost,
    format_percentage_metric,
    format_ratio_metric,
    format_upside_shortfall,
    historical_strategy_explanation,
    historical_view_display_label,
    historical_view_explanation,
    historical_view_from_display_label,
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


# ---------------------------------------------------------------------------
# "Main Strategies" / "Wider Strike Settings" user-facing view labels
# (final polish pass) -- must map to the exact unchanged canonical sets.
# ---------------------------------------------------------------------------


def test_main_strategies_label_maps_to_primary_view() -> None:
    assert historical_view_display_label(HistoricalView.PRIMARY) == MAIN_STRATEGIES_LABEL


def test_wider_strike_settings_label_maps_to_robustness_view() -> None:
    assert historical_view_display_label(HistoricalView.ROBUSTNESS) == WIDER_STRIKE_SETTINGS_LABEL


def test_main_strategies_label_resolves_to_exact_primary_canonical_set() -> None:
    view = historical_view_from_display_label(MAIN_STRATEGIES_LABEL)
    assert view is HistoricalView.PRIMARY
    assert strategies_for_view(view) == PRIMARY_STRATEGIES
    assert strategies_for_view(view) == ("BENCHMARK", "PP95", "CC105", "COLLAR95_105")


def test_wider_strike_settings_label_resolves_to_exact_robustness_canonical_set() -> None:
    view = historical_view_from_display_label(WIDER_STRIKE_SETTINGS_LABEL)
    assert view is HistoricalView.ROBUSTNESS
    assert strategies_for_view(view) == ROBUSTNESS_STRATEGIES
    assert strategies_for_view(view) == ("BENCHMARK", "PP90", "CC110", "COLLAR90_110")


def test_unknown_view_label_rejected() -> None:
    with pytest.raises(ValueError):
        historical_view_from_display_label("Primary")  # old internal-sounding label, not accepted


def test_canonical_internal_strategy_keys_are_unchanged() -> None:
    # The user-facing rename must never leak into the canonical keys used
    # for filtering -- PP95 etc. remain the literal values throughout.
    assert PRIMARY_STRATEGIES == ("BENCHMARK", "PP95", "CC105", "COLLAR95_105")
    assert ROBUSTNESS_STRATEGIES == ("BENCHMARK", "PP90", "CC110", "COLLAR90_110")


def test_view_explanations_present_and_not_overclaiming() -> None:
    primary_text = historical_view_explanation(HistoricalView.PRIMARY)
    robustness_text = historical_view_explanation(HistoricalView.ROBUSTNESS)
    assert primary_text and robustness_text
    for text in (primary_text, robustness_text):
        assert "optimal" not in text.lower()
        assert "recommend" not in text.lower()
        assert "superior" not in text.lower()


def test_historical_strategy_explanations_use_target_language_not_exact_claims() -> None:
    for key in ("PP95", "CC105", "COLLAR95_105", "PP90", "CC110", "COLLAR90_110"):
        text = historical_strategy_explanation(key)
        assert text is not None
        # Must not assert the realized contract strike was exactly X% --
        # only that it targeted approximately that level.
        assert "approximately" in text.lower() or "target" in text.lower()


def test_historical_strategy_explanation_unknown_key_returns_none() -> None:
    assert historical_strategy_explanation("PP99") is None
