#!/usr/bin/env python3
"""Pillow font metrics aligned with render_preview.py (PPM=28)."""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

from kamae.types import InkBounds, Mm
from silk_layout import NAME_CAP_HEIGHT_MM, NAME_Y_MM, TEXT_LEFT_MM

PREVIEW_PPM = 28
GEORGIA_BOLD = Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf")
ARIAL = Path("/System/Library/Fonts/Supplemental/Arial.ttf")


def _font(path: Path, cap_height_mm: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), max(8, int(cap_height_mm * PREVIEW_PPM)))


def line_ink_width_mm(text: str, *, font_size_mm: float, font_path: Path = ARIAL) -> float:
    bb = _font(font_path, font_size_mm).getbbox(text)
    return (bb[2] - bb[0]) / PREVIEW_PPM


def line_ink_bounds_mm(
    text: str,
    *,
    origin_x_mm: float,
    origin_y_mm: float,
    font_size_mm: float,
    font_path: Path = ARIAL,
    anchor: str = "lt",
) -> InkBounds:
    """Return ink box in preview mm (Y down from top)."""
    bb = _font(font_path, font_size_mm).getbbox(text)
    left = Mm(origin_x_mm + bb[0] / PREVIEW_PPM)
    right = Mm(origin_x_mm + bb[2] / PREVIEW_PPM)
    if anchor == "lt":
        top = Mm(origin_y_mm + bb[1] / PREVIEW_PPM)
        bottom = Mm(origin_y_mm + bb[3] / PREVIEW_PPM)
    elif anchor == "lb":
        bottom = Mm(origin_y_mm + bb[1] / PREVIEW_PPM)
        top = Mm(origin_y_mm + bb[3] / PREVIEW_PPM)
    else:
        raise ValueError(anchor)
    return InkBounds(left=left, bottom=bottom, right=right, top=top)


def block_max_ink_width_mm(
    lines: tuple[str, ...],
    *,
    origin_x_mm: float,
    font_size_mm: float,
    font_path: Path = ARIAL,
) -> float:
    return max(line_ink_width_mm(line, font_size_mm=font_size_mm, font_path=font_path) for line in lines)


def name_ink_bounds_mm(text: str) -> InkBounds:
    """Preview ENIG name ink box (Georgia Bold, anchor lt at NAME_Y)."""
    return line_ink_bounds_mm(
        text,
        origin_x_mm=float(TEXT_LEFT_MM),
        origin_y_mm=float(NAME_Y_MM),
        font_size_mm=float(NAME_CAP_HEIGHT_MM),
        font_path=GEORGIA_BOLD,
        anchor="lt",
    )
