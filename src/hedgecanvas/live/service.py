"""Orchestration: build structured live-market inputs for the Phase 1 domain model.

This module never computes a payoff. Its only job is to turn live Deribit
data (an already-selected inverse option instrument, or a put/call pair)
into the exact (S0, Q, H, KP, KC, P, C) inputs that
:class:`hedgecanvas.domain.HedgePosition` expects, plus the raw market
context needed for a UI or audit trail. The Phase 1 domain engine remains
the only payoff/analysis authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from hedgecanvas.domain import HedgePosition, Strategy
from hedgecanvas.live.client import DeribitClient
from hedgecanvas.live.instruments import InverseOptionInstrument
from hedgecanvas.live.pricing import IndexSnapshot, NativeQuote, fetch_bbo, fetch_index_price
from hedgecanvas.live.sizing import normalize_amount
from hedgecanvas.live.states import MarketState


@dataclass(frozen=True)
class LiveHedgeQuote:
    """Structured outcome of building live-market inputs for a hedge position.

    On success (``state is MarketState.OK``) every field required to build
    a Phase 1 :class:`HedgePosition` is populated, alongside the raw market
    context (index snapshot, instruments, native quotes) for transparency.
    This remains an *indicative* live market-based hedge, not a guaranteed
    executable one.
    """

    state: MarketState
    message: Optional[str] = None

    strategy: Optional[Strategy] = None
    S0: Optional[Decimal] = None
    Q: Optional[Decimal] = None
    H: Optional[Decimal] = None
    KP: Optional[Decimal] = None
    KC: Optional[Decimal] = None
    P: Optional[Decimal] = None
    C: Optional[Decimal] = None

    index_snapshot: Optional[IndexSnapshot] = None
    put_instrument: Optional[InverseOptionInstrument] = None
    call_instrument: Optional[InverseOptionInstrument] = None
    put_quote: Optional[NativeQuote] = None
    call_quote: Optional[NativeQuote] = None

    @property
    def ok(self) -> bool:
        return self.state is MarketState.OK

    def to_hedge_position(self) -> HedgePosition:
        """Build the Phase 1 domain HedgePosition. Raises if state != OK."""
        if not self.ok:
            raise ValueError(f"Cannot build HedgePosition from state {self.state}")
        assert self.strategy is not None and self.S0 is not None
        assert self.Q is not None and self.H is not None
        return HedgePosition(
            strategy=self.strategy,
            S0=self.S0,
            Q=self.Q,
            H=self.H,
            KP=self.KP,
            KC=self.KC,
            P=self.P if self.P is not None else Decimal(0),
            C=self.C if self.C is not None else Decimal(0),
        )


def _fail(state: MarketState, message: str) -> LiveHedgeQuote:
    return LiveHedgeQuote(state=state, message=message)


def build_protective_put_quote(
    client: DeribitClient, put_instrument: InverseOptionInstrument, Q: Decimal
) -> LiveHedgeQuote:
    """Build live inputs for a Protective Put: long put at its best ASK."""
    if put_instrument.option_type != "put":
        return _fail(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"{put_instrument.instrument_name} is not a put",
        )

    index_result = fetch_index_price(client, put_instrument.price_index)
    if not index_result.ok:
        return _fail(index_result.state, index_result.message or "index price unavailable")
    assert index_result.value is not None
    index_snapshot = index_result.value
    S0 = index_snapshot.index_price

    sizing_result = normalize_amount(Q, put_instrument.min_trade_amount)
    assert sizing_result.value is not None
    H = sizing_result.value.H
    if sizing_result.state is MarketState.BELOW_MINIMUM_SIZE:
        return LiveHedgeQuote(
            state=MarketState.BELOW_MINIMUM_SIZE,
            message=sizing_result.message,
            strategy=Strategy.PROTECTIVE_PUT,
            S0=S0,
            Q=Q,
            H=Decimal(0),
            KP=put_instrument.strike,
            index_snapshot=index_snapshot,
            put_instrument=put_instrument,
        )
    if not sizing_result.ok:
        return _fail(sizing_result.state, sizing_result.message or "sizing failed")

    quote_result = fetch_bbo(client, put_instrument, "ask")
    if not quote_result.ok:
        return _fail(quote_result.state, quote_result.message or "no ask quote")
    assert quote_result.value is not None
    put_quote = quote_result.value

    if put_quote.best_quote_amount < H:
        return LiveHedgeQuote(
            state=MarketState.INSUFFICIENT_BBO_DEPTH,
            message=(
                f"best ask amount {put_quote.best_quote_amount} < required H={H}"
            ),
            strategy=Strategy.PROTECTIVE_PUT,
            S0=S0,
            Q=Q,
            H=H,
            KP=put_instrument.strike,
            index_snapshot=index_snapshot,
            put_instrument=put_instrument,
            put_quote=put_quote,
        )

    P = put_quote.premium_native * S0

    return LiveHedgeQuote(
        state=MarketState.OK,
        strategy=Strategy.PROTECTIVE_PUT,
        S0=S0,
        Q=Q,
        H=H,
        KP=put_instrument.strike,
        P=P,
        index_snapshot=index_snapshot,
        put_instrument=put_instrument,
        put_quote=put_quote,
    )


def build_covered_call_quote(
    client: DeribitClient, call_instrument: InverseOptionInstrument, Q: Decimal
) -> LiveHedgeQuote:
    """Build live inputs for a Covered Call: written call at its best BID."""
    if call_instrument.option_type != "call":
        return _fail(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"{call_instrument.instrument_name} is not a call",
        )

    index_result = fetch_index_price(client, call_instrument.price_index)
    if not index_result.ok:
        return _fail(index_result.state, index_result.message or "index price unavailable")
    assert index_result.value is not None
    index_snapshot = index_result.value
    S0 = index_snapshot.index_price

    sizing_result = normalize_amount(Q, call_instrument.min_trade_amount)
    assert sizing_result.value is not None
    H = sizing_result.value.H
    if sizing_result.state is MarketState.BELOW_MINIMUM_SIZE:
        return LiveHedgeQuote(
            state=MarketState.BELOW_MINIMUM_SIZE,
            message=sizing_result.message,
            strategy=Strategy.COVERED_CALL,
            S0=S0,
            Q=Q,
            H=Decimal(0),
            KC=call_instrument.strike,
            index_snapshot=index_snapshot,
            call_instrument=call_instrument,
        )
    if not sizing_result.ok:
        return _fail(sizing_result.state, sizing_result.message or "sizing failed")

    quote_result = fetch_bbo(client, call_instrument, "bid")
    if not quote_result.ok:
        return _fail(quote_result.state, quote_result.message or "no bid quote")
    assert quote_result.value is not None
    call_quote = quote_result.value

    if call_quote.best_quote_amount < H:
        return LiveHedgeQuote(
            state=MarketState.INSUFFICIENT_BBO_DEPTH,
            message=(
                f"best bid amount {call_quote.best_quote_amount} < required H={H}"
            ),
            strategy=Strategy.COVERED_CALL,
            S0=S0,
            Q=Q,
            H=H,
            KC=call_instrument.strike,
            index_snapshot=index_snapshot,
            call_instrument=call_instrument,
            call_quote=call_quote,
        )

    C = call_quote.premium_native * S0

    return LiveHedgeQuote(
        state=MarketState.OK,
        strategy=Strategy.COVERED_CALL,
        S0=S0,
        Q=Q,
        H=H,
        KC=call_instrument.strike,
        C=C,
        index_snapshot=index_snapshot,
        call_instrument=call_instrument,
        call_quote=call_quote,
    )


def build_collar_quote(
    client: DeribitClient,
    put_instrument: InverseOptionInstrument,
    call_instrument: InverseOptionInstrument,
    Q: Decimal,
) -> LiveHedgeQuote:
    """Build live inputs for a Collar: long put at ASK, short call at BID.

    Both legs use the SAME S0 index snapshot and the SAME hedged quantity H.
    """
    if put_instrument.option_type != "put":
        return _fail(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"{put_instrument.instrument_name} is not a put",
        )
    if call_instrument.option_type != "call":
        return _fail(
            MarketState.UNSUPPORTED_INSTRUMENT,
            f"{call_instrument.instrument_name} is not a call",
        )
    if put_instrument.asset != call_instrument.asset:
        return _fail(
            MarketState.INCONSISTENT_METADATA,
            "put and call legs are not the same asset",
        )
    if put_instrument.expiration_timestamp != call_instrument.expiration_timestamp:
        return _fail(
            MarketState.INCONSISTENT_METADATA,
            "put and call legs do not share the same expiry",
        )
    if put_instrument.strike > call_instrument.strike:
        return _fail(MarketState.INCONSISTENT_METADATA, "KP > KC for Collar legs")
    if put_instrument.min_trade_amount != call_instrument.min_trade_amount:
        return _fail(
            MarketState.INCONSISTENT_METADATA,
            "put and call legs have incompatible amount granularity",
        )

    index_result = fetch_index_price(client, put_instrument.price_index)
    if not index_result.ok:
        return _fail(index_result.state, index_result.message or "index price unavailable")
    assert index_result.value is not None
    index_snapshot = index_result.value
    S0 = index_snapshot.index_price

    sizing_result = normalize_amount(Q, put_instrument.min_trade_amount)
    assert sizing_result.value is not None
    H = sizing_result.value.H
    if sizing_result.state is MarketState.BELOW_MINIMUM_SIZE:
        return LiveHedgeQuote(
            state=MarketState.BELOW_MINIMUM_SIZE,
            message=sizing_result.message,
            strategy=Strategy.COLLAR,
            S0=S0,
            Q=Q,
            H=Decimal(0),
            KP=put_instrument.strike,
            KC=call_instrument.strike,
            index_snapshot=index_snapshot,
            put_instrument=put_instrument,
            call_instrument=call_instrument,
        )
    if not sizing_result.ok:
        return _fail(sizing_result.state, sizing_result.message or "sizing failed")

    put_quote_result = fetch_bbo(client, put_instrument, "ask")
    if not put_quote_result.ok:
        return _fail(put_quote_result.state, put_quote_result.message or "no put ask quote")
    assert put_quote_result.value is not None
    put_quote = put_quote_result.value

    call_quote_result = fetch_bbo(client, call_instrument, "bid")
    if not call_quote_result.ok:
        return _fail(call_quote_result.state, call_quote_result.message or "no call bid quote")
    assert call_quote_result.value is not None
    call_quote = call_quote_result.value

    if put_quote.best_quote_amount < H:
        return LiveHedgeQuote(
            state=MarketState.INSUFFICIENT_BBO_DEPTH,
            message=f"put best ask amount {put_quote.best_quote_amount} < required H={H}",
            strategy=Strategy.COLLAR,
            S0=S0,
            Q=Q,
            H=H,
            KP=put_instrument.strike,
            KC=call_instrument.strike,
            index_snapshot=index_snapshot,
            put_instrument=put_instrument,
            call_instrument=call_instrument,
            put_quote=put_quote,
            call_quote=call_quote,
        )
    if call_quote.best_quote_amount < H:
        return LiveHedgeQuote(
            state=MarketState.INSUFFICIENT_BBO_DEPTH,
            message=f"call best bid amount {call_quote.best_quote_amount} < required H={H}",
            strategy=Strategy.COLLAR,
            S0=S0,
            Q=Q,
            H=H,
            KP=put_instrument.strike,
            KC=call_instrument.strike,
            index_snapshot=index_snapshot,
            put_instrument=put_instrument,
            call_instrument=call_instrument,
            put_quote=put_quote,
            call_quote=call_quote,
        )

    P = put_quote.premium_native * S0
    C = call_quote.premium_native * S0

    return LiveHedgeQuote(
        state=MarketState.OK,
        strategy=Strategy.COLLAR,
        S0=S0,
        Q=Q,
        H=H,
        KP=put_instrument.strike,
        KC=call_instrument.strike,
        P=P,
        C=C,
        index_snapshot=index_snapshot,
        put_instrument=put_instrument,
        call_instrument=call_instrument,
        put_quote=put_quote,
        call_quote=call_quote,
    )
