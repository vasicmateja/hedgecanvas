"""Core domain model: the hedge position and its exact quantity semantics.

All numeric quantities are normalized to ``decimal.Decimal`` so that the
full-vs-partial coverage classification (``H == Q``) is an exact comparison,
never a floating-point "close enough" check.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union

from hedgecanvas.domain.enums import CoverageState, Strategy

Numeric = Union[Decimal, int, str]

_PUT_STRATEGIES = (Strategy.PROTECTIVE_PUT, Strategy.COLLAR)
_CALL_STRATEGIES = (Strategy.COVERED_CALL, Strategy.COLLAR)


def to_decimal(value: Numeric) -> Decimal:
    """Convert a numeric value to an exact Decimal.

    Floats are rejected: binary floating-point cannot represent most decimal
    fractions exactly, which would undermine the exact-equality guarantees
    this domain model relies on (e.g. full-coverage classification). Callers
    that only have a float should pass ``str(value)`` explicitly.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("bool is not a valid numeric input")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        return Decimal(value)
    raise TypeError(
        f"Unsupported numeric type {type(value)!r}; use Decimal, int, or str."
    )


@dataclass(frozen=True)
class HedgePosition:
    """An exchange-agnostic option-overlay position on a crypto portfolio.

    ``P`` and ``C`` are already-normalized USD-per-underlying-unit inception
    premium values. Any exchange-specific premium conversion is the
    responsibility of a later live-data adapter, not of this domain model.
    """

    strategy: Strategy
    S0: Decimal
    Q: Decimal
    H: Decimal
    KP: Optional[Decimal] = None
    KC: Optional[Decimal] = None
    P: Decimal = Decimal(0)
    C: Decimal = Decimal(0)

    def __init__(
        self,
        strategy: Strategy,
        S0: Numeric,
        Q: Numeric,
        H: Numeric,
        KP: Optional[Numeric] = None,
        KC: Optional[Numeric] = None,
        P: Numeric = Decimal(0),
        C: Numeric = Decimal(0),
    ) -> None:
        if not isinstance(strategy, Strategy):
            raise TypeError("strategy must be a hedgecanvas.domain.enums.Strategy")

        object.__setattr__(self, "strategy", strategy)
        object.__setattr__(self, "S0", to_decimal(S0))
        object.__setattr__(self, "Q", to_decimal(Q))
        object.__setattr__(self, "H", to_decimal(H))
        object.__setattr__(self, "KP", to_decimal(KP) if KP is not None else None)
        object.__setattr__(self, "KC", to_decimal(KC) if KC is not None else None)
        object.__setattr__(self, "P", to_decimal(P))
        object.__setattr__(self, "C", to_decimal(C))

        self._validate()

    def _validate(self) -> None:
        if self.S0 <= 0:
            raise ValueError("S0 must be > 0")
        if self.Q <= 0:
            raise ValueError("Q must be > 0 (Q == 0 or Q < 0 is invalid)")
        if self.H < 0:
            raise ValueError("H must be >= 0")
        if self.H > self.Q:
            raise ValueError("H must be <= Q (H > Q is invalid)")
        if self.P < 0:
            raise ValueError("P must be >= 0")
        if self.C < 0:
            raise ValueError("C must be >= 0")

        uses_put = self.strategy in _PUT_STRATEGIES
        uses_call = self.strategy in _CALL_STRATEGIES

        if uses_put:
            if self.KP is None:
                raise ValueError(f"{self.strategy.value} requires KP")
            if self.KP <= 0:
                raise ValueError("KP must be > 0 where a put is used")

        if uses_call:
            if self.KC is None:
                raise ValueError(f"{self.strategy.value} requires KC")
            if self.KC <= 0:
                raise ValueError("KC must be > 0 where a call is used")

        if self.strategy is Strategy.COLLAR:
            assert self.KP is not None and self.KC is not None
            if self.KP > self.KC:
                raise ValueError("Collar requires KP <= KC")

    # -- coverage semantics ------------------------------------------------

    @property
    def underlying_quantity(self) -> Decimal:
        return self.Q

    @property
    def hedged_quantity(self) -> Decimal:
        return self.H

    @property
    def unhedged_residual_quantity(self) -> Decimal:
        return self.Q - self.H

    @property
    def coverage_fraction(self) -> Decimal:
        return self.H / self.Q

    @property
    def coverage_percentage(self) -> Decimal:
        return self.coverage_fraction * Decimal(100)

    @property
    def coverage_state(self) -> CoverageState:
        if self.H == self.Q:
            return CoverageState.FULL
        if self.H == 0:
            return CoverageState.NONE
        return CoverageState.PARTIAL

    @property
    def is_full_coverage(self) -> bool:
        return self.coverage_state is CoverageState.FULL

    @property
    def is_partial_coverage(self) -> bool:
        return self.coverage_state is CoverageState.PARTIAL

    @property
    def is_no_coverage(self) -> bool:
        return self.coverage_state is CoverageState.NONE

    @property
    def has_put(self) -> bool:
        return self.strategy in _PUT_STRATEGIES

    @property
    def has_call(self) -> bool:
        return self.strategy in _CALL_STRATEGIES
