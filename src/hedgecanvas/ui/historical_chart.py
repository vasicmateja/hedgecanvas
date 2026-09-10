"""Historical wealth-path chart: stored wealth_end only, in decision_month order.

No reconstruction happens here or in the data it consumes
(``hedgecanvas.historical.filtering.wealth_end_series``): this module only
plots the frozen stored values.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from hedgecanvas.historical.filtering import wealth_end_series
from hedgecanvas.historical.keys import HistoricalView, strategies_for_view, strategy_display_label

WEALTH_LINE_COLORS = ("#8a94a6", "#00c896", "#5b8def", "#e2b93b")


def build_wealth_path_figure(
    wealth_df: pd.DataFrame, asset: str, view: HistoricalView
) -> go.Figure:
    fig = go.Figure()
    strategies = strategies_for_view(view)
    for index, strategy in enumerate(strategies):
        series = wealth_end_series(wealth_df, asset, strategy)
        color = WEALTH_LINE_COLORS[index % len(WEALTH_LINE_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=series["decision_month"],
                y=series["wealth_end"],
                mode="lines",
                name=strategy_display_label(strategy),
                line=dict(color=color, width=2.5 if strategy == "BENCHMARK" else 2),
            )
        )

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Portfolio Wealth Index (Start = 100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_dark",
        height=440,
    )
    return fig
