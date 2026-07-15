#!/usr/bin/env python3
"""Append PNG silk graphics to KiCad Gerber silk files.

KiCad does not export embedded PCB ``(image)`` bitmaps to Gerber. This module
rasterizes the same PNG assets used in the PCB generator into Gerber region
polygons (G36) so JLCPCB receives the full silkscreen artwork.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from kicad_bitmap import image_scale_for_size, load_ink_mask, resize_for_silk
from silk_layout import SILK_BITMAP_PX_PER_MM

PPI = 300
MM_PER_INCH = 25.4


def mm_to_gerber(x_mm: float, y_preview_mm: float) -> str:
    """Preview coords (Y down from top) → KiCad Gerber 4.6 (Y negative down)."""
    gx = int(round(x_mm * 1_000_000))
    gy = int(round(-y_preview_mm * 1_000_000))
    return f"X{gx}Y{gy}"


def _g36_rect(x0: float, y0: float, x1: float, y1: float) -> list[str]:
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))
    lines = ["G36*"]
    for i, (x, y) in enumerate(corners):
        op = "02" if i == 0 else "01"
        lines.append(f"{mm_to_gerber(x, y)}D{op}*")
    lines.append("G37*")
    return lines


def _ink_mask_rgba(path: Path, *, alpha_threshold: int = 160) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    out = Image.new("1", (w, h), 0)
    src, dst = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a >= alpha_threshold and max(r, g, b) > 32:
                dst[x, y] = 1
    return out


@dataclass(frozen=True, slots=True)
class SilkBitmap:
    path: Path
    at_x_mm: float
    at_y_mm: float
    layer: str
    center: bool = False
    size_mm: float | None = None
    px_per_mm: float = SILK_BITMAP_PX_PER_MM

    def origin_mm(self) -> tuple[float, float, float, Image.Image]:
        """Return top-left (x, y), pixel pitch in mm, and ink mask."""
        if self.size_mm is not None:
            im = resize_for_silk(load_ink_mask(self.path), self.size_mm)
            w, h = im.size
            draw_w = self.size_mm * (w / max(w, h))
            draw_h = self.size_mm * (h / max(w, h))
            px_per_mm = max(w, h) / self.size_mm
            mask = im
        else:
            im = _ink_mask_rgba(self.path)
            w, h = im.size
            px_per_mm = self.px_per_mm
            draw_w = w / px_per_mm
            draw_h = h / px_per_mm
            mask = im

        if self.center:
            ox = self.at_x_mm - draw_w / 2
            oy = self.at_y_mm - draw_h / 2
        else:
            ox, oy = self.at_x_mm, self.at_y_mm
        return ox, oy, px_per_mm, mask


def regions_for_bitmap(item: SilkBitmap) -> list[str]:
    ox, oy, px_per_mm, mask = item.origin_mm()
    w, h = mask.size
    src = mask.load()
    lines: list[str] = []
    pitch = 1.0 / px_per_mm

    for py in range(h):
        px = 0
        while px < w:
            while px < w and not src[px, py]:
                px += 1
            if px >= w:
                break
            run_start = px
            while px < w and src[px, py]:
                px += 1
            x0 = ox + run_start / px_per_mm
            x1 = ox + px / px_per_mm
            y0 = oy + py / px_per_mm
            y1 = y0 + pitch
            lines.extend(_g36_rect(x0, y0, x1, y1))
    return lines


def append_bitmaps_to_gerber(gerber_path: Path, items: list[SilkBitmap]) -> int:
    """Insert G36 regions before the file terminator. Returns region count."""
    text = gerber_path.read_text(encoding="utf-8")
    if "M02*" not in text:
        raise ValueError(f"unexpected gerber terminator in {gerber_path}")

    regions: list[str] = []
    for item in items:
        regions.extend(regions_for_bitmap(item))

    if not regions:
        return 0

    body = text.rsplit("M02*", 1)[0].rstrip() + "\n"
    gerber_path.write_text(body + "\n".join(regions) + "\nM02*\n", encoding="utf-8")
    return len(regions)
