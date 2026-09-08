"""Structured fail-closed states for historical artifact verification.

Never a bare ``None`` for a failure mode -- every verification outcome is
one of these explicit states so the UI can render a precise message
instead of guessing from an exception.
"""

from __future__ import annotations

from enum import Enum


class HistoricalState(Enum):
    AVAILABLE = "AVAILABLE"
    FILE_MISSING = "FILE_MISSING"
    HASH_MISMATCH = "HASH_MISMATCH"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    ROW_COUNT_MISMATCH = "ROW_COUNT_MISMATCH"
    INVALID_KEYS = "INVALID_KEYS"
    READ_PARSE_FAILURE = "READ_PARSE_FAILURE"
