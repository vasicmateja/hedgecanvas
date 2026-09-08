"""Literal canonical asset/strategy keys for the frozen thesis artifacts.

These are the exact string values stored in the CSVs. They are never
inferred from display labels, and display labels are never used for
filtering -- filtering always uses these literal keys.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Tuple

CANONICAL_ASSETS: Tuple[str, ...] = ("BTC", "ETH")

CANONICAL_STRATEGIES: Tuple[str, ...] = (
    "BENCHMARK",
    "PP95",
    "CC105",
    "COLLAR95_105",
    "PP90",
    "CC110",
    "COLLAR90_110",
)

PRIMARY_STRATEGIES: Tuple[str, ...] = ("BENCHMARK", "PP95", "CC105", "COLLAR95_105")
ROBUSTNESS_STRATEGIES: Tuple[str, ...] = ("BENCHMARK", "PP90", "CC110", "COLLAR90_110")


class HistoricalView(Enum):
    PRIMARY = "PRIMARY"
    ROBUSTNESS = "ROBUSTNESS"


VIEW_STRATEGIES: Dict[HistoricalView, Tuple[str, ...]] = {
    HistoricalView.PRIMARY: PRIMARY_STRATEGIES,
    HistoricalView.ROBUSTNESS: ROBUSTNESS_STRATEGIES,
}

STRATEGY_DISPLAY_LABELS: Dict[str, str] = {
    "BENCHMARK": "Unhedged Benchmark",
    "PP95": "Protective Put 95",
    "CC105": "Covered Call 105",
    "COLLAR95_105": "Collar 95/105",
    "PP90": "Protective Put 90",
    "CC110": "Covered Call 110",
    "COLLAR90_110": "Collar 90/110",
}


def is_valid_asset(asset: str) -> bool:
    return asset in CANONICAL_ASSETS


def is_valid_strategy(strategy: str) -> bool:
    return strategy in CANONICAL_STRATEGIES


def strategies_for_view(view: HistoricalView) -> Tuple[str, ...]:
    return VIEW_STRATEGIES[view]


def strategy_display_label(strategy: str) -> str:
    """Friendly presentation label. Raises for an unrecognized canonical key
    -- an unknown strategy must never be silently accepted or labeled.
    """
    if strategy not in STRATEGY_DISPLAY_LABELS:
        raise ValueError(f"Unknown canonical strategy key: {strategy!r}")
    return STRATEGY_DISPLAY_LABELS[strategy]
