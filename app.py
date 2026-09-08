"""HedgeCanvas -- Crypto Portfolio Protection Analytics.

The HedgeCanvas Streamlit product. Two hard-separated data paths:

- Live Designer (Phase 3): Phase 1 domain engine + Phase 2 Deribit public
  live adapter -> an "Indicative live market-based hedge" for a BTC/ETH
  portfolio, using currently observable market data.
- Historical Evidence (Phase 4): a strictly read-only view over two frozen
  canonical thesis backtest artifacts, fail-closed verified before any
  value is displayed. It never calls the live Deribit API, and the Live
  Designer never reads the historical artifacts.

Run with:

    streamlit run app.py

No payoff, coverage, or boundary-scope mathematics is implemented in this
file -- see hedgecanvas.domain for that. No backtest recomputation or
wealth-path reconstruction is implemented here either -- see
hedgecanvas.historical, which only validates and reads stored values.
This file only wires data, user selections, and presentation together.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import streamlit as st

from hedgecanvas.domain import BoundaryScope, HedgePosition, Strategy, analyze
from hedgecanvas.historical import (
    CANONICAL_ASSETS,
    HISTORICAL_DIR_ENV_VAR,
    HistoricalEvidence,
    HistoricalView,
    filter_metrics,
    load_historical_evidence,
    resolve_historical_dir,
)
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
from hedgecanvas.ui.historical_chart import build_wealth_path_figure
from hedgecanvas.ui.historical_messages import describe_historical_state
from hedgecanvas.ui.historical_view_models import build_metrics_table
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
    is_max_profit_negative,
    max_profit_metric_label,
)

ASSETS = ("BTC", "ETH")
INSTRUMENT_CACHE_TTL_SECONDS = 60

PAGE_CSS = """
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
.hc-badge-warn {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    background: rgba(226, 185, 59, 0.15);
    color: #e2b93b;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid rgba(226, 185, 59, 0.35);
}
.hc-subtitle { color: #8a94a6; margin-top: -0.6rem; }
</style>
"""


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
    return _cached_eligible_instruments(client, asset)


# ---------------------------------------------------------------------------
# Historical evidence loading (frozen local files only -- no network)
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _cached_historical_evidence(directory_str: str) -> HistoricalEvidence:
    return load_historical_evidence(Path(directory_str))


def get_historical_evidence() -> HistoricalEvidence:
    resolved_dir = resolve_historical_dir()
    return _cached_historical_evidence(str(resolved_dir))


# ---------------------------------------------------------------------------
# Live Designer (Phase 3)
# ---------------------------------------------------------------------------


def render_live_designer() -> None:
    client = get_client()

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

    # -- Sidebar: portfolio + strategy + contract controls -------------------

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

    # -- S0: current Deribit index price for the selected asset --------------

    price_index_name = EXPECTED_PRICE_INDEX[asset]
    with st.spinner(f"Fetching current {asset}/USD index price..."):
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
        st.caption(
            f"Source: {price_index_name} · "
            f"{index_result.value.retrieved_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

    # -- resolve Q from the chosen input mode ---------------------------------

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
        st.metric("Underlying Quantity (Q)", f"{format_quantity(Q)} {asset}")
    with value_col:
        st.metric("Current Portfolio Value", format_usd(Q * S0))

    # -- Instrument discovery (only if the strategy needs options) -----------

    instruments: List[InverseOptionInstrument] = []
    if needs_put or needs_call:
        with st.spinner(f"Loading eligible {asset} contracts..."):
            disc_state, disc_value, disc_message = get_eligible_instruments(client, asset)
        if disc_state is not MarketState.OK:
            display = describe_market_state(disc_state)
            getattr(st, display.severity)(f"Instrument discovery: {display.message}")
            st.stop()
        instruments = disc_value or []

    put_instruments = puts_only(instruments)
    call_instruments = calls_only(instruments)

    # -- Expiry / strike selection (per strategy) -----------------------------

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

    # -- Build the position: Unhedged directly, others via Phase 2 service ---

    position: Optional[HedgePosition] = None
    quote: Optional[LiveHedgeQuote] = None
    quote_fetched_at: Optional[datetime] = None

    if strategy is Strategy.UNHEDGED:
        position = HedgePosition(strategy=Strategy.UNHEDGED, S0=S0, Q=Q, H=Decimal(0))
    else:
        request_key = compute_request_key(
            asset, strategy.value, expiration_timestamp, put_strike, call_strike, Q
        )
        cached = None if refresh_clicked else get_snapshot_for_key(st.session_state, request_key)

        if cached is not None:
            quote = cached.value
            quote_fetched_at = cached.fetched_at
        else:
            with st.spinner("Fetching live quote..."):
                if strategy is Strategy.PROTECTIVE_PUT:
                    assert put_instrument is not None
                    quote = build_protective_put_quote(client, put_instrument, Q)
                elif strategy is Strategy.COVERED_CALL:
                    assert call_instrument is not None
                    quote = build_covered_call_quote(client, call_instrument, Q)
                else:
                    assert put_instrument is not None and call_instrument is not None
                    quote = build_collar_quote(client, put_instrument, call_instrument, Q)
            snapshot = store_snapshot(st.session_state, request_key, quote)
            quote_fetched_at = snapshot.fetched_at

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

    hedge_not_constructed = (
        quote is not None and quote.state is MarketState.BELOW_MINIMUM_SIZE
    )

    # -- Main content: chart + metrics ----------------------------------------

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
        if hedge_not_constructed:
            st.info(
                "Position size is below the current minimum tradable option size, so no option "
                "overlay could be constructed (H = 0). The metrics and chart below reflect the "
                "unhedged underlying position only."
            )
        m1, m2 = st.columns(2)
        m1.metric(max_profit_metric_label(result.max_profit), format_max_profit(result.max_profit))
        m2.metric("Max Loss", format_max_loss(result.max_loss))
        if is_max_profit_negative(result.max_profit):
            st.caption(
                "Max Profit is negative: even the best-case terminal price for this strategy at the "
                "selected strikes results in a net loss."
            )
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

    # -- Quote details ---------------------------------------------------------

    if quote is not None and (quote.put_quote is not None or quote.call_quote is not None):
        st.subheader("Quote details")
        if quote_fetched_at is not None:
            st.caption(
                f"Quote captured: {quote_fetched_at.strftime('%Y-%m-%d %H:%M:%S UTC')} "
                "-- applies only to this exact asset/strategy/expiry/strike/quantity selection."
            )

        def _render_leg(label: str, instrument: InverseOptionInstrument, q) -> None:
            st.markdown(f"**{label}: {instrument.instrument_name}**")
            cols = st.columns(4)
            cols[0].markdown(f"Expiry\n\n{instrument.expiry.strftime('%Y-%m-%d %H:%M UTC')}")
            cols[1].markdown(
                f"Strike / Type\n\n{format_usd(instrument.strike)} {instrument.option_type.upper()}"
            )
            cols[2].markdown(f"Quote side\n\n{q.quote_side.upper()}")
            cols[3].markdown(f"BBO amount\n\n{format_quantity(q.best_quote_amount)} {q.premium_currency}")
            cols2 = st.columns(2)
            cols2[0].markdown(
                f"Native premium ({q.premium_currency})\n\n{format_quantity(q.premium_native)}"
            )
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

    st.divider()
    st.caption(
        "Historical Evidence (frozen thesis backtest output) is available from the sidebar "
        "navigation. It uses a separate, frozen dataset -- current live contracts shown above "
        "are not the same instruments as those historical observations."
    )


# ---------------------------------------------------------------------------
# Historical Evidence (Phase 4)
# ---------------------------------------------------------------------------


def render_historical_evidence() -> None:
    st.title("Historical Thesis Evidence")
    st.markdown(
        '<div class="hc-subtitle">Frozen Deribit/Tardis backtest evidence</div>',
        unsafe_allow_html=True,
    )

    evidence = get_historical_evidence()

    badge_col, _ = st.columns([3, 2])
    with badge_col:
        if evidence.metrics_available and evidence.wealth_available:
            st.markdown(
                '<span class="hc-badge">Verified frozen thesis evidence</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="hc-badge-warn">Evidence unavailable</span>', unsafe_allow_html=True
            )
        st.caption(
            f"Sample: {evidence.sample_start_month} to {evidence.sample_end_month} · Assets: BTC / ETH"
        )

    with st.expander("Provenance / verification details"):
        st.markdown(f"**Production Run ID:** `{evidence.run_id}`")
        st.markdown(f"**Artifact directory:** `{evidence.directory}`")
        for label, artifact_result in (
            ("strategy_metrics.csv", evidence.metrics),
            ("monthly_backtest_results.csv", evidence.wealth),
        ):
            st.markdown(f"**{label}** -- state: `{artifact_result.state.value}`")
            if artifact_result.expected_sha256:
                st.caption(f"Expected SHA-256: `{artifact_result.expected_sha256}`")
            if artifact_result.observed_sha256:
                st.caption(f"Observed SHA-256: `{artifact_result.observed_sha256}`")
            if artifact_result.expected_rows is not None:
                st.caption(
                    f"Rows -- expected: {artifact_result.expected_rows}, "
                    f"observed: {artifact_result.observed_rows}"
                )
            if not artifact_result.ok and artifact_result.message:
                st.code(artifact_result.message)

    st.caption(
        "Historical results are sample-specific and do not predict future performance. "
        "Historical Evidence is frozen Deribit/Tardis thesis output; the Live Designer (sidebar) "
        "uses current Deribit public-market data. Current live contracts are not the same "
        "instruments as these historical observations."
    )

    if not evidence.metrics_available and not evidence.wealth_available:
        st.error("Historical thesis evidence unavailable: artifact verification failed.")
        st.caption(
            f"Place the canonical CSV files in `{evidence.directory}` "
            f"(or set the `{HISTORICAL_DIR_ENV_VAR}` environment variable) to enable this view."
        )
        return

    st.divider()
    control_col1, control_col2 = st.columns(2)
    with control_col1:
        hist_asset = st.selectbox("Asset", CANONICAL_ASSETS, key="hist_asset_select")
    with control_col2:
        view_label = st.radio("View", ("Primary", "Robustness"), key="hist_view_select", horizontal=True)
    view = HistoricalView.PRIMARY if view_label == "Primary" else HistoricalView.ROBUSTNESS

    st.subheader("Stored Wealth Path")
    if evidence.wealth_available:
        assert evidence.wealth.dataframe is not None
        fig = build_wealth_path_figure(evidence.wealth.dataframe, hist_asset, view)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Chart plots the frozen stored `wealth_end` values directly, in `decision_month` order. "
            "No wealth reconstruction, cumulative-product, or renormalization is performed."
        )
    else:
        display = describe_historical_state(evidence.wealth.state)
        getattr(st, display.severity)(display.message)
        if evidence.wealth.message:
            with st.expander("Technical details"):
                st.code(evidence.wealth.message)

    st.subheader("Strategy Metrics")
    if evidence.metrics_available:
        assert evidence.metrics.dataframe is not None
        metrics_filtered = filter_metrics(evidence.metrics.dataframe, hist_asset, view)
        table = build_metrics_table(metrics_filtered)
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.caption(
            "Net Premium Cost and Upside Shortfall are cumulative stored values, not annualized "
            "or averaged. All figures are read directly from the frozen production artifact."
        )
    else:
        display = describe_historical_state(evidence.metrics.state)
        getattr(st, display.severity)(display.message)
        if evidence.metrics.message:
            with st.expander("Technical details"):
                st.code(evidence.metrics.message)


# ---------------------------------------------------------------------------
# Page setup + top-level navigation
# ---------------------------------------------------------------------------

st.set_page_config(page_title="HedgeCanvas", layout="wide", page_icon="\U0001F6E1")
st.markdown(PAGE_CSS, unsafe_allow_html=True)

with st.sidebar:
    nav_choice = st.radio(
        "View", ("Live Designer", "Historical Evidence"), key="nav_view_select"
    )
    st.divider()

if nav_choice == "Live Designer":
    render_live_designer()
else:
    render_historical_evidence()
