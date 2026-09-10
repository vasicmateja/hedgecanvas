"""Payoff chart: Selected Strategy vs Unhedged Portfolio, built with Plotly.

Both curves are evaluated exclusively through ``hedgecanvas.domain.pnl`` --
this module contains no payoff mathematics of its own. Scenario ST values
stay as ``Decimal`` through domain evaluation and are only converted to
``float`` afterwards, for plotting.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Sequence

import plotly.graph_objects as go

from hedgecanvas.domain import HedgePosition, Strategy, pnl

UNHEDGED_LINE_COLOR = "#8a94a6"
STRATEGY_LINE_COLOR = "#00c896"
ZERO_LINE_COLOR = "#4a5568"
STRIKE_LINE_COLOR = "#e2b93b"
S0_LINE_COLOR = "#5b8def"


def _unhedged_reference(position: HedgePosition) -> HedgePosition:
    """The same portfolio (S0, Q) with no option overlay, for comparison."""
    return HedgePosition(
        strategy=Strategy.UNHEDGED,
        S0=position.S0,
        Q=position.Q,
        H=Decimal(0),
    )


def build_payoff_figure(
    position: HedgePosition, grid: Sequence[Decimal], asset: Optional[str] = None
) -> go.Figure:
    st_values: List[float] = [float(value) for value in grid]
    strategy_pnl: List[float] = [float(pnl(position, value)) for value in grid]

    fig = go.Figure()

    if position.strategy is not Strategy.UNHEDGED:
        unhedged_position = _unhedged_reference(position)
        unhedged_pnl = [float(pnl(unhedged_position, value)) for value in grid]
        fig.add_trace(
            go.Scatter(
                x=st_values,
                y=unhedged_pnl,
                name="Unhedged Portfolio",
                mode="lines",
                line=dict(color=UNHEDGED_LINE_COLOR, width=2, dash="dot"),
            )
        )
        strategy_name = "Selected Strategy"
    else:
        strategy_name = "Unhedged Portfolio"

    fig.add_trace(
        go.Scatter(
            x=st_values,
            y=strategy_pnl,
            name=strategy_name,
            mode="lines",
            line=dict(color=STRATEGY_LINE_COLOR, width=3),
        )
    )

    fig.add_hline(y=0, line=dict(color=ZERO_LINE_COLOR, width=1, dash="dot"))
    fig.add_vline(
        x=float(position.S0),
        line=dict(color=S0_LINE_COLOR, width=1, dash="dash"),
        annotation_text="S0",
        annotation_position="top",
    )
    if position.KP is not None:
        fig.add_vline(
            x=float(position.KP),
            line=dict(color=STRIKE_LINE_COLOR, width=1, dash="dot"),
            annotation_text="KP",
            annotation_position="bottom",
        )
    if position.KC is not None:
        fig.add_vline(
            x=float(position.KC),
            line=dict(color=STRIKE_LINE_COLOR, width=1, dash="dot"),
            annotation_text="KC",
            annotation_position="bottom",
        )

    price_label = f"{asset} Price at Expiry (USD)" if asset else "Underlying Price at Expiry (USD)"
    fig.update_layout(
        xaxis_title=price_label,
        yaxis_title="Portfolio Profit / Loss at Expiry (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_dark",
        height=440,
    )
    return fig
