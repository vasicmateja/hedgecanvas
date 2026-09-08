"""Tests for underlying-quantity normalization into a tradable option amount H."""

from decimal import Decimal

from hedgecanvas.domain import CoverageState, HedgePosition, Strategy
from hedgecanvas.live.sizing import normalize_amount
from hedgecanvas.live.states import MarketState


def test_btc_quantity_normalization_floors_to_min_trade_amount_multiple() -> None:
    result = normalize_amount(Decimal("0.37"), Decimal("0.1"))
    assert result.ok
    assert result.value is not None
    assert result.value.H == Decimal("0.3")
    assert result.value.steps == 3


def test_eth_quantity_normalization_floors_to_min_trade_amount_multiple() -> None:
    result = normalize_amount(Decimal("7.9"), Decimal("1"))
    assert result.ok
    assert result.value is not None
    assert result.value.H == Decimal("7")
    assert result.value.steps == 7


def test_quantity_never_rounds_above_q() -> None:
    result = normalize_amount(Decimal("0.29999"), Decimal("0.1"))
    assert result.value is not None
    assert result.value.H <= Decimal("0.29999")
    assert result.value.H == Decimal("0.2")


def test_below_minimum_btc_position() -> None:
    result = normalize_amount(Decimal("0.05"), Decimal("0.1"))
    assert result.state is MarketState.BELOW_MINIMUM_SIZE
    assert result.value is not None
    assert result.value.H == Decimal("0")


def test_below_minimum_eth_position() -> None:
    result = normalize_amount(Decimal("0.5"), Decimal("1"))
    assert result.state is MarketState.BELOW_MINIMUM_SIZE
    assert result.value is not None
    assert result.value.H == Decimal("0")


def test_exact_full_coverage_after_normalization() -> None:
    Q = Decimal("0.5")
    result = normalize_amount(Q, Decimal("0.1"))
    assert result.value is not None
    H = result.value.H
    assert H == Q
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q=Q, H=H, KP="55000", P="500")
    assert pos.coverage_state is CoverageState.FULL


def test_partial_coverage_after_normalization() -> None:
    Q = Decimal("0.55")
    result = normalize_amount(Q, Decimal("0.1"))
    assert result.value is not None
    H = result.value.H
    assert H == Decimal("0.5")
    assert H != Q
    pos = HedgePosition(Strategy.PROTECTIVE_PUT, S0="60000", Q=Q, H=H, KP="55000", P="500")
    assert pos.coverage_state is CoverageState.PARTIAL


def test_h_never_exceeds_q_across_many_values() -> None:
    for q_raw, step_raw in [
        ("0.1", "0.1"),
        ("0.19999", "0.1"),
        ("1.03", "0.1"),
        ("2.999999999", "1"),
        ("100", "1"),
    ]:
        Q = Decimal(q_raw)
        min_trade_amount = Decimal(step_raw)
        result = normalize_amount(Q, min_trade_amount)
        assert result.value is not None
        assert result.value.H <= Q


def test_full_partial_semantics_agree_with_phase1_domain() -> None:
    # A value strictly below Q by normalization granularity must classify
    # as PARTIAL, not FULL, in the shared Phase 1 domain model -- no
    # separate/duplicated coverage logic lives in the live adapter.
    Q = Decimal("1.0")
    result = normalize_amount(Q, Decimal("0.1"))
    assert result.value is not None
    assert result.value.H == Q  # exact multiple: full coverage
    pos_full = HedgePosition(Strategy.COVERED_CALL, S0="60000", Q=Q, H=result.value.H, KC="65000")
    assert pos_full.is_full_coverage

    Q2 = Decimal("1.05")
    result2 = normalize_amount(Q2, Decimal("0.1"))
    assert result2.value is not None
    assert result2.value.H == Decimal("1.0")
    pos_partial = HedgePosition(
        Strategy.COVERED_CALL, S0="60000", Q=Q2, H=result2.value.H, KC="65000"
    )
    assert pos_partial.is_partial_coverage
