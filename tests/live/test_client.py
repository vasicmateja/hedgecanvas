"""Tests for the low-level Deribit JSON-RPC client's error handling."""

import httpx
import pytest

from hedgecanvas.live.client import (
    DeribitHTTPError,
    DeribitMalformedResponseError,
    DeribitNetworkError,
    DeribitRPCError,
)
from tests.live.helpers import make_raw_response_client


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
