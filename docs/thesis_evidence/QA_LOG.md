# Final QA Log

This is a record of what was actually observed during the final QA pass
(see the main handoff for the full summary). All values below were read
directly from the running application against the real, live public
Deribit API and the real canonical historical artifacts -- nothing here
is fabricated or assumed. Every state was viewed live in an internal
browser preview tool; no screenshot files were saved (see
[`MANUAL_SCREENSHOT_CHECKLIST.md`](MANUAL_SCREENSHOT_CHECKLIST.md) for
how to capture real image files).

## Live Designer -- BTC

### Unhedged (baseline)

- Captured: 2026-09-08 20:24:17 UTC
- S0: $78,420.01 (source: `btc_usd`)
- Q: 1 BTC, Portfolio value: $78,420.01
- Max Profit: Unlimited; Max Loss: $78,420.01; Breakeven: $78,420.01
- Coverage: Zero (0.00%)

### Protective Put, full coverage

- Captured: 2026-09-08 20:24:26 UTC (quote), S0 as of 20:24:25 UTC
- S0: $78,463.28; Q: 1 BTC
- Contract: `BTC-9SEP26-71000-P`, expiry 2026-09-09 08:00 UTC, KP $71,000.00
- Quote side: ASK; native premium: 0.0001 BTC; USD-equivalent: $7.85;
  BBO amount: 30.8 BTC
- H: 1 BTC, Residual: 0 BTC, Coverage: Full (100.00%)
- Max Profit: Unlimited; Max Loss: $7,470.38; Breakeven: $78,470.38
- Net Option Cost: Cost: $7.85
- Protection floor: "Whole-portfolio protection strike: $71,000.00"

### Covered Call, full coverage, near expiry (deep ITM strike, negative best case)

- Captured: 2026-09-08 20:25:08 UTC
- S0: $78,493.69; Contract: `BTC-9SEP26-71000-C`, KC $71,000.00
- Quote side: BID; native premium: 0.093 BTC; USD-equivalent: $7,299.91
- **Metric label read "Best-Case P&L: -$193.78"** (not "Max Profit") --
  confirms the new label-switching polish item works correctly for a
  genuinely negative best case, observed on real market data without any
  fabrication.
- Net Option Cost: Credit: $7,299.91
- Breakeven: "No breakeven" (payoff never crosses zero -- consistent with
  a best case that is itself negative)

### Covered Call, full coverage, further expiry, positive best case

- Captured: 2026-09-08 20:27:19 UTC
- S0: $78,511.90; Contract: `BTC-30OCT26-55000-C`, expiry 2026-10-30, KC $55,000.00
- Quote side: BID; native premium: 0.304 BTC; USD-equivalent: $23,867.62
- Max Profit: $355.72 (label correctly reads "Max Profit", not
  "Best-Case P&L", since the value is positive); Max Loss: $54,644.28;
  Breakeven: $54,644.28
- Upside cap: "Whole-portfolio upside cap: $55,000.00"

### Collar, partial coverage

- Captured: 2026-09-08 20:27:42 UTC
- S0: $78,527.02; Q: 0.35 BTC (deliberately not a multiple of the 0.1 BTC
  minimum, to force partial sizing)
- Contracts: `BTC-30OCT26-40000-P` (KP $40,000, ASK, 0.0008 BTC ->
  $62.82) and `BTC-30OCT26-55000-C` (KC $55,000, BID, 0.304 BTC ->
  $23,872.21)
- H: 0.3 BTC, Residual: 0.05 BTC, **Coverage: Partial (85.71%)**
- **Max Profit: Unlimited** -- confirms the critical partial-Collar
  requirement (whole-portfolio upside remains uncapped) on real data.
- Protection floor: "Put protection applies to the hedged portion only:
  $40,000.00 strike (residual 0.05 unprotected)"
- Upside cap: "Upside cap applies to the hedged portion only: $55,000.00
  strike (residual 0.05 uncapped)"

### Below-minimum-size

- Captured: 2026-09-08 20:27:59 UTC
- Q: 0.05 BTC (below the 0.1 BTC minimum); Strategy: Collar
- Warning shown: "Position size is below the current minimum tradable
  option size; no option overlay is applied (H = 0)."
- Info banner shown: "...no option overlay could be constructed (H = 0).
  The metrics and chart below reflect the unhedged underlying position
  only."
- H: 0 BTC, Coverage: Zero (0.00%). Q was NOT silently rounded up.

### Natural NO_QUOTE observation

- While probing Covered Call strikes on the nearest (1-day) BTC expiry,
  selecting the $85,000 strike produced: "Live quote: No live quote is
  currently available on the required side for this contract." with a
  "Technical details" expander and a graceful "No live hedge could be
  constructed for the current selection." message -- the app did not
  crash and did not substitute a theoretical price. This occurred
  naturally on live market data; it was not forced or fabricated.

## Live Designer -- ETH

### Below-minimum-size

- Captured: 2026-09-08 20:28:12 UTC
- Asset switched BTC -> ETH: strike selectors correctly reset to fresh
  ETH values ($2,100 default) rather than showing stale BTC strikes --
  confirms asset-change invalidation.
- Q: 0.05 ETH (below the 1 ETH minimum), Strategy: Collar
- Same below-minimum warning/info banner as BTC; H: 0 ETH.

### Collar, partial coverage

- Captured: 2026-09-08 20:28:29 UTC
- S0: $2,486.32; Q: 4.5 ETH (not a multiple of the 1 ETH minimum)
- Contracts: `ETH-30OCT26-1000-P` (ASK, 0.0005 ETH -> $1.24) and
  `ETH-30OCT26-1000-C` (BID, 0.5985 ETH -> $1,488.06)
- H: 4 ETH, Residual: 0.5 ETH, Coverage: Partial (88.89%)
- Max Profit: Unlimited; floor/cap both worded "hedged portion only"

### Collar, full coverage (Max Loss = $0.00 edge case)

- Captured: 2026-09-08 20:28:43 UTC
- Q: 4 ETH exactly (a clean multiple of the 1 ETH minimum)
- H: 4 ETH, Residual: 0 ETH, Coverage: Full (100.00%)
- Max Profit: $2.51; **Max Loss: $0.00** -- a genuine domain edge case
  (deep-ITM KP=KC=$1,000 collar with a large net credit) where the
  minimum P&L over the ST>=0 domain is positive, so Max Loss correctly
  displays as zero rather than a negative number.
- Floor/cap: "Whole-portfolio protection strike: $1,000.00" /
  "Whole-portfolio upside cap: $1,000.00"

### Unhedged

- Captured: 2026-09-08 20:28:55 UTC
- S0: $2,486.98; Q: 4 ETH; Max Loss: $9,947.92; Coverage: Zero (0.00%)

## Historical Evidence

Verified with `HEDGECANVAS_HISTORICAL_DIR` pointed (read-only) at the
real canonical files. Provenance expander confirmed for both artifacts:

- `strategy_metrics.csv`: state `AVAILABLE`, observed SHA-256 ==
  expected SHA-256 (`eb7c38...488c70`), rows 14/14.
- `monthly_backtest_results.csv`: state `AVAILABLE`, observed SHA-256 ==
  expected SHA-256 (`ee276e...760a0a5`), rows 840/840.
- Production Run ID displayed:
  `0cc87d60337032ec493534d312fc84734c5a4ae6a34b5687424f0761937d6132`
- Sample: "2020-01 to 2024-12"; Badge: "Verified frozen thesis evidence".

### BTC, Primary

- Legend: Unhedged Benchmark, Protective Put 95, Covered Call 105,
  Collar 95/105 -- matches the canonical Primary set exactly.
- Wealth path chart spans Jan 2020 to Jul 2024+ (full sample), peaking
  around 1400 on the normalized wealth index for the Benchmark line.
- Strategy Metrics table row for "Unhedged Benchmark": Cumulative Return
  1235.10%, matching the stored `cumulative_return=12.350994736` value
  from the raw CSV multiplied by 100 for display (12.350994736 * 100 =
  1235.0994736%, displayed rounded to 1235.10%) -- confirms no
  recomputation, only display-unit conversion.

### ETH, Primary

- Legend correctly shows the same four Primary strategy labels for ETH.
- Wealth path chart renders a distinct ETH-specific path (peaking ~4000
  on the index), confirming the asset filter is literal and correct.

### Robustness (checked on ETH)

- Legend: Unhedged Benchmark, Protective Put 90, Covered Call 110,
  Collar 90/110 -- matches the canonical Robustness set exactly; no
  Primary-only strategy names appeared.

### Fail-closed (missing artifacts)

- With `HEDGECANVAS_HISTORICAL_DIR` unset and no files at the default
  `data/historical/frozen/` location: badge read "Evidence unavailable",
  `st.error` showed "Historical thesis evidence unavailable: artifact
  verification failed.", with placement instructions naming the default
  directory and the environment variable override. No crash. The Live
  Designer, checked immediately before and after, was fully functional
  throughout.

## Independence checks

- With historical artifacts absent, Live Designer fully operated (S0,
  quotes, all four strategies) with no historical-related error.
- With `HEDGECANVAS_HISTORICAL_DIR` pointed at the real files, switching
  to Historical Evidence never triggered a Deribit API call (this is also
  covered by an automated regression test,
  `tests/historical/test_separation.py`, and by
  `tests/test_app_smoke.py::test_historical_view_does_not_require_live_api_connectivity`,
  which fails the test if `DeribitClient` is called while Historical
  Evidence is displayed).

## Final UX / comprehension polish pass (after commit bbee2a6)

Terminology changed: "Historical Evidence" -> "Historical Backtest —
2020–2024" (nav label and page title); "Primary"/"Robustness" ->
"Main Strategies"/"Wider Strike Settings" (canonical internal
`HistoricalView.PRIMARY`/`ROBUSTNESS` and strategy-set membership
unchanged). All values below observed live against the real public
Deribit API and the real canonical historical artifacts.

### Unlimited Max Profit explanation (partial Covered Call / Collar)

- BTC Covered Call, Q=0.35, H=0.3 (residual 0.05 BTC): metric card showed
  "Max Profit: Unlimited" with caption "Why unlimited? 0.05 BTC remains
  uncapped. Above the call strike, only this residual position continues
  to benefit from further price increases." -- residual matches Q-H
  exactly.
- BTC Collar (KP=KC=$60,000, later KP=KC=$72,000), same Q/H: identical
  correct explanation shown alongside the Collar-specific equal-strikes
  note (both rendered together, non-contradictory).
- ETH Collar, Q=4.5, H=4 (residual 0.5 ETH): "Why unlimited? 0.5 ETH
  remains uncapped..." -- confirmed asset-correct wording.
- Full-coverage cases (Q=H) throughout the session never showed this
  note, as expected (Max Profit is finite for full Covered Call/Collar).

### KP == KC Collar explanation

- BTC Collar naturally defaulted to KP=KC=$60,000 at partial coverage
  (Q=0.35, H=0.3): note read "Put and call strikes are equal on the
  hedged portion. That portion is effectively locked around this strike
  at expiry, while the residual 0.05 BTC remains exposed to further price
  moves." -- correctly did NOT claim the whole portfolio was locked.
- ETH Collar likewise defaulted to KP=KC=$1,800 at partial coverage
  (Q=4.5, H=4): "...residual 0.5 ETH remains exposed..." shown correctly.
- Full-coverage KP==KC case verified deterministically only (see
  `tests/ui/test_view_models.py::test_full_collar_kp_equals_kc_gets_whole_position_lock_note`)
  -- no full-coverage KP==KC state occurred naturally during this live
  session (current listed strikes only produced full coverage at Q=1.0
  BTC / Q=4.0 ETH with default distinct KP/KC selections).

### KP-driven KC auto-adjustment feedback

- BTC Collar: KP changed 60000 -> 72000 while KC was set to 70000 (now
  invalid, since 70000 < 72000). Observed: KC auto-reset to 72000 (the
  lowest valid remaining call strike), and the info message "Call strike
  adjusted because it must be equal to or above the put strike." appeared
  directly below the Call strike control.
- Manually changing KC directly to a still-valid strike (e.g. 70000, a
  valid choice under the KP in effect at the time) produced NO adjustment
  message, confirming it only fires for genuine automatic resets.
- Changing quantity alone (unrelated to KP/KC) did not spuriously
  re-trigger the message.

### Responsive / Option Cost/Credit clipping

Manually verified at 100% browser zoom, three viewport widths, in the
Live Designer (BTC and ETH, Unhedged/Covered Call/Collar):

- **1440x900**: no clipping anywhere; Max Profit, Max Loss, Breakeven,
  Option Cost/Credit, S0/Q/Portfolio Value, and Hedge coverage cards all
  fully readable.
- **1366x768**: same -- no clipping.
- **~1024px wide**: initial layout (2-up Max Profit/Max Loss, 4-across S0
  row, 3-across coverage row) DID clip at this width (e.g. "Unli...",
  "$1,2...", "$77,21..."). Fixed by stacking Max Profit/Max Loss/
  Breakeven/Option Cost/Credit to one full-width metric per row, splitting
  the top S0 status row into two 2-column rows instead of four across,
  and splitting Hedge coverage into a 2-up + 1 full-width row instead of
  3-across. Re-verified after the fix: no clipping at 1024px for any of
  Max Profit/Best-Case P&L, Max Loss, Breakeven, Option Cost/Credit, S0,
  Q, Portfolio Value, or the three coverage quantities. The Quote Details
  section (put/call leg cards) uses markdown text rather than `st.metric`
  and was never clipped at any tested width.

### Historical Backtest terminology (live-verified)

- Page title: "Historical Backtest — 2020–2024"; subtitle: "See how BTC
  or ETH portfolios evolved under the different protection strategies in
  the frozen thesis backtest. These are historical results, not live data
  or forecasts."; secondary badge retained: "Verified frozen thesis
  evidence".
- View control options read "Main Strategies" / "Wider Strike Settings";
  selecting each produced the exact canonical strategy sets (confirmed by
  the rendered legend/table: Main Strategies -> Unhedged Benchmark/
  Protective Put 95/Covered Call 105/Collar 95/105; Wider Strike Settings
  -> Unhedged Benchmark/Protective Put 90/Covered Call 110/Collar 90/110)
  for both BTC and ETH.
- "What do these strategies mean?" expander showed target-language
  explanations ("approximately 95% put-strike target", etc.) -- never
  claimed an exact realized strike percentage.
- Wealth chart: title "Portfolio Wealth Over Time", y-axis "Portfolio
  Wealth Index (Start = 100)", x-axis "Month", with caption explaining
  100 is a normalized starting value, not an account balance.
- "What do these metrics mean?" expander showed the five required
  explanations (Max Monthly Drawdown, Downside Deviation, Sortino Ratio,
  Net Premium Cost, Upside Shortfall) with correct cumulative/non-averaged
  wording for the last two.
- Fail-closed state (no `HEDGECANVAS_HISTORICAL_DIR`, no default-location
  files) re-verified after all changes: "Evidence unavailable" badge,
  clean error message, same placement instructions, no crash; Live
  Designer confirmed fully functional immediately before and after.
