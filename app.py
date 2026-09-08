"""HedgeCanvas -- Crypto Portfolio Protection Analytics.

The live Streamlit product layer (Phase 3). Wires the Phase 1 deterministic
domain engine to the Phase 2 Deribit public-market adapter to build an
"Indicative live market-based hedge" for a BTC or ETH portfolio.

Run with:

    streamlit run app.py

No payoff, coverage, or boundary-scope mathematics is implemented in this
file -- see hedgecanvas.domain for that. This file only wires live data,
user selections, and presentation together.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import streamlit as st

from hedgecanvas.domain import BoundaryScope, HedgePosition, Strategy, analyze
from hedgecanvas.live import (
    DeribitClient,
    EXPECTED_PRICE_INDEX,
    InverseOptionInstrument,
    MarketState,
    build_collar_quote,
    build_covered_call_quote,
    build_protective_put_quote,
    fetch_eligible_instruments,
    fetch_index_price,
)
from hedgecanvas.live.service import LiveHedgeQuote
from hedgecanvas.ui.chart import build_payoff_figure
from hedgecanvas.ui.formatting import format_quantity, format_usd, parse_decimal_input
from hedgecanvas.ui.instrument_select import (
    call_strikes_at_or_above,
    calls_only,
    expiries_for_collar,
    expiries_for_covered_call,
    expiries_for_protective_put,
    instrument_by_strike,
    puts_only,
    strikes_for_expiry,
)
from hedgecanvas.ui.market_messages import describe_market_state
from hedgecanvas.ui.portfolio import PortfolioInputMode, quantity_from_portfolio_value
from hedgecanvas.ui.scenario import build_scenario_grid
from hedgecanvas.ui.state import (
    compute_request_key,
    get_snapshot_for_key,
    invalidate_for_asset_change,
    store_snapshot,
)
from hedgecanvas.ui.view_models import (
    format_breakeven,
    format_coverage_state,
    format_max_loss,
    format_max_profit,
    format_net_option_cost,
    format_protection_floor,
    format_upside_cap,
)

ASSETS = ("BTC", "ETH")
INSTRUMENT_CACHE_TTL_SECONDS = 60


# ---------------------------------------------------------------------------
# Live client + cached discovery (short TTL only -- see README caching notes)
# ---------------------------------------------------------------------------


@st.cache_resource
def get_client() -> DeribitClient:
    return DeribitClient()


@st.cache_data(ttl=INSTRUMENT_CACHE_TTL_SECONDS)
def _cached_eligible_instruments(_client: DeribitClient, asset: str):
    result = fetch_eligible_instruments(_client, asset)
    return result.state, result.value, result.message


def get_eligible_instruments(client: DeribitClient, asset: str):
    state, value, message = _cached_eligible_instruments(client, asset)
    return state, value, message


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="HedgeCanvas", layout="wide", page_icon="\U0001F6E1")

st.markdown(
    """
    <style>
    .hc-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        background: rgba(0, 200, 150, 0.15);
        color: #00c896;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        border: 1px solid rgba(0, 200, 150, 0.35);
    }
    .hc-subtitle { color: #8a94a6; margin-top: -0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

header_left, header_right = st.columns([3, 2])
with header_left:
    st.title("HedgeCanvas")
    st.markdown(
        '<div class="hc-subtitle">Crypto Portfolio Protection Analytics</div>',
        unsafe_allow_html=True,
    )
with header_right:
    st.markdown(
        '<div style="text-align:right; padding-top: 1.1rem;">'
        '<span class="hc-badge">Indicative live market-based hedge</span></div>',
        unsafe_allow_html=True,
    )

with st.expander("Market-data disclaimer", expanded=False):
    st.markdown(
        "- Quotes shown are public Deribit top-of-book observations. They do not guarantee execution.\n"
        "- Actual execution price may differ; displayed BBO depth is limited to the validation implemented here.\n"
        "- HedgeCanvas does not verify account eligibility, balances, permissions, regional availability, or execution.\n"
        "- No trade is placed and no account is accessed.\n"
        "- The payoff chart is deterministic expiry scenario analysis. Hypothetical terminal prices (ST) are "
        "scenario inputs, not a forecast, and carry no probability interpretation.\n"
        "- HedgeCanvas is not a brokerage or trading platform."
    )

client = get_client()

# ---------------------------------------------------------------------------
# Sidebar: portfolio + strategy + contract controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Controls")

    asset = st.selectbox("Asset", ASSETS, key="asset_select")
    asset_changed = invalidate_for_asset_change(st.session_state, asset)
    if asset_changed:
        st.session_state.pop("expiry_select", None)
        st.session_state.pop("put_strike_select", None)
        st.session_state.pop("call_strike_select", None)

    st.divider()
    st.subheader("Portfolio")

    input_mode_label = st.radio(
        "Position input",
        ("Underlying Quantity", "Portfolio Value (USD)"),
        key="portfolio_input_mode",
    )
    input_mode = (
        PortfolioInputMode.UNDERLYING_QUANTITY
        if input_mode_label == "Underlying Quantity"
        else PortfolioInputMode.PORTFOLIO_VALUE_USD
    )

    if input_mode is PortfolioInputMode.UNDERLYING_QUANTITY:
        quantity_raw = st.text_input(f"{asset} quantity", value="1.0", key="quantity_input")
    else:
        value_raw = st.text_input("Portfolio value (USD)", value="50000", key="value_input")

    st.divider()
    st.subheader("Strategy")
    strategy_label = st.selectbox(
        "Strategy",
        ("Unhedged", "Protective Put", "Covered Call", "Collar"),
        key="strategy_select",
    )
    strategy_map = {
        "Unhedged": Strategy.UNHEDGED,
        "Protective Put": Strategy.PROTECTIVE_PUT,
        "Covered Call": Strategy.COVERED_CALL,
        "Collar": Strategy.COLLAR,
    }
    strategy = strategy_map[strategy_label]

    needs_put = strategy in (Strategy.PROTECTIVE_PUT, Strategy.COLLAR)
    needs_call = strategy in (Strategy.COVERED_CALL, Strategy.COLLAR)

# ---------------------------------------------------------------------------
# S0: current Deribit index price for the selected asset
# ---------------------------------------------------------------------------

price_index_name = EXPECTED_PRICE_INDEX[asset]
index_result = fetch_index_price(client, price_index_name)

st.markdown("---")
status_col, s0_col, q_col, value_col = st.columns(4)

if not index_result.ok:
    display = describe_market_state(index_result.state)
    with status_col:
        st.error(f"Index price unavailable: {display.message}")
    st.stop()

S0 = index_result.value.index_price
with status_col:
    st.metric("Market status", "Live")
with s0_col:
    st.metric(f"Current {asset}/USD Index (S0)", format_usd(S0))
    st.caption(f"Source: {price_index_name} · {index_result.value.retrieved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# -- resolve Q from the chosen input mode -----------------------------------

Q: Optional[Decimal] = None
input_error: Optional[str] = None

if input_mode is PortfolioInputMode.UNDERLYING_QUANTITY:
    Q = parse_decimal_input(quantity_raw)
    if Q is None or Q <= 0:
        input_error = f"Enter a valid positive {asset} quantity."
else:
    portfolio_value = parse_decimal_input(value_raw)
    if portfolio_value is None or portfolio_value <= 0:
        input_error = "Enter a valid positive portfolio value in USD."
    else:
        Q = quantity_from_portfolio_value(portfolio_value, S0)

if input_error:
    st.warning(input_error)
    st.stop()

assert Q is not None
with q_col:
    st.metric(f"Underlying Quantity (Q)", f"{format_quantity(Q)} {asset}")
with value_col:
    st.metric("Current Portfolio Value", format_usd(Q * S0))

# ---------------------------------------------------------------------------
# Instrument discovery (only if the strategy needs options)
# ---------------------------------------------------------------------------

instruments: List[InverseOptionInstrument] = []
if needs_put or needs_call:
    disc_state, disc_value, disc_message = get_eligible_instruments(client, asset)
    if disc_state is not MarketState.OK:
        display = describe_market_state(disc_state)
        getattr(st, display.severity)(f"Instrument discovery: {display.message}")
        st.stop()
    instruments = disc_value or []

put_instruments = puts_only(instruments)
call_instruments = calls_only(instruments)

# ---------------------------------------------------------------------------
# Expiry / strike selection (per strategy)
# ---------------------------------------------------------------------------

expiration_timestamp: Optional[int] = None
put_strike: Optional[Decimal] = None
call_strike: Optional[Decimal] = None
put_instrument: Optional[InverseOptionInstrument] = None
call_instrument: Optional[InverseOptionInstrument] = None

with st.sidebar:
    if needs_put and needs_call:
        eligible_expiries = expiries_for_collar(instruments)
    elif needs_put:
        eligible_expiries = expiries_for_protective_put(put_instruments)
    elif needs_call:
        eligible_expiries = expiries_for_covered_call(call_instruments)
    else:
        eligible_expiries = []

    if strategy is not Strategy.UNHEDGED:
        st.divider()
        st.subheader("Contract")
        if not eligible_expiries:
            st.warning("No eligible current expiries found for this strategy right now.")
            st.stop()

        expiry_labels = {
            ts: datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            for ts in eligible_expiries
        }
        expiration_timestamp = st.selectbox(
            "Expiry",
            eligible_expiries,
            format_func=lambda ts: expiry_labels[ts],
            key="expiry_select",
        )

        if needs_put:
            put_strikes = strikes_for_expiry(put_instruments, expiration_timestamp)
            if not put_strikes:
                st.warning("No eligible put strikes for this expiry.")
                st.stop()
            put_strike = st.selectbox(
                "Put strike (KP)",
                put_strikes,
                format_func=lambda k: format_usd(k),
                key="put_strike_select",
            )
            put_instrument = instrument_by_strike(put_instruments, expiration_timestamp, put_strike)

        if needs_call:
            if needs_put:
                call_strikes = call_strikes_at_or_above(
                    call_instruments, expiration_timestamp, put_strike
                )
                helper_text = "Restricted to KC >= KP."
            else:
                call_strikes = strikes_for_expiry(call_instruments, expiration_timestamp)
                helper_text = None
            if not call_strikes:
                st.warning("No eligible call strikes at or above KP for this expiry.")
                st.stop()
            call_strike = st.selectbox(
                "Call strike (KC)",
                call_strikes,
                format_func=lambda k: format_usd(k),
                key="call_strike_select",
                help=helper_text,
            )
            call_instrument = instrument_by_strike(call_instruments, expiration_timestamp, call_strike)

    refresh_clicked = False
    if strategy is not Strategy.UNHEDGED:
        refresh_clicked = st.button("Refresh quote", use_container_width=True)

# ---------------------------------------------------------------------------
# Build the position: Unhedged directly, others via Phase 2 live service
# ---------------------------------------------------------------------------

position: Optional[HedgePosition] = None
quote: Optional[LiveHedgeQuote] = None

if strategy is Strategy.UNHEDGED:
    position = HedgePosition(strategy=Strategy.UNHEDGED, S0=S0, Q=Q, H=Decimal(0))
else:
    request_key = compute_request_key(
        asset, strategy.value, expiration_timestamp, put_strike, call_strike, Q
    )
    cached = None if refresh_clicked else get_snapshot_for_key(st.session_state, request_key)

    if cached is not None:
        quote = cached.value
    else:
        if strategy is Strategy.PROTECTIVE_PUT:
            assert put_instrument is not None
            quote = build_protective_put_quote(client, put_instrument, Q)
        elif strategy is Strategy.COVERED_CALL:
            assert call_instrument is not None
            quote = build_covered_call_quote(client, call_instrument, Q)
        else:
            assert put_instrument is not None and call_instrument is not None
            quote = build_collar_quote(client, put_instrument, call_instrument, Q)
        store_snapshot(st.session_state, request_key, quote)

    if quote.state is not MarketState.OK and quote.state is not MarketState.BELOW_MINIMUM_SIZE:
        display = describe_market_state(quote.state)
        getattr(st, display.severity)(f"Live quote: {display.message}")
        if quote.message:
            with st.expander("Technical details"):
                st.code(quote.message)
    elif quote.state is MarketState.BELOW_MINIMUM_SIZE:
        display = describe_market_state(quote.state)
        st.warning(display.message)

    if quote.ok:
        position = quote.to_hedge_position()
    elif quote.state is MarketState.BELOW_MINIMUM_SIZE and quote.S0 is not None:
        # H = 0: still show the unhedged-equivalent picture with a clear notice.
        position = HedgePosition(strategy=Strategy.UNHEDGED, S0=quote.S0, Q=Q, H=Decimal(0))

if position is None:
    st.info("No live hedge could be constructed for the current selection.")
    st.stop()

# ---------------------------------------------------------------------------
# Main content: chart + metrics (left/center) -- controls already in sidebar
# ---------------------------------------------------------------------------

result = analyze(position)

chart_col, metrics_col = st.columns([3, 2])

with chart_col:
    st.subheader("Protected Strategy vs Unhedged Portfolio")
    strikes = [k for k in (position.KP, position.KC) if k is not None]
    grid = build_scenario_grid(S0, strikes)
    fig = build_payoff_figure(position, grid)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "The payoff chart shows deterministic portfolio P&L at option expiry for hypothetical "
        "terminal prices. Terminal price ST is a scenario input, not a forecast."
    )

with metrics_col:
    st.subheader("Strategy metrics")
    m1, m2 = st.columns(2)
    m1.metric("Max Profit", format_max_profit(result.max_profit))
    m2.metric("Max Loss", format_max_loss(result.max_loss))
    m3, m4 = st.columns(2)
    m3.metric("Breakeven", format_breakeven(result.breakeven))
    m4.metric("Net Option Cost / Credit", format_net_option_cost(position))

    floor_text = format_protection_floor(position, result.protection_floor_scope)
    cap_text = format_upside_cap(position, result.upside_cap_scope)
    if floor_text:
        st.markdown(f"**Protection floor:** {floor_text}")
    if cap_text:
        st.markdown(f"**Upside cap:** {cap_text}")

    st.divider()
    st.subheader("Hedge coverage")
    c1, c2, c3 = st.columns(3)
    c1.metric("Underlying Qty (Q)", f"{format_quantity(position.Q)} {asset}")
    c2.metric("Hedged Qty (H)", f"{format_quantity(position.H)} {asset}")
    c3.metric("Residual (Q-H)", f"{format_quantity(position.unhedged_residual_quantity)} {asset}")
    st.markdown(
        f"**Coverage:** {format_coverage_state(position.coverage_state)} "
        f"({position.coverage_percentage:.2f}%)"
    )

# ---------------------------------------------------------------------------
# Quote details
# ---------------------------------------------------------------------------

if quote is not None and (quote.put_quote is not None or quote.call_quote is not None):
    st.subheader("Quote details")

    def _render_leg(label: str, instrument: InverseOptionInstrument, q) -> None:
        st.markdown(f"**{label}: {instrument.instrument_name}**")
        cols = st.columns(4)
        cols[0].markdown(f"Expiry\n\n{instrument.expiry.strftime('%Y-%m-%d %H:%M UTC')}")
        cols[1].markdown(f"Strike / Type\n\n{format_usd(instrument.strike)} {instrument.option_type.upper()}")
        cols[2].markdown(f"Quote side\n\n{q.quote_side.upper()}")
        cols[3].markdown(f"BBO amount\n\n{format_quantity(q.best_quote_amount)} {q.premium_currency}")
        cols2 = st.columns(2)
        cols2[0].markdown(f"Native premium ({q.premium_currency})\n\n{q.premium_native}")
        usd_equiv = q.premium_native * position.S0
        cols2[1].markdown(f"Inception USD-equivalent\n\n{format_usd(usd_equiv)}")
        st.caption(
            "Deribit inverse option premium is native "
            f"{q.premium_currency}; the USD value is the inception-equivalent, normalized using S0."
        )

    if quote.put_quote is not None and quote.put_instrument is not None:
        _render_leg("Put leg", quote.put_instrument, quote.put_quote)
    if quote.call_quote is not None and quote.call_instrument is not None:
        _render_leg("Call leg", quote.call_instrument, quote.call_quote)

# ---------------------------------------------------------------------------
# Historical Evidence placeholder (non-functional, Phase 4+)
# ---------------------------------------------------------------------------

st.divider()
st.caption("Historical Evidence -- available in a later phase.")
