"""Structured market/quote states for the Deribit public live-data adapter.

Failures are never represented as ``None``: every operation that can fail
returns one of these explicit states so a caller (a future UI) can
distinguish, e.g., "no quote on the book" from "the network is down" from
"this instrument does not qualify as an inverse option".
"""

from __future__ import annotations

from enum import Enum


class MarketState(Enum):
    OK = "OK"
    NO_QUOTE = "NO_QUOTE"
    BELOW_MINIMUM_SIZE = "BELOW_MINIMUM_SIZE"
    INSUFFICIENT_BBO_DEPTH = "INSUFFICIENT_BBO_DEPTH"
    INSTRUMENT_INACTIVE = "INSTRUMENT_INACTIVE"
    UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"
    INCONSISTENT_METADATA = "INCONSISTENT_METADATA"
    NETWORK_ERROR = "NETWORK_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    RPC_ERROR = "RPC_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
