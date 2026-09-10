"""Tests that the payoff chart uses the Phase 1 domain engine, not a copy of it."""

from decimal import Decimal

from hedgecanvas.domain import HedgePosition, Strategy, pnl
from hedgecanvas.ui.chart import build_payoff_figure
from hedgecanvas.ui.scenario import build_scenario_grid


def test_chart_strategy_curve_matches_domain_pnl() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="60000", Q="1", H="1", KP="55000", P="500"
    )
    grid = build_scenario_grid(pos.S0, [pos.KP], num_points=21)
    fig = build_payoff_figure(pos, grid)

    strategy_trace = next(t for t in fig.data if t.name == "Selected Strategy")
    for x, y in zip(strategy_trace.x, strategy_trace.y):
        expected = float(pnl(pos, Decimal(str(x))))
        assert abs(y - expected) < 1e-6


def test_chart_unhedged_comparison_matches_domain_pnl() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="60000", Q="1", H="1", KC="65000", C="300"
    )
    grid = build_scenario_grid(pos.S0, [pos.KC], num_points=21)
    fig = build_payoff_figure(pos, grid)

    unhedged_position = HedgePosition(Strategy.UNHEDGED, S0=pos.S0, Q=pos.Q, H=Decimal(0))
    unhedged_trace = next(t for t in fig.data if t.name == "Unhedged Portfolio")
    for x, y in zip(unhedged_trace.x, unhedged_trace.y):
        expected = float(pnl(unhedged_position, Decimal(str(x))))
        assert abs(y - expected) < 1e-6


def test_chart_unhedged_strategy_has_single_trace() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    grid = build_scenario_grid(pos.S0, [], num_points=11)
    fig = build_payoff_figure(pos, grid)
    assert len(fig.data) == 1
    assert fig.data[0].name == "Unhedged Portfolio"


def test_chart_hedged_strategy_has_two_traces() -> None:
    pos = HedgePosition(
        Strategy.COLLAR, S0="60000", Q="1", H="1", KP="55000", KC="65000", P="500", C="300"
    )
    grid = build_scenario_grid(pos.S0, [pos.KP, pos.KC], num_points=11)
    fig = build_payoff_figure(pos, grid)
    trace_names = {t.name for t in fig.data}
    assert trace_names == {"Selected Strategy", "Unhedged Portfolio"}


def test_chart_axis_titles_generic_without_asset() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    grid = build_scenario_grid(pos.S0, [], num_points=11)
    fig = build_payoff_figure(pos, grid)
    assert fig.layout.xaxis.title.text == "Underlying Price at Expiry (USD)"
    assert fig.layout.yaxis.title.text == "Portfolio Profit / Loss at Expiry (USD)"


def test_chart_axis_titles_use_plain_english_asset_name() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="60000", Q="1", H="0")
    grid = build_scenario_grid(pos.S0, [], num_points=11)
    fig = build_payoff_figure(pos, grid, asset="BTC")
    assert fig.layout.xaxis.title.text == "BTC Price at Expiry (USD)"
    assert fig.layout.yaxis.title.text == "Portfolio Profit / Loss at Expiry (USD)"
