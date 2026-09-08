"""Tests for the top-level HistoricalEvidence orchestrator: fail-closed
per-artifact behavior, directory resolution, and env-var override.
"""

import hashlib
import os
from pathlib import Path

import pytest

from hedgecanvas.historical.config import HISTORICAL_DIR_ENV_VAR
from hedgecanvas.historical.evidence import load_historical_evidence
from hedgecanvas.historical.loader import load_monthly_results, load_strategy_metrics
from hedgecanvas.historical.states import HistoricalState
from tests.historical.helpers import (
    default_metrics_rows,
    default_monthly_rows,
    write_metrics_csv,
    write_monthly_csv,
)


def test_missing_strategy_metrics_file_is_fail_closed(tmp_path: Path) -> None:
    # loader.py uses the real production expectations, so an empty
    # directory always fails closed regardless of fixture content.
    result = load_strategy_metrics(tmp_path)
    assert result.state is HistoricalState.FILE_MISSING
    assert result.dataframe is None


def test_missing_monthly_results_file_is_fail_closed(tmp_path: Path) -> None:
    result = load_monthly_results(tmp_path)
    assert result.state is HistoricalState.FILE_MISSING
    assert result.dataframe is None


def test_evidence_metrics_failure_does_not_expose_metrics(tmp_path: Path) -> None:
    evidence = load_historical_evidence(tmp_path)
    assert not evidence.metrics_available
    assert evidence.metrics.dataframe is None


def test_evidence_wealth_failure_does_not_expose_wealth(tmp_path: Path) -> None:
    evidence = load_historical_evidence(tmp_path)
    assert not evidence.wealth_available
    assert evidence.wealth.dataframe is None


def test_evidence_directory_override_used(tmp_path: Path) -> None:
    evidence = load_historical_evidence(tmp_path)
    assert evidence.directory == tmp_path


def test_evidence_env_var_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HISTORICAL_DIR_ENV_VAR, str(tmp_path))
    evidence = load_historical_evidence()
    assert evidence.directory == tmp_path


def test_evidence_carries_canonical_run_id_and_sample_range(tmp_path: Path) -> None:
    evidence = load_historical_evidence(tmp_path)
    assert evidence.run_id == "0cc87d60337032ec493534d312fc84734c5a4ae6a34b5687424f0761937d6132"
    assert evidence.sample_start_month == "2020-01"
    assert evidence.sample_end_month == "2024-12"


def test_one_artifact_valid_other_missing_reports_independently(tmp_path: Path) -> None:
    # Only the monthly-results file exists (production hash won't match a
    # fixture, so it still fails closed) -- metrics is FILE_MISSING,
    # wealth is HASH_MISMATCH (since fixture bytes != canonical production
    # bytes). Neither is silently treated as available.
    write_monthly_csv(tmp_path / "monthly_backtest_results.csv", default_monthly_rows())
    evidence = load_historical_evidence(tmp_path)
    assert evidence.metrics.state is HistoricalState.FILE_MISSING
    assert evidence.wealth.state in (
        HistoricalState.HASH_MISMATCH,
        HistoricalState.SCHEMA_MISMATCH,
        HistoricalState.ROW_COUNT_MISMATCH,
    )
    assert not evidence.wealth_available
