"""Result type — errors as values (no exceptions in domain code)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T

    @property
    def kind(self) -> str:
        return "ok"


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    error: E

    @property
    def kind(self) -> str:
        return "err"


Result = Ok[T] | Err[E]


def unwrap(result: Result[T, E], *, context: str = "operation") -> T:
    match result:
        case Ok(value=value):
            return value
        case Err(error=error):
            raise RuntimeError(f"{context} failed: {error}") from None
