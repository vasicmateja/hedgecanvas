"""Tests for request-key snapshot storage and asset-change invalidation."""

from decimal import Decimal

from hedgecanvas.ui.state import (
    compute_request_key,
    get_snapshot_for_key,
    invalidate_for_asset_change,
    store_snapshot,
)


def test_request_key_changes_with_asset() -> None:
    key_btc = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("50000"), None)
    key_eth = compute_request_key("ETH", "PROTECTIVE_PUT", 123, Decimal("50000"), None)
    assert key_btc != key_eth


def test_request_key_changes_with_quantity() -> None:
    # Regression: H (and coverage) is derived from Q via Phase 2 sizing, so
    # a quantity-only change must invalidate any previously stored quote --
    # observed live where changing Q alone left a stale H/coverage displayed.
    key1 = compute_request_key(
        "BTC", "COLLAR", 123, Decimal("73000"), Decimal("78000"), Decimal("1")
    )
    key2 = compute_request_key(
        "BTC", "COLLAR", 123, Decimal("73000"), Decimal("78000"), Decimal("0.15")
    )
    assert key1 != key2


def test_stale_snapshot_from_different_quantity_is_not_reused() -> None:
    session_state: dict = {}
    old_key = compute_request_key(
        "BTC", "COLLAR", 123, Decimal("73000"), Decimal("78000"), Decimal("1")
    )
    store_snapshot(session_state, old_key, {"H": Decimal("1")})

    new_key = compute_request_key(
        "BTC", "COLLAR", 123, Decimal("73000"), Decimal("78000"), Decimal("0.15")
    )
    assert get_snapshot_for_key(session_state, new_key) is None


def test_request_key_changes_with_strike() -> None:
    key1 = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("50000"), None)
    key2 = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("55000"), None)
    assert key1 != key2


def test_request_key_stable_for_identical_selection() -> None:
    key1 = compute_request_key("BTC", "COLLAR", 123, Decimal("50000"), Decimal("60000"))
    key2 = compute_request_key("BTC", "COLLAR", 123, Decimal("50000"), Decimal("60000"))
    assert key1 == key2


def test_store_and_retrieve_snapshot_for_matching_key() -> None:
    session_state: dict = {}
    key = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("50000"), None)
    store_snapshot(session_state, key, {"quote": "example"})

    retrieved = get_snapshot_for_key(session_state, key)
    assert retrieved is not None
    assert retrieved.value == {"quote": "example"}


def test_stale_snapshot_from_different_key_is_not_reused() -> None:
    session_state: dict = {}
    old_key = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("50000"), None)
    store_snapshot(session_state, old_key, {"quote": "btc-put-50k"})

    new_key = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("55000"), None)
    retrieved = get_snapshot_for_key(session_state, new_key)
    assert retrieved is None


def test_stale_snapshot_from_different_asset_is_not_reused() -> None:
    session_state: dict = {}
    old_key = compute_request_key("BTC", "PROTECTIVE_PUT", 123, Decimal("50000"), None)
    store_snapshot(session_state, old_key, {"quote": "btc-put"})

    new_key = compute_request_key("ETH", "PROTECTIVE_PUT", 123, Decimal("3000"), None)
    retrieved = get_snapshot_for_key(session_state, new_key)
    assert retrieved is None


def test_no_snapshot_returns_none() -> None:
    session_state: dict = {}
    key = compute_request_key("BTC", "UNHEDGED", None, None, None)
    assert get_snapshot_for_key(session_state, key) is None


def test_asset_change_invalidates_dependent_state() -> None:
    session_state: dict = {
        "hedgecanvas_expiry_selection": 123,
        "hedgecanvas_put_strike_selection": Decimal("50000"),
        "hedgecanvas_call_strike_selection": Decimal("60000"),
        "hedgecanvas_live_quote": "stale-btc-snapshot",
    }
    changed = invalidate_for_asset_change(session_state, "BTC")
    assert changed  # first time seeing an asset counts as a change
    assert "hedgecanvas_expiry_selection" not in session_state

    # Re-invoking with the SAME asset must not wipe freshly-set selections.
    session_state["hedgecanvas_expiry_selection"] = 999
    changed_again = invalidate_for_asset_change(session_state, "BTC")
    assert not changed_again
    assert session_state["hedgecanvas_expiry_selection"] == 999

    # Switching to a different asset invalidates again.
    changed_to_eth = invalidate_for_asset_change(session_state, "ETH")
    assert changed_to_eth
    assert "hedgecanvas_expiry_selection" not in session_state
    assert "hedgecanvas_live_quote" not in session_state
