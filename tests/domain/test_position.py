"""Tests for HedgePosition validation and coverage semantics."""

from decimal import Decimal

import pytest

from hedgecanvas.domain import CoverageState, HedgePosition, Strategy


def test_h_equals_q_is_full_coverage() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="1")
    assert pos.coverage_state is CoverageState.FULL
    assert pos.is_full_coverage
    assert not pos.is_partial_coverage


def test_h_zero_is_no_coverage() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    assert pos.coverage_state is CoverageState.NONE
    assert pos.unhedged_residual_quantity == Decimal("1")


def test_partial_coverage_fraction() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="10", H="4", KP="28000", P="500"
    )
    assert pos.coverage_state is CoverageState.PARTIAL
    assert pos.coverage_fraction == Decimal("0.4")
    assert pos.coverage_percentage == Decimal("40.0")
    assert pos.unhedged_residual_quantity == Decimal("6")


def test_value_strictly_below_q_is_not_full_coverage_via_tolerance() -> None:
    # H is one unit of last-decimal-place below Q; must NOT be classified as
    # FULL through any tolerance-based / approximate equality logic.
    pos = HedgePosition(
        Strategy.UNHEDGED, S0="30000", Q="1.0000000000", H="0.9999999999"
    )
    assert pos.coverage_state is not CoverageState.FULL
    assert pos.coverage_state is CoverageState.PARTIAL


def test_h_greater_than_q_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="2")


def test_h_negative_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="-1")


def test_q_zero_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.UNHEDGED, S0="30000", Q="0", H="0")


def test_q_negative_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.UNHEDGED, S0="30000", Q="-1", H="0")


def test_s0_zero_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.UNHEDGED, S0="0", Q="1", H="0")


def test_s0_negative_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.UNHEDGED, S0="-100", Q="1", H="0")


def test_negative_put_premium_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(
            Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="-1"
        )


def test_negative_call_premium_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(
            Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="32000", C="-1"
        )


def test_non_positive_put_strike_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="0", P="1")


def test_non_positive_call_strike_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(
            Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="-1000", C="1"
        )


def test_collar_kp_greater_than_kc_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(
            Strategy.COLLAR,
            S0="30000",
            Q="1",
            H="1",
            KP="32000",
            KC="28000",
            P="500",
            C="300",
        )


def test_collar_kp_equal_kc_allowed() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="30000", Q="1", H="1", KP="30000", KC="30000"
    )
    assert pos.KP == pos.KC


def test_h_zero_allowed_with_no_strike_requirement_violation() -> None:
    # H = 0 is allowed; strikes are still required by the strategy shape.
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="5", H="0", KP="28000", P="500"
    )
    assert pos.coverage_state is CoverageState.NONE
    assert pos.hedged_quantity == Decimal("0")


def test_protective_put_missing_strike_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1")


def test_covered_call_missing_strike_rejected() -> None:
    with pytest.raises(ValueError):
        HedgePosition(Strategy.COVERED_CALL, S0="30000", Q="1", H="1")
