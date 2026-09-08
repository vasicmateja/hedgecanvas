"""Fixture builders for deterministic historical-artifact tests.

These build small, hand-constructed CSVs with the exact canonical schema
(never the real production files) so ordinary unit tests never depend on
the real canonical artifacts. Tests needing a wrong expected hash/schema/
row-count pass fixture-specific expectations into ``validate_artifact``
directly rather than pretending fixture bytes match the production SHA-256
values.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import pandas as pd

from hedgecanvas.historical.config import MONTHLY_RESULTS_SCHEMA, STRATEGY_METRICS_SCHEMA


def metrics_row(
    *,
    asset: str,
    strategy: str,
    net_premium_cost: float = 0.0,
    upside_shortfall: float = 0.0,
    cumulative_return: float = 0.2,
    annualized_return: float = 0.5,
    annualized_volatility: float = 0.6,
    monthly_maximum_drawdown: float = -0.1,
    downside_deviation_annualized: float = 0.3,
    sortino_ratio: float = 1.5,
) -> dict:
    return {
        "asset": asset,
        "strategy": strategy,
        "scope": "PRIMARY",
        "months": 2,
        "initial_wealth_index": 100.0,
        "final_wealth_index": 120.0,
        "cumulative_return": cumulative_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "monthly_maximum_drawdown": monthly_maximum_drawdown,
        "downside_deviation_annualized": downside_deviation_annualized,
        "sortino_ratio": sortino_ratio,
        "net_premium_cost_coin_per_unit_notional_sum": net_premium_cost,
        "upside_shortfall_positive_benchmark_months_sum": upside_shortfall,
    }


def default_metrics_rows() -> List[dict]:
    return [
        metrics_row(asset="BTC", strategy="BENCHMARK"),
        metrics_row(asset="BTC", strategy="PP95", net_premium_cost=1.5, upside_shortfall=0.75),
        metrics_row(asset="BTC", strategy="CC105", net_premium_cost=-2.25),
        metrics_row(asset="BTC", strategy="COLLAR95_105"),
        metrics_row(asset="BTC", strategy="PP90"),
        metrics_row(asset="BTC", strategy="CC110"),
        metrics_row(asset="BTC", strategy="COLLAR90_110"),
        metrics_row(asset="ETH", strategy="BENCHMARK"),
        metrics_row(asset="ETH", strategy="PP95"),
        metrics_row(asset="ETH", strategy="CC105"),
        metrics_row(asset="ETH", strategy="COLLAR95_105"),
        metrics_row(asset="ETH", strategy="PP90"),
        metrics_row(asset="ETH", strategy="CC110"),
        metrics_row(asset="ETH", strategy="COLLAR90_110"),
    ]


def write_metrics_csv(
    path: Path, rows: Sequence[dict], *, columns: Sequence[str] = STRATEGY_METRICS_SCHEMA
) -> Path:
    pd.DataFrame(list(rows), columns=list(columns)).to_csv(path, index=False)
    return path


def monthly_row(
    *,
    asset: str,
    strategy: str,
    decision_month: str,
    wealth_start: float,
    wealth_end: float,
    cycle_id: str = "cycle-1",
) -> dict:
    return {
        "cycle_id": cycle_id,
        "asset": asset,
        "decision_month": decision_month,
        "strategy": strategy,
        "scope": "PRIMARY",
        "decision_timestamp_utc": f"{decision_month}-01T00:00:00Z",
        "terminal_timestamp_utc": f"{decision_month}-01T00:00:00Z",
        "decision_spot_usd": 30000.0,
        "terminal_spot_usd": 31000.0,
        "underlying_return": 0.03,
        "selected_leg_count": 1,
        "no_eligible_contract": False,
        "entry_premium_cashflow_coin_per_unit_underlying": 0.0,
        "settlement_cashflow_coin_per_unit_underlying": 0.0,
        "terminal_coin_per_initial_coin": 1.0,
        "premium_return_contribution": 0.0,
        "settlement_return_contribution": 0.0,
        "strategy_return": 0.03,
        "accounting_decomposition_error": 0.0,
        "wealth_start": wealth_start,
        "wealth_end": wealth_end,
    }


def default_monthly_rows() -> List[dict]:
    return [
        # BTC BENCHMARK: two months, deliberately written out of order to
        # test decision_month sorting.
        monthly_row(
            asset="BTC", strategy="BENCHMARK", decision_month="2020-02",
            wealth_start=105.0, wealth_end=110.0, cycle_id="c2",
        ),
        monthly_row(
            asset="BTC", strategy="BENCHMARK", decision_month="2020-01",
            wealth_start=100.0, wealth_end=105.0, cycle_id="c1",
        ),
        monthly_row(
            asset="BTC", strategy="PP95", decision_month="2020-01",
            wealth_start=100.0, wealth_end=102.0, cycle_id="c3",
        ),
        monthly_row(
            asset="BTC", strategy="PP95", decision_month="2020-02",
            wealth_start=102.0, wealth_end=104.0, cycle_id="c4",
        ),
        monthly_row(
            asset="BTC", strategy="PP90", decision_month="2020-01",
            wealth_start=100.0, wealth_end=101.0, cycle_id="c5",
        ),
        monthly_row(
            asset="ETH", strategy="BENCHMARK", decision_month="2020-01",
            wealth_start=100.0, wealth_end=103.0, cycle_id="c6",
        ),
    ]


def write_monthly_csv(
    path: Path, rows: Sequence[dict], *, columns: Sequence[str] = MONTHLY_RESULTS_SCHEMA
) -> Path:
    pd.DataFrame(list(rows), columns=list(columns)).to_csv(path, index=False)
    return path
