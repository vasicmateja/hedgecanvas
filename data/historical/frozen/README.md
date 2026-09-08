# Historical artifact directory

Place the two canonical frozen thesis artifacts here:

```
strategy_metrics.csv
monthly_backtest_results.csv
```

They are **not** committed to this repository (see `.gitignore`). If you'd
rather keep them elsewhere, set `HEDGECANVAS_HISTORICAL_DIR` to that
directory instead of using this default location.

See the main [README.md](../../../README.md#phase-4-scope-historical-thesis-evidence-read-only)
for the expected SHA-256 hashes, exact column schema, and fail-closed
validation behavior. HedgeCanvas only ever reads these files -- it never
writes, copies, or modifies them.
