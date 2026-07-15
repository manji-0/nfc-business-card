#!/usr/bin/env python3
"""Bake ENIG name text via KiCad pcbnew (TrueType + render_cache)."""

from __future__ import annotations

import sys
import warnings

from bake_kicad_text import TextSpec, align_ink_bounds_top, bake_specs_raw
from kamae.result import Err, Ok, Result
from kamae.types import Mm
from kicad10 import build_name_enig_sexpr
from layout_metrics import name_ink_bounds_mm
from name_render_cache import align_gr_text_block_left, fit_gr_text_block_width
from silk_layout import (
    NAME_CAP_HEIGHT_MM,
    NAME_FONT_FACE,
    NAME_TEXT_THICKNESS_MM,
    NAME_X_MM,
    NAME_Y_MM,
    TEXT_LEFT_MM,
)

NAME_TTF_THICKNESS_MM = 0.15


def bake_name_enig_sexpr_result(
    text: str,
    *,
    x_mm: float = NAME_X_MM,
    y_mm: float = NAME_Y_MM,
    size_mm: float = NAME_CAP_HEIGHT_MM,
    face: str = NAME_FONT_FACE,
) -> Result[str, str]:
    """Return gr_text (F.Cu + F.Mask) aligned to preview Pillow metrics."""
    ink = name_ink_bounds_mm(text)
    target_w = float(ink.right) - float(ink.left)
    base = dict(
        text=text,
        x_mm=Mm(x_mm),
        y_mm=Mm(y_mm),
        size_mm=Mm(size_mm),
        face=face,
        thickness_mm=Mm(NAME_TTF_THICKNESS_MM),
        h_justify="left",
        v_justify="top",
    )
    baked = bake_specs_raw(
        [
            TextSpec(**base, layer="F.Cu"),
            TextSpec(**base, layer="F.Mask"),
        ]
    )
    match baked:
        case Err(error=error):
            return Err(error.detail)
        case Ok(value=blocks):
            out: list[str] = []
            for block in blocks:
                block = align_gr_text_block_left(block, float(TEXT_LEFT_MM))
                block = fit_gr_text_block_width(block, target_w)
                block = align_ink_bounds_top(block, left_mm=float(ink.left), top_mm=float(ink.top))
                out.append(block)
            return Ok("\n".join(out))


def bake_name_enig_sexpr(
    text: str,
    *,
    x_mm: float = NAME_X_MM,
    y_mm: float = NAME_Y_MM,
    size_mm: float = NAME_CAP_HEIGHT_MM,
    face: str = NAME_FONT_FACE,
) -> str:
    match bake_name_enig_sexpr_result(text, x_mm=x_mm, y_mm=y_mm, size_mm=size_mm, face=face):
        case Ok(value=sexpr):
            return sexpr
        case Err(error=detail):
            warnings.warn(f"{detail}; falling back to KiCad stroke font for ENIG name", stacklevel=2)
            return build_name_enig_sexpr(
                text,
                x_mm=x_mm,
                y_mm=y_mm,
                size_mm=size_mm,
                thickness_mm=NAME_TEXT_THICKNESS_MM,
            )


if __name__ == "__main__":
    print(bake_name_enig_sexpr(sys.argv[1] if len(sys.argv) > 1 else "Wataru Manji"))
