"""Central mapping from Phase 4 HistoricalState to concise user-facing messages.

Mirrors ``hedgecanvas.ui.market_messages`` for the live layer: the UI never
interprets a low-level validation state itself, and never prints raw
artifact contents as a substitute for a real message.
"""

from __future__ import annotations

from dataclasses import dataclass

from hedgecanvas.historical import HistoricalState

Severity = str  # "info" | "warning" | "error"


@dataclass(frozen=True)
class HistoricalStateDisplay:
    severity: Severity
    message: str


_MESSAGES = {
    HistoricalState.AVAILABLE: HistoricalStateDisplay(
        "info", "Historical evidence verified and available."
    ),
    HistoricalState.FILE_MISSING: HistoricalStateDisplay(
        "warning",
        "Historical thesis evidence unavailable: the canonical artifact file was not found.",
    ),
    HistoricalState.HASH_MISMATCH: HistoricalStateDisplay(
        "error",
        "Historical thesis evidence unavailable: artifact verification failed (hash mismatch).",
    ),
    HistoricalState.SCHEMA_MISMATCH: HistoricalStateDisplay(
        "error",
        "Historical thesis evidence unavailable: artifact verification failed (schema mismatch).",
    ),
    HistoricalState.ROW_COUNT_MISMATCH: HistoricalStateDisplay(
        "error",
        "Historical thesis evidence unavailable: artifact verification failed (row count mismatch).",
    ),
    HistoricalState.INVALID_KEYS: HistoricalStateDisplay(
        "error",
        "Historical thesis evidence unavailable: artifact contains non-canonical key values.",
    ),
    HistoricalState.READ_PARSE_FAILURE: HistoricalStateDisplay(
        "error",
        "Historical thesis evidence unavailable: the artifact file could not be read.",
    ),
}

_FALLBACK = HistoricalStateDisplay(
    "error", "Historical thesis evidence unavailable: artifact verification failed."
)


def describe_historical_state(state: HistoricalState) -> HistoricalStateDisplay:
    return _MESSAGES.get(state, _FALLBACK)
