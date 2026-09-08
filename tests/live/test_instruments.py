"""Tests for inverse-option discovery and strict eligibility classification."""

from datetime import timezone
from decimal import Decimal

from hedgecanvas.live.instruments import classify_instrument, fetch_eligible_instruments
from hedgecanvas.live.states import MarketState
from tests.live.helpers import (
    btc_usdc_linear_call_raw,
    make_mock_client,
    valid_btc_call_raw,
    valid_btc_put_raw,
    valid_eth_call_raw,
    valid_eth_put_raw,
)


def test_parse_valid_btc_inverse_put() -> None:
    classification = classify_instrument(valid_btc_put_raw(), "BTC")
    assert classification.ok
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.instrument_name == "BTC-27DEC24-90000-P"
    assert instrument.asset == "BTC"
    assert instrument.option_type == "put"
    assert instrument.strike == Decimal("90000")


def test_parse_valid_btc_inverse_call() -> None:
    classification = classify_instrument(valid_btc_call_raw(), "BTC")
    assert classification.ok
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.option_type == "call"
    assert instrument.strike == Decimal("100000")


def test_parse_valid_eth_inverse_put() -> None:
    classification = classify_instrument(valid_eth_put_raw(), "ETH")
    assert classification.ok
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.asset == "ETH"
    assert instrument.option_type == "put"
    assert instrument.min_trade_amount == Decimal("1")


def test_parse_valid_eth_inverse_call() -> None:
    classification = classify_instrument(valid_eth_call_raw(), "ETH")
    assert classification.ok
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.option_type == "call"


def test_reject_btc_usdc_linear_option() -> None:
    classification = classify_instrument(btc_usdc_linear_call_raw(), "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT
    assert classification.instrument is None


def test_reject_eth_usdc_linear_option() -> None:
    raw = btc_usdc_linear_call_raw()
    raw.update(
        instrument_name="ETH_USDC-27DEC24-3500-C",
        base_currency="ETH",
        settlement_currency="USDC",
        price_index="eth_usd",
    )
    classification = classify_instrument(raw, "ETH")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_reject_wrong_settlement_currency() -> None:
    raw = valid_btc_put_raw()
    raw["settlement_currency"] = "USDC"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_reject_wrong_counter_currency() -> None:
    raw = valid_btc_put_raw()
    raw["counter_currency"] = "EUR"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_reject_non_option_instrument() -> None:
    raw = valid_btc_put_raw()
    raw["kind"] = "future"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_reject_unexpected_contract_size() -> None:
    raw = valid_btc_put_raw()
    raw["contract_size"] = 10
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_expiry_conversion_is_utc_timezone_aware() -> None:
    classification = classify_instrument(valid_btc_put_raw(), "BTC")
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.expiry.tzinfo is not None
    assert instrument.expiry.utcoffset().total_seconds() == 0
    assert instrument.expiry.astimezone(timezone.utc) == instrument.expiry


def test_option_type_parsing() -> None:
    put = classify_instrument(valid_btc_put_raw(), "BTC").instrument
    call = classify_instrument(valid_btc_call_raw(), "BTC").instrument
    assert put is not None and put.option_type == "put"
    assert call is not None and call.option_type == "call"


def test_strike_parsing_exact_decimal() -> None:
    raw = valid_btc_put_raw(strike=87654.5)
    classification = classify_instrument(raw, "BTC")
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.strike == Decimal("87654.5")


def test_price_index_parsing() -> None:
    classification = classify_instrument(valid_eth_call_raw(), "ETH")
    instrument = classification.instrument
    assert instrument is not None
    assert instrument.price_index == "eth_usd"


def test_reject_instrument_type_not_reversed() -> None:
    raw = valid_btc_call_raw()
    raw["instrument_type"] = "linear"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_reject_inactive_instrument() -> None:
    raw = valid_btc_call_raw()
    raw["is_active"] = False
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.INSTRUMENT_INACTIVE


def test_reject_state_not_open() -> None:
    raw = valid_btc_call_raw()
    raw["state"] = "closed"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.INSTRUMENT_INACTIVE


def test_reject_name_suffix_mismatch_with_option_type() -> None:
    raw = valid_btc_put_raw()
    raw["option_type"] = "call"  # instrument_name still ends in "-P"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.INCONSISTENT_METADATA


def test_reject_missing_price_index_wrong_asset() -> None:
    raw = valid_btc_put_raw()
    raw["price_index"] = "eth_usd"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.UNSUPPORTED_INSTRUMENT


def test_fetch_eligible_instruments_filters_mixed_snapshot() -> None:
    def handler(method: str, params: dict) -> list:
        assert method == "public/get_instruments"
        assert params["currency"] == "BTC"
        assert params["kind"] == "option"
        assert params["expired"] is False
        return [valid_btc_put_raw(), valid_btc_call_raw(), btc_usdc_linear_call_raw()]

    client = make_mock_client(handler)
    result = fetch_eligible_instruments(client, "BTC")
    assert result.ok
    assert result.value is not None
    names = {inst.instrument_name for inst in result.value}
    assert names == {"BTC-27DEC24-90000-P", "BTC-27DEC24-100000-C"}


def test_malformed_result_missing_strike() -> None:
    raw = valid_btc_put_raw()
    del raw["strike"]
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.MALFORMED_RESPONSE


def test_malformed_result_non_numeric_min_trade_amount() -> None:
    raw = valid_btc_call_raw()
    raw["min_trade_amount"] = "not-a-number"
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.MALFORMED_RESPONSE


def test_malformed_result_missing_expiration_timestamp() -> None:
    raw = valid_btc_call_raw()
    del raw["expiration_timestamp"]
    classification = classify_instrument(raw, "BTC")
    assert classification.state is MarketState.MALFORMED_RESPONSE


def test_get_instruments_non_list_result_is_malformed() -> None:
    def handler(method: str, params: dict):
        return {"unexpected": "shape"}

    client = make_mock_client(handler)
    result = fetch_eligible_instruments(client, "BTC")
    assert result.state is MarketState.MALFORMED_RESPONSE


def test_fetch_eligible_instruments_single_call_per_asset() -> None:
    call_count = {"n": 0}

    def handler(method: str, params: dict) -> list:
        call_count["n"] += 1
        return [valid_eth_put_raw()]

    client = make_mock_client(handler)
    fetch_eligible_instruments(client, "ETH")
    assert call_count["n"] == 1
