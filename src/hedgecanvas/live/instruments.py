"""Discovery and strict eligibility filtering of BTC/ETH inverse options.

Eligibility is decided from the coherent set of instrument metadata Deribit
reports for a genuine inverse option, never from the instrument name alone.
The trailing "C"/"P" in ``instrument_name`` is used only as a secondary
consistency check against ``option_type``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from hedgecanvas.live.client import DeribitAdapterError, DeribitClient, error_to_market_state
from hedgecanvas.live.numeric import json_number_to_decimal
from hedgecanvas.live.result import LiveResult
from hedgecanvas.live.states import MarketState

SUPPORTED_ASSETS = ("BTC", "ETH")

EXPECTED_PRICE_INDEX = {
    "BTC": "btc_usd",
    "ETH": "eth_usd",
}

EXPECTED_CONTRACT_SIZE = Decimal(1)

_OPTION_TYPE_NAME_SUFFIX = {"call": "C", "put": "P"}


@dataclass(frozen=True)
class InverseOptionInstrument:
    """Parsed, eligibility-verified BTC/ETH inverse option instrument."""

    instrument_name: str
    asset: str
    expiration_timestamp: int
    expiry: datetime
    strike: Decimal
    option_type: str
    contract_size: Decimal
    min_trade_amount: Decimal
    tick_size: Decimal
    tick_size_steps: Optional[Any]
    price_index: str
    quote_currency: str
    base_currency: str
    settlement_currency: str
    counter_currency: str
    instrument_type: Optional[str]
    state: Optional[str]
    is_active: bool


@dataclass(frozen=True)
class InstrumentClassification:
    """Result of evaluating one raw instrument record for inverse-option eligibility."""

    state: MarketState
    instrument: Optional[InverseOptionInstrument]
    message: Optional[str]

    @property
    def ok(self) -> bool:
        return self.state is MarketState.OK


def _reject(state: MarketState, message: str) -> InstrumentClassification:
    return InstrumentClassification(state=state, instrument=None, message=message)


def classify_instrument(raw: Dict[str, Any], asset: str) -> InstrumentClassification:
    """Evaluate a single raw ``public/get_instruments`` record.

    Returns OK with a parsed :class:`InverseOptionInstrument` only if the
    full coherent inverse-option metadata set agrees; otherwise returns a
    structured rejection state.
    """
    if asset not in SUPPORTED_ASSETS:
        raise ValueError(f"Unsupported asset: {asset}")

    if not isinstance(raw, dict):
        return _reject(MarketState.MALFORMED_RESPONSE, "instrument record is not an object")

    instrument_name = raw.get("instrument_name")
    kind = raw.get("kind")
    option_type = raw.get("option_type")
    strike_raw = raw.get("strike")
    expiration_timestamp = raw.get("expiration_timestamp")
    contract_size_raw = raw.get("contract_size")
    min_trade_amount_raw = raw.get("min_trade_amount")
    tick_size_raw = raw.get("tick_size")
    price_index = raw.get("price_index")
    quote_currency = raw.get("quote_currency")
    base_currency = raw.get("base_currency")
    settlement_currency = raw.get("settlement_currency")
    counter_currency = raw.get("counter_currency")
    is_active = raw.get("is_active")

    required_str_fields = {
        "instrument_name": instrument_name,
        "kind": kind,
        "price_index": price_index,
        "quote_currency": quote_currency,
        "base_currency": base_currency,
        "settlement_currency": settlement_currency,
        "counter_currency": counter_currency,
    }
    for name, value in required_str_fields.items():
        if not isinstance(value, str) or not value:
            return _reject(
                MarketState.MALFORMED_RESPONSE, f"missing/invalid field '{name}'"
            )

    if not isinstance(expiration_timestamp, int) or expiration_timestamp <= 0:
        return _reject(
            MarketState.MALFORMED_RESPONSE, "missing/invalid 'expiration_timestamp'"
        )

    if not isinstance(is_active, bool):
        return _reject(MarketState.MALFORMED_RESPONSE, "missing/invalid 'is_active'")

    strike = json_number_to_decimal(strike_raw)
    contract_size = json_number_to_decimal(contract_size_raw)
    min_trade_amount = json_number_to_decimal(min_trade_amount_raw)
    tick_size = json_number_to_decimal(tick_size_raw)

    if strike is None or strike <= 0:
        return _reject(MarketState.MALFORMED_RESPONSE, "missing/invalid 'strike'")
    if contract_size is None or contract_size <= 0:
        return _reject(MarketState.MALFORMED_RESPONSE, "missing/invalid 'contract_size'")
    if min_trade_amount is None or min_trade_amount <= 0:
        return _reject(
            MarketState.MALFORMED_RESPONSE, "missing/invalid 'min_trade_amount'"
        )
    if tick_size is None or tick_size <= 0:
        return _reject(MarketState.MALFORMED_RESPONSE, "missing/invalid 'tick_size'")

    if option_type not in ("call", "put"):
        return _reject(MarketState.MALFORMED_RESPONSE, "missing/invalid 'option_type'")

    # -- coherent inverse-option metadata set -------------------------------

    if kind != "option":
        return _reject(MarketState.UNSUPPORTED_INSTRUMENT, "kind is not 'option'")

    if base_currency != asset:
        return _reject(
            MarketState.UNSUPPORTED_INSTRUMENT, f"base_currency != {asset}"
        )

    if settlement_currency != asset:
        return _reject(
            MarketState.UNSUPPORTED_INSTRUMENT, f"settlement_currency != {asset}"
        )

    if counter_currency != "USD":
        return _reject(MarketState.UNSUPPORTED_INSTRUMENT, "counter_currency != 'USD'")

    if price_index != EXPECTED_PRICE_INDEX[asset]:
        return _reject(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"price_index does not match {asset}'s USD index",
        )

    if contract_size != EXPECTED_CONTRACT_SIZE:
        return _reject(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"contract_size {contract_size} != {EXPECTED_CONTRACT_SIZE}",
        )

    if not is_active:
        return _reject(MarketState.INSTRUMENT_INACTIVE, "is_active is False")

    state = raw.get("state")
    if state is not None and state != "open":
        return _reject(MarketState.INSTRUMENT_INACTIVE, f"state != 'open' ({state!r})")

    instrument_type = raw.get("instrument_type")
    if instrument_type is not None and instrument_type != "reversed":
        return _reject(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"instrument_type != 'reversed' ({instrument_type!r})",
        )

    if "_USDC-" in instrument_name:
        return _reject(
            MarketState.UNSUPPORTED_INSTRUMENT, "instrument_name indicates a USDC-quoted option"
        )

    expected_suffix = _OPTION_TYPE_NAME_SUFFIX[option_type]
    if not instrument_name.endswith(expected_suffix):
        return _reject(
            MarketState.INCONSISTENT_METADATA,
            f"instrument_name suffix does not match option_type={option_type!r}",
        )

    tick_size_steps = raw.get("tick_size_steps")

    instrument = InverseOptionInstrument(
        instrument_name=instrument_name,
        asset=asset,
        expiration_timestamp=expiration_timestamp,
        expiry=datetime.fromtimestamp(expiration_timestamp / 1000, tz=timezone.utc),
        strike=strike,
        option_type=option_type,
        contract_size=contract_size,
        min_trade_amount=min_trade_amount,
        tick_size=tick_size,
        tick_size_steps=tick_size_steps,
        price_index=price_index,
        quote_currency=quote_currency,
        base_currency=base_currency,
        settlement_currency=settlement_currency,
        counter_currency=counter_currency,
        instrument_type=instrument_type,
        state=state,
        is_active=is_active,
    )
    return InstrumentClassification(state=MarketState.OK, instrument=instrument, message=None)


def fetch_eligible_instruments(
    client: DeribitClient, asset: str
) -> LiveResult[List[InverseOptionInstrument]]:
    """Fetch the current instrument snapshot for ``asset`` and keep only
    instruments that pass the strict inverse-option eligibility check.

    A single ``public/get_instruments`` call per asset; non-eligible
    instruments (e.g. linear USDC options) are filtered out rather than
    raising, since a mixed-product snapshot is the expected raw response.
    """
    if asset not in SUPPORTED_ASSETS:
        raise ValueError(f"Unsupported asset: {asset}")

    try:
        raw_instruments = client.get_instruments(currency=asset, kind="option", expired=False)
    except DeribitAdapterError as exc:
        return LiveResult.fail(error_to_market_state(exc), str(exc))

    if not isinstance(raw_instruments, list):
        return LiveResult.fail(
            MarketState.MALFORMED_RESPONSE, "get_instruments did not return a list"
        )

    eligible: List[InverseOptionInstrument] = []
    for raw in raw_instruments:
        classification = classify_instrument(raw, asset)
        if classification.ok:
            assert classification.instrument is not None
            eligible.append(classification.instrument)

    return LiveResult.ok_value(eligible)
