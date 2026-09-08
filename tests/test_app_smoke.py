"""High-value Streamlit AppTest smoke tests for app.py.

These run the real app.py script through Streamlit's AppTest harness with
DeribitClient's HTTP-calling methods monkeypatched at the class level, so
no test here depends on network access -- app.py itself is never modified
or special-cased for testing.
"""

from __future__ import annotations

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from hedgecanvas.historical.evidence import HistoricalEvidence
from hedgecanvas.historical.states import HistoricalState
from hedgecanvas.historical.validation import ArtifactValidationResult
from hedgecanvas.live.client import DeribitClient
from tests.historical.helpers import default_metrics_rows, default_monthly_rows
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


# ---------------------------------------------------------------------------
# Phase 4: Historical Evidence navigation and rendering
# ---------------------------------------------------------------------------


def _fixture_historical_evidence(directory) -> HistoricalEvidence:
    metrics_df = pd.DataFrame(default_metrics_rows())
    wealth_df = pd.DataFrame(default_monthly_rows())
    metrics_result = ArtifactValidationResult(state=HistoricalState.AVAILABLE, dataframe=metrics_df)
    wealth_result = ArtifactValidationResult(state=HistoricalState.AVAILABLE, dataframe=wealth_df)
    return HistoricalEvidence(directory=directory, metrics=metrics_result, wealth=wealth_result)


def _patch_historical_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    import hedgecanvas.historical as historical_pkg

    def fake_load_historical_evidence(directory=None):
        from pathlib import Path

        return _fixture_historical_evidence(Path(directory) if directory else Path("."))

    monkeypatch.setattr(historical_pkg, "load_historical_evidence", fake_load_historical_evidence)


def test_navigation_exposes_both_views(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live_client(monkeypatch)
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception

    nav_radio = at.sidebar.radio[0]
    assert set(nav_radio.options) == {"Live Designer", "Historical Evidence"}


def test_historical_evidence_renders_with_verified_mocked_data(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_historical_evidence(monkeypatch)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Historical Evidence must not call the live Deribit client")

    monkeypatch.setattr(DeribitClient, "get_index_price", fail_if_called)
    monkeypatch.setattr(DeribitClient, "get_instruments", fail_if_called)
    monkeypatch.setattr(DeribitClient, "get_order_book", fail_if_called)

    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    at.sidebar.radio[0].set_value("Historical Evidence")
    at.run(timeout=30)

    assert not at.exception
    body_text = "\n".join(m.value for m in at.markdown) + "\n".join(t.value for t in at.title)
    assert "Historical Thesis Evidence" in body_text
    assert len(at.error) == 0


def test_artifact_verification_failure_renders_clean_unavailable_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("HEDGECANVAS_HISTORICAL_DIR", str(tmp_path))

    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    at.sidebar.radio[0].set_value("Historical Evidence")
    at.run(timeout=30)

    assert not at.exception
    assert len(at.error) >= 1
    error_text = " ".join(e.value for e in at.error)
    assert "unavailable" in error_text.lower()


def test_historical_view_does_not_require_live_api_connectivity(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("HEDGECANVAS_HISTORICAL_DIR", str(tmp_path))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Historical Evidence must not call the live Deribit client")

    monkeypatch.setattr(DeribitClient, "get_index_price", fail_if_called)
    monkeypatch.setattr(DeribitClient, "get_instruments", fail_if_called)
    monkeypatch.setattr(DeribitClient, "get_order_book", fail_if_called)

    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    at.sidebar.radio[0].set_value("Historical Evidence")
    at.run(timeout=30)

    assert not at.exception


def test_primary_robustness_toggle_changes_displayed_strategy_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_historical_evidence(monkeypatch)

    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    at.sidebar.radio[0].set_value("Historical Evidence")
    at.run(timeout=30)
    assert not at.exception

    view_radio = at.radio[0]
    assert view_radio.value == "Primary"

    dataframes_primary = list(at.dataframe)
    assert len(dataframes_primary) == 1
    primary_strategies = set(dataframes_primary[0].value["Strategy"])
    assert "Protective Put 95" in primary_strategies
    assert "Protective Put 90" not in primary_strategies

    view_radio.set_value("Robustness")
    at.run(timeout=30)
    assert not at.exception

    dataframes_robustness = list(at.dataframe)
    robustness_strategies = set(dataframes_robustness[0].value["Strategy"])
    assert "Protective Put 90" in robustness_strategies
    assert "Protective Put 95" not in robustness_strategies


def test_live_designer_still_renders_after_navigation_added(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_live_client(monkeypatch)
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception
    assert at.sidebar.radio[0].value == "Live Designer"
    select_labels = {box.label for box in at.sidebar.selectbox}
    assert "Asset" in select_labels
