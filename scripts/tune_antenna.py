#!/usr/bin/env python3
"""Antenna LC resonance estimates: C1 trim and turn-count trade-offs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from antenna_model import (  # noqa: E402
    c_needed_pf,
    estimate_l_uh,
    f_res_mhz,
    rectangular_spiral,
)
from generate_kicad_project import (  # noqa: E402
    BOARD_H,
    BOARD_W,
    GAP,
    TEXT_ZONE_W,
    TRACE_W,
    COMP_STRIP_W,
    ANT_INSET,
    nfc_layout,
)

CIN_PF = 50.0  # NT3H2111 on-chip input capacitance (typ)
CPAR_PF = 3.0  # layout + inter-turn parasitic estimate (first-article trim refines)
F_TARGET_MHZ = 13.56
F_AN11276_SINGLE_MHZ = 14.5  # AN11276 nominal for single-tag operation


def spiral_fits(turns: int) -> tuple[bool, str, float, float]:
    ant_w = BOARD_W - TEXT_ZONE_W - COMP_STRIP_W - ANT_INSET
    ant_h = BOARD_H - 2 * ANT_INSET
    ant_cx = TEXT_ZONE_W + COMP_STRIP_W + ant_w / 2
    ant_cy = BOARD_H / 2
    pts = rectangular_spiral(0, 0, ant_w, ant_h, turns, TRACE_W, GAP)
    abs_pts = [(ant_cx + x, ant_cy + y) for x, y in pts]
    ant_x0 = TEXT_ZONE_W + COMP_STRIP_W
    for x, y in abs_pts:
        if x < ant_x0 - 0.1 or x > BOARD_W or y < 0 or y > BOARD_H:
            return False, f"spiral point ({x:.2f},{y:.2f}) out of NFC zone", ant_w, ant_h
        if x < TEXT_ZONE_W:
            return False, f"spiral enters text zone at ({x:.2f},{y:.2f})", ant_w, ant_h
    return True, "OK", ant_w, ant_h


def print_c1_table(l_uh: float) -> None:
    c_base = CIN_PF + CPAR_PF
    f_bare = f_res_mhz(l_uh, c_base)
    print(f"\n## C1 trim (L≈{l_uh:.2f} µH, Cin={CIN_PF:.0f} pF + Cpar≈{CPAR_PF:.0f} pF)")
    print(f"Bare resonance (no C1): {f_bare:.2f} MHz")
    for target in (F_TARGET_MHZ, F_AN11276_SINGLE_MHZ):
        c_tot = c_needed_pf(l_uh, target)
        c1 = c_tot - c_base
        print(f"  Target {target:.2f} MHz → C_total≈{c_tot:.1f} pF → C1≈{c1:.1f} pF")
    print("\n| C1 (pF) | f_res (MHz) | note |")
    print("|---------|-------------|------|")
    for c1 in (0, 5, 10, 12, 15, 18, 22, 27, 33):
        f = f_res_mhz(l_uh, c_base + c1)
        note = ""
        if abs(f - F_TARGET_MHZ) < 0.3:
            note = "← near 13.56 MHz"
        elif abs(f - F_AN11276_SINGLE_MHZ) < 0.3:
            note = "← AN11276 single-tag band"
        print(f"| {c1:5d} | {f:11.2f} | {note} |")


def print_turn_comparison() -> None:
    print("\n## Turn-count comparison (same outer envelope)")
    print("| turns | L (µH) | f bare (MHz) | C1→13.56 MHz | C1→14.5 MHz | geometry |")
    print("|-------|--------|--------------|--------------|-------------|----------|")
    for n in (4, 5, 6, 7):
        ok, msg, aw, ah = spiral_fits(n)
        l_uh = estimate_l_uh(aw, ah, n, TRACE_W, GAP)
        c_base = CIN_PF + CPAR_PF
        f0 = f_res_mhz(l_uh, c_base)
        c1_1356 = c_needed_pf(l_uh, F_TARGET_MHZ) - c_base
        c1_145 = c_needed_pf(l_uh, F_AN11276_SINGLE_MHZ) - c_base
        geom = "OK" if ok else msg[:24]
        print(
            f"| {n:5d} | {l_uh:6.2f} | {f0:12.2f} | {c1_1356:12.1f} | {c1_145:11.1f} | {geom} |"
        )


def main() -> None:
    lay = nfc_layout()
    l5 = estimate_l_uh(lay["ant_w"], lay["ant_h"], 5, TRACE_W, GAP)
    print("NFC business card — antenna tuning estimates")
    print(f"Board {BOARD_W}×{BOARD_H} mm, text zone {TEXT_ZONE_W} mm, comp strip {COMP_STRIP_W} mm")
    print(f"Current design: {lay['ant_w']:.1f}×{lay['ant_h']:.1f} mm, {5} turns")
    print_c1_table(l5)
    print_turn_comparison()
    ok6, msg6, _, _ = spiral_fits(6)
    print("\n## 6-turn recommendation")
    l6 = estimate_l_uh(lay["ant_w"], lay["ant_h"], 6, TRACE_W, GAP)
    c1_6 = c_needed_pf(l6, F_AN11276_SINGLE_MHZ) - (CIN_PF + CPAR_PF)
    if ok6:
        print(f"Geometry: {msg6}")
        print(f"L≈{l6:.2f} µH (vs {l5:.2f} µH at 5 turns); bare f≈{f_res_mhz(l6, CIN_PF + CPAR_PF):.1f} MHz")
        print(f"C1 for 14.5 MHz ≈ {c1_6:.0f} pF (vs ≈ {c_needed_pf(l5, F_AN11276_SINGLE_MHZ) - (CIN_PF + CPAR_PF):.0f} pF at 5 turns)")
        print("Prefer C1 trim first; 6 turns if range stays poor after populated C1.")
    else:
        print(f"6 turns does NOT fit: {msg6}")
        print("Stay at 5 turns; tune with C1 only.")


if __name__ == "__main__":
    main()
