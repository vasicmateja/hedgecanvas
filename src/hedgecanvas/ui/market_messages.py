"""Central mapping from Phase 2 MarketState to concise user-facing messages.

Keeps Streamlit rendering code from ad-hoc-ing failure copy per call site,
and ensures every MarketState (including states added later) degrades to
a message instead of an uncaught crash.
"""

from __future__ import annotations

from dataclasses import dataclass

from hedgecanvas.live import MarketState

Severity = str  # "info" | "warning" | "error"


@dataclass(frozen=True)
class MarketStateDisplay:
    severity: Severity
    message: str


_MESSAGES = {
    MarketState.OK: MarketStateDisplay("info", "Live quote available."),
    MarketState.NO_QUOTE: MarketStateDisplay(
        "warning",
        "No live quote is currently available on the required side for this contract.",
    ),
    MarketState.BELOW_MINIMUM_SIZE: MarketStateDisplay(
        "warning",
        "Position size is below the current minimum tradable option size; "
        "no option overlay is applied (H = 0).",
    ),
    MarketState.INSUFFICIENT_BBO_DEPTH: MarketStateDisplay(
        "warning",
        "Displayed top-of-book depth is insufficient for the required hedge size.",
    ),
    MarketState.INSTRUMENT_INACTIVE: MarketStateDisplay(
        "warning", "The selected contract is not currently active."
    ),
    MarketState.UNSUPPORTED_INSTRUMENT: MarketStateDisplay(
        "error",
        "The selected contract does not qualify as a supported BTC/ETH inverse option.",
    ),
    MarketState.INCONSISTENT_METADATA: MarketStateDisplay(
        "error", "Contract metadata is inconsistent; cannot construct a reliable hedge."
    ),
    MarketState.NETWORK_ERROR: MarketStateDisplay(
        "error", "Could not reach Deribit (network error)."
    ),
    MarketState.HTTP_ERROR: MarketStateDisplay(
        "error", "Deribit returned an HTTP error."
    ),
    MarketState.RPC_ERROR: MarketStateDisplay(
        "error", "Deribit returned an API error."
    ),
    MarketState.MALFORMED_RESPONSE: MarketStateDisplay(
        "error", "Deribit returned an unexpected response format."
    ),
}

_FALLBACK = MarketStateDisplay("error", "An unexpected market-data condition occurred.")


def describe_market_state(state: MarketState) -> MarketStateDisplay:
    """Map any MarketState (including future/unknown ones) to display info."""
    return _MESSAGES.get(state, _FALLBACK)
