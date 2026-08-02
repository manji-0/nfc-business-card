"""Rectangular spiral geometry + LC resonance estimates.

Shared by the KiCad generator, layout checks, and the antenna tuner so the
inductance model and the spiral polyline stay a single source of truth.
"""

from __future__ import annotations

import math


def rectangular_spiral(
    cx: float,
    cy: float,
    outer_w: float,
    outer_h: float,
    turns: int,
    width: float,
    gap: float,
) -> list[tuple[float, float]]:
    """Return centerline polyline for a rectangular spiral (outer → inner)."""
    pts: list[tuple[float, float]] = []
    left = cx - outer_w / 2
    right = cx + outer_w / 2
    bottom = cy - outer_h / 2
    top = cy + outer_h / 2
    pitch = width + gap

    # Start at bottom-left outer corner, go CCW inward
    x, y = left, bottom
    pts.append((x, y))
    for t in range(turns):
        # bottom edge L→R
        x = right - t * pitch
        pts.append((x, y))
        # right edge B→T
        y = top - t * pitch
        pts.append((x, y))
        # top edge R→L
        x = left + t * pitch
        pts.append((x, y))
        # left edge T→B (stop short to leave gap for next turn)
        y = bottom + (t + 1) * pitch
        pts.append((x, y))
        # step inward for next bottom start
        if t < turns - 1:
            x = left + (t + 1) * pitch
            pts.append((x, y))
    return pts


def estimate_l_uh(
    outer_w: float, outer_h: float, turns: int, trace_w: float, gap: float
) -> float:
    """Rough Wheeler-style inductance estimate (µH)."""
    d_out = (outer_w + outer_h) / 2
    d_in = d_out - 2 * turns * (trace_w + gap)
    d_avg = (d_out + d_in) / 2
    fill = (d_out - d_in) / (d_out + d_in) if (d_out + d_in) > 0 else 0.0
    return 0.027 * (turns**2) * (d_avg / 10) / (1 + 2.75 * fill)


def f_res_mhz(l_uh: float, c_pf: float) -> float:
    """Resonance MHz from L (µH) and parallel C (pF)."""
    if l_uh <= 0 or c_pf <= 0:
        return 0.0
    return 1e3 / (2 * math.pi * math.sqrt(l_uh * c_pf))


def c_needed_pf(l_uh: float, f_mhz: float) -> float:
    """Parallel capacitance (pF) for a target resonance frequency (MHz)."""
    if l_uh <= 0 or f_mhz <= 0:
        return 0.0
    return (1e3 / (2 * math.pi * f_mhz)) ** 2 / l_uh
