"""Tests for the low-level Deribit JSON-RPC client's error handling."""

import httpx
import pytest

from hedgecanvas.live.client import (
    DeribitClient,
    DeribitHTTPError,
    DeribitMalformedResponseError,
    DeribitNetworkError,
    DeribitRPCError,
)
from tests.live.helpers import make_raw_response_client


def test_client_constructs_with_default_timeout_without_raising() -> None:
    # Regression: httpx.Timeout requires either a default or all four
    # parameters (connect/read/write/pool) set explicitly; constructing the
    # client must not raise before any network request is made.
    client = DeribitClient()
    try:
        timeout = client._http_client.timeout
        assert timeout.connect == 5.0
        assert timeout.read == 10.0
        assert timeout.write == 10.0
        assert timeout.pool == 10.0
    finally:
        client.close()


def test_client_constructs_with_custom_timeouts_without_raising() -> None:
    client = DeribitClient(connect_timeout=2.5, read_timeout=7.5)
    try:
        timeout = client._http_client.timeout
        assert timeout.connect == 2.5
        assert timeout.read == 7.5
        assert timeout.write == 7.5
        assert timeout.pool == 7.5
    finally:
        client.close()


def test_http_timeout_raises_network_error() -> None:
    client = make_raw_response_client(
        raise_exc=httpx.ConnectTimeout("connect timed out")
    )
    with pytest.raises(DeribitNetworkError):
        client.get_index_price("btc_usd")


def test_connection_error_raises_network_error() -> None:
    client = make_raw_response_client(
        raise_exc=httpx.ConnectError("could not connect")
    )
    with pytest.raises(DeribitNetworkError):
        client.get_index_price("btc_usd")


def test_non_success_http_status_raises_http_error() -> None:
    client = make_raw_response_client(status_code=503, json_body={})
    with pytest.raises(DeribitHTTPError) as exc_info:
        client.get_index_price("btc_usd")
    assert exc_info.value.status_code == 503


def test_valid_jsonrpc_error_response_raises_rpc_error() -> None:
    client = make_raw_response_client(
        status_code=200,
        json_body={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": 10009, "message": "not_found"},
        },
    )
    with pytest.raises(DeribitRPCError) as exc_info:
        client.get_index_price("btc_usd")
    assert exc_info.value.code == 10009


def test_malformed_json_raises_malformed_response_error() -> None:
    client = make_raw_response_client(status_code=200, raw_text="{not json")
    with pytest.raises(DeribitMalformedResponseError):
        client.get_index_price("btc_usd")


def test_missing_result_raises_malformed_response_error() -> None:
    client = make_raw_response_client(status_code=200, json_body={"jsonrpc": "2.0", "id": 1})
    with pytest.raises(DeribitMalformedResponseError):
        client.get_index_price("btc_usd")


def test_non_object_body_raises_malformed_response_error() -> None:
    client = make_raw_response_client(status_code=200, raw_text="[1, 2, 3]")
    with pytest.raises(DeribitMalformedResponseError):
        client.get_index_price("btc_usd")


def test_client_rejects_private_method() -> None:
    client = make_raw_response_client(status_code=200, json_body={"result": {}})
    with pytest.raises(ValueError):
        client._call("private/get_account_summary", {})
