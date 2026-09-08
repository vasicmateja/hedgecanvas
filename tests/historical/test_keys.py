"""Tests for canonical asset/strategy key validity and display labels."""

import pytest

from hedgecanvas.historical.keys import (
    CANONICAL_STRATEGIES,
    PRIMARY_STRATEGIES,
    ROBUSTNESS_STRATEGIES,
    HistoricalView,
    is_valid_asset,
    is_valid_strategy,
    strategies_for_view,
    strategy_display_label,
)


def test_btc_asset_accepted() -> None:
    assert is_valid_asset("BTC")


def test_eth_asset_accepted() -> None:
    assert is_valid_asset("ETH")


def test_unknown_asset_rejected() -> None:
    assert not is_valid_asset("DOGE")
    assert not is_valid_asset("btc")  # case-sensitive literal key


@pytest.mark.parametrize("strategy", CANONICAL_STRATEGIES)
def test_all_seven_canonical_strategies_accepted(strategy: str) -> None:
    assert is_valid_strategy(strategy)


def test_unknown_strategy_rejected() -> None:
    assert not is_valid_strategy("PP99")
    assert not is_valid_strategy("pp95")


def test_primary_strategies_for_view() -> None:
    assert strategies_for_view(HistoricalView.PRIMARY) == PRIMARY_STRATEGIES


def test_robustness_strategies_for_view() -> None:
    assert strategies_for_view(HistoricalView.ROBUSTNESS) == ROBUSTNESS_STRATEGIES


@pytest.mark.parametrize(
    "strategy,expected_label",
    [
        ("BENCHMARK", "Unhedged Benchmark"),
        ("PP95", "Protective Put 95"),
        ("CC105", "Covered Call 105"),
        ("COLLAR95_105", "Collar 95/105"),
        ("PP90", "Protective Put 90"),
        ("CC110", "Covered Call 110"),
        ("COLLAR90_110", "Collar 90/110"),
    ],
)
def test_strategy_display_labels(strategy: str, expected_label: str) -> None:
    assert strategy_display_label(strategy) == expected_label


def test_unknown_strategy_label_raises() -> None:
    with pytest.raises(ValueError):
        strategy_display_label("PP99")
