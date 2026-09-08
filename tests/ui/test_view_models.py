"""Tests for metric-card presentation transforms over Phase 1 domain results."""

from decimal import Decimal

from hedgecanvas.domain import (
    BoundaryScope,
    CoverageState,
    HedgePosition,
    Strategy,
    analyze,
)
from hedgecanvas.ui.view_models import (
    format_breakeven,
    format_coverage_state,
    format_max_loss,
    format_max_profit,
    format_net_option_cost,
    format_protection_floor,
    format_upside_cap,
    is_max_profit_negative,
)


def test_unlimited_max_profit_presentation() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    result = analyze(pos)
    assert format_max_profit(result.max_profit) == "Unlimited"


def test_finite_max_profit_presentation() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    result = analyze(pos)
    assert format_max_profit(result.max_profit) == "$5,300.00"


def test_negative_max_profit_flagged() -> None:
    # A deep-ITM written call: even the best case is a net loss.
    pos = HedgePosition(Strategy.COVERED_CALL, S0="78374", Q="1", H="1", KC="71000", C="7210.43")
    result = analyze(pos)
    assert is_max_profit_negative(result.max_profit)


def test_positive_finite_max_profit_not_flagged() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    result = analyze(pos)
    assert not is_max_profit_negative(result.max_profit)


def test_unlimited_max_profit_not_flagged_negative() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    result = analyze(pos)
    assert not is_max_profit_negative(result.max_profit)


def test_max_loss_formatting() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="2", H="0")
    result = analyze(pos)
    assert format_max_loss(result.max_loss) == "$120,000.00"


def test_single_breakeven_presentation() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    result = analyze(pos)
    assert format_breakeven(result.breakeven) == "$60,000.00"


def test_multiple_breakeven_presentation() -> None:
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="100", Q="10", H="9", KP="95", P="20")
    result = analyze(pos)
    text = format_breakeven(result.breakeven)
    assert "$" in text
    assert text == "$118.00"


def test_no_breakeven_presentation() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="30000", Q="1", H="1", KP="29900", KC="30100", P="50", C="500"
    )
    result = analyze(pos)
    assert format_breakeven(result.breakeven) == "No breakeven"


def test_breakeven_interval_presentation() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="100", Q="1", H="1", KP="100", KC="100", P="0", C="0"
    )
    result = analyze(pos)
    text = format_breakeven(result.breakeven)
    assert "flat at zero" in text
    assert "$100.00" in text


def test_whole_portfolio_floor_presentation() -> None:
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q="1", H="1", KP="55000", P="500")
    result = analyze(pos)
    text = format_protection_floor(pos, result.protection_floor_scope)
    assert text == "Whole-portfolio protection strike: $55,000.00"


def test_hedged_portion_floor_presentation() -> None:
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q="10", H="4", KP="55000", P="500")
    result = analyze(pos)
    text = format_protection_floor(pos, result.protection_floor_scope)
    assert text is not None
    assert "hedged portion only" in text
    assert "Whole-portfolio" not in text


def test_whole_portfolio_cap_presentation() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    result = analyze(pos)
    text = format_upside_cap(pos, result.upside_cap_scope)
    assert text == "Whole-portfolio upside cap: $65,000.00"


def test_hedged_portion_cap_presentation() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="10", H="4", KC="65000", C="300")
    result = analyze(pos)
    text = format_upside_cap(pos, result.upside_cap_scope)
    assert text is not None
    assert "hedged portion only" in text


def test_none_boundary_presentation() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    result = analyze(pos)
    assert format_protection_floor(pos, result.protection_floor_scope) is None
    assert format_upside_cap(pos, result.upside_cap_scope) is None


def test_net_debit_presentation() -> None:
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q="1", H="1", KP="55000", P="500")
    assert format_net_option_cost(pos) == "Cost: $500.00"


def test_net_credit_presentation() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    assert format_net_option_cost(pos) == "Credit: $300.00"


def test_zero_option_cost_presentation() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    assert format_net_option_cost(pos) == "N/A"

    pos_zero_premium = HedgePosition(
        Strategy.COLLAR, S0="60000", Q="1", H="1", KP="55000", KC="65000", P="0", C="0"
    )
    assert format_net_option_cost(pos_zero_premium) == "Zero (no net premium)"


def test_full_coverage_display() -> None:
    assert format_coverage_state(CoverageState.FULL) == "Full"


def test_partial_coverage_display() -> None:
    assert format_coverage_state(CoverageState.PARTIAL) == "Partial"


def test_zero_coverage_display() -> None:
    assert format_coverage_state(CoverageState.NONE) == "Zero"


def test_partial_covered_call_never_shows_whole_portfolio_cap() -> None:
    # Regression: a partial overlay's cap must never be worded as
    # whole-portfolio, since the residual quantity remains uncapped.
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="10", H="4", KC="65000", C="300")
    result = analyze(pos)
    assert result.upside_cap_scope is BoundaryScope.HEDGED_PORTION
    text = format_upside_cap(pos, result.upside_cap_scope)
    assert text is not None
    assert "Whole-portfolio" not in text
