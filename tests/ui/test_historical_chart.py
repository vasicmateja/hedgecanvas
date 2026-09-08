"""Tests that the historical wealth chart plots stored wealth_end only."""

import pandas as pd

from hedgecanvas.historical.keys import HistoricalView
from hedgecanvas.ui.historical_chart import build_wealth_path_figure
from tests.historical.helpers import default_monthly_rows


def test_wealth_chart_traces_use_stored_wealth_end_values() -> None:
    df = pd.DataFrame(default_monthly_rows())
    fig = build_wealth_path_figure(df, "BTC", HistoricalView.PRIMARY)
    benchmark_trace = next(t for t in fig.data if t.name == "Unhedged Benchmark")
    assert list(benchmark_trace.y) == [105.0, 110.0]
    assert list(benchmark_trace.x) == ["2020-01", "2020-02"]


def test_wealth_chart_only_includes_view_strategies() -> None:
    df = pd.DataFrame(default_monthly_rows())
    fig = build_wealth_path_figure(df, "BTC", HistoricalView.ROBUSTNESS)
    trace_names = {t.name for t in fig.data}
    assert trace_names <= {"Unhedged Benchmark", "Protective Put 90", "Covered Call 110", "Collar 90/110"}
    assert "Protective Put 95" not in trace_names


def test_wealth_chart_axis_titles() -> None:
    df = pd.DataFrame(default_monthly_rows())
    fig = build_wealth_path_figure(df, "BTC", HistoricalView.PRIMARY)
    assert fig.layout.xaxis.title.text == "decision_month"
    assert fig.layout.yaxis.title.text == "Stored Normalized Wealth Index"
