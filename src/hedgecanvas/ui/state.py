"""Request-identity-keyed live snapshot storage and asset-change invalidation.

Pure functions over a dict-like mutable mapping (Streamlit's
``st.session_state`` behaves like one, and a plain ``dict`` is used in
tests). A stale snapshot from a different request (different asset,
strategy, expiry, or strike) must never be displayed as though it applies
to the current selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, MutableMapping, Optional, Sequence, Tuple

RequestKey = Tuple[Any, ...]

_LIVE_QUOTE_STATE_KEY = "hedgecanvas_live_quote"
_LAST_ASSET_KEY = "hedgecanvas_last_asset"

# Session keys that are meaningless once the asset changes.
DEPENDENT_STATE_KEYS = (
    "hedgecanvas_expiry_selection",
    "hedgecanvas_put_strike_selection",
    "hedgecanvas_call_strike_selection",
    _LIVE_QUOTE_STATE_KEY,
)


def compute_request_key(
    asset: str,
    strategy: str,
    expiration_timestamp: Optional[int],
    put_strike: Optional[Decimal],
    call_strike: Optional[Decimal],
    quantity: Optional[Decimal] = None,
) -> RequestKey:
    """A deterministic identity for "the live quote that answers this exact
    selection". Any change to asset/strategy/expiry/strike/quantity must
    change it -- H (and therefore coverage) depends on quantity via Phase 2
    sizing, so a quantity change alone must also invalidate a prior snapshot.
    """
    return (
        asset,
        strategy,
        expiration_timestamp,
        str(put_strike) if put_strike is not None else None,
        str(call_strike) if call_strike is not None else None,
        str(quantity) if quantity is not None else None,
    )


@dataclass(frozen=True)
class StoredSnapshot:
    request_key: RequestKey
    value: Any
    fetched_at: datetime


def store_snapshot(
    session_state: MutableMapping[str, Any], request_key: RequestKey, value: Any
) -> StoredSnapshot:
    snapshot = StoredSnapshot(
        request_key=request_key, value=value, fetched_at=datetime.now(timezone.utc)
    )
    session_state[_LIVE_QUOTE_STATE_KEY] = snapshot
    return snapshot


def get_snapshot_for_key(
    session_state: MutableMapping[str, Any], request_key: RequestKey
) -> Optional[StoredSnapshot]:
    """Return the last stored snapshot ONLY if it matches the current request
    key exactly; otherwise None (never reuse a stale/different-request snapshot).
    """
    stored = session_state.get(_LIVE_QUOTE_STATE_KEY)
    if stored is None:
        return None
    if stored.request_key != request_key:
        return None
    return stored


def invalidate_for_asset_change(
    session_state: MutableMapping[str, Any], new_asset: str
) -> bool:
    """If the asset differs from the last-seen asset, clear all
    asset-dependent selection/snapshot state and record the new asset.

    Returns True if an invalidation occurred.
    """
    last_asset = session_state.get(_LAST_ASSET_KEY)
    if last_asset == new_asset:
        return False
    for key in DEPENDENT_STATE_KEYS:
        session_state.pop(key, None)
    session_state[_LAST_ASSET_KEY] = new_asset
    return True


def call_strike_needs_reset(
    previous_selected: Optional[Decimal], valid_call_strikes: Sequence[Decimal]
) -> bool:
    """True when a previously selected call strike is no longer a valid
    choice for the current put strike (KP changed such that KC < KP is no
    longer offered). ``previous_selected`` being None (no prior selection,
    e.g. first render) is never a reset.
    """
    if previous_selected is None:
        return False
    return previous_selected not in valid_call_strikes


def should_show_call_strike_adjusted_message(
    previous_selected: Optional[Decimal],
    valid_call_strikes: Sequence[Decimal],
    had_prior_tracked_value: bool,
) -> bool:
    """True only for a genuine automatic KC adjustment: there was a
    meaningfully tracked prior selection (not the very first render) AND
    that selection is no longer valid for the current KP. False whenever
    the prior KC is still valid (including an ordinary manual re-selection
    of a different, still-valid KC) or there was no prior selection yet.
    """
    if not had_prior_tracked_value:
        return False
    return call_strike_needs_reset(previous_selected, valid_call_strikes)
