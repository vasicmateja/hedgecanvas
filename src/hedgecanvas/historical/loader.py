"""Production-default loaders for the two canonical historical artifacts.

These wire the frozen expectations in ``config.py`` into the generic
``validate_artifact`` check. Tests that need a different expected hash
(e.g. against small fixture files) call ``validate_artifact`` directly
with fixture-specific expectations instead of using these functions --
the production defaults here always retain the exact canonical hashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from hedgecanvas.historical import config
from hedgecanvas.historical.keys import CANONICAL_ASSETS, CANONICAL_STRATEGIES
from hedgecanvas.historical.validation import ArtifactValidationResult, validate_artifact


def load_strategy_metrics(directory: Optional[Path] = None) -> ArtifactValidationResult:
    resolved_dir = config.resolve_historical_dir(directory)
    path = resolved_dir / config.STRATEGY_METRICS_FILENAME
    return validate_artifact(
        path,
        expected_sha256=config.STRATEGY_METRICS_EXPECTED_SHA256,
        expected_schema=config.STRATEGY_METRICS_SCHEMA,
        expected_rows=config.STRATEGY_METRICS_EXPECTED_ROWS,
        key_checks=(
            ("asset", CANONICAL_ASSETS),
            ("strategy", CANONICAL_STRATEGIES),
        ),
    )


def load_monthly_results(directory: Optional[Path] = None) -> ArtifactValidationResult:
    resolved_dir = config.resolve_historical_dir(directory)
    path = resolved_dir / config.MONTHLY_RESULTS_FILENAME
    return validate_artifact(
        path,
        expected_sha256=config.MONTHLY_RESULTS_EXPECTED_SHA256,
        expected_schema=config.MONTHLY_RESULTS_SCHEMA,
        expected_rows=config.MONTHLY_RESULTS_EXPECTED_ROWS,
        key_checks=(
            ("asset", CANONICAL_ASSETS),
            ("strategy", CANONICAL_STRATEGIES),
        ),
    )
