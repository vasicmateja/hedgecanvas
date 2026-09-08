"""Shared numeric conversion helper for the live adapter.

JSON-RPC responses deliver numbers as Python ``int``/``float``. We convert
them to ``Decimal`` via their ``repr``/``str`` (not by feeding a float
directly into ``Decimal``) to avoid importing binary floating-point noise
into values that flow into the Phase 1 domain model's exact-equality
comparisons.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def json_number_to_decimal(value: Any) -> Optional[Decimal]:
    """Convert a JSON-decoded number to Decimal, or None if not a valid number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    return None
