"""Tests for expiry/strike filtering over already-discovered instruments."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from hedgecanvas.live import InverseOptionInstrument
from hedgecanvas.ui.instrument_select import (
    call_strikes_at_or_above,
    expiries_for_collar,
    expiries_for_covered_call,
    expiries_for_protective_put,
    instrument_by_strike,
    strikes_for_expiry,
)

EXP_1 = 1735286400000
EXP_2 = 1738000000000


def _instrument(
    *, asset: str, option_type: str, strike: str, expiration_timestamp: int, min_trade_amount: str = "0.1"
) -> InverseOptionInstrument:
    suffix = "P" if option_type == "put" else "C"
    return InverseOptionInstrument(
        instrument_name=f"{asset}-EXP-{strike}-{suffix}",
        asset=asset,
        expiration_timestamp=expiration_timestamp,
        expiry=datetime.fromtimestamp(expiration_timestamp / 1000, tz=timezone.utc),
        strike=Decimal(strike),
        option_type=option_type,
        contract_size=Decimal(1),
        min_trade_amount=Decimal(min_trade_amount),
        tick_size=Decimal("0.0001"),
        tick_size_steps=None,
        price_index=f"{asset.lower()}_usd",
        quote_currency=asset,
        base_currency=asset,
        settlement_currency=asset,
        counter_currency="USD",
        instrument_type="reversed",
        state="open",
        is_active=True,
    )


@pytest.fixture
def mixed_instruments():
    return [
        _instrument(asset="BTC", option_type="put", strike="55000", expiration_timestamp=EXP_1),
        _instrument(asset="BTC", option_type="put", strike="50000", expiration_timestamp=EXP_1),
        _instrument(asset="BTC", option_type="call", strike="65000", expiration_timestamp=EXP_1),
        _instrument(asset="BTC", option_type="call", strike="70000", expiration_timestamp=EXP_1),
        # EXP_2 has a put but no call -> ineligible for Collar/Covered Call.
        _instrument(asset="BTC", option_type="put", strike="52000", expiration_timestamp=EXP_2),
    ]


def test_expiry_filtering_protective_put(mixed_instruments) -> None:
    assert expiries_for_protective_put(mixed_instruments) == [EXP_1, EXP_2]


def test_expiry_filtering_covered_call(mixed_instruments) -> None:
    assert expiries_for_covered_call(mixed_instruments) == [EXP_1]


def test_expiry_filtering_collar_requires_both_legs(mixed_instruments) -> None:
    assert expiries_for_collar(mixed_instruments) == [EXP_1]


def test_strikes_for_expiry_sorted(mixed_instruments) -> None:
    puts = [i for i in mixed_instruments if i.option_type == "put" and i.expiration_timestamp == EXP_1]
    assert strikes_for_expiry(puts, EXP_1) == [Decimal("50000"), Decimal("55000")]


def test_call_strikes_restricted_to_kp_or_above(mixed_instruments) -> None:
    calls = [i for i in mixed_instruments if i.option_type == "call"]
    restricted = call_strikes_at_or_above(calls, EXP_1, Decimal("66000"))
    assert restricted == [Decimal("70000")]

    restricted_all = call_strikes_at_or_above(calls, EXP_1, Decimal("50000"))
    assert restricted_all == [Decimal("65000"), Decimal("70000")]


def test_call_strikes_restriction_excludes_below_kp(mixed_instruments) -> None:
    calls = [i for i in mixed_instruments if i.option_type == "call"]
    restricted = call_strikes_at_or_above(calls, EXP_1, Decimal("70000"))
    assert Decimal("65000") not in restricted
    assert restricted == [Decimal("70000")]


def test_instrument_by_strike_lookup(mixed_instruments) -> None:
    found = instrument_by_strike(mixed_instruments, EXP_1, Decimal("55000"))
    assert found.option_type == "put"
    assert found.strike == Decimal("55000")


def test_instrument_by_strike_missing_raises(mixed_instruments) -> None:
    with pytest.raises(KeyError):
        instrument_by_strike(mixed_instruments, EXP_1, Decimal("999999"))
