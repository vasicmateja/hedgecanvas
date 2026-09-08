"""High-value Streamlit AppTest smoke tests for app.py.

These run the real app.py script through Streamlit's AppTest harness with
DeribitClient's HTTP-calling methods monkeypatched at the class level, so
no test here depends on network access -- app.py itself is never modified
or special-cased for testing.
"""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from hedgecanvas.live.client import DeribitClient
from tests.live.helpers import order_book_raw, valid_btc_call_raw, valid_btc_put_raw


def _patch_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_index_price(self, index_name):
        return {"index_price": 65000.0}

    def fake_get_instruments(self, currency, kind="option", expired=False):
        if currency == "BTC":
            return [valid_btc_put_raw(), valid_btc_call_raw()]
        return []

    def fake_get_order_book(self, instrument_name, depth=1):
        return order_book_raw(
            best_bid_price=0.010,
            best_bid_amount=5,
            best_ask_price=0.012,
            best_ask_amount=5,
        )

    monkeypatch.setattr(DeribitClient, "get_index_price", fake_get_index_price)
    monkeypatch.setattr(DeribitClient, "get_instruments", fake_get_instruments)
    monkeypatch.setattr(DeribitClient, "get_order_book", fake_get_order_book)


def test_app_starts_without_network_when_live_services_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live_client(monkeypatch)
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception


def test_basic_asset_and_strategy_controls_render(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live_client(monkeypatch)
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception

    select_labels = {box.label for box in at.sidebar.selectbox}
    assert "Asset" in select_labels
    assert "Strategy" in select_labels


def test_unhedged_mode_does_not_require_option_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live_client(monkeypatch)
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception

    # Strategy defaults to "Unhedged" (first option): no expiry/strike widgets.
    select_labels = {box.label for box in at.sidebar.selectbox}
    assert "Expiry" not in select_labels
    assert "Put strike (KP)" not in select_labels
    assert "Call strike (KC)" not in select_labels


def test_structured_market_failure_renders_warning_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    from hedgecanvas.live.client import DeribitNetworkError

    def failing_get_index_price(self, index_name):
        raise DeribitNetworkError("simulated network outage")

    monkeypatch.setattr(DeribitClient, "get_index_price", failing_get_index_price)

    at = AppTest.from_file("app.py")
    at.run(timeout=30)

    assert not at.exception
    assert len(at.error) >= 1
