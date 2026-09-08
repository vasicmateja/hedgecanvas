# HedgeCanvas

**Crypto Portfolio Protection Analytics**

A WealthTech prototype accompanying the Master's thesis:

> *"Option-Based Downside Protection for Crypto Portfolios: A WealthTech Prototype and Backtesting Study."*

## Product summary

HedgeCanvas is a Streamlit application with two views, selected from the
sidebar:

- **Live Designer** -- construct an indicative BTC/ETH options hedge
  (Unhedged, Protective Put, Covered Call, or Collar) using current public
  Deribit market data.
- **Historical Evidence** -- a read-only view of the thesis's own frozen
  2020-01 to 2024-12 backtest output (BTC/ETH, seven canonical
  strategies), verified before display and never recomputed.

**Supported assets:** BTC, ETH only. **Supported strategies:** Unhedged,
Protective Put, Covered Call, Collar (Live Designer); the seven canonical
`BENCHMARK`/`PP95`/`CC105`/`COLLAR95_105`/`PP90`/`CC110`/`COLLAR90_110`
keys (Historical Evidence). Nothing else.

**Environment:** developed and tested on **Python 3.9.6**; no newer
Python version is required by the current dependency stack (Streamlit,
Plotly, pandas, httpx, pytest). See [Getting started](#getting-started).

**Run:** `streamlit run app.py` (see [Getting started](#getting-started)).

**Limitations, in one place:**

- A Live Designer quote is a top-of-book observation, not a guaranteed
  execution price; displayed BBO depth is limited to the validation this
  app implements (best bid/ask only -- no book-walking, no VWAP, no
  slippage model).
- The Live Designer's payoff chart is deterministic *scenario* analysis
  over hypothetical terminal prices -- it is not a forecast and carries
  no probability interpretation.
- Historical Evidence results are specific to the frozen 2020-01 to
  2024-12 sample and do not predict future performance.
- HedgeCanvas is read-only market/research tooling: no account access, no
  order placement, no authentication, no private Deribit endpoint, and no
  theoretical pricing fallback (no Black-Scholes, no Greeks, no Monte
  Carlo) anywhere in this repository.

## Phase 1 scope

Phase 1 implements the exchange-agnostic **domain layer** only:

- repository foundation (packaging, tests, README);
- core domain models (`Strategy`, `CoverageState`, `BoundaryScope`, `HedgePosition`);
- a deterministic expiry payoff / P&L engine;
- Max Profit / Max Loss analysis;
- breakeven analysis;
- full-vs-partial hedge coverage semantics;
- Protection Floor / Upside Cap scope metadata;
- a comprehensive unit test suite.

### Explicitly out of scope for Phase 1

The following are **not** implemented and are intentionally deferred to later phases:

- Deribit (or any exchange/broker) integration;
- historical thesis backtest data integration;
- the real Streamlit UI;
- Black-Scholes pricing, option Greeks, Monte Carlo simulation, or optimization/ML;
- authentication, trading, or brokerage functions;
- Docker infrastructure.

`src/hedgecanvas/live` contains the Phase 2 Deribit public market-data
adapter, `src/hedgecanvas/ui` + `app.py` contain the Phase 3 live Streamlit
UI, and `src/hedgecanvas/historical` contains the Phase 4 read-only
Historical Evidence layer -- all described below.

## Domain model

Let:

| Symbol | Meaning |
|---|---|
| `S0` | current underlying price in USD |
| `ST` | terminal underlying price in USD |
| `Q`  | total BTC/ETH underlying portfolio quantity |
| `H`  | underlying quantity covered by the option overlay |
| `KP` | put strike in USD |
| `KC` | call strike in USD |
| `P`  | long-put premium cost in USD per underlying unit at inception |
| `C`  | written-call premium credit in USD per underlying unit at inception |

Constraints enforced by `HedgePosition`: `S0 > 0`, `Q > 0`, `0 <= H <= Q`,
`KP > 0` / `KC > 0` where used, `P >= 0`, `C >= 0`, and `KP <= KC` for a Collar.

`P` and `C` are already-normalized USD-per-underlying-unit inception premiums;
any exchange-specific premium conversion belongs to a future live-data
adapter, not to this domain model.

### Supported strategies

Exactly four: `UNHEDGED`, `PROTECTIVE_PUT`, `COVERED_CALL`, `COLLAR`.

### Payoff / P&L formulas

```
Unhedged:
  PnL(ST) = Q(ST - S0)

Protective Put:
  PnL(ST) = Q(ST - S0) + H * max(KP - ST, 0) - H * P

Covered Call:
  PnL(ST) = Q(ST - S0) - H * max(ST - KC, 0) + H * C

Collar:
  PnL(ST) = Q(ST - S0) + H * max(KP - ST, 0) - H * max(ST - KC, 0) - H * P + H * C
```

Valid for any `ST >= 0`; negative `ST` is rejected.

### Full vs. partial coverage

- **Full coverage**: `H == Q` — exact equality, never an approximate
  floating-point comparison. Quantities are normalized to `decimal.Decimal`
  so this comparison is deterministic.
- **Partial coverage**: `0 < H < Q`.
- **No coverage**: `H == 0`.

Coverage state drives whether a strategy's Max Profit is finite and whether
its protection floor / upside cap apply to the whole portfolio or only to
the hedged portion (see `BoundaryScope`).

### Max Profit / Max Loss / breakeven

The payoff is represented as a piecewise-linear function of `ST` with kinks
at the strikes in use. Max Profit, Max Loss, and breakeven are all derived
from that general piecewise-linear geometry (vertex values and per-segment
affine root solving) rather than from strategy-specific textbook shortcuts
inserted blindly. Max Profit is represented as either a finite value or an
explicit "unlimited" state — never approximated with an arbitrarily large
number. Breakeven is solved analytically per segment (no numerical grid
scan) and can report zero, one, multiple, or a degenerate zero-PnL interval.

## Phase 2 scope: Deribit public live market-data adapter

`src/hedgecanvas/live` is a **read-only, public-API-only** adapter that
turns current Deribit BTC/ETH inverse-option market data into the inputs
the Phase 1 domain model expects. It does not compute any payoff itself —
`hedgecanvas.domain` remains the only payoff/analysis authority.

**No API key. No authentication. No trading. No order placement.** Only
Deribit's public JSON-RPC methods are called:

- `public/get_instruments` — discover current, non-expired BTC/ETH options;
- `public/get_index_price` — the live S0 (spot/reference) reading;
- `public/get_order_book` (depth=1) — top-of-book bid/ask for a selected contract;
- `public/test` — optional connectivity check, used only by the live smoke test.

### Inverse-option scope, explicitly

Only **BTC/ETH inverse options** are considered eligible. An instrument
must satisfy the full coherent metadata set — `kind == "option"`,
`base_currency`/`settlement_currency == BTC or ETH`, `counter_currency ==
"USD"`, `price_index` matching the asset's USD index, `contract_size ==
1`, `is_active`, `state == "open"` when present, `instrument_type ==
"reversed"` when present, and `instrument_name` not containing `"_USDC-"`.
**Linear USDC-settled options are always excluded** and never silently
mixed in. The instrument's `option_type` field is canonical for call/put
identification; the trailing `C`/`P` in the instrument name is checked
only as a secondary consistency check.

### S0 (index) convention

S0 is always `public/get_index_price(price_index)` for the selected
instrument's own `price_index` metadata — **never** the option's
`underlying_price` (which belongs to Deribit's forward/IV framework, not
the live spot reference the Phase 1 payoff model needs). The index
snapshot (name, price, retrieval time) is recorded alongside the result.

### Native premium and USD-equivalent conversion

Inverse BTC/ETH option prices are native BTC/ETH amounts per underlying
unit. The adapter always reads the correct BBO side — **never** midpoint,
mark price, or last trade:

- Protective Put (long put): best **ask**;
- Covered Call (written call): best **bid**;
- Collar: put leg **ask**, call leg **bid**.

The native quote is retained (`premium_native`, `premium_currency`,
`quote_side`, `best_quote_amount`) and never overwritten. It is converted
into the Phase 1 USD-per-unit inception convention using the *same* S0
snapshot for both legs of a Collar:

```
P = put_best_ask_native * S0
C = call_best_bid_native * S0
```

### Sizing / coverage convention

Given a user-supplied underlying quantity `Q`, the hedged amount `H` is the
largest multiple of the instrument's live `min_trade_amount` that is `<=
Q` — **never rounded up**. If `Q` is below one minimum tradable unit, `H =
0` and a `BELOW_MINIMUM_SIZE` state is returned. Full/partial/zero
coverage classification is delegated entirely to the Phase 1
`HedgePosition` (`H == Q` exactly), so live and static analysis always
agree. A Collar requires both legs to share the same `min_trade_amount`
(and therefore the same `H`); otherwise an `INCONSISTENT_METADATA` state
is returned.

### BBO depth validation

After computing `H`, the top-of-book *amount* at the required side must be
`>= H`, or the adapter returns `INSUFFICIENT_BBO_DEPTH`. Only depth=1 is
read — Phase 2 never walks the deeper book or computes VWAP/slippage.
Even a passing check only describes an **indicative live market-based
hedge**, not a guaranteed executable one.

### Structured failure states

Every operation returns a typed `MarketState` rather than `None`: `OK`,
`NO_QUOTE`, `BELOW_MINIMUM_SIZE`, `INSUFFICIENT_BBO_DEPTH`,
`INSTRUMENT_INACTIVE`, `UNSUPPORTED_INSTRUMENT`, `INCONSISTENT_METADATA`,
`NETWORK_ERROR`, `HTTP_ERROR`, `RPC_ERROR`, `MALFORMED_RESPONSE`.

### Running the mock tests

```bash
pytest tests/live
```

All adapter tests use deterministic mocked HTTP responses (`httpx.MockTransport`)
and never touch the network.

### Running the optional live smoke test

Skipped by default so normal test runs never depend on internet
availability. To opt in against the real Deribit production API
(read-only, public methods only):

```bash
HEDGECANVAS_LIVE_TESTS=1 pytest -m live tests/live/test_live_smoke.py
```

## Phase 3 scope: the live Streamlit UI

`app.py` (repository root) is HedgeCanvas's first functional product
surface: a Streamlit dashboard that lets a user construct and understand an
**"Indicative live market-based hedge"** for a BTC or ETH position, using
currently observable Deribit inverse-option market data. It wires the
Phase 1 domain engine and Phase 2 live adapter together and adds no new
financial logic of its own — `hedgecanvas.ui` contains only formatting,
filtering, and Plotly chart-building helpers over results those two layers
already produced.

**Supported assets:** BTC, ETH. **Supported strategies:** Unhedged,
Protective Put, Covered Call, Collar. Nothing else.

### What it does

- Displays the current Deribit `BTC/USD` or `ETH/USD` index price (S0) via
  `public/get_index_price` — never an option's `underlying_price`.
- Lets you size a position either directly (`Underlying Quantity`) or via
  `Portfolio Value (USD)` (`Q = portfolio_value / S0`), always converting
  UI input through a safe Decimal/string boundary (Phase 1 rejects raw
  floats by design).
- For option strategies: discovers currently eligible BTC/ETH **inverse**
  options only (never linear USDC options), lets you pick a real listed
  expiry and strike(s) — a Collar's call-strike selector is restricted to
  `KC >= KP` so an invalid corridor cannot be chosen — and fetches the
  correct-side top-of-book quote (put ASK, call BID; never midpoint, mark,
  or last price).
- Shows both the native BTC/ETH premium and its inception USD-equivalent
  (normalized using the same S0 snapshot as the rest of the position) —
  the native quote is never relabeled as USD.
- Runs Phase 2 sizing (`H` floored to the instrument's live
  `min_trade_amount`, never rounded up) and displays `Q`, `H`, `Q-H`,
  coverage %, and the exact Full/Partial/Zero coverage state as classified
  by the Phase 1 domain model (never re-derived in the UI).
- Renders the expiry payoff chart (Plotly) using `hedgecanvas.domain.pnl`
  for both the selected strategy and the unhedged comparison curve, over a
  deterministic scenario grid centered on S0 and the active strikes — the
  x-axis is scenario analysis, not a forecast.
- Shows Max Profit (explicit `Unlimited` where applicable — e.g. a partial
  Covered Call or partial Collar's whole-portfolio upside is always
  Unlimited), Max Loss, breakeven (single/multiple/none/degenerate
  interval), Net Option Cost/Credit, and Protection Floor / Upside Cap
  worded according to `BoundaryScope` (`WHOLE_PORTFOLIO` vs
  `HEDGED_PORTION` vs no card at all).
- Maps every Phase 2 `MarketState` to a concise warning/error/info message
  instead of a crash or a silently substituted price; never falls back to
  a theoretical (Black-Scholes) price when no live quote exists.
- Caches instrument discovery briefly (60s `st.cache_data` TTL per asset);
  index/BBO quotes are fetched fresh per request and only reused for an
  identical (asset, strategy, expiry, strike(s), quantity) selection —
  changing any of those never displays a stale snapshot, and an explicit
  "Refresh quote" button is available.
- A static "Historical Evidence — available in a later phase" notice is
  shown; no thesis data, backtest, or metrics are loaded in Phase 3.

### Running the app

```bash
streamlit run app.py
```

No API key or account is required. No trade is ever placed and no private
Deribit endpoint is ever called.

### Running the Phase 3 tests

```bash
pytest tests/ui tests/test_app_smoke.py
```

All Phase 3 tests are deterministic and offline: the presentation/view-model
tests exercise plain functions, and the Streamlit `AppTest`-based smoke
tests run the real `app.py` with `DeribitClient`'s HTTP-calling methods
monkeypatched at the class level (never live network).

## Phase 4 scope: Historical Thesis Evidence (read-only)

`src/hedgecanvas/historical` is a strictly **read-only** layer over two
frozen canonical artifacts produced by the thesis's own backtest run. It
never recomputes, reruns, or reconstructs anything from that research --
it only fail-closed verifies the two files and reads stored values.
`app.py`'s sidebar **View** control (`Live Designer` / `Historical
Evidence`) switches between this and the Phase 3 designer; only the
selected view executes on a given rerun, so choosing Historical Evidence
never triggers a Deribit API call, and choosing Live Designer never loads
the historical artifacts.

**Hard separation from the Live Designer:** Historical Evidence is frozen
Deribit/Tardis thesis output over a fixed 2020-01 to 2024-12 sample; the
Live Designer is current Deribit public-market data. Neither path feeds
the other -- the historical loader never imports the live Deribit client,
and the live adapter never reads the historical CSVs (enforced by a
dedicated test, `tests/historical/test_separation.py`).

### Canonical artifacts

| File | Expected SHA-256 | Expected rows |
|---|---|---|
| `strategy_metrics.csv` | `eb7c38...488c70` | 14 |
| `monthly_backtest_results.csv` | `ee276e...760a0a5` | 840 |

(Full hashes are kept in `hedgecanvas.historical.config` and shown in the
UI's provenance expander -- not printed in full here.) Both files must also
match an **exact ordered column schema** (see `config.py`); a reordered,
missing, or extra column fails validation just like a hash mismatch.

Production Run ID (shown in the UI's provenance expander):
`0cc87d60337032ec493534d312fc84734c5a4ae6a34b5687424f0761937d6132`

### Where to place the files

Default location (repository-relative, not committed):

```
data/historical/frozen/strategy_metrics.csv
data/historical/frozen/monthly_backtest_results.csv
```

Or point at any other read-only location with:

```bash
export HEDGECANVAS_HISTORICAL_DIR=/path/to/your/frozen/artifacts
```

The files are only ever read, never written, copied, or modified by
HedgeCanvas. If they are absent or fail verification, Historical Evidence
shows a clean "unavailable" state (with a technical-details expander) and
the Live Designer keeps working normally -- historical artifact presence
is never a prerequisite for launching the app.

### Fail-closed validation

Each artifact is independently checked, in order: file exists → SHA-256 of
the raw file bytes matches exactly → column schema matches exactly
(names **and** order) → row count matches exactly → `asset`/`strategy`
columns contain only the seven canonical keys. Any single failure stops
at that check and returns a structured state (`FILE_MISSING`,
`HASH_MISMATCH`, `SCHEMA_MISMATCH`, `ROW_COUNT_MISMATCH`, `INVALID_KEYS`,
`READ_PARSE_FAILURE`, or `AVAILABLE`) -- the file is never partially
trusted, reordered-and-continued, repaired, or regenerated.

### Canonical keys and views

Assets: `BTC`, `ETH`. Strategies (literal, never inferred from display
labels): `BENCHMARK`, `PP95`, `CC105`, `COLLAR95_105`, `PP90`, `CC110`,
`COLLAR90_110`. **Primary** view = `BENCHMARK, PP95, CC105, COLLAR95_105`;
**Robustness** view = `BENCHMARK, PP90, CC110, COLLAR90_110`. No strike,
DTE, moneyness, quote-age, transaction, date-range, or rebalance controls
are exposed -- the user only picks Asset and Primary/Robustness.

### No recomputation, ever

HedgeCanvas reads, verifies, filters, sorts, formats, and plots stored
values -- nothing more. It never reruns a backtest, reconstructs a wealth
path, derives a new risk metric, or recomputes premium cost or upside
shortfall. The wealth-path chart plots the stored `wealth_end` column
directly, in `decision_month` order; it never cumulates `strategy_return`,
never uses `wealth_start` to manufacture a value, and never renormalizes.
Metric cards (Cumulative/Annualized Return, Annualized Volatility, Max
Monthly Drawdown, Downside Deviation, Sortino Ratio, Net Premium Cost, and
Upside Shortfall) show the eight stored `strategy_metrics.csv` columns
with display-only formatting (e.g. a stored `0.679` shown as `67.92%`) --
the underlying numeric values are never altered. Net Premium Cost and
Upside Shortfall are explicitly labeled as cumulative, summed values, never
as annualized or averaged figures.

### Running the Phase 4 tests

```bash
pytest tests/historical tests/ui/test_historical_view_models.py tests/ui/test_historical_chart.py tests/ui/test_historical_messages.py
```

These are fully offline: they build small fixture CSVs on the fly (never
the real canonical files) and check fixture-specific expected hashes,
never weakening the hardcoded production hashes used by
`hedgecanvas.historical.loader`.

### Optional: canonical-artifact smoke check

If you have placed the real canonical files locally, you can run a
read-only smoke validation against them directly (byte-for-byte hash,
exact schema, exact row count, and literal-key filtering/wealth
extraction):

```bash
pytest -m canonical_artifacts -v -s tests/historical/test_canonical_smoke.py
```

This is skipped automatically (not failed) when the real files aren't
present in the resolved historical directory.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

This runs the complete deterministic suite (domain + live + ui + historical
+ app smoke), which never depends on internet access and never requires
the real canonical historical CSVs. Two things remain separately opt-in:

```bash
# Phase 2: live smoke test against the real Deribit production API (public methods only)
HEDGECANVAS_LIVE_TESTS=1 pytest -m live tests/live/test_live_smoke.py

# Phase 4: read-only smoke validation against the real canonical historical artifacts, if present
pytest -m canonical_artifacts -v -s tests/historical/test_canonical_smoke.py
```

No trading, authentication, or backtest-recomputation functionality
exists anywhere in this repository.
