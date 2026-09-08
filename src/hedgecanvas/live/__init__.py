"""Deribit public-only live market-data adapter for BTC/ETH inverse options.

Phase 2 scope: read-only discovery, index price (S0), and BBO retrieval for
BTC/ETH inverse options, normalized into the inputs the Phase 1 domain
layer expects. No authentication, no private endpoints, no order
placement, no pricing models. See the README for full scope and
exclusions.
"""

from hedgecanvas.live.client import (
    DeribitAdapterError,
    DeribitClient,
    DeribitHTTPError,
    DeribitMalformedResponseError,
    DeribitNetworkError,
    DeribitRPCError,
)
from hedgecanvas.live.instruments import (
    EXPECTED_PRICE_INDEX,
    SUPPORTED_ASSETS,
    InstrumentClassification,
    InverseOptionInstrument,
    classify_instrument,
    fetch_eligible_instruments,
)
from hedgecanvas.live.pricing import IndexSnapshot, NativeQuote, fetch_bbo, fetch_index_price
from hedgecanvas.live.result import LiveResult
from hedgecanvas.live.service import (
    LiveHedgeQuote,
    build_collar_quote,
    build_covered_call_quote,
    build_protective_put_quote,
)
from hedgecanvas.live.sizing import SizingOutcome, normalize_amount
from hedgecanvas.live.states import MarketState

__all__ = [
    "DeribitClient",
    "DeribitAdapterError",
    "DeribitNetworkError",
    "DeribitHTTPError",
    "DeribitRPCError",
    "DeribitMalformedResponseError",
    "MarketState",
    "LiveResult",
    "SUPPORTED_ASSETS",
    "EXPECTED_PRICE_INDEX",
    "InverseOptionInstrument",
    "InstrumentClassification",
    "classify_instrument",
    "fetch_eligible_instruments",
    "IndexSnapshot",
    "NativeQuote",
    "fetch_index_price",
    "fetch_bbo",
    "SizingOutcome",
    "normalize_amount",
    "LiveHedgeQuote",
    "build_protective_put_quote",
    "build_covered_call_quote",
    "build_collar_quote",
]
