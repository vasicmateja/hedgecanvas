"""Tests for S0 (index price) retrieval and BBO native-quote retrieval."""

from decimal import Decimal

from hedgecanvas.live.instruments import classify_instrument
from hedgecanvas.live.pricing import fetch_bbo, fetch_index_price
from hedgecanvas.live.states import MarketState
from tests.live.helpers import (
    make_mock_client,
    order_book_raw,
    valid_btc_call_raw,
    valid_btc_put_raw,
)


def _btc_put_instrument():
    return classify_instrument(valid_btc_put_raw(), "BTC").instrument


def _btc_call_instrument():
    return classify_instrument(valid_btc_call_raw(), "BTC").instrument


def test_s0_comes_from_get_index_price() -> None:
    def handler(method: str, params: dict) -> dict:
        assert method == "public/get_index_price"
        assert params["index_name"] == "btc_usd"
        return {"index_price": 65432.1, "estimated_delivery_price": 65432.1}

    client = make_mock_client(handler)
    result = fetch_index_price(client, "btc_usd")
    assert result.ok
    assert result.value is not None
    assert result.value.index_price == Decimal("65432.1")
    assert result.value.index_name == "btc_usd"


def test_underlying_price_is_not_substituted_for_s0() -> None:
    # get_order_book carries an unrelated 'underlying_price' field for the
    # option's forward/IV framework; S0 must never be read from it. Only
    # fetch_index_price (backed by public/get_index_price) supplies S0.
    def handler(method: str, params: dict) -> dict:
        if method == "public/get_order_book":
            return order_book_raw(
                best_bid_price=0.01,
                best_bid_amount=5,
                best_ask_price=0.015,
                best_ask_amount=5,
            ) | {"underlying_price": 999999.0}
        raise AssertionError(f"unexpected method {method}")

    client = make_mock_client(handler)
    instrument = _btc_put_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "ask")
    assert result.ok
    assert result.value is not None
    # premium_native must come from best_ask_price, never underlying_price.
    assert result.value.premium_native == Decimal("0.015")


def test_long_put_selects_ask() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=0.010,
            best_bid_amount=3,
            best_ask_price=0.012,
            best_ask_amount=4,
        )

    client = make_mock_client(handler)
    instrument = _btc_put_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "ask")
    assert result.ok
    assert result.value is not None
    assert result.value.quote_side == "ask"
    assert result.value.premium_native == Decimal("0.012")
    assert result.value.best_quote_amount == Decimal("4")


def test_short_call_selects_bid() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=0.020,
            best_bid_amount=2,
            best_ask_price=0.025,
            best_ask_amount=6,
        )

    client = make_mock_client(handler)
    instrument = _btc_call_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "bid")
    assert result.ok
    assert result.value is not None
    assert result.value.quote_side == "bid"
    assert result.value.premium_native == Decimal("0.020")
    assert result.value.best_quote_amount == Decimal("2")


def test_missing_ask_returns_no_quote() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=0.010, best_bid_amount=3, best_ask_price=None, best_ask_amount=None
        )

    client = make_mock_client(handler)
    instrument = _btc_put_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "ask")
    assert result.state is MarketState.NO_QUOTE
    assert result.value is None


def test_missing_bid_returns_no_quote() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=None, best_bid_amount=None, best_ask_price=0.02, best_ask_amount=4
        )

    client = make_mock_client(handler)
    instrument = _btc_call_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "bid")
    assert result.state is MarketState.NO_QUOTE


def test_zero_quote_price_rejected() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=0.0, best_bid_amount=3, best_ask_price=0.02, best_ask_amount=4
        )

    client = make_mock_client(handler)
    instrument = _btc_call_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "bid")
    assert result.state is MarketState.NO_QUOTE


def test_negative_quote_price_rejected() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=-0.01, best_bid_amount=3, best_ask_price=0.02, best_ask_amount=4
        )

    client = make_mock_client(handler)
    instrument = _btc_call_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "bid")
    assert result.state is MarketState.NO_QUOTE


def test_raw_btc_premium_retained_natively() -> None:
    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=0.010, best_bid_amount=3, best_ask_price=0.012, best_ask_amount=4
        )

    client = make_mock_client(handler)
    instrument = _btc_put_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "ask")
    assert result.value is not None
    assert result.value.premium_currency == "BTC"
    assert result.value.premium_native == Decimal("0.012")


def test_raw_eth_premium_retained_natively() -> None:
    from tests.live.helpers import valid_eth_call_raw

    def handler(method: str, params: dict) -> dict:
        return order_book_raw(
            best_bid_price=0.030, best_bid_amount=10, best_ask_price=0.035, best_ask_amount=8
        )

    client = make_mock_client(handler)
    instrument = classify_instrument(valid_eth_call_raw(), "ETH").instrument
    assert instrument is not None
    result = fetch_bbo(client, instrument, "bid")
    assert result.value is not None
    assert result.value.premium_currency == "ETH"
    assert result.value.premium_native == Decimal("0.030")


def test_p_equals_put_native_ask_times_s0() -> None:
    put_native = Decimal("0.012")
    S0 = Decimal("65000")
    assert put_native * S0 == Decimal("780")


def test_c_equals_call_native_bid_times_s0() -> None:
    call_native = Decimal("0.020")
    S0 = Decimal("65000")
    assert call_native * S0 == Decimal("1300")


def test_malformed_index_price_field_returns_malformed_response() -> None:
    def handler(method: str, params: dict) -> dict:
        return {"index_price": "not-a-number"}

    client = make_mock_client(handler)
    result = fetch_index_price(client, "btc_usd")
    assert result.state is MarketState.MALFORMED_RESPONSE


def test_missing_index_price_field_returns_malformed_response() -> None:
    def handler(method: str, params: dict) -> dict:
        return {"estimated_delivery_price": 65000.0}

    client = make_mock_client(handler)
    result = fetch_index_price(client, "btc_usd")
    assert result.state is MarketState.MALFORMED_RESPONSE


def test_order_book_non_object_result_returns_malformed_response() -> None:
    def handler(method: str, params: dict):
        return ["not", "an", "object"]

    client = make_mock_client(handler)
    instrument = _btc_put_instrument()
    assert instrument is not None
    result = fetch_bbo(client, instrument, "ask")
    assert result.state is MarketState.MALFORMED_RESPONSE
