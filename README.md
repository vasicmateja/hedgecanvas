# HedgeCanvas

**Crypto Portfolio Protection Analytics**

A WealthTech prototype accompanying the Master's thesis:

> *"Option-Based Downside Protection for Crypto Portfolios: A WealthTech Prototype and Backtesting Study."*

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

`src/hedgecanvas/live`, `src/hedgecanvas/historical`, and `src/hedgecanvas/ui` exist
only as placeholder packages for future phases.

**No live market integration exists yet.** All analysis is a closed-form,
deterministic function of user-supplied inputs (`S0`, `Q`, `H`, strikes,
premiums); nothing in this repository calls an external API.

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
