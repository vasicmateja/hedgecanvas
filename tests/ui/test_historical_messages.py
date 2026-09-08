"""Tests for the HistoricalState -> UI message/severity mapping."""

from hedgecanvas.historical import HistoricalState
from hedgecanvas.ui.historical_messages import describe_historical_state


def test_all_historical_states_map_to_a_message() -> None:
    for state in HistoricalState:
        display = describe_historical_state(state)
        assert display.severity in {"info", "warning", "error"}
        assert display.message


def test_file_missing_is_warning() -> None:
    assert describe_historical_state(HistoricalState.FILE_MISSING).severity == "warning"


def test_hash_mismatch_is_error() -> None:
    assert describe_historical_state(HistoricalState.HASH_MISMATCH).severity == "error"


def test_schema_mismatch_is_error() -> None:
    assert describe_historical_state(HistoricalState.SCHEMA_MISMATCH).severity == "error"


def test_row_count_mismatch_is_error() -> None:
    assert describe_historical_state(HistoricalState.ROW_COUNT_MISMATCH).severity == "error"


def test_available_is_info() -> None:
    assert describe_historical_state(HistoricalState.AVAILABLE).severity == "info"
