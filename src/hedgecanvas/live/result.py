"""Generic structured result wrapper used throughout the live adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from hedgecanvas.live.states import MarketState

T = TypeVar("T")


@dataclass(frozen=True)
class LiveResult(Generic[T]):
    """The outcome of a live-adapter operation: either OK with a value, or a
    structured failure state with a human-readable message. Never ``None``.
    """

    state: MarketState
    value: Optional[T] = None
    message: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.state is MarketState.OK

    @classmethod
    def ok_value(cls, value: T) -> "LiveResult[T]":
        return cls(state=MarketState.OK, value=value)

    @classmethod
    def fail(cls, state: MarketState, message: Optional[str] = None) -> "LiveResult[T]":
        if state is MarketState.OK:
            raise ValueError("LiveResult.fail requires a non-OK state")
        return cls(state=state, value=None, message=message)
