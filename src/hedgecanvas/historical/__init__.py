"""Phase 4: read-only frozen historical thesis evidence.

Loads and fail-closed-validates the two canonical production artifacts
(``strategy_metrics.csv``, ``monthly_backtest_results.csv``) and exposes
stored values only -- nothing here recomputes a backtest, reconstructs a
wealth path, or retrieves historical data from the live Deribit API. See
the README's Historical Evidence section for the full contract.
"""

from hedgecanvas.historical.config import (
    CANONICAL_PRODUCTION_RUN_ID,
    DEFAULT_HISTORICAL_DIR,
    HISTORICAL_DIR_ENV_VAR,
    MONTHLY_RESULTS_EXPECTED_ROWS,
    MONTHLY_RESULTS_EXPECTED_SHA256,
    MONTHLY_RESULTS_FILENAME,
    MONTHLY_RESULTS_SCHEMA,
    SAMPLE_END_MONTH,
    SAMPLE_START_MONTH,
    STRATEGY_METRICS_EXPECTED_ROWS,
    STRATEGY_METRICS_EXPECTED_SHA256,
    STRATEGY_METRICS_FILENAME,
    STRATEGY_METRICS_SCHEMA,
    resolve_historical_dir,
)
from hedgecanvas.historical.evidence import HistoricalEvidence, load_historical_evidence
from hedgecanvas.historical.filtering import filter_metrics, filter_wealth_path, wealth_end_series
from hedgecanvas.historical.keys import (
    CANONICAL_ASSETS,
    CANONICAL_STRATEGIES,
    PRIMARY_STRATEGIES,
    ROBUSTNESS_STRATEGIES,
    STRATEGY_DISPLAY_LABELS,
    HistoricalView,
    is_valid_asset,
    is_valid_strategy,
    strategies_for_view,
    strategy_display_label,
)
from hedgecanvas.historical.loader import load_monthly_results, load_strategy_metrics
from hedgecanvas.historical.states import HistoricalState
from hedgecanvas.historical.validation import ArtifactValidationResult, validate_artifact

__all__ = [
    "CANONICAL_PRODUCTION_RUN_ID",
    "DEFAULT_HISTORICAL_DIR",
    "HISTORICAL_DIR_ENV_VAR",
    "MONTHLY_RESULTS_EXPECTED_ROWS",
    "MONTHLY_RESULTS_EXPECTED_SHA256",
    "MONTHLY_RESULTS_FILENAME",
    "MONTHLY_RESULTS_SCHEMA",
    "SAMPLE_END_MONTH",
    "SAMPLE_START_MONTH",
    "STRATEGY_METRICS_EXPECTED_ROWS",
    "STRATEGY_METRICS_EXPECTED_SHA256",
    "STRATEGY_METRICS_FILENAME",
    "STRATEGY_METRICS_SCHEMA",
    "resolve_historical_dir",
    "HistoricalEvidence",
    "load_historical_evidence",
    "filter_metrics",
    "filter_wealth_path",
    "wealth_end_series",
    "CANONICAL_ASSETS",
    "CANONICAL_STRATEGIES",
    "PRIMARY_STRATEGIES",
    "ROBUSTNESS_STRATEGIES",
    "STRATEGY_DISPLAY_LABELS",
    "HistoricalView",
    "is_valid_asset",
    "is_valid_strategy",
    "strategies_for_view",
    "strategy_display_label",
    "load_monthly_results",
    "load_strategy_metrics",
    "HistoricalState",
    "ArtifactValidationResult",
    "validate_artifact",
]
