"""Fail-closed validation for a single frozen historical CSV artifact.

The hash is computed over the exact raw file bytes -- before any parsing,
and never over a parsed/re-serialized DataFrame. Any single failed check
(missing file, hash mismatch, wrong ordered schema, wrong row count,
unparseable CSV, or an out-of-canon key value) stops validation at that
point and returns a structured non-AVAILABLE state; the file is never
partially trusted, repaired, reordered-and-continued, or regenerated.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import pandas as pd

from hedgecanvas.historical.states import HistoricalState


@dataclass(frozen=True)
class ArtifactValidationResult:
    state: HistoricalState
    message: Optional[str] = None
    dataframe: Optional[pd.DataFrame] = None
    observed_sha256: Optional[str] = None
    expected_sha256: Optional[str] = None
    observed_rows: Optional[int] = None
    expected_rows: Optional[int] = None
    observed_schema: Optional[Tuple[str, ...]] = None
    expected_schema: Optional[Tuple[str, ...]] = None

    @property
    def ok(self) -> bool:
        return self.state is HistoricalState.AVAILABLE


def validate_artifact(
    path: Path,
    *,
    expected_sha256: str,
    expected_schema: Sequence[str],
    expected_rows: int,
    key_checks: Sequence[Tuple[str, Sequence[str]]] = (),
) -> ArtifactValidationResult:
    """Validate one CSV artifact: existence, exact byte-hash, exact ordered
    schema, exact row count, and (optionally) that given columns contain
    only canonical key values. Returns AVAILABLE with the parsed
    DataFrame only if every check passes.
    """
    expected_schema_t = tuple(expected_schema)

    if not path.is_file():
        return ArtifactValidationResult(
            state=HistoricalState.FILE_MISSING,
            message=f"Artifact not found: {path}",
            expected_sha256=expected_sha256,
            expected_rows=expected_rows,
            expected_schema=expected_schema_t,
        )

    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        return ArtifactValidationResult(
            state=HistoricalState.READ_PARSE_FAILURE,
            message=f"Could not read {path.name}: {exc}",
            expected_sha256=expected_sha256,
            expected_rows=expected_rows,
            expected_schema=expected_schema_t,
        )

    observed_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if observed_sha256 != expected_sha256:
        return ArtifactValidationResult(
            state=HistoricalState.HASH_MISMATCH,
            message=f"{path.name} SHA-256 does not match the expected canonical hash",
            observed_sha256=observed_sha256,
            expected_sha256=expected_sha256,
            expected_rows=expected_rows,
            expected_schema=expected_schema_t,
        )

    try:
        dataframe = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception as exc:  # pandas raises a variety of error types
        return ArtifactValidationResult(
            state=HistoricalState.READ_PARSE_FAILURE,
            message=f"Could not parse {path.name}: {exc}",
            observed_sha256=observed_sha256,
            expected_sha256=expected_sha256,
            expected_rows=expected_rows,
            expected_schema=expected_schema_t,
        )

    observed_schema = tuple(str(c) for c in dataframe.columns)
    if observed_schema != expected_schema_t:
        return ArtifactValidationResult(
            state=HistoricalState.SCHEMA_MISMATCH,
            message=f"{path.name} column schema does not match exactly (names and/or order)",
            observed_sha256=observed_sha256,
            expected_sha256=expected_sha256,
            observed_schema=observed_schema,
            expected_schema=expected_schema_t,
            expected_rows=expected_rows,
        )

    observed_rows = len(dataframe)
    if observed_rows != expected_rows:
        return ArtifactValidationResult(
            state=HistoricalState.ROW_COUNT_MISMATCH,
            message=f"{path.name} has {observed_rows} rows, expected {expected_rows}",
            observed_sha256=observed_sha256,
            expected_sha256=expected_sha256,
            observed_schema=observed_schema,
            expected_schema=expected_schema_t,
            observed_rows=observed_rows,
            expected_rows=expected_rows,
        )

    for column, allowed_values in key_checks:
        observed_values = set(dataframe[column].astype(str).unique())
        invalid_values = observed_values - set(allowed_values)
        if invalid_values:
            return ArtifactValidationResult(
                state=HistoricalState.INVALID_KEYS,
                message=(
                    f"{path.name} column '{column}' contains non-canonical values: "
                    f"{sorted(invalid_values)}"
                ),
                observed_sha256=observed_sha256,
                expected_sha256=expected_sha256,
                observed_schema=observed_schema,
                expected_schema=expected_schema_t,
                observed_rows=observed_rows,
                expected_rows=expected_rows,
            )

    return ArtifactValidationResult(
        state=HistoricalState.AVAILABLE,
        dataframe=dataframe,
        observed_sha256=observed_sha256,
        expected_sha256=expected_sha256,
        observed_schema=observed_schema,
        expected_schema=expected_schema_t,
        observed_rows=observed_rows,
        expected_rows=expected_rows,
    )
