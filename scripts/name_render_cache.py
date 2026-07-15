#!/usr/bin/env python3
"""Parse and transform KiCad gr_text render_cache polygons (ENIG name)."""

from __future__ import annotations

import re
from pathlib import Path

_XY_RE = re.compile(r"\(xy ([\d.-]+) ([\d.-]+)\)")


def parse_render_cache_polys(block: str) -> list[list[tuple[float, float]]]:
    """Extract polygon point lists from a gr_text block or render_cache section."""
    polys: list[list[tuple[float, float]]] = []
    for pts_block in re.finditer(r"\(pts\s*((?:\(xy [^)]+\)\s*)+)\)", block):
        pts = [(float(x), float(y)) for x, y in _XY_RE.findall(pts_block.group(1))]
        if len(pts) >= 3:
            polys.append(pts)
    return polys


def polys_bounds(polys: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    xs = [x for poly in polys for x, _ in poly]
    ys = [y for poly in polys for _, y in poly]
    return min(xs), min(ys), max(xs), max(ys)


def shift_polys(polys: list[list[tuple[float, float]]], dx: float, dy: float) -> list[list[tuple[float, float]]]:
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return polys
    return [[(x + dx, y + dy) for x, y in poly] for poly in polys]


def shift_gr_text_block(block: str, dx: float, dy: float) -> str:
    """Shift (at) and all render_cache (xy) coordinates."""
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return block

    def repl_at(m: re.Match[str]) -> str:
        x, y, rot = m.group(1), m.group(2), m.group(3)
        return f"(at {float(x) + dx:g} {float(y) + dy:g} {rot})"

    def repl_xy(m: re.Match[str]) -> str:
        return f"(xy {float(m.group(1)) + dx:g} {float(m.group(2)) + dy:g})"

    out = re.sub(r"\(at ([\d.-]+) ([\d.-]+) (\d+)\)", repl_at, block, count=1)
    return _XY_RE.sub(repl_xy, out)


def align_gr_text_block_left(block: str, target_left_mm: float) -> str:
    polys = parse_render_cache_polys(block)
    if not polys:
        return block
    min_x, _, _, _ = polys_bounds(polys)
    return shift_gr_text_block(block, target_left_mm - min_x, 0.0)


def _parse_at(block: str) -> tuple[float, float]:
    m = re.search(r"\(at ([\d.-]+) ([\d.-]+) (\d+)\)", block)
    if not m:
        raise ValueError("gr_text block missing (at ...)")
    return float(m.group(1)), float(m.group(2))


def scale_gr_text_block(block: str, scale: float, anchor_x: float, anchor_y: float) -> str:
    """Uniform scale around anchor; updates render_cache, (at), and font size."""
    if abs(scale - 1.0) < 1e-6:
        return block

    def repl_xy(m: re.Match[str]) -> str:
        x, y = float(m.group(1)), float(m.group(2))
        return f"(xy {anchor_x + (x - anchor_x) * scale:g} {anchor_y + (y - anchor_y) * scale:g})"

    def repl_at(m: re.Match[str]) -> str:
        x, y, rot = float(m.group(1)), float(m.group(2)), m.group(3)
        return (
            f"(at {anchor_x + (x - anchor_x) * scale:g} "
            f"{anchor_y + (y - anchor_y) * scale:g} {rot})"
        )

    def repl_size(m: re.Match[str]) -> str:
        sx, sy = float(m.group(1)), float(m.group(2))
        return f"(size {sx * scale:g} {sy * scale:g})"

    def repl_thickness(m: re.Match[str]) -> str:
        return f"(thickness {float(m.group(1)) * scale:g})"

    out = re.sub(r"\(at ([\d.-]+) ([\d.-]+) (\d+)\)", repl_at, block, count=1)
    out = _XY_RE.sub(repl_xy, out)
    out = re.sub(r"\(size ([\d.-]+) ([\d.-]+)\)", repl_size, out)
    out = re.sub(r"\(thickness ([\d.-]+)\)", repl_thickness, out)
    return out


def fit_gr_text_block_width(block: str, max_width_mm: float) -> str:
    """Shrink uniformly (about gr_text anchor) until render_cache fits max width."""
    polys = parse_render_cache_polys(block)
    if not polys:
        return block
    min_x, _, max_x, _ = polys_bounds(polys)
    width = max_x - min_x
    if width <= max_width_mm + 1e-6:
        return block
    anchor_x, anchor_y = _parse_at(block)
    return scale_gr_text_block(block, max_width_mm / width, anchor_x, anchor_y)


def parse_name_polys_from_pcb(pcb_path: Path, *, layer: str = "F.Cu") -> list[list[tuple[float, float]]]:
    text = pcb_path.read_text(encoding="utf-8")
    i = 0
    while i < len(text):
        start = text.find("\t(gr_text ", i)
        if start < 0:
            break
        depth = 0
        j = start
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    block = text[start : j + 1]
                    layer_m = re.search(r'\(layer "([^"]+)"\)', block)
                    if layer_m and layer_m.group(1) == layer:
                        return parse_render_cache_polys(block)
                    i = j + 1
                    break
            j += 1
        else:
            break
    raise FileNotFoundError(f"No gr_text on {layer} in {pcb_path}")
