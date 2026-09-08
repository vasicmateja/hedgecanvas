"""Expiry/strike selection helpers over Phase 2's already-discovered instruments.

These are pure filtering/grouping functions over
:class:`hedgecanvas.live.InverseOptionInstrument` lists. They never parse
instrument names or recompute metadata already supplied by ``live/`` --
they only group and restrict what Phase 2 has already classified as
eligible.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Sequence

from hedgecanvas.live import InverseOptionInstrument


def puts_only(instruments: Sequence[InverseOptionInstrument]) -> List[InverseOptionInstrument]:
    return [i for i in instruments if i.option_type == "put"]


def calls_only(instruments: Sequence[InverseOptionInstrument]) -> List[InverseOptionInstrument]:
    return [i for i in instruments if i.option_type == "call"]


def expiries_for_protective_put(instruments: Sequence[InverseOptionInstrument]) -> List[int]:
    """Expiries with at least one eligible put."""
    return sorted({i.expiration_timestamp for i in puts_only(instruments)})


def expiries_for_covered_call(instruments: Sequence[InverseOptionInstrument]) -> List[int]:
    """Expiries with at least one eligible call."""
    return sorted({i.expiration_timestamp for i in calls_only(instruments)})


def expiries_for_collar(instruments: Sequence[InverseOptionInstrument]) -> List[int]:
    """Expiries with at least one eligible put AND at least one eligible call."""
    put_expiries = {i.expiration_timestamp for i in puts_only(instruments)}
    call_expiries = {i.expiration_timestamp for i in calls_only(instruments)}
    return sorted(put_expiries & call_expiries)


def strikes_for_expiry(
    instruments: Sequence[InverseOptionInstrument], expiration_timestamp: int
) -> List[Decimal]:
    """All distinct strikes available at a given expiry, ascending."""
    return sorted({i.strike for i in instruments if i.expiration_timestamp == expiration_timestamp})


def call_strikes_at_or_above(
    call_instruments: Sequence[InverseOptionInstrument],
    expiration_timestamp: int,
    kp: Decimal,
) -> List[Decimal]:
    """Call strikes at the given expiry with KC >= kp, so a Collar KP<=KC is
    impossible to violate through the control itself.
    """
    return sorted(
        {
            i.strike
            for i in call_instruments
            if i.expiration_timestamp == expiration_timestamp and i.strike >= kp
        }
    )


def instrument_by_strike(
    instruments: Sequence[InverseOptionInstrument],
    expiration_timestamp: int,
    strike: Decimal,
) -> InverseOptionInstrument:
    """Look up the single instrument for an already-validated (expiry, strike)."""
    for instrument in instruments:
        if instrument.expiration_timestamp == expiration_timestamp and instrument.strike == strike:
            return instrument
    raise KeyError(f"No instrument found for expiry={expiration_timestamp} strike={strike}")


def group_strikes_by_expiry(
    instruments: Sequence[InverseOptionInstrument],
) -> Dict[int, List[Decimal]]:
    grouped: Dict[int, List[Decimal]] = {}
    for instrument in instruments:
        grouped.setdefault(instrument.expiration_timestamp, []).append(instrument.strike)
    return {expiry: sorted(strikes) for expiry, strikes in grouped.items()}
