"""Presentation formatting for stored Historical Evidence metrics.

Every function here only formats an already-stored numeric value from
``strategy_metrics.csv`` for display (percentage sign, rounding, cost/credit
wording, friendly strategy labels). None of them recompute, annualize,
average, or otherwise alter the underlying stored value.
"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from hedgecanvas.historical.keys import HistoricalView, strategy_display_label

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


# ---------------------------------------------------------------------------
# User-facing view labels ("Main Strategies" / "Wider Strike Settings").
#
# These are presentation labels ONLY. The canonical internal HistoricalView
# enum (PRIMARY/ROBUSTNESS) and the strategy-set membership it drives in
# hedgecanvas.historical are completely unchanged -- this mapping exists
# so the UI never has to spell out PRIMARY/ROBUSTNESS to a user.
# ---------------------------------------------------------------------------

MAIN_STRATEGIES_LABEL = "Main Strategies"
WIDER_STRIKE_SETTINGS_LABEL = "Wider Strike Settings"

HISTORICAL_VIEW_DISPLAY_LABELS: Dict[HistoricalView, str] = {
    HistoricalView.PRIMARY: MAIN_STRATEGIES_LABEL,
    HistoricalView.ROBUSTNESS: WIDER_STRIKE_SETTINGS_LABEL,
}

HISTORICAL_VIEW_EXPLANATIONS: Dict[HistoricalView, str] = {
    HistoricalView.PRIMARY: "The thesis's primary protection settings.",
    HistoricalView.ROBUSTNESS: (
        "Predefined alternative strike settings used to check whether the historical "
        "conclusions depend strongly on how far the option strikes are from the "
        "reference price."
    ),
}


def historical_view_display_label(view: HistoricalView) -> str:
    return HISTORICAL_VIEW_DISPLAY_LABELS[view]


def historical_view_explanation(view: HistoricalView) -> str:
    return HISTORICAL_VIEW_EXPLANATIONS[view]


def historical_view_from_display_label(label: str) -> HistoricalView:
    """The inverse of ``historical_view_display_label`` -- resolves a
    user-facing label back to the canonical HistoricalView. Raises for an
    unrecognized label rather than silently defaulting.
    """
    for view, display_label in HISTORICAL_VIEW_DISPLAY_LABELS.items():
        if display_label == label:
            return view
    raise ValueError(f"Unknown historical view label: {label!r}")


# ---------------------------------------------------------------------------
# Strategy and metric microcopy (progressive disclosure -- shown in a
# compact "What does this mean?" expander, not permanently on screen).
# ---------------------------------------------------------------------------

HISTORICAL_STRATEGY_EXPLANATIONS: Dict[str, str] = {
    "BENCHMARK": "The unhedged BTC/ETH position, shown for comparison.",
    "PP95": "Downside protection using the thesis's approximately 95% put-strike target.",
    "CC105": (
        "Premium income using the thesis's approximately 105% call-strike target, with "
        "upside limited above the call strike on the covered portion."
    ),
    "COLLAR95_105": (
        "Combines the downside put with an upside call, using the thesis's approximately "
        "95%/105% strike targets."
    ),
    "PP90": "Downside protection using the thesis's approximately 90% put-strike target.",
    "CC110": (
        "Premium income using the thesis's approximately 110% call-strike target, with "
        "upside limited above the call strike on the covered portion."
    ),
    "COLLAR90_110": (
        "Combines the downside put with an upside call, using the thesis's approximately "
        "90%/110% strike targets."
    ),
}


def historical_strategy_explanation(strategy: str) -> Optional[str]:
    return HISTORICAL_STRATEGY_EXPLANATIONS.get(strategy)


HISTORICAL_METRIC_EXPLANATIONS: Dict[str, str] = {
    "Max Monthly Drawdown": "Largest historical peak-to-trough decline in the portfolio wealth path.",
    "Downside Deviation (ann.)": "Measures harmful downside variability rather than all price movement.",
    "Sortino Ratio": (
        "Return relative to downside risk; higher values indicate more return per unit "
        "of downside risk."
    ),
    NET_PREMIUM_COST_LABEL: "Cumulative option premium cost or credit over the backtest.",
    UPSIDE_SHORTFALL_LABEL: (
        "How much return was forgone during months when the unhedged benchmark rose "
        "(cumulative, not averaged or annualized)."
    ),
}
