#!/usr/bin/env python3
"""Lightweight geometric checks."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from card_copy import NAME  # noqa: E402
from copper_checks import (  # noqa: E402
    check_geometry,
    check_pcb_file,
)
from generate_kicad_project import (  # noqa: E402
    BOARD_H,
    BOARD_W,
    GAP,
    TEXT_ZONE_W,
    TRACE_W,
    TURNS,
    NC_TERMINATORS,
    feed_routes,
    feed_vias,
    gnd_island_route,
    nc_terminator_placements,
    nc_terminator_routes,
    nfc_layout,
    xqfn_pad_wh,
)
from jlcpcb_limits import (  # noqa: E402
    ANT_TIE_TAKEOFF_DX_MM,
    ANT_TIE_VIA_DY_MM,
    ANTENNA_FEED_PAD_D_MM,
    ANTENNA_GAP_MM,
    ANTENNA_TRACE_W_MM,
    DESIGN_MASK_BRIDGE_MM,
    DESIGN_TRACE_CLEARANCE_MM,
    FEED_BUS_HALF_PITCH_MM,
    FEED_LA_BYPASS_DX_MM,
    FEED_TRACE_W_MM,
    FEED_VIA_DRILL_MM,
    FEED_VIA_SIZE_MM,
    GND_ISLAND_DX_MM,
    GND_ISLAND_H_MM,
    GND_ISLAND_W_MM,
    JLC_MIN_MASK_BRIDGE_MM,
    JLC_MIN_TRACE_CLEARANCE_MM,
    JLC_MIN_TRACE_WIDTH_MM,
    NC_TERM_GND_BUS_INSET_MM,
    NC_TERM_R_OFFSET_MM,
    R0402_PAD_OFFSET_MM,
    XQFN_PAD_EDGE_MM,
    XQFN_PAD_ROW_MM,
    XQFN_PITCH_MM,
)
from silk_layout import NAME_CAP_HEIGHT_MM, NAME_RIGHT_MARGIN_MM, NAME_X_MM, ROLES_Y0_MM, TEXT_ZONE_W  # noqa: E402
from layout_metrics import name_ink_bounds_mm  # noqa: E402

errors: list[str] = []
warnings: list[str] = []

lay = nfc_layout()
pts = lay["ant_pts"]
abs_pts = [(lay["ant_cx"] + x, lay["ant_cy"] + y) for x, y in pts]
u1_x, u1_y = lay["u1"]

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
# Spiral is now netted F.Cu tracks (net LA) — include them in the LA-vs-LB scan
coil = [
    (lay["ant_cx"] + a[0], lay["ant_cy"] + a[1], lay["ant_cx"] + b[0], lay["ant_cy"] + b[1], "LA", TRACE_W, "F.Cu")
    for a, b in zip(pts, pts[1:])
]
all_segs = coil + routes
for i, a in enumerate(all_segs):
    x0, y0, x1, y1, net_a, _w, layer_a = a
    for j, b in enumerate(all_segs[i + 1 :], start=i + 1):
        x2, y2, x3, y3, net_b, _w2, layer_b = b
        if net_a == net_b or layer_a != layer_b:
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

# F.Cu LB must not cross the antenna left edge (historical short through outer turn)
ant_left = lay["ant_x0"]
lb_cross = False
for x0, y0, x1, y1, net, w, layer in routes:
    if net != "LB" or layer != "F.Cu":
        continue
    if abs(y0 - y1) < 1e-9:  # horizontal
        lo, hi = sorted((x0, x1))
        if lo < ant_left < hi:
            errors.append(f"LB F.Cu crosses antenna left edge at y={y0:.2f}")
            lb_cross = True
    if abs(x0 - x1) < 1e-9 and abs(x0 - ant_left) < (TRACE_W + w) / 2:
        errors.append(f"LB F.Cu runs on antenna left edge at x={x0:.2f}")
        lb_cross = True
if not lb_cross:
    print("OK: LB F.Cu stays clear of antenna left edge (B.Cu underpass)")

la_bus = u1[0] - FEED_BUS_HALF_PITCH_MM
lb_bus = u1[0] + FEED_BUS_HALF_PITCH_MM
bus_gap = lb_bus - la_bus - FEED_TRACE_W_MM
if bus_gap < JLC_MIN_TRACE_CLEARANCE_MM:
    errors.append(f"LA/LB bus gap {bus_gap:.3f} mm < JLC min {JLC_MIN_TRACE_CLEARANCE_MM} mm")
elif bus_gap < DESIGN_TRACE_CLEARANCE_MM:
    warnings.append(f"LA/LB bus gap {bus_gap:.3f} mm below design target {DESIGN_TRACE_CLEARANCE_MM} mm")
else:
    print(f"OK: LA/LB bus gap {bus_gap:.3f} mm (pitch {lb_bus - la_bus:.2f} mm)")

la_bypass = u1_x - FEED_LA_BYPASS_DX_MM
if la_bypass - FEED_TRACE_W_MM / 2 < TEXT_ZONE_W:
    errors.append(f"LA bypass x={la_bypass:.2f} enters text zone")
else:
    print(f"OK: LA bypass x={la_bypass:.2f} mm (skirts left of U1)")

# Feed traces must not hit NC pads (FD/SCL/SDA/VCC/VOUT) or wrong nets
# Pad centres relative to U1; half-sizes after orientation
xqfn_pads = {
    "1": (-0.20, 0.75, 90, "LA"),
    "2": (-0.75, 0.20, 0, "GND"),
    "3": (-0.75, -0.20, 0, "SCL"),
    "4": (-0.20, -0.75, 90, "FD"),
    "5": (0.20, -0.75, 90, "SDA"),
    "6": (0.75, -0.20, 0, "VCC"),
    "7": (0.75, 0.20, 0, "VOUT"),
    "8": (0.20, 0.75, 90, "LB"),
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


def seg_hits_rect(
    x0: float, y0: float, x1: float, y1: float, w: float, rect: tuple[float, float, float, float]
) -> bool:
    """Axis-aligned segment vs axis-aligned rect, with half-width inflation."""
    rx0, ry0, rx1, ry1 = rect
    hw = w / 2
    if abs(y0 - y1) < 1e-9:  # horizontal
        sy = y0
        lo, hi = sorted((x0, x1))
        return not (hi < rx0 - hw or lo > rx1 + hw or sy < ry0 - hw or sy > ry1 + hw)
    if abs(x0 - x1) < 1e-9:  # vertical
        sx = x0
        lo, hi = sorted((y0, y1))
        return not (sx < rx0 - hw or sx > rx1 + hw or hi < ry0 - hw or lo > ry1 + hw)
    return False


for num, (px, py, rot, pad_net) in xqfn_pads.items():
    rect = pad_bbox(u1_x + px, u1_y + py, rot)
    for x0, y0, x1, y1, net, w, layer in routes:
        if layer != "F.Cu":
            continue
        if pad_net not in ("NC",) and net == pad_net:
            continue  # intentional connection to LA/LB/GND/NC-pin nets
        if seg_hits_rect(x0, y0, x1, y1, w, rect):
            errors.append(f"Feed net {net} hits U1 pad {num} ({pad_net}) — copper short")

print("OK: feed routes clear of unrelated U1 pads")

gnd_x = u1_x - GND_ISLAND_DX_MM
gnd_bus_x = gnd_x - GND_ISLAND_W_MM / 2 - NC_TERM_GND_BUS_INSET_MM
nc_places = nc_terminator_placements((u1_x, u1_y))
if len(nc_places) != len(NC_TERMINATORS):
    errors.append(f"Expected {len(NC_TERMINATORS)} NC terminators, got {len(nc_places)}")
for ref, _net, rcx, _rcy, _pad_x, _pad_y in nc_places:
    body_left = rcx - R0402_PAD_OFFSET_MM - 0.31
    if body_left < TEXT_ZONE_W:
        errors.append(f"{ref} B.Cu body enters text zone (x={body_left:.2f})")
    if rcx > lay["ant_x0"]:
        errors.append(f"{ref} outside component strip")
if gnd_bus_x < TEXT_ZONE_W:
    errors.append(f"NC GND bus x={gnd_bus_x:.2f} enters text zone")
else:
    print(f"OK: NC terminators R2–R6 on B.Cu, GND bus x={gnd_bus_x:.2f} mm")

if TRACE_W < JLC_MIN_TRACE_WIDTH_MM:
    errors.append(f"Antenna trace {TRACE_W} mm < JLC min")
if GAP < DESIGN_TRACE_CLEARANCE_MM:
    warnings.append(f"Antenna turn gap {GAP} mm below design target {DESIGN_TRACE_CLEARANCE_MM} mm")
elif GAP >= DESIGN_TRACE_CLEARANCE_MM:
    print(f"OK: antenna turn gap {GAP:.2f} mm")

feed_clr = (ANTENNA_TRACE_W_MM + ANTENNA_GAP_MM) - ANTENNA_FEED_PAD_D_MM / 2 - ANTENNA_TRACE_W_MM / 2
if feed_clr < JLC_MIN_TRACE_CLEARANCE_MM:
    errors.append(f"LB net-tie pad vs turn-5 clearance {feed_clr:.3f} mm < JLC min {JLC_MIN_TRACE_CLEARANCE_MM} mm")
elif feed_clr < DESIGN_TRACE_CLEARANCE_MM - 1e-9:
    warnings.append(f"LB net-tie pad vs turn-5 clearance {feed_clr:.3f} mm below design target {DESIGN_TRACE_CLEARANCE_MM} mm")
else:
    print(f"OK: LB net-tie pad Ø{ANTENNA_FEED_PAD_D_MM} mm, turn-5 clearance {feed_clr:.3f} mm")

# LB net-tie pad 2 sits 1.3 mm right of the coil lead-out (via_in take-off)
leadout_clr = 1.3 - ANTENNA_FEED_PAD_D_MM / 2 - ANTENNA_TRACE_W_MM / 2
if leadout_clr < DESIGN_TRACE_CLEARANCE_MM:
    errors.append(f"LB net-tie pad vs coil lead-out clearance {leadout_clr:.3f} mm too tight")
else:
    print(f"OK: LB net-tie pad vs coil lead-out {leadout_clr:.2f} mm")

# Net-tie bridge: pad1 (LA roundrect, coil end→take-off) must overlap pad2
# (LB roundrect, take-off→via_in) — that physical overlap is what closes the
# coil to the LB feed without a cross-net track touch.
tie_x0, tie_y0 = ant2
tie_x1 = tie_x0 + ANT_TIE_TAKEOFF_DX_MM
p1 = (tie_x0, tie_y0 - ANTENNA_FEED_PAD_D_MM / 2, tie_x1, tie_y0 + ANTENNA_FEED_PAD_D_MM / 2)
p2 = (tie_x1 - ANTENNA_FEED_PAD_D_MM / 2, tie_y0, tie_x1 + ANTENNA_FEED_PAD_D_MM / 2, tie_y0 + ANT_TIE_VIA_DY_MM)
ov_x = min(p1[2], p2[2]) - max(p1[0], p2[0])
ov_y = min(p1[3], p2[3]) - max(p1[1], p2[1])
if min(ov_x, ov_y) < 0.1:
    errors.append(f"ANT1 net-tie pads overlap only {min(ov_x, ov_y):.3f} mm (need ≥0.1 mm)")
else:
    print(f"OK: ANT1 net-tie pads overlap {ov_x:.2f}×{ov_y:.2f} mm (LA coil end → LB take-off)")

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
f_mhz = 1e3 / (2 * math.pi * math.sqrt(L_uh * 50.0)) if L_uh > 0 else 0.0
print(f"OK: rough L≈{L_uh:.2f} µH → f_res≈{f_mhz:.1f} MHz with Cin=50 pF (C1 may be needed)")
if not (1.5 <= L_uh <= 6.0):
    warnings.append(f"L estimate {L_uh:.2f} µH outside expected band")

gnd_routes = gnd_island_route(lay["u1"])
gnd_x = u1_x - GND_ISLAND_DX_MM
gnd_y = u1_y + 0.20
if gnd_x <= TEXT_ZONE_W or gnd_x >= lay["ant_x0"]:
    errors.append(f"GND island x={gnd_x:.2f} not in component strip")
elif not gnd_routes:
    errors.append("GND island route missing")
else:
    bypass_edge = la_bypass + FEED_TRACE_W_MM / 2
    island_left = gnd_x - GND_ISLAND_W_MM / 2
    if island_left < bypass_edge + JLC_MIN_TRACE_CLEARANCE_MM:
        errors.append(
            f"GND island vs LA bypass clearance too tight "
            f"(island {gnd_x:.2f}, bypass {la_bypass:.2f})"
        )
    else:
        # Clearance to SCL (pad 3) — historical DRC hit with oversized island
        scl = pad_bbox(u1_x - 0.75, u1_y - 0.20, 0)
        island = (
            gnd_x - GND_ISLAND_W_MM / 2,
            gnd_y - GND_ISLAND_H_MM / 2,
            gnd_x + GND_ISLAND_W_MM / 2,
            gnd_y + GND_ISLAND_H_MM / 2,
        )
        gnd_scl = rect_gap(island, scl)
        if gnd_scl < DESIGN_TRACE_CLEARANCE_MM:
            errors.append(f"GND island vs SCL clearance {gnd_scl:.3f} mm < {DESIGN_TRACE_CLEARANCE_MM} mm")
        else:
            print(f"OK: local GND island at x={gnd_x:.2f} mm (vs SCL {gnd_scl:.2f} mm)")

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

# XQFN adjacent pads on the same side: short axis = ROW
row_gap = XQFN_PITCH_MM - XQFN_PAD_ROW_MM
if row_gap < JLC_MIN_MASK_BRIDGE_MM:
    errors.append(f"XQFN same-side pad gap {row_gap:.3f} mm < JLC min {JLC_MIN_MASK_BRIDGE_MM} mm")
elif row_gap < DESIGN_MASK_BRIDGE_MM:
    warnings.append(f"XQFN same-side pad gap {row_gap:.3f} mm below design target {DESIGN_MASK_BRIDGE_MM} mm")
else:
    print(f"OK: XQFN same-side pad gap {row_gap:.3f} mm (row pad {XQFN_PAD_ROW_MM} mm)")

# Explicit side-pad bbox check (catches orientation regressions like 2↔3 overlap)
for a, b in (("2", "3"), ("6", "7"), ("1", "8"), ("4", "5")):
    ra = pad_bbox(u1_x + xqfn_pads[a][0], u1_y + xqfn_pads[a][1], xqfn_pads[a][2])
    rb = pad_bbox(u1_x + xqfn_pads[b][0], u1_y + xqfn_pads[b][1], xqfn_pads[b][2])
    # gap along the shared axis
    ax0, ay0, ax1, ay1 = ra
    bx0, by0, bx1, by1 = rb
    gap = max(0.0, max(ax0 - bx1, bx0 - ax1, ay0 - by1, by0 - ay1))
    if gap < 1e-6:
        errors.append(f"XQFN pads {a}/{b} overlap (orientation bug?)")
    elif abs(gap - row_gap) > 0.02:
        warnings.append(f"XQFN pads {a}/{b} gap {gap:.3f} mm (expected ~{row_gap:.3f})")


p1 = pad_bbox(u1_x - 0.20, u1_y + 0.75, 90)
p2 = pad_bbox(u1_x - 0.75, u1_y + 0.20, 0)
p8 = pad_bbox(u1_x + 0.20, u1_y + 0.75, 90)
p7 = pad_bbox(u1_x + 0.75, u1_y + 0.20, 0)
corner_gap = min(rect_gap(p1, p2), rect_gap(p8, p7))
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

# --- Exhaustive copper: generator geometry + on-disk PCB ----------------
nc_segs, nc_via_raw = nc_terminator_routes(lay["u1"])
gnd_segs = gnd_island_route(lay["u1"])
gen_segs = coil + list(routes) + list(nc_segs) + list(gnd_segs)
gen_vias: list[tuple[float, float, str, float, float]] = [
    (vx, vy, vnet, FEED_VIA_SIZE_MM, FEED_VIA_DRILL_MM)
    for vx, vy, vnet in feed_vias(ant2, lay["u1"], lay["c1"])
]
for item in nc_via_raw:
    if len(item) == 3:
        vx, vy, vnet = item
        gen_vias.append((vx, vy, vnet, 0.5, 0.3))
    else:
        vx, vy, vnet, size, drill = item
        gen_vias.append((vx, vy, vnet, size, drill))

xqfn_pad_rects = []
for num, (px, py, rot, pad_net) in xqfn_pads.items():
    x0, y0, x1, y1 = pad_bbox(u1_x + px, u1_y + py, rot)
    xqfn_pad_rects.append((x0, y0, x1, y1, pad_net, "F.Cu"))

# Net-tie LA/LB overlap is intentional; do not allow other cross-net pairs.
allow_tie = {("LA", "LB")}
gen_result = check_geometry(
    gen_segs,
    gen_vias,
    xqfn_pad_rects,
    design_clearance=DESIGN_TRACE_CLEARANCE_MM,
    hole_clearance=0.25,
    jlc_min=JLC_MIN_TRACE_CLEARANCE_MM,
    board_w=BOARD_W,
    board_h=BOARD_H,
    text_zone_w=TEXT_ZONE_W,
    ant_left=lay["ant_x0"],
    feed_half_w=FEED_TRACE_W_MM / 2,
    allow_net_pairs=allow_tie,
)
if gen_result.kind == "err":
    for issue in gen_result.error:
        errors.append(f"copper(gen) [{issue.kind}] {issue.message}")
else:
    print("OK: generator copper — no cross-net crossings, design clearance ≥ 0.20 mm")

pcb_path = ROOT / "nfc-business-card.kicad_pcb"
if pcb_path.is_file():
    pcb_result = check_pcb_file(
        pcb_path,
        design_clearance=DESIGN_TRACE_CLEARANCE_MM,
        hole_clearance=0.25,
        jlc_min=JLC_MIN_TRACE_CLEARANCE_MM,
        board_w=BOARD_W,
        board_h=BOARD_H,
        text_zone_w=TEXT_ZONE_W,
        ant_left=lay["ant_x0"],
        feed_half_w=FEED_TRACE_W_MM / 2,
        pads=xqfn_pad_rects,
    )
    if pcb_result.kind == "err":
        for issue in pcb_result.error:
            errors.append(f"copper(pcb) [{issue.kind}] {issue.message}")
    else:
        print("OK: PCB copper — no cross-net crossings, design clearance ≥ 0.20 mm")

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
