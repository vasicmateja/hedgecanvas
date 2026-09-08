"""Canonical Phase 4 artifact configuration: filenames, expected hashes,
exact ordered schemas, expected row counts, provenance, and the local
artifact-directory convention.

Nothing in this module reads or validates a file -- it only defines the
frozen expectations that ``validation.py`` checks against. The default
location is repository-relative ``data/historical/frozen/``; it may be
overridden with the ``HEDGECANVAS_HISTORICAL_DIR`` environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_HISTORICAL_DIR = REPO_ROOT / "data" / "historical" / "frozen"
HISTORICAL_DIR_ENV_VAR = "HEDGECANVAS_HISTORICAL_DIR"

CANONICAL_PRODUCTION_RUN_ID = (
    "0cc87d60337032ec493534d312fc84734c5a4ae6a34b5687424f0761937d6132"
)

SAMPLE_START_MONTH = "2020-01"
SAMPLE_END_MONTH = "2024-12"

# -- strategy_metrics.csv ----------------------------------------------------

STRATEGY_METRICS_FILENAME = "strategy_metrics.csv"
STRATEGY_METRICS_EXPECTED_SHA256 = (
    "eb7c38272283b79c5fa878975276e9251e98c50e88bcd8c5e7a2138078488c70"
)
STRATEGY_METRICS_EXPECTED_ROWS = 14

STRATEGY_METRICS_SCHEMA: Tuple[str, ...] = (
    "asset",
    "strategy",
    "scope",
    "months",
    "initial_wealth_index",
    "final_wealth_index",
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "monthly_maximum_drawdown",
    "downside_deviation_annualized",
    "sortino_ratio",
    "net_premium_cost_coin_per_unit_notional_sum",
    "upside_shortfall_positive_benchmark_months_sum",
)

# -- monthly_backtest_results.csv -------------------------------------------

MONTHLY_RESULTS_FILENAME = "monthly_backtest_results.csv"
MONTHLY_RESULTS_EXPECTED_SHA256 = (
    "ee276e5709b0efb47238a61a0ba7145de097bb2b95cd4201e911304d7760a0a5"
)
MONTHLY_RESULTS_EXPECTED_ROWS = 840

MONTHLY_RESULTS_SCHEMA: Tuple[str, ...] = (
    "cycle_id",
    "asset",
    "decision_month",
    "strategy",
    "scope",
    "decision_timestamp_utc",
    "terminal_timestamp_utc",
    "decision_spot_usd",
    "terminal_spot_usd",
    "underlying_return",
    "selected_leg_count",
    "no_eligible_contract",
    "entry_premium_cashflow_coin_per_unit_underlying",
    "settlement_cashflow_coin_per_unit_underlying",
    "terminal_coin_per_initial_coin",
    "premium_return_contribution",
    "settlement_return_contribution",
    "strategy_return",
    "accounting_decomposition_error",
    "wealth_start",
    "wealth_end",
)


def resolve_historical_dir(override: Optional[Path] = None) -> Path:
    """Resolve the historical artifact directory.

    Precedence: explicit ``override`` argument, then the
    ``HEDGECANVAS_HISTORICAL_DIR`` environment variable, then the default
    repository-relative ``data/historical/frozen/``.
    """
    if override is not None:
        return Path(override)
    env_value = os.environ.get(HISTORICAL_DIR_ENV_VAR)
    if env_value:
        return Path(env_value)
    return DEFAULT_HISTORICAL_DIR
