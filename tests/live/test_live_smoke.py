"""Optional, read-only live smoke test against the real Deribit production API.

Public methods only. Never authenticates, never sends an order, never
touches an account. Skipped by default -- normal unit test runs never
depend on internet availability. Opt in explicitly with:

    HEDGECANVAS_LIVE_TESTS=1 pytest -m live tests/live/test_live_smoke.py
"""

import os
from decimal import Decimal

import pytest

from hedgecanvas.live.client import DeribitClient
from hedgecanvas.live.instruments import fetch_eligible_instruments
from hedgecanvas.live.pricing import fetch_bbo, fetch_index_price

pytestmark = pytest.mark.live

_LIVE_TESTS_ENABLED = os.environ.get("HEDGECANVAS_LIVE_TESTS") == "1"

skip_reason = (
    "Live Deribit smoke test skipped by default; set HEDGECANVAS_LIVE_TESTS=1 to enable."
)


@pytest.mark.skipif(not _LIVE_TESTS_ENABLED, reason=skip_reason)
def test_live_deribit_public_smoke() -> None:
    with DeribitClient() as client:
        connectivity = client.test()
        assert connectivity is not None

        btc_result = fetch_eligible_instruments(client, "BTC")
        assert btc_result.ok, btc_result.message
        assert btc_result.value is not None
        assert len(btc_result.value) > 0, "expected at least one eligible BTC inverse option"

        eth_result = fetch_eligible_instruments(client, "ETH")
        assert eth_result.ok, eth_result.message
        assert eth_result.value is not None
        assert len(eth_result.value) > 0, "expected at least one eligible ETH inverse option"

        sample = btc_result.value[0]
        index_result = fetch_index_price(client, sample.price_index)
        assert index_result.ok, index_result.message
        assert index_result.value is not None
        assert index_result.value.index_price > Decimal(0)
        print(f"S0 ({sample.price_index}) = {index_result.value.index_price}")

        side = "put" if sample.option_type == "put" else "call"
        bbo_side = "ask" if side == "put" else "bid"
        bbo_result = fetch_bbo(client, sample, bbo_side)
        print(
            f"{sample.instrument_name} depth=1 {bbo_side}: "
            f"state={bbo_result.state.value}"
        )
        # A quote may legitimately be absent for a given contract; we only
        # assert the call completed with a structured, non-crashing result.
        assert bbo_result.state is not None
