"""Tests for the MarketState -> UI message/severity mapping."""

from hedgecanvas.live import MarketState
from hedgecanvas.ui.market_messages import describe_market_state


def test_market_state_to_ui_mapping_covers_all_states() -> None:
    for state in MarketState:
        display = describe_market_state(state)
        assert display.severity in {"info", "warning", "error"}
        assert display.message


def test_no_quote_is_warning() -> None:
    assert describe_market_state(MarketState.NO_QUOTE).severity == "warning"


def test_below_minimum_size_is_warning() -> None:
    assert describe_market_state(MarketState.BELOW_MINIMUM_SIZE).severity == "warning"


def test_insufficient_bbo_depth_is_warning() -> None:
    assert describe_market_state(MarketState.INSUFFICIENT_BBO_DEPTH).severity == "warning"


def test_network_error_is_error() -> None:
    assert describe_market_state(MarketState.NETWORK_ERROR).severity == "error"


def test_http_error_is_error() -> None:
    assert describe_market_state(MarketState.HTTP_ERROR).severity == "error"


def test_rpc_error_is_error() -> None:
    assert describe_market_state(MarketState.RPC_ERROR).severity == "error"


def test_malformed_response_is_error() -> None:
    assert describe_market_state(MarketState.MALFORMED_RESPONSE).severity == "error"


def test_inconsistent_metadata_is_error() -> None:
    assert describe_market_state(MarketState.INCONSISTENT_METADATA).severity == "error"


def test_ok_state_is_info() -> None:
    assert describe_market_state(MarketState.OK).severity == "info"
