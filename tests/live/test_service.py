"""Tests for the live-adapter orchestration layer: building structured inputs
for Protective Put, Covered Call, and Collar from live Deribit data.
"""

from decimal import Decimal

from hedgecanvas.domain import Strategy
from hedgecanvas.live.instruments import classify_instrument
from hedgecanvas.live.service import (
    build_collar_quote,
    build_covered_call_quote,
    build_protective_put_quote,
)
from hedgecanvas.live.states import MarketState
from tests.live.helpers import (
    make_mock_client,
    order_book_raw,
    valid_btc_call_raw,
    valid_btc_put_raw,
    valid_eth_call_raw,
)


def _instrument(raw: dict, asset: str):
    result = classify_instrument(raw, asset)
    assert result.instrument is not None
    return result.instrument


def _handler_factory(index_price: float, bid, bid_amount, ask, ask_amount):
    def handler(method: str, params: dict) -> dict:
        if method == "public/get_index_price":
            return {"index_price": index_price}
        if method == "public/get_order_book":
            return order_book_raw(
                best_bid_price=bid,
                best_bid_amount=bid_amount,
                best_ask_price=ask,
                best_ask_amount=ask_amount,
            )
        raise AssertionError(f"unexpected method {method}")

    return handler


# ---------------------------------------------------------------------------
# Protective Put
# ---------------------------------------------------------------------------


def test_protective_put_sufficient_bbo_depth_ok() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=0.010, bid_amount=1, ask=0.012, ask_amount=1.0)
    )
    quote = build_protective_put_quote(client, put, Decimal("0.5"))
    assert quote.ok
    assert quote.strategy is Strategy.PROTECTIVE_PUT
    assert quote.S0 == Decimal("65000")
    assert quote.H == Decimal("0.5")
    assert quote.KP == Decimal("90000")
    assert quote.P == Decimal("0.012") * Decimal("65000")
    pos = quote.to_hedge_position()
    assert pos.is_full_coverage


def test_protective_put_insufficient_bbo_depth() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=0.010, bid_amount=1, ask=0.012, ask_amount=0.2)
    )
    quote = build_protective_put_quote(client, put, Decimal("0.5"))
    assert quote.state is MarketState.INSUFFICIENT_BBO_DEPTH
    assert not quote.ok


def test_protective_put_below_minimum_size() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=0.010, bid_amount=5, ask=0.012, ask_amount=5)
    )
    quote = build_protective_put_quote(client, put, Decimal("0.05"))
    assert quote.state is MarketState.BELOW_MINIMUM_SIZE
    assert quote.H == Decimal("0")


def test_protective_put_missing_ask_is_no_quote() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=0.010, bid_amount=5, ask=None, ask_amount=None)
    )
    quote = build_protective_put_quote(client, put, Decimal("0.5"))
    assert quote.state is MarketState.NO_QUOTE


# ---------------------------------------------------------------------------
# Covered Call
# ---------------------------------------------------------------------------


def test_covered_call_sufficient_bbo_depth_ok() -> None:
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=0.020, bid_amount=2, ask=0.025, ask_amount=2)
    )
    quote = build_covered_call_quote(client, call, Decimal("2"))
    assert quote.ok
    assert quote.strategy is Strategy.COVERED_CALL
    assert quote.H == Decimal("2.0")
    assert quote.C == Decimal("0.020") * Decimal("65000")


def test_covered_call_insufficient_bbo_depth() -> None:
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=0.020, bid_amount=1, ask=0.025, ask_amount=2)
    )
    quote = build_covered_call_quote(client, call, Decimal("2"))
    assert quote.state is MarketState.INSUFFICIENT_BBO_DEPTH


def test_covered_call_missing_bid_is_no_quote() -> None:
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.1), "BTC")
    client = make_mock_client(
        _handler_factory(65000.0, bid=None, bid_amount=None, ask=0.025, ask_amount=2)
    )
    quote = build_covered_call_quote(client, call, Decimal("2"))
    assert quote.state is MarketState.NO_QUOTE


# ---------------------------------------------------------------------------
# Collar
# ---------------------------------------------------------------------------


def test_collar_requires_both_bbo_depth_checks_put_insufficient() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.1), "BTC")

    def handler(method: str, params: dict) -> dict:
        if method == "public/get_index_price":
            return {"index_price": 65000.0}
        if method == "public/get_order_book":
            if params["instrument_name"] == put.instrument_name:
                return order_book_raw(
                    best_bid_price=0.010, best_bid_amount=5, best_ask_price=0.012, best_ask_amount=0.1
                )
            return order_book_raw(
                best_bid_price=0.020, best_bid_amount=5, best_ask_price=0.025, best_ask_amount=5
            )
        raise AssertionError(method)

    client = make_mock_client(handler)
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.state is MarketState.INSUFFICIENT_BBO_DEPTH
    assert "put" in (quote.message or "")


def test_collar_requires_both_bbo_depth_checks_call_insufficient() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.1), "BTC")

    def handler(method: str, params: dict) -> dict:
        if method == "public/get_index_price":
            return {"index_price": 65000.0}
        if method == "public/get_order_book":
            if params["instrument_name"] == put.instrument_name:
                return order_book_raw(
                    best_bid_price=0.010, best_bid_amount=5, best_ask_price=0.012, best_ask_amount=5
                )
            return order_book_raw(
                best_bid_price=0.020, best_bid_amount=0.1, best_ask_price=0.025, best_ask_amount=5
            )
        raise AssertionError(method)

    client = make_mock_client(handler)
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.state is MarketState.INSUFFICIENT_BBO_DEPTH
    assert "call" in (quote.message or "")


def test_collar_ok_uses_same_s0_for_both_legs() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.1), "BTC")

    index_calls = []

    def handler(method: str, params: dict) -> dict:
        if method == "public/get_index_price":
            index_calls.append(params["index_name"])
            return {"index_price": 65000.0}
        if method == "public/get_order_book":
            if params["instrument_name"] == put.instrument_name:
                return order_book_raw(
                    best_bid_price=0.010, best_bid_amount=5, best_ask_price=0.012, best_ask_amount=5
                )
            return order_book_raw(
                best_bid_price=0.020, best_bid_amount=5, best_ask_price=0.025, best_ask_amount=5
            )
        raise AssertionError(method)

    client = make_mock_client(handler)
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.ok
    # Exactly one index price fetch, reused for both P and C conversion.
    assert index_calls == ["btc_usd"]
    assert quote.P == Decimal("0.012") * Decimal("65000")
    assert quote.C == Decimal("0.020") * Decimal("65000")
    assert quote.S0 == Decimal("65000")


def test_collar_same_expiry_validation() -> None:
    put = _instrument(valid_btc_put_raw(expiration_timestamp=1735286400000), "BTC")
    call = _instrument(valid_btc_call_raw(expiration_timestamp=1738000000000), "BTC")
    client = make_mock_client(lambda m, p: {})
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.state is MarketState.INCONSISTENT_METADATA


def test_collar_same_asset_validation() -> None:
    put = _instrument(valid_btc_put_raw(), "BTC")
    call = _instrument(valid_eth_call_raw(), "ETH")
    client = make_mock_client(lambda m, p: {})
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.state is MarketState.INCONSISTENT_METADATA


def test_collar_kp_greater_than_kc_validation() -> None:
    put = _instrument(valid_btc_put_raw(strike=110000.0), "BTC")
    call = _instrument(valid_btc_call_raw(strike=100000.0), "BTC")
    client = make_mock_client(lambda m, p: {})
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.state is MarketState.INCONSISTENT_METADATA


def test_collar_incompatible_min_trade_amount() -> None:
    put = _instrument(valid_btc_put_raw(min_trade_amount=0.1), "BTC")
    call = _instrument(valid_btc_call_raw(min_trade_amount=0.01), "BTC")
    client = make_mock_client(lambda m, p: {})
    quote = build_collar_quote(client, put, call, Decimal("0.5"))
    assert quote.state is MarketState.INCONSISTENT_METADATA


def test_wrong_option_type_for_leg_is_rejected() -> None:
    not_a_put = _instrument(valid_btc_call_raw(), "BTC")
    client = make_mock_client(lambda m, p: {})
    quote = build_protective_put_quote(client, not_a_put, Decimal("0.5"))
    assert quote.state is MarketState.UNSUPPORTED_INSTRUMENT
