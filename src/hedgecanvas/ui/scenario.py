"""Deterministic hypothetical terminal-price (ST) scenario grid for the payoff chart.

This is scenario analysis, not a forecast and not a probability model: no
distributions, no Monte Carlo. The grid is a fixed, deterministic set of
Decimal ST values centered on S0 and the strategy's strikes, always >= 0.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Sequence

DEFAULT_GRID_POINTS = 201
DEFAULT_MARGIN_FRACTION = Decimal("0.15")


def build_scenario_grid(
    S0: Decimal,
    strikes: Sequence[Optional[Decimal]] = (),
    *,
    num_points: int = DEFAULT_GRID_POINTS,
    margin_fraction: Decimal = DEFAULT_MARGIN_FRACTION,
) -> List[Decimal]:
    """Build a deterministic, evenly spaced ST grid.

    The range spans from the lowest reference point (S0 and any given
    strikes) minus a margin, to the highest reference point plus a margin.
    The margin is the larger of the strike span itself and
    ``margin_fraction`` of S0, so the grid always extends meaningfully
    beyond the relevant strikes (or around S0 alone, for Unhedged). The
    lower bound is clamped at 0 -- ST is never negative.
    """
    if S0 <= 0:
        raise ValueError("S0 must be > 0")
    if num_points < 2:
        raise ValueError("num_points must be >= 2")

    reference_points = [S0] + [k for k in strikes if k is not None and k > 0]
    lo_anchor = min(reference_points)
    hi_anchor = max(reference_points)
    span = hi_anchor - lo_anchor
    margin = max(span, S0 * margin_fraction)

    lower = lo_anchor - margin
    if lower < 0:
        lower = Decimal(0)
    upper = hi_anchor + margin

    if upper <= lower:
        return [lower]

    step = (upper - lower) / Decimal(num_points - 1)
    return [lower + step * i for i in range(num_points)]
