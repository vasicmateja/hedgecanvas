"""Tests for the deterministic expiry payoff / P&L engine.

Every expected value below is hand-computed from the stated formulas, not
copied from the implementation.
"""

from decimal import Decimal

import pytest

from hedgecanvas.domain import HedgePosition, Strategy, pnl


def D(x: str) -> Decimal:
    return Decimal(x)


# ---------------------------------------------------------------------------
# Unhedged
# ---------------------------------------------------------------------------


def test_unhedged_payoff() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="2", H="0")
    # PnL = Q(ST - S0) = 2 * (35000 - 30000) = 10000
    assert pnl(pos, "35000") == D("10000")
    # Downside: 2 * (20000 - 30000) = -20000
    assert pnl(pos, "20000") == D("-20000")


def test_unhedged_st_zero() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    assert pnl(pos, "0") == D("-30000")


def test_unhedged_st_equals_s0_is_zero() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="3", H="0")
    assert pnl(pos, "30000") == D("0")


def test_unhedged_very_large_st_unbounded_upside() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    # No cap: PnL grows linearly without bound.
    assert pnl(pos, "1000000") == D("970000")


def test_negative_st_rejected() -> None:
    pos = HedgePosition(Strategy.UNHEDGED, S0="30000", Q="1", H="0")
    with pytest.raises(ValueError):
        pnl(pos, "-1")


# ---------------------------------------------------------------------------
# Protective Put
# ---------------------------------------------------------------------------


def test_protective_put_fully_hedged() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    # ST below strike: PnL = 1*(25000-30000) + 1*max(28000-25000,0) - 1*500
    #                = -5000 + 3000 - 500 = -2500
    assert pnl(pos, "25000") == D("-2500")
    # ST above strike, put worthless: 1*(35000-30000) + 0 - 500 = 4500
    assert pnl(pos, "35000") == D("4500")


def test_protective_put_partially_hedged() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="10", H="4", KP="28000", P="500"
    )
    # ST = 20000: base = 10*(20000-30000) = -100000
    # put payoff = 4*max(28000-20000,0) = 4*8000 = 32000
    # premium = 4*500 = 2000
    # total = -100000 + 32000 - 2000 = -70000
    assert pnl(pos, "20000") == D("-70000")


def test_protective_put_at_strike() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    # ST == KP: put payoff = max(28000-28000,0) = 0
    # base = 1*(28000-30000) = -2000; total = -2000 + 0 - 500 = -2500
    assert pnl(pos, "28000") == D("-2500")


def test_protective_put_unlimited_upside() -> None:
    pos = HedgePosition(
        Strategy.PROTECTIVE_PUT, S0="30000", Q="1", H="1", KP="28000", P="500"
    )
    assert pnl(pos, "10000000") == D("1") * (D("10000000") - D("30000")) - D("500")


# ---------------------------------------------------------------------------
# Covered Call
# ---------------------------------------------------------------------------


def test_covered_call_fully_covered() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="32000", C="300"
    )
    # ST above strike: base = 1*(40000-30000) = 10000
    # call payoff owed = 1*max(40000-32000,0) = 8000
    # premium received = 1*300
    # total = 10000 - 8000 + 300 = 2300
    assert pnl(pos, "40000") == D("2300")
    # ST below strike, call worthless: 1*(25000-30000) - 0 + 300 = -4700
    assert pnl(pos, "25000") == D("-4700")


def test_covered_call_partially_covered() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="10", H="4", KC="32000", C="300"
    )
    # ST = 40000: base = 10*(40000-30000) = 100000
    # call payoff owed = 4*max(40000-32000,0) = 4*8000 = 32000
    # premium received = 4*300 = 1200
    # total = 100000 - 32000 + 1200 = 69200
    assert pnl(pos, "40000") == D("69200")


def test_covered_call_at_strike() -> None:
    pos = HedgePosition(
        Strategy.COVERED_CALL, S0="30000", Q="1", H="1", KC="32000", C="300"
    )
    # base = 1*(32000-30000) = 2000; call payoff = 0; total = 2000+300=2300
    assert pnl(pos, "32000") == D("2300")


# ---------------------------------------------------------------------------
# Collar
# ---------------------------------------------------------------------------


def test_collar_fully_covered() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    # ST below KP: base = 1*(25000-30000) = -5000
    # put payoff = 1*max(28000-25000,0) = 3000
    # call payoff owed = 0
    # total = -5000 + 3000 - 500 + 300 = -2200
    assert pnl(pos, "25000") == D("-2200")

    # ST between strikes: base = 1*(30000-30000)=0, no put/call payoff
    # total = 0 - 500 + 300 = -200
    assert pnl(pos, "30000") == D("-200")

    # ST above KC: base = 1*(40000-30000)=10000
    # call payoff owed = 1*max(40000-32000,0)=8000
    # total = 10000 - 8000 - 500 + 300 = 1800
    assert pnl(pos, "40000") == D("1800")


def test_collar_partially_covered() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="10",
        H="4",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    # ST = 40000: base = 10*(40000-30000) = 100000
    # call payoff owed = 4*max(40000-32000,0) = 32000
    # put payoff = 0
    # premiums: -4*500 + 4*300 = -2000+1200 = -800
    # total = 100000 - 32000 - 800 = 67200
    assert pnl(pos, "40000") == D("67200")


def test_collar_net_credit_c_greater_than_p() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="31000",
        P="200",
        C="600",
    )
    # ST = S0 = 30000: base=0, no put/call payoff, net premium = -200+600=400
    assert pnl(pos, "30000") == D("400")


def test_collar_at_kp_and_kc() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    # ST == KP: put payoff = max(28000-28000,0)=0; base=1*(28000-30000)=-2000
    # total = -2000 + 0 - 0 - 500 + 300 = -2200
    assert pnl(pos, "28000") == D("-2200")
    # ST == KC: call payoff = max(32000-32000,0)=0; base=1*(32000-30000)=2000
    # total = 2000 - 0 - 500 + 300 = 1800
    assert pnl(pos, "32000") == D("1800")


def test_zero_premium() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="0",
        C="0",
    )
    assert pnl(pos, "30000") == D("0")
    # base = 1*(25000-30000) = -5000; put payoff = max(28000-25000,0) = 3000
    # no premiums: total = -5000 + 3000 = -2000
    assert pnl(pos, "25000") == D("-2000")


def test_st_zero_collar() -> None:
    pos = HedgePosition(
        Strategy.COLLAR,
        S0="30000",
        Q="1",
        H="1",
        KP="28000",
        KC="32000",
        P="500",
        C="300",
    )
    # base = 1*(0-30000) = -30000; put payoff = 28000; total = -30000+28000-500+300 = -2200
    assert pnl(pos, "0") == D("-2200")
