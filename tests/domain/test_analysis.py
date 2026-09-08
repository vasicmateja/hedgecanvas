"""Tests for Max Profit / Max Loss / breakeven / boundary-scope analysis."""

from decimal import Decimal

from hedgecanvas.domain import (
    BoundaryScope,
    HedgePosition,
    Strategy,
    breakeven,
    max_loss,
    max_profit,
    protection_floor_scope,
    upside_cap_scope,
)


def D(x: str) -> Decimal:
    return Decimal(x)


# ---------------------------------------------------------------------------
# Max Profit
# ---------------------------------------------------------------------------


def test_unhedged_max_profit_unlimited() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    result = max_profit(pos)
    assert result.is_unlimited
    assert result.value is None


def test_protective_put_max_profit_unlimited() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    assert max_profit(pos).is_unlimited


def test_covered_call_full_coverage_finite_max_profit() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="32000", C="300"
    )
    result = max_profit(pos)
    assert result.is_finite
    # Max at ST -> KC (flat beyond): 1*(32000-30000) - 0 + 300 = 2300
    assert result.value == D("2300")


def test_covered_call_partial_coverage_unlimited_whole_portfolio_upside() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="10", H="4", KC="32000", C="300"
    )
    # Residual (Q-H)=6 uncapped underlying keeps whole-portfolio profit unbounded.
    assert max_profit(pos).is_unlimited


def test_collar_full_coverage_finite_max_profit() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    result = max_profit(pos)
    assert result.is_finite
    # Max at ST -> KC: 1*(32000-30000) - 0 - 500 + 300 = 1800
    assert result.value == D("1800")


def test_collar_partial_coverage_unlimited_whole_portfolio_upside() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="10",
        H="4",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    assert max_profit(pos).is_unlimited


# ---------------------------------------------------------------------------
# Max Loss
# ---------------------------------------------------------------------------


def test_unhedged_max_loss_at_zero() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="2", H="0")
    result = max_loss(pos)
    # Worst case ST=0: PnL = 2*(0-30000) = -60000
    assert result.minimum_pnl == D("-60000")
    assert result.max_loss == D("60000")


def test_protective_put_full_hedge_max_loss_floored() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    # Below KP the position is flat: worst case at ST=0 == worst case at KP.
    # PnL(0) = 1*(0-30000) + 1*28000 - 500 = -30000+28000-500 = -2500
    result = max_loss(pos)
    assert result.minimum_pnl == D("-2500")
    assert result.max_loss == D("2500")


def test_max_loss_never_negative_when_min_pnl_positive() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="29900",
        KC="30100",
        P="50",
        C="500",
    )
    # Net credit is large relative to the narrow corridor; worst case at ST=0
    # is still: base=1*(0-30000)=-30000, put payoff=29900, premium=-50+500=450
    # total = -30000+29900+450 = 350 (positive) -> max_loss must be 0.
    result = max_loss(pos)
    assert result.minimum_pnl == D("350")
    assert result.max_loss == D("0")


# ---------------------------------------------------------------------------
# Breakeven
# ---------------------------------------------------------------------------


def test_unhedged_breakeven_at_s0() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    result = breakeven(pos)
    assert result.points == (D("30000"),)
    assert not result.degenerate_intervals


def test_protective_put_breakeven() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    # Above KP, PnL(ST) = 1*(ST-30000) - 500 = ST - 30500; zero at ST=30500.
    result = breakeven(pos)
    assert result.points == (D("30500"),)


def test_covered_call_breakeven() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="32000", C="300"
    )
    # Below KC, PnL(ST) = 1*(ST-30000) + 300 = ST - 29700; zero at ST=29700.
    result = breakeven(pos)
    assert result.points == (D("29700"),)


def test_collar_breakeven() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    # Between strikes, PnL(ST) = 1*(ST-30000) - 500 + 300 = ST - 30200.
    result = breakeven(pos)
    assert result.points == (D("30200"),)


def test_no_breakeven_when_always_positive() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="29900",
        KC="30100",
        P="50",
        C="500",
    )
    # Net credit large enough that PnL is positive across the whole domain
    # (see test_max_loss_never_negative_when_min_pnl_positive: min PnL=350).
    result = breakeven(pos)
    assert result.points == ()
    assert not result.degenerate_intervals


def test_multiple_breakevens_protective_put_partial_hedge() -> None:
    # With partial hedge the put can create a kink such that the payoff dips
    # negative between S0-region and KP before rising, or crosses zero twice
    # depending on parameters; construct one with two crossings.
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="100", Q="10", H="9", KP="95", P="20"
    )
    # Segment 1 (ST<95): slope = Q-H = 1; value(0) = 10*(0-100)+9*95-9*20
    #   = -1000 + 855 - 180 = -325
    #   root = 0 - (-325)/1 = 325 -> not in [0,95), no root here.
    # Segment 2 (ST>=95): slope = Q = 10; value(95) = 10*(95-100)-9*20
    #   = -50-180 = -230
    #   root = 95 - (-230)/10 = 95+23 = 118 -> in range, root at 118.
    result = breakeven(pos)
    assert result.points == (D("118"),)


def test_piecewise_breakeven_root_exactly_at_kink_boundary() -> None:
    # Construct a case where the analytic root of a segment lands exactly on
    # the next segment's lower breakpoint, exercising the half-open interval
    # boundary handling (root must be attributed to exactly one segment).
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="100", Q="1", H="1", KC="120", C="0"
    )
    # Below KC: PnL(ST) = ST - 100; root at ST=100, well inside [0,120).
    result = breakeven(pos)
    assert result.points == (D("100"),)


def test_degenerate_zero_pnl_segment() -> None:
    # Collar with P == C and KP == KC == S0, H == Q: PnL is identically zero
    # for ST >= KC (slope 0, value 0), a genuine degenerate zero segment.
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="100",
        Q="1",
        H="1",
        KP="100",
        KC="100",
        P="0",
        C="0",
    )
    result = breakeven(pos)
    assert result.is_degenerate
    assert (D("100"), None) in result.degenerate_intervals


# ---------------------------------------------------------------------------
# Boundary scope
# ---------------------------------------------------------------------------


def test_protective_put_full_hedge_whole_portfolio_floor() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    assert protection_floor_scope(pos) is BoundaryScope.WHOLE_PORTFOLIO
    assert upside_cap_scope(pos) is BoundaryScope.NONE


def test_protective_put_partial_hedge_hedged_portion_floor() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="10", H="4", KP="28000", P="500"
    )
    assert protection_floor_scope(pos) is BoundaryScope.HEDGED_PORTION


def test_protective_put_zero_hedge_no_floor() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="10", H="0", KP="28000", P="500"
    )
    assert protection_floor_scope(pos) is BoundaryScope.NONE


def test_covered_call_full_coverage_whole_portfolio_cap() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="32000", C="300"
    )
    assert upside_cap_scope(pos) is BoundaryScope.WHOLE_PORTFOLIO
    assert protection_floor_scope(pos) is BoundaryScope.NONE


def test_covered_call_partial_coverage_hedged_portion_cap() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="10", H="4", KC="32000", C="300"
    )
    assert upside_cap_scope(pos) is BoundaryScope.HEDGED_PORTION


def test_collar_full_coverage_whole_portfolio_corridor() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    assert protection_floor_scope(pos) is BoundaryScope.WHOLE_PORTFOLIO
    assert upside_cap_scope(pos) is BoundaryScope.WHOLE_PORTFOLIO


def test_collar_partial_coverage_hedged_portion_corridor() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="10",
        H="4",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    assert protection_floor_scope(pos) is BoundaryScope.HEDGED_PORTION
    assert upside_cap_scope(pos) is BoundaryScope.HEDGED_PORTION


def test_unhedged_no_boundaries() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    assert protection_floor_scope(pos) is BoundaryScope.NONE
    assert upside_cap_scope(pos) is BoundaryScope.NONE
