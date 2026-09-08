"""Presentation transforms over Phase 1 domain results.

Every function here formats an already-computed Phase 1 result
(``MaxProfitResult``, ``MaxLossResult``, ``BreakevenResult``,
``BoundaryScope``, ``CoverageState``, ``HedgePosition``) into display
strings. None of them compute payoff, coverage, or boundary-scope logic --
that stays exclusively in ``hedgecanvas.domain``.
"""

from __future__ import annotations

from typing import Optional

from hedgecanvas.domain import (
    BoundaryScope,
    BreakevenResult,
    CoverageState,
    HedgePosition,
    MaxLossResult,
    MaxProfitResult,
    Strategy,
)
from hedgecanvas.ui.formatting import format_quantity, format_usd

UNLIMITED_LABEL = "Unlimited"

COVERAGE_STATE_LABELS = {
    CoverageState.FULL: "Full",
    CoverageState.PARTIAL: "Partial",
    CoverageState.NONE: "Zero",
}


def format_max_profit(result: MaxProfitResult) -> str:
    if result.is_unlimited:
        return UNLIMITED_LABEL
    assert result.value is not None
    return format_usd(result.value)


def is_max_profit_negative(result: MaxProfitResult) -> bool:
    """True when Max Profit is finite and negative: even the best-case
    terminal price for this strategy at its selected strikes is a net
    loss. A presentation-only check over the existing Phase 1 result --
    computes nothing new.
    """
    return (not result.is_unlimited) and result.value is not None and result.value < 0


def max_profit_metric_label(result: MaxProfitResult) -> str:
    """The metric-card label to pair with ``format_max_profit``.

    Unlimited or a genuine positive best case keeps the familiar "Max
    Profit" label. A finite, non-positive best case avoids implying a
    "profit" that isn't there: exactly zero is labeled "Maximum P&L",
    and a net loss even in the best case is labeled "Best-Case P&L".
    This changes only the label text -- the underlying Phase 1 value is
    never altered.
    """
    if result.is_unlimited:
        return "Max Profit"
    assert result.value is not None
    if result.value > 0:
        return "Max Profit"
    if result.value == 0:
        return "Maximum P&L"
    return "Best-Case P&L"


def format_max_loss(result: MaxLossResult) -> str:
    return format_usd(result.max_loss)


def format_breakeven(result: BreakevenResult) -> str:
    if result.degenerate_intervals:
        parts = []
        for lower, upper in result.degenerate_intervals:
            if upper is None:
                parts.append(f"{format_usd(lower)} and above (P&L flat at zero)")
            else:
                parts.append(f"{format_usd(lower)} – {format_usd(upper)} (P&L flat at zero)")
        return "; ".join(parts)
    if not result.points:
        return "No breakeven"
    return ", ".join(format_usd(p) for p in sorted(result.points))


def format_net_option_cost(position: HedgePosition) -> str:
    if position.strategy is Strategy.UNHEDGED:
        return "N/A"
    net = position.net_option_cost
    if net > 0:
        return f"Cost: {format_usd(net)}"
    if net < 0:
        return f"Credit: {format_usd(-net)}"
    return "Zero (no net premium)"


def format_protection_floor(position: HedgePosition, scope: BoundaryScope) -> Optional[str]:
    if scope is BoundaryScope.NONE or position.KP is None:
        return None
    strike = format_usd(position.KP)
    if scope is BoundaryScope.WHOLE_PORTFOLIO:
        return f"Whole-portfolio protection strike: {strike}"
    residual = format_quantity(position.unhedged_residual_quantity)
    return (
        f"Put protection applies to the hedged portion only: {strike} strike "
        f"(residual {residual} unprotected)"
    )


def format_upside_cap(position: HedgePosition, scope: BoundaryScope) -> Optional[str]:
    if scope is BoundaryScope.NONE or position.KC is None:
        return None
    strike = format_usd(position.KC)
    if scope is BoundaryScope.WHOLE_PORTFOLIO:
        return f"Whole-portfolio upside cap: {strike}"
    residual = format_quantity(position.unhedged_residual_quantity)
    return (
        f"Upside cap applies to the hedged portion only: {strike} strike "
        f"(residual {residual} uncapped)"
    )


def format_coverage_state(state: CoverageState) -> str:
    return COVERAGE_STATE_LABELS[state]
