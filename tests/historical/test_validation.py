"""Tests for fail-closed artifact validation: hash, ordered schema, row count."""

import hashlib
from pathlib import Path

from hedgecanvas.historical.config import MONTHLY_RESULTS_SCHEMA, STRATEGY_METRICS_SCHEMA
from hedgecanvas.historical.states import HistoricalState
from hedgecanvas.historical.validation import validate_artifact
from tests.historical.helpers import (
    default_metrics_rows,
    default_monthly_rows,
    write_metrics_csv,
    write_monthly_csv,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_strategy_metrics_fixture_passes(tmp_path: Path) -> None:
    path = write_metrics_csv(tmp_path / "strategy_metrics.csv", default_metrics_rows())
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(default_metrics_rows()),
        key_checks=(("asset", ("BTC", "ETH")),),
    )
    assert result.ok
    assert result.state is HistoricalState.AVAILABLE
    assert result.dataframe is not None
    assert len(result.dataframe) == 14


def test_strategy_metrics_hash_mismatch_fails(tmp_path: Path) -> None:
    path = write_metrics_csv(tmp_path / "strategy_metrics.csv", default_metrics_rows())
    result = validate_artifact(
        path,
        expected_sha256="0" * 64,
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(default_metrics_rows()),
    )
    assert result.state is HistoricalState.HASH_MISMATCH
    assert result.dataframe is None


def test_valid_monthly_results_fixture_passes(tmp_path: Path) -> None:
    path = write_monthly_csv(tmp_path / "monthly_backtest_results.csv", default_monthly_rows())
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(default_monthly_rows()),
    )
    assert result.ok


def test_monthly_results_hash_mismatch_fails(tmp_path: Path) -> None:
    path = write_monthly_csv(tmp_path / "monthly_backtest_results.csv", default_monthly_rows())
    result = validate_artifact(
        path,
        expected_sha256="f" * 64,
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(default_monthly_rows()),
    )
    assert result.state is HistoricalState.HASH_MISMATCH


def test_exact_strategy_metrics_schema_passes(tmp_path: Path) -> None:
    path = write_metrics_csv(tmp_path / "m.csv", default_metrics_rows())
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(default_metrics_rows()),
    )
    assert result.state is HistoricalState.AVAILABLE
    assert result.observed_schema == tuple(STRATEGY_METRICS_SCHEMA)


def test_reordered_strategy_metrics_columns_fails(tmp_path: Path) -> None:
    reordered = list(STRATEGY_METRICS_SCHEMA)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    path = write_metrics_csv(tmp_path / "m.csv", default_metrics_rows(), columns=reordered)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(default_metrics_rows()),
    )
    assert result.state is HistoricalState.SCHEMA_MISMATCH


def test_missing_strategy_metrics_column_fails(tmp_path: Path) -> None:
    reduced = [c for c in STRATEGY_METRICS_SCHEMA if c != "sortino_ratio"]
    rows = [{k: v for k, v in row.items() if k != "sortino_ratio"} for row in default_metrics_rows()]
    path = write_metrics_csv(tmp_path / "m.csv", rows, columns=reduced)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(rows),
    )
    assert result.state is HistoricalState.SCHEMA_MISMATCH


def test_extra_strategy_metrics_column_fails(tmp_path: Path) -> None:
    extended = list(STRATEGY_METRICS_SCHEMA) + ["extra_column"]
    rows = [dict(row, extra_column=1) for row in default_metrics_rows()]
    path = write_metrics_csv(tmp_path / "m.csv", rows, columns=extended)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(rows),
    )
    assert result.state is HistoricalState.SCHEMA_MISMATCH


def test_exact_monthly_results_schema_passes(tmp_path: Path) -> None:
    path = write_monthly_csv(tmp_path / "w.csv", default_monthly_rows())
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(default_monthly_rows()),
    )
    assert result.ok
    assert result.observed_schema == tuple(MONTHLY_RESULTS_SCHEMA)


def test_reordered_monthly_results_columns_fails(tmp_path: Path) -> None:
    reordered = list(MONTHLY_RESULTS_SCHEMA)
    reordered[-1], reordered[-2] = reordered[-2], reordered[-1]  # swap wealth_start/wealth_end
    path = write_monthly_csv(tmp_path / "w.csv", default_monthly_rows(), columns=reordered)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(default_monthly_rows()),
    )
    assert result.state is HistoricalState.SCHEMA_MISMATCH


def test_missing_monthly_results_column_fails(tmp_path: Path) -> None:
    reduced = [c for c in MONTHLY_RESULTS_SCHEMA if c != "wealth_start"]
    rows = [{k: v for k, v in row.items() if k != "wealth_start"} for row in default_monthly_rows()]
    path = write_monthly_csv(tmp_path / "w.csv", rows, columns=reduced)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(rows),
    )
    assert result.state is HistoricalState.SCHEMA_MISMATCH


def test_extra_monthly_results_column_fails(tmp_path: Path) -> None:
    extended = list(MONTHLY_RESULTS_SCHEMA) + ["extra_column"]
    rows = [dict(row, extra_column=1) for row in default_monthly_rows()]
    path = write_monthly_csv(tmp_path / "w.csv", rows, columns=extended)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(rows),
    )
    assert result.state is HistoricalState.SCHEMA_MISMATCH


def test_wrong_strategy_metrics_row_count_fails(tmp_path: Path) -> None:
    path = write_metrics_csv(tmp_path / "m.csv", default_metrics_rows())
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(default_metrics_rows()) + 1,
    )
    assert result.state is HistoricalState.ROW_COUNT_MISMATCH


def test_wrong_monthly_results_row_count_fails(tmp_path: Path) -> None:
    path = write_monthly_csv(tmp_path / "w.csv", default_monthly_rows())
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=MONTHLY_RESULTS_SCHEMA,
        expected_rows=len(default_monthly_rows()) - 1,
    )
    assert result.state is HistoricalState.ROW_COUNT_MISMATCH


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    result = validate_artifact(
        tmp_path / "does_not_exist.csv",
        expected_sha256="0" * 64,
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=14,
    )
    assert result.state is HistoricalState.FILE_MISSING
    assert result.dataframe is None


def test_malformed_csv_produces_structured_read_parse_failure(tmp_path: Path) -> None:
    path = tmp_path / "broken.csv"
    path.write_bytes(b"\x00\x01\x02not,a,valid\ncsv\x00\x00")
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=14,
    )
    assert result.state in (HistoricalState.READ_PARSE_FAILURE, HistoricalState.SCHEMA_MISMATCH)


def test_invalid_key_value_fails_closed(tmp_path: Path) -> None:
    rows = default_metrics_rows()
    rows[0] = dict(rows[0], asset="DOGE")
    path = write_metrics_csv(tmp_path / "m.csv", rows)
    result = validate_artifact(
        path,
        expected_sha256=_sha256(path),
        expected_schema=STRATEGY_METRICS_SCHEMA,
        expected_rows=len(rows),
        key_checks=(("asset", ("BTC", "ETH")),),
    )
    assert result.state is HistoricalState.INVALID_KEYS
