"""Presentation formatting for stored Historical Evidence metrics.

Every function here only formats an already-stored numeric value from
``strategy_metrics.csv`` for display (percentage sign, rounding, cost/credit
wording, friendly strategy labels). None of them recompute, annualize,
average, or otherwise alter the underlying stored value.
"""

from __future__ import annotations

import pandas as pd

from hedgecanvas.historical.keys import strategy_display_label

CANONICAL_METRIC_COLUMNS = (
    "cumulative_return",
    "annualized_return",
    "annualized_volatility",
    "monthly_maximum_drawdown",
    "downside_deviation_annualized",
    "sortino_ratio",
    "net_premium_cost_coin_per_unit_notional_sum",
    "upside_shortfall_positive_benchmark_months_sum",
)

NET_PREMIUM_COST_LABEL = "Net Premium Cost (coin/unit notional, cumulative)"
UPSIDE_SHORTFALL_LABEL = "Upside Shortfall — Positive Benchmark Months (cumulative)"


def format_percentage_metric(value: float, *, decimals: int = 2) -> str:
    """Display a stored return-fraction value (e.g. 0.679) as a percentage
    string (e.g. '67.90%'). This is a unit-of-display change only -- the
    same stored value, not a recomputed one.
    """
    return f"{value * 100:.{decimals}f}%"


def format_ratio_metric(value: float, *, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}"


def format_net_premium_cost(value: float) -> str:
    """Positive = net cost, negative = net credit. Cumulative, not annualized
    or averaged -- the wording always keeps that summed nature explicit.
    """
    if value > 0:
        return f"Cost: {value:.6f} coin/unit notional (cumulative)"
    if value < 0:
        return f"Credit: {abs(value):.6f} coin/unit notional (cumulative)"
    return "0.000000 coin/unit notional (cumulative)"


def format_upside_shortfall(value: float) -> str:
    """A cumulative arithmetic sum over positive benchmark months -- never
    presented as an annualized measure, a monthly average, or a percentage.
    """
    return f"{value:.6f} (cumulative, positive benchmark months)"


def build_metrics_table(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """A presentation-only table: friendly strategy labels and formatted
    metric strings, one row per input row, built strictly from the eight
    canonical stored metric columns -- no new metrics, no recomputation.
    """
    records = []
    for _, row in metrics_df.iterrows():
        records.append(
            {
                "Strategy": strategy_display_label(row["strategy"]),
                "Cumulative Return": format_percentage_metric(row["cumulative_return"]),
                "Annualized Return": format_percentage_metric(row["annualized_return"]),
                "Annualized Volatility": format_percentage_metric(row["annualized_volatility"]),
                "Max Monthly Drawdown": format_percentage_metric(row["monthly_maximum_drawdown"]),
                "Downside Deviation (ann.)": format_percentage_metric(
                    row["downside_deviation_annualized"]
                ),
                "Sortino Ratio": format_ratio_metric(row["sortino_ratio"]),
                NET_PREMIUM_COST_LABEL: format_net_premium_cost(
                    row["net_premium_cost_coin_per_unit_notional_sum"]
                ),
                UPSIDE_SHORTFALL_LABEL: format_upside_shortfall(
                    row["upside_shortfall_positive_benchmark_months_sum"]
                ),
            }
        )
    return pd.DataFrame.from_records(records)
