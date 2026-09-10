# Manual Screenshot Checklist

**Status: MANUAL CHECKLIST PREPARED (screenshots not saved as files).**

During final QA/UX passes, every state below was opened and visually
verified live in an internal browser preview tool, and its exact values
were recorded in [`QA_LOG.md`](QA_LOG.md). That tool can render and
inspect the running app but has no mechanism to export/save a screenshot
as a file on disk (only inline images visible within that QA session), so
no PNG files exist in this repository. This checklist lets a person with
normal desktop screenshot tools (macOS `Cmd+Shift+4`, Windows `Win+Shift+S`,
etc.) reproduce each image from scratch in a few minutes.

General setup for every screenshot:

1. `cd` into the repository, activate the venv, run `streamlit run app.py`.
2. Open the app in a normal desktop browser window, sized to roughly
   1440x900 or wider so the chart and metric cards are legible without
   scrolling. (The layout was verified clipping-free down to ~1024px wide
   too, if a narrower capture is needed.)
3. Use the browser's built-in zoom (Cmd/Ctrl `-`) at 80-90% if a state
   doesn't fit the window without scrolling.
4. Do not open browser dev tools / consoles in the shot.
5. Crop to the browser content area only (no OS chrome needed, but do not
   crop out the disclaimer banner, the "Indicative live market-based
   hedge" badge, or the market-status/provenance line -- those are part of
   the product's meaning, not decoration).

---

## 01_live_btc_protective_put.png

- Nav: **Live Designer**
- Asset: **BTC**
- Position input: **Underlying Quantity** = `1.0`
- Strategy: **Protective Put**
- Expiry: the nearest currently listed expiry (default selection)
- Put strike (KP): the nearest currently listed strike (default selection)
- Must be visible: S0 metric, Q/portfolio value, payoff chart with S0/KP
  reference lines, Max Profit/Max Loss/Breakeven/Option Cost/Credit cards,
  Protection floor line, Hedge coverage row, Quote details (put leg) with
  native + USD-equivalent premium and the "Quote captured" timestamp.
- Accept if: Max Profit reads "Unlimited"; coverage reads "Full
  (100.00%)"; the floor text says "Whole-portfolio protection strike".

## 02_live_btc_covered_call.png

- Nav: **Live Designer**, Asset: **BTC**, Strategy: **Covered Call**
- Position input: **Underlying Quantity** = `1.0`
- Pick a call strike that is comfortably above the current S0 (out of the
  money) so the metric label reads "Max Profit" with a positive value, not
  "Best-Case P&L". If the nearest expiry's OTM strikes return "No live
  quote is currently available on the required side for this contract",
  pick a later expiry from the Expiry selector and retry -- do not force a
  strike with no quote, and do not substitute a theoretical price.
- Must be visible: same layout as above, but with "Max Profit" (not
  Best-Case P&L), "Upside cap: Whole-portfolio upside cap: $...", and the
  call leg's BID-side quote details.
- Accept if: quote side reads "BID"; Max Profit is a positive dollar
  figure; coverage reads "Full (100.00%)".

## 03_live_partial_collar.png

- Nav: **Live Designer**
- Asset: BTC or ETH, whichever currently supports a clean partial-coverage
  example (BTC min trade amount is 0.1, ETH is 1 -- pick a quantity that
  is NOT an exact multiple of the minimum, e.g. `0.35` BTC or `4.5` ETH).
- Strategy: **Collar**
- Pick any valid KP <= KC pair with live quotes on both legs.
- Must be visible: Hedge coverage row showing Hedged Quantity strictly
  between 0 and Portfolio Quantity, a non-zero Unhedged Residual,
  "Coverage: Partial (NN.NN%)"; the floor/cap lines must say "applies to
  the hedged portion only" and name the residual quantity -- NOT
  "whole-portfolio"; the "Why unlimited?" explanation naming that same
  residual quantity.
- Accept if: Max Profit reads "Unlimited" (this is the critical
  partial-Collar behavior); floor/cap wording says "hedged portion only".

## 04_historical_btc_main_strategies.png

- Nav: **Historical Backtest**
- Requires the real canonical CSVs to be present (see the main README's
  Phase 4 section for where to place them, or set
  `HEDGECANVAS_HISTORICAL_DIR`).
- Asset: **BTC**, View: **Main Strategies**
- Must be visible: "Historical Backtest — 2020–2024" header, the
  plain-language subtitle, "Verified frozen thesis evidence" badge,
  sample range "2020-01 to 2024-12", the "Portfolio Wealth Over Time"
  chart (y-axis "Portfolio Wealth Index (Start = 100)") with all four
  Main Strategies in the legend (Unhedged Benchmark, Protective Put 95,
  Covered Call 105, Collar 95/105), and the Strategy Metrics table.
- Accept if: the legend shows exactly those four strategies; the x-axis
  spans January 2020 to December 2024.

## 05_historical_eth_main_strategies.png

- Same as #04 but Asset: **ETH**, View: **Main Strategies**.

## 06_historical_wider_strike_settings.png

- Nav: **Historical Backtest**, either asset, View: **Wider Strike
  Settings**.
- Must be visible: legend showing Unhedged Benchmark, Protective Put 90,
  Covered Call 110, Collar 90/110 (NOT the Main Strategies names).
- Accept if: no Main-Strategies-only strategy (PP95/CC105/COLLAR95_105)
  appears.

## 07_optional_warning_state.png (optional)

- Nav: **Live Designer**, any asset, any option strategy.
- Set Underlying Quantity below the instrument's minimum tradable size
  (e.g. `0.05` BTC or `0.5` ETH).
- Must be visible: the warning "Position size is below the current
  minimum tradable option size; no option overlay is applied (H = 0)."
  and the info banner clarifying the chart/metrics reflect the unhedged
  position only.
- Accept if: Hedged Quantity reads exactly `0`; Coverage reads "Zero
  (0.00%)"; the app has not silently rounded Q up to the minimum.

## 08_optional_kc_reset_feedback.png (optional)

- Nav: **Live Designer**, Strategy: **Collar**.
- Select a Put strike (KP), then a Call strike (KC) above it. Then raise
  KP above the previously selected KC.
- Must be visible: the info message "Call strike adjusted because it must
  be equal to or above the put strike." directly below the Call strike
  control.
- Accept if: the new Call strike shown is a real listed strike >= the new
  Put strike (never a fabricated value).

---

## Notes for whoever captures these

- Every Live Designer screenshot is a **live product demonstration**, not
  reproducible research evidence -- the exact quote will differ by the
  time it is captured again. Record the capture timestamp (shown on
  screen next to S0 and next to "Quote captured") alongside the saved
  file, e.g. in the filename or a caption.
- Every Historical Backtest screenshot reflects the **frozen** 2020-01 to
  2024-12 sample and will look identical on any future capture, provided
  the same canonical artifacts are used (verify the "Verified frozen
  thesis evidence" badge and the Production Run ID in the provenance
  expander before treating a capture as valid).
- Do not edit, retouch, or alter any numeric value visible in a captured
  screenshot.
