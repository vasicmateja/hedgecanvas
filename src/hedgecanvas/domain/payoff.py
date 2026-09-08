"""Deterministic expiry payoff / P&L engine.

Implements the closed-form payoff equations for each supported strategy and
a generic piecewise-linear segment representation used by the analysis
module (max profit, max loss, breakeven) to avoid hand-inserting
strategy-specific textbook shortcuts where possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from hedgecanvas.domain.enums import Strategy
from hedgecanvas.domain.position import HedgePosition, Numeric, to_decimal

ZERO = Decimal(0)


def _max0(value: Decimal) -> Decimal:
    return value if value > ZERO else ZERO


def pnl(position: HedgePosition, ST: Numeric) -> Decimal:
    """Compute expiry P&L for a given terminal underlying price ST.

    Valid for any ST >= 0. Negative ST is rejected.
    """
    st = to_decimal(ST)
    if st < 0:
        raise ValueError("ST must be >= 0")

    Q, H, S0 = position.Q, position.H, position.S0
    base = Q * (st - S0)

    if position.strategy is Strategy.UNHEDGED:
        return base

    if position.strategy is Strategy.PROTECTIVE_PUT:
        assert position.KP is not None
        return base + H * _max0(position.KP - st) - H * position.P

    if position.strategy is Strategy.COVERED_CALL:
        assert position.KC is not None
        return base - H * _max0(st - position.KC) + H * position.C

    if position.strategy is Strategy.COLLAR:
        assert position.KP is not None and position.KC is not None
        return (
            base
            + H * _max0(position.KP - st)
            - H * _max0(st - position.KC)
            - H * position.P
            + H * position.C
        )

    raise ValueError(f"Unsupported strategy: {position.strategy}")  # pragma: no cover


@dataclass(frozen=True)
class Segment:
    """A closed-open interval [lower, upper) of the piecewise-linear PnL(ST).

    ``upper is None`` denotes the final, unbounded-above segment.
    ``value_at_lower`` is PnL evaluated at ``lower`` (continuous with the
    previous segment). ``slope`` is d(PnL)/d(ST) throughout the interval.
    """

    lower: Decimal
    upper: Optional[Decimal]
    slope: Decimal
    value_at_lower: Decimal

    def value_at(self, st: Decimal) -> Decimal:
        return self.value_at_lower + self.slope * (st - self.lower)

    def contains(self, st: Decimal) -> bool:
        if st < self.lower:
            return False
        if self.upper is None:
            return True
        return st < self.upper


def breakpoints(position: HedgePosition) -> List[Decimal]:
    """Sorted, deduplicated critical ST values where the payoff slope can change.

    ST = 0 is always included since the valid terminal domain is ST >= 0.
    """
    points = {ZERO}
    if position.has_put:
        assert position.KP is not None
        points.add(position.KP)
    if position.has_call:
        assert position.KC is not None
        points.add(position.KC)
    return sorted(points)


def segments(position: HedgePosition) -> List[Segment]:
    """Build the piecewise-linear representation of PnL(ST) over ST >= 0.

    The slope of each interval is derived directly from which option legs
    are active there (put active below KP, call active above KC), rather
    than from strategy-specific closed-form shortcuts.
    """
    points = breakpoints(position)
    result: List[Segment] = []

    for i, lower in enumerate(points):
        upper = points[i + 1] if i + 1 < len(points) else None
        probe = (lower + upper) / 2 if upper is not None else lower + Decimal(1)

        slope = position.Q
        if position.has_put:
            assert position.KP is not None
            if probe < position.KP:
                slope -= position.H
        if position.has_call:
            assert position.KC is not None
            if probe > position.KC:
                slope -= position.H

        result.append(
            Segment(
                lower=lower,
                upper=upper,
                slope=slope,
                value_at_lower=pnl(position, lower),
            )
        )

    return result
