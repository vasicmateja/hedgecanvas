"""Enumerations for the HedgeCanvas domain model."""

from __future__ import annotations

from enum import Enum


class Strategy(Enum):
    """Supported option-overlay strategies. No others are permitted in Phase 1."""

    UNHEDGED = "UNHEDGED"
    PROTECTIVE_PUT = "PROTECTIVE_PUT"
    COVERED_CALL = "COVERED_CALL"
    COLLAR = "COLLAR"


class CoverageState(Enum):
    """Classification of how much of the underlying quantity is option-covered."""

    NONE = "NONE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class BoundaryScope(Enum):
    """Scope over which a protection floor or upside cap applies."""

    WHOLE_PORTFOLIO = "WHOLE_PORTFOLIO"
    HEDGED_PORTION = "HEDGED_PORTION"
    NONE = "NONE"
