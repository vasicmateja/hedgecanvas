"""Underlying quantity normalization into a tradable option amount (H).

Deribit inverse-option order amounts must be non-negative integer multiples
of the instrument's live ``min_trade_amount`` (also its amount granularity
for this MVP). H is always rounded DOWN to the largest such multiple that
does not exceed the user's requested underlying quantity Q; H never exceeds
Q and is never rounded up.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hedgecanvas.live.result import LiveResult
from hedgecanvas.live.states import MarketState


@dataclass(frozen=True)
class SizingOutcome:
    H: Decimal
    steps: int


def normalize_amount(Q: Decimal, min_trade_amount: Decimal) -> LiveResult[SizingOutcome]:
    """Compute H_candidate = largest multiple of min_trade_amount that is <= Q.

    Returns BELOW_MINIMUM_SIZE (H = 0) if Q is smaller than one minimum
    tradable unit. Runtime instrument metadata (``min_trade_amount``) is
    authoritative; it is not assumed to equal any hardcoded expectation.
    """
    if Q <= 0:
        raise ValueError("Q must be > 0")
    if min_trade_amount <= 0:
        return LiveResult.fail(
            MarketState.MALFORMED_RESPONSE, "min_trade_amount must be > 0"
        )

    steps = int(Q // min_trade_amount)

    if steps <= 0:
        return LiveResult(
            state=MarketState.BELOW_MINIMUM_SIZE,
            value=SizingOutcome(H=Decimal(0), steps=0),
            message=f"Q={Q} is below min_trade_amount={min_trade_amount}",
        )

    H = min_trade_amount * steps
    if H > Q:  # pragma: no cover - defensive; floor division guarantees H <= Q
        raise AssertionError("normalized H must never exceed Q")

    return LiveResult.ok_value(SizingOutcome(H=H, steps=steps))
