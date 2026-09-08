"""Index price (S0) and top-of-book (BBO) native premium retrieval.

S0 is always taken from ``public/get_index_price`` for the option's declared
``price_index`` — never from an option's ``underlying_price``, which belongs
to the expiry forward/IV framework rather than the live spot portfolio
reference the Phase 1 payoff model requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Literal

from hedgecanvas.live.client import DeribitAdapterError, DeribitClient, error_to_market_state
from hedgecanvas.live.instruments import InverseOptionInstrument
from hedgecanvas.live.numeric import json_number_to_decimal
from hedgecanvas.live.result import LiveResult
from hedgecanvas.live.states import MarketState

QuoteSide = Literal["bid", "ask"]


@dataclass(frozen=True)
class IndexSnapshot:
    """A single S0 reading: the index name, its price, and when we read it."""

    index_name: str
    index_price: Decimal
    retrieved_at: datetime


@dataclass(frozen=True)
class NativeQuote:
    """A top-of-book quote in the option's native (BTC/ETH) premium currency.

    Retained separately from any USD-normalized value: the native quote is
    never overwritten by the USD conversion.
    """

    instrument_name: str
    quote_side: QuoteSide
    premium_native: Decimal
    premium_currency: str
    best_quote_amount: Decimal


def fetch_index_price(client: DeribitClient, index_name: str) -> LiveResult[IndexSnapshot]:
    """Fetch the current index price to use as S0 for a given price_index."""
    try:
        result = client.get_index_price(index_name)
    except DeribitAdapterError as exc:
        return LiveResult.fail(error_to_market_state(exc), str(exc))

    if not isinstance(result, dict):
        return LiveResult.fail(
            MarketState.MALFORMED_RESPONSE, "get_index_price did not return an object"
        )

    index_price = json_number_to_decimal(result.get("index_price"))
    if index_price is None or index_price <= 0:
        return LiveResult.fail(
            MarketState.MALFORMED_RESPONSE, "missing/invalid 'index_price'"
        )

    snapshot = IndexSnapshot(
        index_name=index_name,
        index_price=index_price,
        retrieved_at=datetime.now(timezone.utc),
    )
    return LiveResult.ok_value(snapshot)


_SIDE_FIELDS: Dict[QuoteSide, Any] = {
    "ask": ("best_ask_price", "best_ask_amount"),
    "bid": ("best_bid_price", "best_bid_amount"),
}


def fetch_bbo(
    client: DeribitClient, instrument: InverseOptionInstrument, side: QuoteSide
) -> LiveResult[NativeQuote]:
    """Fetch the top-of-book price/amount for the required side (bid or ask).

    Never uses midpoint, mark price, or last trade as a substitute. If the
    required side is absent, null, or non-positive, returns NO_QUOTE.
    """
    try:
        result = client.get_order_book(instrument.instrument_name, depth=1)
    except DeribitAdapterError as exc:
        return LiveResult.fail(error_to_market_state(exc), str(exc))

    if not isinstance(result, dict):
        return LiveResult.fail(
            MarketState.MALFORMED_RESPONSE, "get_order_book did not return an object"
        )

    price_field, amount_field = _SIDE_FIELDS[side]
    price = json_number_to_decimal(result.get(price_field))
    amount = json_number_to_decimal(result.get(amount_field))

    if price is None or price <= 0 or amount is None or amount <= 0:
        return LiveResult.fail(
            MarketState.NO_QUOTE,
            f"no valid {side} quote for {instrument.instrument_name}",
        )

    quote = NativeQuote(
        instrument_name=instrument.instrument_name,
        quote_side=side,
        premium_native=price,
        premium_currency=instrument.asset,
        best_quote_amount=amount,
    )
    return LiveResult.ok_value(quote)
