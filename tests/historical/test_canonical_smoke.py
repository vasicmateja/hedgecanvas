"""Read-only smoke validation against the REAL canonical production artifacts.

Runs only if both canonical files are present in the resolved historical
directory (default ``data/historical/frozen/``, or
``HEDGECANVAS_HISTORICAL_DIR`` if set) -- never fabricated, never copied
here, never modified. Skipped (not failed) when the files are absent, so
the ordinary deterministic suite never depends on them.
"""

from __future__ import annotations

import hashlib

import pytest

from hedgecanvas.historical import config
from hedgecanvas.historical.filtering import filter_metrics, wealth_end_series
from hedgecanvas.historical.keys import HistoricalView
from hedgecanvas.historical.loader import load_monthly_results, load_strategy_metrics
from hedgecanvas.historical.states import HistoricalState

pytestmark = pytest.mark.canonical_artifacts

_RESOLVED_DIR = config.resolve_historical_dir()
_METRICS_PATH = _RESOLVED_DIR / config.STRATEGY_METRICS_FILENAME
_WEALTH_PATH = _RESOLVED_DIR / config.MONTHLY_RESULTS_FILENAME
_BOTH_PRESENT = _METRICS_PATH.is_file() and _WEALTH_PATH.is_file()

skip_reason = (
    f"Real canonical artifacts not found in {_RESOLVED_DIR} "
    f"(set {config.HISTORICAL_DIR_ENV_VAR} or place them at the default location) -- "
    "canonical-artifact smoke test NOT RUN / FILES UNAVAILABLE."
)


def _print_artifact_report(name: str, path, expected_sha256: str, expected_rows: int) -> None:
    observed_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"\n{name}:")
    print(f"  observed SHA-256: {observed_sha256}")
    print(f"  expected SHA-256: {expected_sha256}")
    print(f"  hash match: {observed_sha256 == expected_sha256}")


@pytest.mark.skipif(not _BOTH_PRESENT, reason=skip_reason)
def test_canonical_strategy_metrics_smoke() -> None:
    _print_artifact_report(
        "strategy_metrics.csv",
        _METRICS_PATH,
        config.STRATEGY_METRICS_EXPECTED_SHA256,
        config.STRATEGY_METRICS_EXPECTED_ROWS,
    )
    result = load_strategy_metrics()
    print(f"  schema PASS/FAIL: {result.observed_schema == result.expected_schema}")
    print(f"  observed rows: {result.observed_rows} / expected rows: {result.expected_rows}")
    assert result.state is HistoricalState.AVAILABLE, result.message
    assert result.observed_sha256 == config.STRATEGY_METRICS_EXPECTED_SHA256
    assert result.observed_schema == config.STRATEGY_METRICS_SCHEMA
    assert result.observed_rows == config.STRATEGY_METRICS_EXPECTED_ROWS


@pytest.mark.skipif(not _BOTH_PRESENT, reason=skip_reason)
def test_canonical_monthly_results_smoke() -> None:
    _print_artifact_report(
        "monthly_backtest_results.csv",
        _WEALTH_PATH,
        config.MONTHLY_RESULTS_EXPECTED_SHA256,
        config.MONTHLY_RESULTS_EXPECTED_ROWS,
    )
    result = load_monthly_results()
    print(f"  schema PASS/FAIL: {result.observed_schema == result.expected_schema}")
    print(f"  observed rows: {result.observed_rows} / expected rows: {result.expected_rows}")
    assert result.state is HistoricalState.AVAILABLE, result.message
    assert result.observed_sha256 == config.MONTHLY_RESULTS_EXPECTED_SHA256
    assert result.observed_schema == config.MONTHLY_RESULTS_SCHEMA
    assert result.observed_rows == config.MONTHLY_RESULTS_EXPECTED_ROWS


@pytest.mark.skipif(not _BOTH_PRESENT, reason=skip_reason)
@pytest.mark.parametrize(
    "asset,view",
    [
        ("BTC", HistoricalView.PRIMARY),
        ("ETH", HistoricalView.PRIMARY),
        ("BTC", HistoricalView.ROBUSTNESS),
        ("ETH", HistoricalView.ROBUSTNESS),
    ],
)
def test_canonical_filtering_returns_rows(asset: str, view: HistoricalView) -> None:
    result = load_strategy_metrics()
    assert result.ok, result.message
    filtered = filter_metrics(result.dataframe, asset, view)
    assert len(filtered) == 4  # BENCHMARK + 3 strategies in each canonical set
    assert set(filtered["asset"]) == {asset}


@pytest.mark.skipif(not _BOTH_PRESENT, reason=skip_reason)
def test_canonical_wealth_end_path_extraction_in_decision_month_order() -> None:
    result = load_monthly_results()
    assert result.ok, result.message
    series = wealth_end_series(result.dataframe, "BTC", "BENCHMARK")
    months = list(series["decision_month"])
    assert months == sorted(months)
    assert months[0] == config.SAMPLE_START_MONTH
    assert months[-1] == config.SAMPLE_END_MONTH
    assert len(series) == 60  # 5 years of monthly cycles
