"""Shared fixtures for mocked Deribit adapter tests.

All fixtures here build deterministic, hand-constructed mock responses; no
test in this package (other than the explicitly marked live smoke test)
touches the network.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

import httpx

from hedgecanvas.live.client import DeribitClient

RpcHandler = Callable[[str, Dict[str, Any]], Any]


def make_mock_client(handler: RpcHandler, status_code: int = 200) -> DeribitClient:
    """Build a DeribitClient whose HTTP transport is fully mocked.

    ``handler(method, params) -> result_dict`` supplies the JSON-RPC
    "result" payload for each call. Raise inside ``handler`` to simulate a
    JSON-RPC error being encoded by the caller (use the raw-response
    helpers below for HTTP/JSON-level failures instead).
    """

    def transport_handler(request: httpx.Request) -> httpx.Response:
        method = request.url.path.split("/api/v2/", 1)[-1]
        body = json.loads(request.content)
        params = body.get("params", {})
        result = handler(method, params)
        return httpx.Response(
            status_code,
            json={"jsonrpc": "2.0", "id": body.get("id"), "result": result},
        )

    transport = httpx.MockTransport(transport_handler)
    http_client = httpx.Client(transport=transport)
    return DeribitClient(http_client=http_client)


def make_raw_response_client(
    *,
    status_code: int = 200,
    json_body: Optional[Dict[str, Any]] = None,
    raw_text: Optional[str] = None,
    raise_exc: Optional[Exception] = None,
) -> DeribitClient:
    """Build a DeribitClient whose transport returns a fixed raw response,
    or raises a given httpx exception, regardless of the request.
    """

    def transport_handler(request: httpx.Request) -> httpx.Response:
        if raise_exc is not None:
            raise raise_exc
        if raw_text is not None:
            return httpx.Response(status_code, text=raw_text)
        return httpx.Response(status_code, json=json_body if json_body is not None else {})

    transport = httpx.MockTransport(transport_handler)
    http_client = httpx.Client(transport=transport)
    return DeribitClient(http_client=http_client)


def valid_btc_put_raw(
    *,
    instrument_name: str = "BTC-27DEC24-90000-P",
    strike: float = 90000.0,
    expiration_timestamp: int = 1735286400000,
    min_trade_amount: float = 0.1,
) -> Dict[str, Any]:
    return {
        "instrument_name": instrument_name,
        "kind": "option",
        "option_type": "put",
        "strike": strike,
        "expiration_timestamp": expiration_timestamp,
        "contract_size": 1,
        "min_trade_amount": min_trade_amount,
        "tick_size": 0.0001,
        "tick_size_steps": [],
        "price_index": "btc_usd",
        "quote_currency": "BTC",
        "base_currency": "BTC",
        "settlement_currency": "BTC",
        "counter_currency": "USD",
        "instrument_type": "reversed",
        "state": "open",
        "is_active": True,
    }


def valid_btc_call_raw(
    *,
    instrument_name: str = "BTC-27DEC24-100000-C",
    strike: float = 100000.0,
    expiration_timestamp: int = 1735286400000,
    min_trade_amount: float = 0.1,
) -> Dict[str, Any]:
    return {
        "instrument_name": instrument_name,
        "kind": "option",
        "option_type": "call",
        "strike": strike,
        "expiration_timestamp": expiration_timestamp,
        "contract_size": 1,
        "min_trade_amount": min_trade_amount,
        "tick_size": 0.0001,
        "tick_size_steps": [],
        "price_index": "btc_usd",
        "quote_currency": "BTC",
        "base_currency": "BTC",
        "settlement_currency": "BTC",
        "counter_currency": "USD",
        "instrument_type": "reversed",
        "state": "open",
        "is_active": True,
    }


def valid_eth_put_raw(
    *,
    instrument_name: str = "ETH-27DEC24-3000-P",
    strike: float = 3000.0,
    expiration_timestamp: int = 1735286400000,
    min_trade_amount: float = 1.0,
) -> Dict[str, Any]:
    return {
        "instrument_name": instrument_name,
        "kind": "option",
        "option_type": "put",
        "strike": strike,
        "expiration_timestamp": expiration_timestamp,
        "contract_size": 1,
        "min_trade_amount": min_trade_amount,
        "tick_size": 0.0005,
        "tick_size_steps": [],
        "price_index": "eth_usd",
        "quote_currency": "ETH",
        "base_currency": "ETH",
        "settlement_currency": "ETH",
        "counter_currency": "USD",
        "instrument_type": "reversed",
        "state": "open",
        "is_active": True,
    }


def valid_eth_call_raw(
    *,
    instrument_name: str = "ETH-27DEC24-3500-C",
    strike: float = 3500.0,
    expiration_timestamp: int = 1735286400000,
    min_trade_amount: float = 1.0,
) -> Dict[str, Any]:
    return {
        "instrument_name": instrument_name,
        "kind": "option",
        "option_type": "call",
        "strike": strike,
        "expiration_timestamp": expiration_timestamp,
        "contract_size": 1,
        "min_trade_amount": min_trade_amount,
        "tick_size": 0.0005,
        "tick_size_steps": [],
        "price_index": "eth_usd",
        "quote_currency": "ETH",
        "base_currency": "ETH",
        "settlement_currency": "ETH",
        "counter_currency": "USD",
        "instrument_type": "reversed",
        "state": "open",
        "is_active": True,
    }


def btc_usdc_linear_call_raw() -> Dict[str, Any]:
    """A linear USDC-settled BTC option: must be rejected, never mixed in."""
    return {
        "instrument_name": "BTC_USDC-27DEC24-100000-C",
        "kind": "option",
        "option_type": "call",
        "strike": 100000.0,
        "expiration_timestamp": 1735286400000,
        "contract_size": 1,
        "min_trade_amount": 0.1,
        "tick_size": 0.0001,
        "price_index": "btc_usd",
        "quote_currency": "USDC",
        "base_currency": "BTC",
        "settlement_currency": "USDC",
        "counter_currency": "USD",
        "instrument_type": "linear",
        "state": "open",
        "is_active": True,
    }


def order_book_raw(
    *,
    best_bid_price: Optional[float],
    best_bid_amount: Optional[float],
    best_ask_price: Optional[float],
    best_ask_amount: Optional[float],
) -> Dict[str, Any]:
    return {
        "best_bid_price": best_bid_price,
        "best_bid_amount": best_bid_amount,
        "best_ask_price": best_ask_price,
        "best_ask_amount": best_ask_amount,
        "bids": [[best_bid_price, best_bid_amount]] if best_bid_price else [],
        "asks": [[best_ask_price, best_ask_amount]] if best_ask_price else [],
    }
