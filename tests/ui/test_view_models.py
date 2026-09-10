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
    collar_equal_strikes_note,
    format_breakeven,
    format_coverage_state,
    format_max_loss,
    format_max_profit,
    format_net_option_cost,
    format_protection_floor,
    format_upside_cap,
    is_max_profit_negative,
    max_profit_metric_label,
    partial_coverage_note,
    strategy_description,
    unlimited_max_profit_note,
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


def test_max_profit_label_unlimited() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    result = analyze(pos)
    assert max_profit_metric_label(result.max_profit) == "Max Profit"


def test_max_profit_label_positive_finite() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    result = analyze(pos)
    assert max_profit_metric_label(result.max_profit) == "Max Profit"


def test_max_profit_label_negative_is_best_case_pnl() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="78374", Q="1", H="1", KC="71000", C="7210.43")
    result = analyze(pos)
    assert max_profit_metric_label(result.max_profit) == "Best-Case P&L"


def test_max_profit_label_exactly_zero_is_maximum_pnl() -> None:
    # KP == KC collar with a net premium that exactly offsets the flat
    # payoff at zero: max profit == 0 exactly.
    pos = HedgePosition(
        Strategy.COLLAR, S0="100", Q="1", H="1", KP="100", KC="100", P="0", C="0"
    )
    result = analyze(pos)
    assert result.max_profit.value == Decimal("0")
    assert max_profit_metric_label(result.max_profit) == "Maximum P&L"


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


# ---------------------------------------------------------------------------
# UX comprehension helpers (final polish pass)
# ---------------------------------------------------------------------------


def test_unlimited_note_for_partial_covered_call() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="10", H="4", KC="65000", C="300")
    result = analyze(pos)
    note = unlimited_max_profit_note(pos, result.max_profit, "BTC")
    assert note is not None
    assert "6 BTC" in note
    assert "uncapped" in note.lower()


def test_unlimited_note_for_partial_collar() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="60000", Q="10", H="4", KP="55000", KC="65000", P="500", C="300"
    )
    result = analyze(pos)
    note = unlimited_max_profit_note(pos, result.max_profit, "ETH")
    assert note is not None
    assert "6 ETH" in note


def test_unlimited_note_residual_matches_q_minus_h() -> None:
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="10", H="4", KC="65000", C="300")
    result = analyze(pos)
    note = unlimited_max_profit_note(pos, result.max_profit, "BTC")
    assert note is not None
    expected_residual = pos.Q - pos.H
    assert str(expected_residual) in note or "6 BTC" in note
    assert pos.unhedged_residual_quantity == expected_residual


def test_full_covered_call_gets_no_unlimited_note() -> None:
    # Full coverage: finite Max Profit, so the note must not appear.
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    result = analyze(pos)
    assert not result.max_profit.is_unlimited
    assert unlimited_max_profit_note(pos, result.max_profit, "BTC") is None


def test_protective_put_never_gets_unlimited_note() -> None:
    # Protective Put is always Unlimited but for a different reason (no
    # call at all) -- the residual-uncapped explanation doesn't apply.
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q="10", H="4", KP="55000", P="500")
    result = analyze(pos)
    assert result.max_profit.is_unlimited
    assert unlimited_max_profit_note(pos, result.max_profit, "BTC") is None


def test_unhedged_never_gets_unlimited_note() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    result = analyze(pos)
    assert unlimited_max_profit_note(pos, result.max_profit, "BTC") is None


def test_full_collar_kp_equals_kc_gets_whole_position_lock_note() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="60000", Q="1", H="1", KP="60000", KC="60000", P="100", C="100"
    )
    note = collar_equal_strikes_note(pos, "BTC")
    assert note is not None
    assert "fully covered" in note.lower()
    assert "locked" in note.lower()
    assert "hedged portion" not in note.lower()


def test_partial_collar_kp_equals_kc_gets_hedged_portion_note() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="60000", Q="10", H="4", KP="60000", KC="60000", P="100", C="100"
    )
    note = collar_equal_strikes_note(pos, "BTC")
    assert note is not None
    assert "hedged portion" in note.lower()
    assert "6 BTC" in note
    assert "fully covered" not in note.lower()


def test_collar_unequal_strikes_gets_no_note() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="60000", Q="1", H="1", KP="55000", KC="65000", P="500", C="300"
    )
    assert collar_equal_strikes_note(pos, "BTC") is None


def test_non_collar_strategy_gets_no_equal_strikes_note() -> None:
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q="1", H="1", KP="60000", P="500")
    assert collar_equal_strikes_note(pos, "BTC") is None


def test_partial_coverage_note_present_only_when_partial() -> None:
    partial = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="10", H="4", KC="65000", C="300")
    full = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300")
    zero = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    assert partial_coverage_note(partial) is not None
    assert partial_coverage_note(full) is None
    assert partial_coverage_note(zero) is None


def test_strategy_descriptions_present_for_all_four_strategies() -> None:
    for strategy in Strategy:
        text = strategy_description(strategy)
        assert isinstance(text, str)
        assert len(text) > 0


def test_explanatory_helpers_do_not_alter_underlying_values() -> None:
    # Presentation helpers must never mutate or misreport the Phase 1
    # numeric results they explain.
    pos = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q="10", H="4", KC="65000", C="300")
    result = analyze(pos)
    before_h, before_q = pos.H, pos.Q
    unlimited_max_profit_note(pos, result.max_profit, "BTC")
    partial_coverage_note(pos)
    assert pos.H == before_h
    assert pos.Q == before_q
    assert result.max_profit.is_unlimited  # unchanged domain result
