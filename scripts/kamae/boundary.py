"""Boundary validation for script entry points and I/O."""

from __future__ import annotations

from pathlib import Path

from kamae.result import Err, Ok, Result
from kamae.types import Mm


def require_positive_mm(value: float, *, field: str) -> Result[Mm, str]:
    if value <= 0:
        return Err(f"{field} must be positive, got {value}")
    return Ok(Mm(value))


def require_existing_file(path: Path, *, label: str) -> Result[Path, str]:
    if not path.exists():
        return Err(f"Missing {label}: {path}")
    return Ok(path)
