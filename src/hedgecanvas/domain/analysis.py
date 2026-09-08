"""Max Profit / Max Loss / breakeven / boundary-scope analysis.

All results are derived from the general piecewise-linear payoff geometry
(see :mod:`hedgecanvas.domain.payoff`) rather than from strategy-specific
textbook formulas inserted blindly. Because every supported strategy keeps
H <= Q (never a naked short position), each segment's slope is >= 0 in
practice, but the algorithms below do not assume this — they work from the
segment geometry directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple

from hedgecanvas.domain.enums import BoundaryScope, CoverageState
from hedgecanvas.domain.payoff import Segment, breakpoints, segments
from hedgecanvas.domain.position import HedgePosition

ZERO = Decimal(0)


@dataclass(frozen=True)
class MaxProfitResult:
    is_unlimited: bool
    value: Optional[Decimal]  # None when is_unlimited is True

    @property
    def is_finite(self) -> bool:
        return not self.is_unlimited


@dataclass(frozen=True)
class MaxLossResult:
    minimum_pnl: Decimal  # signed minimum PnL over ST >= 0
    max_loss: Decimal  # non-negative loss magnitude


@dataclass(frozen=True)
class BreakevenResult:
    points: Tuple[Decimal, ...]
    degenerate_intervals: Tuple[Tuple[Decimal, Optional[Decimal]], ...]

    @property
    def has_breakeven(self) -> bool:
        return bool(self.points) or bool(self.degenerate_intervals)

    @property
    def is_degenerate(self) -> bool:
        return bool(self.degenerate_intervals)


@dataclass(frozen=True)
class StrategyAnalysis:
    max_profit: MaxProfitResult
    max_loss: MaxLossResult
    breakeven: BreakevenResult
    protection_floor_scope: BoundaryScope
    upside_cap_scope: BoundaryScope
    coverage_state: CoverageState


def _vertex_values(segs: List[Segment]) -> List[Decimal]:
    return [s.value_at_lower for s in segs]


def max_profit(position: HedgePosition) -> MaxProfitResult:
    """Max profit is the supremum of PnL(ST) over ST >= 0.

    Piecewise-linear extrema occur only at vertices (breakpoints) or, for
    the final unbounded segment, at +infinity if that segment's slope > 0.
    """
    segs = segments(position)
    last = segs[-1]
    if last.slope > 0:
        return MaxProfitResult(is_unlimited=True, value=None)
    return MaxProfitResult(is_unlimited=False, value=max(_vertex_values(segs)))


def max_loss(position: HedgePosition) -> MaxLossResult:
    """Global minimum PnL over ST >= 0, derived from vertex values.

    Every supported strategy satisfies H <= Q, so the final segment's slope
    is always >= 0 and the minimum is never at +infinity; it is attained at
    a finite vertex (possibly ST = 0).
    """
    segs = segments(position)
    minimum_pnl = min(_vertex_values(segs))
    loss = -minimum_pnl if minimum_pnl < 0 else ZERO
    return MaxLossResult(minimum_pnl=minimum_pnl, max_loss=loss)


def breakeven(position: HedgePosition) -> BreakevenResult:
    """Solve PnL(ST) = 0 for ST >= 0 using the piecewise-linear segments.

    Each segment is affine: value(x) = value_at_lower + slope * (x - lower).
    A root within a segment is found analytically (no numerical grid scan).
    A segment with zero slope and zero value_at_lower is a degenerate
    interval over which PnL is identically zero.
    """
    points: List[Decimal] = []
    degenerate: List[Tuple[Decimal, Optional[Decimal]]] = []

    for seg in segments(position):
        if seg.slope == 0:
            if seg.value_at_lower == 0:
                degenerate.append((seg.lower, seg.upper))
            continue

        root = seg.lower - seg.value_at_lower / seg.slope
        if root < seg.lower:
            continue
        if seg.upper is not None and root >= seg.upper:
            continue
        points.append(root)

    # A segment boundary can itself be an exact root; the half-open [lower,
    # upper) convention across segments already prevents double-counting.
    return BreakevenResult(points=tuple(points), degenerate_intervals=tuple(degenerate))


def protection_floor_scope(position: HedgePosition) -> BoundaryScope:
    """Scope of the put protection floor (KP), if any."""
    if not position.has_put:
        return BoundaryScope.NONE
    if position.coverage_state is CoverageState.NONE:
        return BoundaryScope.NONE
    if position.coverage_state is CoverageState.FULL:
        return BoundaryScope.WHOLE_PORTFOLIO
    return BoundaryScope.HEDGED_PORTION


def upside_cap_scope(position: HedgePosition) -> BoundaryScope:
    """Scope of the written-call upside cap (KC), if any."""
    if not position.has_call:
        return BoundaryScope.NONE
    if position.coverage_state is CoverageState.NONE:
        return BoundaryScope.NONE
    if position.coverage_state is CoverageState.FULL:
        return BoundaryScope.WHOLE_PORTFOLIO
    return BoundaryScope.HEDGED_PORTION


def analyze(position: HedgePosition) -> StrategyAnalysis:
    """Run the full Phase 1 analysis for a hedge position."""
    return StrategyAnalysis(
        max_profit=max_profit(position),
        max_loss=max_loss(position),
        breakeven=breakeven(position),
        protection_floor_scope=protection_floor_scope(position),
        upside_cap_scope=upside_cap_scope(position),
        coverage_state=position.coverage_state,
    )


__all__ = [
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
    "breakpoints",
]
