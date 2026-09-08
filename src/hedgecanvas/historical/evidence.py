"""Top-level structured Historical Evidence result consumed by the UI.

The UI never performs its own SHA/schema validation -- it calls
``load_historical_evidence`` once and reads the two
``ArtifactValidationResult`` objects it returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from hedgecanvas.historical import config
from hedgecanvas.historical.loader import load_monthly_results, load_strategy_metrics
from hedgecanvas.historical.validation import ArtifactValidationResult


@dataclass(frozen=True)
class HistoricalEvidence:
    directory: Path
    metrics: ArtifactValidationResult
    wealth: ArtifactValidationResult
    run_id: str = config.CANONICAL_PRODUCTION_RUN_ID
    sample_start_month: str = config.SAMPLE_START_MONTH
    sample_end_month: str = config.SAMPLE_END_MONTH

    @property
    def metrics_available(self) -> bool:
        return self.metrics.ok

    @property
    def wealth_available(self) -> bool:
        return self.wealth.ok

    @property
    def any_available(self) -> bool:
        return self.metrics_available or self.wealth_available


def load_historical_evidence(directory: Optional[Path] = None) -> HistoricalEvidence:
    """Validate and (if valid) load both canonical artifacts.

    Each artifact is validated independently: a failure in one does not
    prevent the other's evidence from being shown if it is itself valid.
    """
    resolved_dir = config.resolve_historical_dir(directory)
    metrics_result = load_strategy_metrics(resolved_dir)
    wealth_result = load_monthly_results(resolved_dir)
    return HistoricalEvidence(
        directory=resolved_dir, metrics=metrics_result, wealth=wealth_result
    )
