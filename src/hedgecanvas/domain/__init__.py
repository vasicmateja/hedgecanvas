"""HedgeCanvas domain layer: exchange-agnostic hedge position modelling.

This package contains the only substantive Phase 1 implementation. It has
no knowledge of any exchange, broker, or live market data source.
"""

from hedgecanvas.domain.analysis import (
    BreakevenResult,
    MaxLossResult,
    MaxProfitResult,
    StrategyAnalysis,
    analyze,
    breakeven,
    max_loss,
    max_profit,
    protection_floor_scope,
    upside_cap_scope,
)
from hedgecanvas.domain.enums import BoundaryScope, CoverageState, Strategy
from hedgecanvas.domain.payoff import Segment, breakpoints, pnl, segments
from hedgecanvas.domain.position import HedgePosition

__all__ = [
    "Strategy",
    "CoverageState",
    "BoundaryScope",
    "HedgePosition",
    "pnl",
    "Segment",
    "segments",
    "breakpoints",
    "MaxProfitResult",
    "MaxLossResult",
    "BreakevenResult",
    "StrategyAnalysis",
    "max_profit",
    "max_loss",
    "breakeven",
    "protection_floor_scope",
    "upside_cap_scope",
    "analyze",
]
