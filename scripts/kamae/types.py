"""Branded primitives and closed sets for layout / KiCad domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType

Mm = NewType("Mm", float)
PreviewY = NewType("PreviewY", float)

Layer = Literal["F.Cu", "F.Mask", "F.SilkS", "B.SilkS"]
HJustify = Literal["left", "center", "right"]
VJustify = Literal["top", "center", "bottom"]


@dataclass(frozen=True, slots=True)
class InkBounds:
    """Axis-aligned ink box in preview coordinates (Y down from top)."""

    left: Mm
    bottom: Mm
    right: Mm
    top: Mm


@dataclass(frozen=True, slots=True)
class Sensitive:
    """PII wrapper — redacted in logs and repr."""

    value: str

    def __repr__(self) -> str:
        return "Sensitive(***)"

    def reveal(self) -> str:
        return self.value
