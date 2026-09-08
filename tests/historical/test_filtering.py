"""Tests for pure filtering/sorting/extraction over verified historical data.

No arithmetic on stored values is exercised here: only filtering, sorting,
and confirming the wealth chart source is wealth_end, never reconstructed.
"""

import pandas as pd
import pytest

from hedgecanvas.historical.filtering import filter_metrics, filter_wealth_path, wealth_end_series
from hedgecanvas.historical.keys import HistoricalView
from tests.historical.helpers import default_metrics_rows, default_monthly_rows


@pytest.fixture
def metrics_df() -> pd.DataFrame:
    return pd.DataFrame(default_metrics_rows())


@pytest.fixture
def monthly_df() -> pd.DataFrame:
    return pd.DataFrame(default_monthly_rows())


def test_btc_primary_filtering(metrics_df: pd.DataFrame) -> None:
    filtered = filter_metrics(metrics_df, "BTC", HistoricalView.PRIMARY)
    assert set(filtered["strategy"]) == {"BENCHMARK", "PP95", "CC105", "COLLAR95_105"}
    assert set(filtered["asset"]) == {"BTC"}


def test_eth_primary_filtering(metrics_df: pd.DataFrame) -> None:
    filtered = filter_metrics(metrics_df, "ETH", HistoricalView.PRIMARY)
    assert set(filtered["strategy"]) == {"BENCHMARK", "PP95", "CC105", "COLLAR95_105"}
    assert set(filtered["asset"]) == {"ETH"}


def test_btc_robustness_filtering(metrics_df: pd.DataFrame) -> None:
    filtered = filter_metrics(metrics_df, "BTC", HistoricalView.ROBUSTNESS)
    assert set(filtered["strategy"]) == {"BENCHMARK", "PP90", "CC110", "COLLAR90_110"}


def test_eth_robustness_filtering(metrics_df: pd.DataFrame) -> None:
    filtered = filter_metrics(metrics_df, "ETH", HistoricalView.ROBUSTNESS)
    assert set(filtered["strategy"]) == {"BENCHMARK", "PP90", "CC110", "COLLAR90_110"}


def test_benchmark_in_both_primary_and_robustness(metrics_df: pd.DataFrame) -> None:
    primary = filter_metrics(metrics_df, "BTC", HistoricalView.PRIMARY)
    robustness = filter_metrics(metrics_df, "BTC", HistoricalView.ROBUSTNESS)
    assert "BENCHMARK" in set(primary["strategy"])
    assert "BENCHMARK" in set(robustness["strategy"])


def test_no_robustness_only_strategies_in_primary(metrics_df: pd.DataFrame) -> None:
    filtered = filter_metrics(metrics_df, "BTC", HistoricalView.PRIMARY)
    assert not ({"PP90", "CC110", "COLLAR90_110"} & set(filtered["strategy"]))


def test_no_primary_only_strategies_in_robustness(metrics_df: pd.DataFrame) -> None:
    filtered = filter_metrics(metrics_df, "BTC", HistoricalView.ROBUSTNESS)
    assert not ({"PP95", "CC105", "COLLAR95_105"} & set(filtered["strategy"]))


def test_filter_metrics_rejects_unknown_asset(metrics_df: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        filter_metrics(metrics_df, "DOGE", HistoricalView.PRIMARY)


def test_wealth_data_filtered_by_literal_asset_and_strategy(monthly_df: pd.DataFrame) -> None:
    filtered = filter_wealth_path(monthly_df, "BTC", HistoricalView.PRIMARY)
    assert set(filtered["asset"]) == {"BTC"}
    assert set(filtered["strategy"]) <= {"BENCHMARK", "PP95", "CC105", "COLLAR95_105"}


def test_decision_month_ordering_respected(monthly_df: pd.DataFrame) -> None:
    series = wealth_end_series(monthly_df, "BTC", "BENCHMARK")
    months = list(series["decision_month"])
    assert months == sorted(months)
    assert months == ["2020-01", "2020-02"]


def test_wealth_chart_data_uses_wealth_end(monthly_df: pd.DataFrame) -> None:
    series = wealth_end_series(monthly_df, "BTC", "BENCHMARK")
    # Fixture: 2020-01 wealth_end=105.0, 2020-02 wealth_end=110.0
    assert list(series["wealth_end"]) == [105.0, 110.0]


def test_wealth_start_is_not_substituted_for_chart_values(monthly_df: pd.DataFrame) -> None:
    series = wealth_end_series(monthly_df, "BTC", "BENCHMARK")
    # wealth_start values for the same rows are 100.0 and 105.0 -- distinct
    # from wealth_end (105.0, 110.0). Confirm the series is wealth_end, not
    # wealth_start, and that wealth_start is not even present in the output.
    assert "wealth_start" not in series.columns
    assert list(series["wealth_end"]) != [100.0, 105.0]


def test_strategy_return_not_used_to_rebuild_wealth(monthly_df: pd.DataFrame) -> None:
    series = wealth_end_series(monthly_df, "BTC", "BENCHMARK")
    assert "strategy_return" not in series.columns


def test_no_cumulative_product_reconstruction(monthly_df: pd.DataFrame) -> None:
    # A cumulative-product reconstruction from strategy_return (0.03 per
    # fixture row) would NOT equal the stored wealth_end values (105, 110).
    series = wealth_end_series(monthly_df, "BTC", "BENCHMARK")
    naive_reconstruction = [100.0 * (1.03**1), 100.0 * (1.03**2)]
    assert list(series["wealth_end"]) != naive_reconstruction


def test_stored_wealth_end_values_remain_unchanged(monthly_df: pd.DataFrame) -> None:
    series = wealth_end_series(monthly_df, "ETH", "BENCHMARK")
    assert list(series["wealth_end"]) == [103.0]


def test_filter_wealth_path_sorted_across_strategies(monthly_df: pd.DataFrame) -> None:
    filtered = filter_wealth_path(monthly_df, "BTC", HistoricalView.PRIMARY)
    months = list(filtered["decision_month"])
    assert months == sorted(months)
