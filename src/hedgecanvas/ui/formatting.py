"""Decimal-safe input parsing and display formatting for the Streamlit UI.

Phase 1's domain model intentionally rejects raw floats (see
``hedgecanvas.domain.position.to_decimal``). All numeric user input must
cross a safe string -> Decimal boundary here before reaching the domain or
live layers -- never a bare float.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


def parse_decimal_input(raw: object) -> Optional[Decimal]:
    """Parse a UI text/number input into an exact Decimal, or None if invalid.

    Accepts a string (preferred) or an int/Decimal already. A bare float is
    converted via its ``str()`` (not fed to Decimal directly) to avoid
    importing binary floating-point noise, matching the convention used by
    the Phase 2 live adapter.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int):
        return Decimal(raw)
    if isinstance(raw, float):
        raw = str(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except InvalidOperation:
            return None
    return None


def format_usd(value: Decimal, *, sign: bool = False) -> str:
    """Format a Decimal as a USD amount, e.g. Decimal('1234.5') -> '$1,234.50'."""
    quantized = value.quantize(Decimal("0.01"))
    prefix = "-$" if quantized < 0 else ("+$" if sign else "$")
    return f"{prefix}{abs(quantized):,.2f}"


def format_quantity(value: Decimal, *, max_decimals: int = 8) -> str:
    """Format an underlying quantity without misleading trailing noise."""
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        integer_part, frac_part = text.split(".")
        frac_part = frac_part[:max_decimals].rstrip("0")
        text = integer_part if not frac_part else f"{integer_part}.{frac_part}"
    return text


def format_percentage(value: Decimal, *, decimals: int = 2) -> str:
    """Format a percentage value (already scaled 0-100), e.g. 40 -> '40.00%'.

    Visual rounding only -- callers must present coverage *state* (Full /
    Partial / Zero) from the domain's exact classification, never inferred
    from this rounded string.
    """
    quantizer = Decimal(1).scaleb(-decimals)
    return f"{value.quantize(quantizer):.{decimals}f}%"
