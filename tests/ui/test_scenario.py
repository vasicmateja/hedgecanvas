"""Tests for the deterministic ST scenario grid used by the payoff chart."""

from decimal import Decimal

from hedgecanvas.ui.scenario import build_scenario_grid


def test_grid_never_negative() -> None:
    grid = build_scenario_grid(Decimal("100"), [Decimal("10")])
    assert all(value >= 0 for value in grid)


def test_grid_covers_s0() -> None:
    S0 = Decimal("60000")
    grid = build_scenario_grid(S0, [])
    assert min(grid) <= S0 <= max(grid)


def test_grid_covers_strikes() -> None:
    S0 = Decimal("60000")
    KP = Decimal("55000")
    KC = Decimal("65000")
    grid = build_scenario_grid(S0, [KP, KC])
    assert min(grid) < KP
    assert max(grid) > KC


def test_grid_works_for_unhedged_with_no_strikes() -> None:
    grid = build_scenario_grid(Decimal("60000"), [])
    assert len(grid) > 1
    assert min(grid) >= 0
    assert max(grid) > Decimal("60000")


def test_grid_is_deterministic() -> None:
    grid1 = build_scenario_grid(Decimal("60000"), [Decimal("55000"), Decimal("65000")])
    grid2 = build_scenario_grid(Decimal("60000"), [Decimal("55000"), Decimal("65000")])
    assert grid1 == grid2


def test_grid_clamps_at_zero_for_low_s0_and_strikes() -> None:
    grid = build_scenario_grid(Decimal("5"), [Decimal("1")])
    assert min(grid) == Decimal("0")


def test_grid_point_count_matches_request() -> None:
    grid = build_scenario_grid(Decimal("60000"), [], num_points=101)
    assert len(grid) == 101


def test_grid_values_are_decimal() -> None:
    grid = build_scenario_grid(Decimal("60000"), [Decimal("55000")])
    assert all(isinstance(value, Decimal) for value in grid)
