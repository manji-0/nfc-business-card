#!/usr/bin/env python3
"""Lightweight geometric checks."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from card_copy import NAME  # noqa: E402
from jlcpcb_limits import (  # noqa: E402
    DESIGN_MASK_BRIDGE_MM,
    DESIGN_TRACE_CLEARANCE_MM,
    FEED_BUS_HALF_PITCH_MM,
    FEED_TRACE_W_MM,
    JLC_MIN_MASK_BRIDGE_MM,
    JLC_MIN_TRACE_CLEARANCE_MM,
    JLC_MIN_TRACE_WIDTH_MM,
    XQFN_PAD_EDGE_MM,
    XQFN_PAD_ROW_MM,
    XQFN_PITCH_MM,
)
from generate_kicad_project import (  # noqa: E402
    BOARD_H,
    BOARD_W,
    GAP,
    TEXT_ZONE_W,
    TRACE_W,
    TURNS,
    feed_routes,
    nfc_layout,
    xqfn_pad_wh,
)
from silk_layout import NAME_CAP_HEIGHT_MM, NAME_RIGHT_MARGIN_MM, NAME_X_MM, ROLES_Y0_MM, TEXT_ZONE_W  # noqa: E402
from layout_metrics import name_ink_bounds_mm  # noqa: E402

errors: list[str] = []
warnings: list[str] = []

lay = nfc_layout()
pts = lay["ant_pts"]
abs_pts = [(lay["ant_cx"] + x, lay["ant_cy"] + y) for x, y in pts]

for x, y in abs_pts:
    if x < lay["ant_x0"] - 0.1 or x > BOARD_W or y < 0 or y > BOARD_H:
        errors.append(f"Spiral outside NFC zone: ({x:.2f},{y:.2f})")

# Text zone must stay copper-free (no spiral points)
for x, y in abs_pts:
    if x < TEXT_ZONE_W:
        errors.append(f"Copper in text zone: ({x:.2f},{y:.2f})")

u1 = lay["u1"]
if not (TEXT_ZONE_W <= u1[0] <= lay["ant_x0"]):
    errors.append("U1 not in component strip")
else:
    print(f"OK: U1 at feed ({u1[0]:.2f},{u1[1]:.2f}) mm")

ant1 = (lay["ant_cx"] + pts[0][0], lay["ant_cy"] + pts[0][1])
ant2 = (lay["ant_cx"] + pts[-1][0], lay["ant_cy"] + pts[-1][1])
routes = feed_routes(ant1, ant2, lay["u1"], lay["c1"])
for i, a in enumerate(routes):
    x0, y0, x1, y1, net_a, _w = a
    for j, b in enumerate(routes[i + 1 :], start=i + 1):
        x2, y2, x3, y3, net_b, _w2 = b
        if net_a == net_b:
            continue
        # axis-aligned overlap on shared horizontal or vertical span
        if abs(y0 - y1) < 1e-6 and abs(y2 - y3) < 1e-6 and abs(y0 - y2) < 1e-6:
            lo1, hi1 = sorted((x0, x1))
            lo2, hi2 = sorted((x2, x3))
            if lo1 < hi2 and lo2 < hi1:
                errors.append(f"LA/LB overlap on y={y0:.2f}: seg {i} vs {j}")
        if abs(x0 - x1) < 1e-6 and abs(x2 - x3) < 1e-6 and abs(x0 - x2) < 1e-6:
            lo1, hi1 = sorted((y0, y1))
            lo2, hi2 = sorted((y2, y3))
            if lo1 < hi2 and lo2 < hi1:
                errors.append(f"LA/LB overlap on x={x0:.2f}: seg {i} vs {j}")

print(f"OK: feed routes {len(routes)} segs, no LA/LB overlap")

la_bus = u1[0] - FEED_BUS_HALF_PITCH_MM
lb_bus = u1[0] + FEED_BUS_HALF_PITCH_MM
bus_gap = lb_bus - la_bus - FEED_TRACE_W_MM
if bus_gap < JLC_MIN_TRACE_CLEARANCE_MM:
    errors.append(f"LA/LB bus gap {bus_gap:.3f} mm < JLC min {JLC_MIN_TRACE_CLEARANCE_MM} mm")
elif bus_gap < DESIGN_TRACE_CLEARANCE_MM:
    warnings.append(f"LA/LB bus gap {bus_gap:.3f} mm below design target {DESIGN_TRACE_CLEARANCE_MM} mm")
else:
    print(f"OK: LA/LB bus gap {bus_gap:.3f} mm (pitch {lb_bus - la_bus:.2f} mm)")

if TRACE_W < JLC_MIN_TRACE_WIDTH_MM:
    errors.append(f"Antenna trace {TRACE_W} mm < JLC min")
if GAP < DESIGN_TRACE_CLEARANCE_MM:
    warnings.append(f"Antenna turn gap {GAP} mm below design target {DESIGN_TRACE_CLEARANCE_MM} mm")
elif GAP >= DESIGN_TRACE_CLEARANCE_MM:
    print(f"OK: antenna turn gap {GAP:.2f} mm")

print(f"OK: text zone width {TEXT_ZONE_W:.0f} mm (copper-free)")
print(f"OK: antenna {lay['ant_w']:.1f}×{lay['ant_h']:.1f} mm, {TURNS} turns")

dists = [math.hypot(x - u1[0], y - u1[1]) for x, y in abs_pts]
print(f"OK: chip-to-spiral min distance {min(dists):.2f} mm")

n = TURNS
d_out = (lay["ant_w"] + lay["ant_h"]) / 2
d_in = d_out - 2 * n * (TRACE_W + GAP)
d_avg = (d_out + d_in) / 2
fill = (d_out - d_in) / (d_out + d_in) if (d_out + d_in) else 0
L_uh = 0.027 * (n**2) * (d_avg / 10) / (1 + 2.75 * fill)
print(f"OK: rough L≈{L_uh:.2f} µH (nominal ~14.5 MHz with 50 pF + parasitics)")
if not (1.5 <= L_uh <= 6.0):
    warnings.append(f"L estimate {L_uh:.2f} µH outside expected band")

pcb_path = ROOT / "nfc-business-card.kicad_pcb"
name_bottom_preview = float(name_ink_bounds_mm(NAME).bottom)
name_roles_gap = ROLES_Y0_MM - name_bottom_preview
if name_roles_gap < 1.8:
    errors.append(f"Name/roles gap {name_roles_gap:.2f} mm < 1.8 mm (preview coords)")
else:
    print(f"OK: name→roles gap {name_roles_gap:.1f} mm (preview)")

if pcb_path.exists():
    from name_render_cache import parse_name_polys_from_pcb, polys_bounds

    try:
        polys = parse_name_polys_from_pcb(pcb_path)
        _, name_min_y, name_right, _name_max_y = polys_bounds(polys)
        margin = TEXT_ZONE_W - name_right
        target = name_ink_bounds_mm(NAME)
        target_right = float(target.right)
        if abs(name_right - target_right) > 0.3:
            warnings.append(f"Name right {name_right:.2f} mm vs preview target {target_right:.2f} mm")
        elif margin < NAME_RIGHT_MARGIN_MM - 0.5:
            errors.append(
                f"Name right edge {name_right:.2f} mm leaves only {margin:.2f} mm "
                f"to text zone (need ≥{NAME_RIGHT_MARGIN_MM} mm)"
            )
        else:
            print(
                f"OK: ENIG name right {name_right:.1f} mm "
                f"({margin:.1f} mm to circuit zone, preview-aligned)"
            )
    except FileNotFoundError:
        warnings.append("No ENIG name gr_text in PCB — run generate_kicad_project.py")
else:
    name_w_est = NAME_CAP_HEIGHT_MM * 0.58 * len(NAME.replace(" ", "")) + NAME_CAP_HEIGHT_MM * 0.35
    name_right = NAME_X_MM + name_w_est
    if name_right > TEXT_ZONE_W - NAME_RIGHT_MARGIN_MM:
        warnings.append(f"Name may exceed text zone ({name_right:.1f} > {TEXT_ZONE_W - NAME_RIGHT_MARGIN_MM:.1f} mm)")

# XQFN pad 1 (LA) vs 8 (LB) — row pads on top edge
row_gap = XQFN_PITCH_MM - XQFN_PAD_ROW_MM
if row_gap < JLC_MIN_MASK_BRIDGE_MM:
    errors.append(f"XQFN pads 1/8 gap {row_gap:.3f} mm < JLC min {JLC_MIN_MASK_BRIDGE_MM} mm")
elif row_gap < DESIGN_MASK_BRIDGE_MM:
    warnings.append(f"XQFN pads 1/8 gap {row_gap:.3f} mm below design target {DESIGN_MASK_BRIDGE_MM} mm")
else:
    print(f"OK: XQFN pads 1/8 gap {row_gap:.3f} mm (row pad {XQFN_PAD_ROW_MM} mm)")

# Pad corner clearance: pad 1 vs pad 2 (top-left corner)
pads = {
    "1": (-0.20, 0.75, 90),
    "8": (0.20, 0.75, 90),
    "2": (-0.75, 0.20, 0),
}


def pad_bbox(x: float, y: float, rot: float) -> tuple[float, float, float, float]:
    pw, ph = xqfn_pad_wh(rot)
    if int(rot) % 180 == 90:
        hw, hh = ph / 2, pw / 2
    else:
        hw, hh = pw / 2, ph / 2
    return x - hw, y - hh, x + hw, y + hh


def rect_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(0.0, max(ax0 - bx1, bx0 - ax1))
    dy = max(0.0, max(ay0 - by1, by0 - ay1))
    return math.hypot(dx, dy)


p1 = pad_bbox(*pads["1"])
p8 = pad_bbox(*pads["8"])
p2 = pad_bbox(*pads["2"])
corner_gap = min(rect_gap(p1, p2), rect_gap(p8, pad_bbox(0.75, 0.20, 0)))
if corner_gap < JLC_MIN_MASK_BRIDGE_MM:
    errors.append(f"XQFN corner pad gap {corner_gap:.3f} mm < JLC min {JLC_MIN_MASK_BRIDGE_MM} mm")
elif corner_gap < DESIGN_MASK_BRIDGE_MM:
    warnings.append(f"XQFN corner pad gap {corner_gap:.3f} mm below design target {DESIGN_MASK_BRIDGE_MM} mm")
else:
    print(f"OK: XQFN corner pad gap {corner_gap:.3f} mm (edge pad {XQFN_PAD_EDGE_MM} mm)")

for rel in [
    "nfc-business-card.kicad_pcb",
    "fab/bom.csv",
    "fab/positions.csv",
    "fab/preview.png",
    "README.md",
]:
    if not (ROOT / rel).exists():
        warnings.append(f"Missing {rel}")

if warnings:
    print("Warnings:")
    for w in warnings:
        print(f"  - {w}")
if errors:
    print("Errors:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print("Layout checks passed.")
