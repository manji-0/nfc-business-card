#!/usr/bin/env python3
"""Generate KiCad 10 project for NFC business card (89x51 mm)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from card_copy import NAME
from jlcpcb_limits import (
    ANT_INSET_MM,
    ANT_TIE_TAKEOFF_DX_MM,
    ANT_TIE_VIA_DY_MM,
    ANTENNA_FEED_PAD_D_MM,
    ANTENNA_GAP_MM,
    ANTENNA_TRACE_W_MM,
    FEED_BUS_HALF_PITCH_MM,
    FEED_BUS_W_MM,
    FEED_LA_TAKEOFF_DX_MM,
    FEED_TRACE_W_MM,
    FEED_VIA_OUT_DX_MM,
    FEED_VIA_OUT_DY_MM,
    FEED_VIA_SIZE_MM,
    FEED_VIA_DRILL_MM,
    FEED_LB_JOIN_DX_MM,
    GND_ISLAND_DX_MM,
    GND_ISLAND_DY_MM,
    GND_ISLAND_H_MM,
    GND_ISLAND_W_MM,
    NC_R_COL_DX_MM,
    NC_STUB_NARROW_W_MM,
    NC_TERM_GND_BUS_INSET_MM,
    NC_TERM_R_LCSC,
    NC_TERM_R_KOHM,
    NC_VIA_DRILL_MM,
    NC_VIA_GND_DY_MM,
    NC_VIA_SIZE_MM,
    R0402_PAD_OFFSET_MM,
)
from antenna_model import estimate_l_uh, f_res_mhz, rectangular_spiral
from bake_name_enig import bake_name_enig_sexpr
from kamae.boundary import require_existing_file
from kamae.result import Err, unwrap
from kicad10 import (
    PCB_FORMAT_VERSION,
    fp_circle,
    fp_line,
    fp_pad_circle,
    fp_pad_connect_roundrect,
    fp_pad_roundrect,
    fp_rect,
    footprint_property,
    gr_line,
    gr_rect,
    gr_text,
    pcb_header,
    pcb_layers,
    pcb_setup,
    quuid,
    segment,
    via,
)
from kicad_bitmap import bitmap_sexpr, bitmap_sexpr_rgba
from symbol_lib import symbol_bodies, symbol_bodies_embedded
from silk_layout import (
    BOARD_H,
    BOARD_W,
    CONTACT_X_MM,
    NAME_CAP_HEIGHT_MM,
    NAME_FONT_FACE,
    NAME_X_MM,
    NAME_Y_MM,
    NFC_LOGO_SIZE_MM,
    QR_X_MM,
    ROLES_Y0_MM,
    TEXT_LEFT_MM,
    TEXT_ZONE_W,
    back_logo_grid,
    contact_top_y_mm,
    qr_size_mm,
    qr_top_y_mm,
)
from xqfn_geometry import XQFN_PADS, xqfn_pad_wh

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
FAB = ROOT / "fab"
ASSETS = ROOT / "assets"
LOGOS = ASSETS / "logos"

ANT_INSET = ANT_INSET_MM
COMP_STRIP_W = 7.0  # U1 + C1 between text and antenna
TRACE_W = ANTENNA_TRACE_W_MM
GAP = ANTENNA_GAP_MM
TURNS = 5  # ~1.9–2.1 µH → ~15–16 MHz with 50 pF alone; C1 DNP for first-article trim
C1_LCSC = "C301961"  # Walsin 0402N100J500CT 10 pF NP0 — primary tuning cap
FEED_TRACE_W = FEED_TRACE_W_MM
# NC pins terminated to VSS via DNP 100 kΩ on B.Cu (R2–R6)


@dataclass(frozen=True, slots=True)
class NcTerminator:
    """One DNP pull-down resistor: reference, NC net, U1-relative pad offset."""

    ref: str
    net: str
    pad_dx: float
    pad_dy: float


@dataclass(frozen=True, slots=True)
class NcFanout:
    """Per-net NC fan-out: F.Cu stub → via → B.Cu jog to column → south row.

    Columns west→east / rows north→south so HV routes on B.Cu never cross.
    """

    pad: tuple[float, float]
    stub: tuple[tuple[float, float], ...]
    via: tuple[float, float]
    col: float
    row: float
    narrow: bool = False
    bc_via_y: float | None = None


NC_TERMINATORS: tuple[NcTerminator, ...] = (
    NcTerminator("R2", "SCL", -0.75, -0.20),
    NcTerminator("R4", "FD", -0.20, -0.75),
    NcTerminator("R3", "SDA", 0.20, -0.75),
    NcTerminator("R5", "VCC", 0.75, -0.20),
    NcTerminator("R6", "VOUT", 0.75, 0.20),
)
# NC fan-out: short F.Cu stub → via → B.Cu (jog to col) → south → R pad 1.
# VOUT enters via a north B.Cu lane (above other NC vias) then joins the
# easternmost west-channel column.
NC_FANOUT: dict[str, NcFanout] = {
    "SCL": NcFanout(
        pad=(-0.75, -0.20),
        stub=((-0.75, -0.20), (-2.00, -0.20), (-2.00, -0.85)),
        via=(-2.00, -0.85),
        col=-2.00,  # abs 51.50
        row=4.80,
        narrow=True,
    ),
    "FD": NcFanout(
        pad=(-0.20, -0.75),
        stub=((-0.20, -0.75), (-1.30, -0.75), (-1.30, -1.55)),
        via=(-1.30, -1.55),
        col=-1.30,  # abs 52.20
        row=6.00,
        narrow=True,
    ),
    "SDA": NcFanout(
        pad=(0.20, -0.75),
        stub=((0.20, -0.75), (1.05, -0.75), (1.05, -2.25)),
        via=(1.05, -2.25),
        col=-0.60,  # abs 52.90
        row=7.20,
        narrow=True,
    ),
    "VCC": NcFanout(
        pad=(0.75, -0.20),
        stub=((0.75, -0.20), (1.70, -0.20), (1.70, -1.20)),
        via=(1.70, -1.20),
        col=0.10,  # abs 53.60
        row=8.40,
        narrow=True,
    ),
    "VOUT": NcFanout(
        pad=(0.75, 0.20),
        stub=((0.75, 0.20), (2.30, 0.20), (2.30, -0.05)),
        via=(2.30, -0.05),
        col=2.30,  # abs 55.80
        row=9.60,
        narrow=True,
        bc_via_y=-2.80,  # north jog lane above other NC vias
    ),
}
# Stable root schematic UUID — reused in .kicad_pro sheets and symbol instance paths.
SCHEMATIC_ROOT_UUID = "db0e1d12-1252-490b-9c29-4e9a9001ab69"


def nfc_layout():
    """Return antenna size/centre and component positions (mm)."""
    ant_w = BOARD_W - TEXT_ZONE_W - COMP_STRIP_W - ANT_INSET
    ant_h = BOARD_H - 2 * ANT_INSET
    ant_cx = TEXT_ZONE_W + COMP_STRIP_W + ant_w / 2
    ant_cy = BOARD_H / 2
    ant_pts = rectangular_spiral(0, 0, ant_w, ant_h, TURNS, TRACE_W, GAP)
    feed_la_y = ant_cy + ant_pts[0][1]
    feed_lb_y = ant_cy + ant_pts[-1][1]
    u1_x = TEXT_ZONE_W + COMP_STRIP_W / 2
    u1_y = (feed_la_y + feed_lb_y) / 2
    c1_x, c1_y = u1_x, u1_y + 3.0
    return {
        "ant_w": ant_w,
        "ant_h": ant_h,
        "ant_cx": ant_cx,
        "ant_cy": ant_cy,
        "ant_pts": ant_pts,
        "feed_la_y": feed_la_y,
        "feed_lb_y": feed_lb_y,
        "u1": (u1_x, u1_y),
        "c1": (c1_x, c1_y),
        "text_w": TEXT_ZONE_W,
        "comp_x0": TEXT_ZONE_W,
        "ant_x0": TEXT_ZONE_W + COMP_STRIP_W,
    }


def ant_tie_geometry(ant_pts: list[tuple[float, float]]) -> dict[str, object]:
    """Net-tie junction at the coil inner end (footprint-local mm).

    Pad 1 (LA) is a horizontal bar at the take-off y; pad 2 (LB) is a vertical
    bar down to via_in.  Both use trace width for crisp 90° corners (no roundrect
    bulge at the LA→LB elbow).
    """
    end_x, end_y = ant_pts[-1]
    w = ANTENNA_TRACE_W_MM
    hw = w / 2
    takeoff_x = end_x + ANT_TIE_TAKEOFF_DX_MM
    la_poly = [
        (end_x - hw, end_y - hw),
        (takeoff_x + hw, end_y - hw),
        (takeoff_x + hw, end_y + hw),
        (end_x - hw, end_y + hw),
    ]
    lb_poly = [
        (takeoff_x - hw, end_y),
        (takeoff_x + hw, end_y),
        (takeoff_x + hw, end_y + ANT_TIE_VIA_DY_MM),
        (takeoff_x - hw, end_y + ANT_TIE_VIA_DY_MM),
    ]
    return {
        "end": (end_x, end_y),
        "takeoff_x": takeoff_x,
        "w": w,
        "la_poly": la_poly,
        "lb_poly": lb_poly,
    }


def feed_routes(
    ant1_abs: tuple[float, float],
    ant2_abs: tuple[float, float],
    u1: tuple[float, float],
    c1: tuple[float, float],
) -> list[tuple[float, float, float, float, str, float, str]]:
    """Return feed polylines as (x0, y0, x1, y1, net, width_mm, layer).

    LA leaves the spiral at its true outer start, steps west into the component
    strip, then rises to the skirt — never along the outer left-edge centerline
    (that would short turn 1). The bus then skirts above the LB pad row and
    drops to pad 1 (left of U1 so it never crosses FD).

    LB uses a thin B.Cu underpass from the inner spiral end into the component strip —
    an F.Cu path at ant2_y would cross the outer left turn (x≈ant_x0). The copper
    bridge from the coil inner end to the take-off is the ANT1 net-tie pad 1 (LA),
    which overlaps pad 2 (LB) at the take-off; the B.Cu underpass starts at via_in
    (under pad 2), so no cross-net track is needed in the hollow.
    """
    u1_x, u1_y = u1
    c1_x, c1_y = c1
    la_x = u1_x - FEED_BUS_HALF_PITCH_MM
    lb_x = u1_x + FEED_BUS_HALF_PITCH_MM
    pad_y = u1_y + 0.75
    la_skirt_y = pad_y + 0.65
    la_rise_x = ant1_abs[0] - FEED_LA_TAKEOFF_DX_MM
    c1_la = (c1_x - 0.48, c1_y)
    c1_lb = (c1_x + 0.48, c1_y)
    w = FEED_TRACE_W
    wb = FEED_BUS_W_MM
    # Inner via: step into spiral hollow; outer via: component strip east of U1
    via_in = (ant2_abs[0] + ANT_TIE_TAKEOFF_DX_MM, ant2_abs[1] + ANT_TIE_VIA_DY_MM)
    via_out = (u1_x + FEED_VIA_OUT_DX_MM, pad_y + FEED_VIA_OUT_DY_MM)
    # B.Cu underpass column between VCC (col 0.10) and VOUT (col 2.30).
    # Westbound crossing of VOUT is on F.Cu (above LA skirt); southbound
    # under the LA skirt is on B.Cu so it never centerline-shorts LA.
    lb_exit_x = u1_x + 1.20
    lb_north = (lb_exit_x, via_out[1])
    lb_exit = (lb_exit_x, pad_y)
    c1_lb_via = (lb_exit_x, c1_y)
    return [
        # LA: west off spiral start, rise in strip, skirt to bus, drop to pad 1.
        (ant1_abs[0], ant1_abs[1], la_rise_x, ant1_abs[1], "LA", w, "F.Cu"),
        (la_rise_x, ant1_abs[1], la_rise_x, la_skirt_y, "LA", w, "F.Cu"),
        (la_rise_x, la_skirt_y, la_x, la_skirt_y, "LA", w, "F.Cu"),
        # LA/LB buses share 0.40 mm pitch: narrow to XQFN ROW so gap ≥ 0.20.
        (la_x, la_skirt_y, la_x, pad_y, "LA", wb, "F.Cu"),
        # LA from C1 (above chip — la_x vertical is clear of FD)
        (c1_la[0], c1_la[1], la_x, c1_la[1], "LA", w, "F.Cu"),
        (la_x, c1_la[1], la_x, pad_y, "LA", wb, "F.Cu"),
        # LB antenna: B.Cu to via_out (east of VOUT), F.Cu west over VOUT,
        # B.Cu south under LA skirt, F.Cu stub to pad 8.
        (via_in[0], via_in[1], via_out[0], via_in[1], "LB", w, "B.Cu"),
        (via_out[0], via_in[1], via_out[0], via_out[1], "LB", w, "B.Cu"),
        (via_out[0], via_out[1], lb_north[0], lb_north[1], "LB", w, "F.Cu"),
        (lb_north[0], lb_north[1], lb_exit[0], lb_exit[1], "LB", w, "B.Cu"),
        (lb_exit[0], lb_exit[1], lb_x, pad_y, "LB", wb, "F.Cu"),
        # LB from C1: F.Cu to underpass column, B.Cu south into lb_exit
        (c1_lb[0], c1_lb[1], c1_lb_via[0], c1_lb_via[1], "LB", w, "F.Cu"),
        (c1_lb_via[0], c1_lb_via[1], lb_exit[0], lb_exit[1], "LB", w, "B.Cu"),
    ]


def feed_vias(
    ant2_abs: tuple[float, float],
    u1: tuple[float, float],
    c1: tuple[float, float],
) -> list[tuple[float, float, str]]:
    """Vias for the LB underpass (inner hollow + component strip)."""
    u1_x, u1_y = u1
    _c1_x, c1_y = c1
    pad_y = u1_y + 0.75
    via_in = (ant2_abs[0] + ANT_TIE_TAKEOFF_DX_MM, ant2_abs[1] + ANT_TIE_VIA_DY_MM)
    via_out = (u1_x + FEED_VIA_OUT_DX_MM, pad_y + FEED_VIA_OUT_DY_MM)
    lb_exit_x = u1_x + 1.20
    return [
        (via_in[0], via_in[1], "LB"),
        (via_out[0], via_out[1], "LB"),
        (lb_exit_x, via_out[1], "LB"),
        (lb_exit_x, c1_y, "LB"),
        (lb_exit_x, pad_y, "LB"),
    ]


def gnd_island_route(u1: tuple[float, float]) -> list[tuple[float, float, float, float, str, float, str]]:
    """F.Cu from VSS (pad 2) west to the local island."""
    u1_x, u1_y = u1
    vss = (u1_x - 0.75, u1_y + 0.20)
    island_cx = u1_x - GND_ISLAND_DX_MM
    island_cy = u1_y + GND_ISLAND_DY_MM
    w = FEED_TRACE_W
    return [(vss[0], vss[1], island_cx, vss[1], "GND", w, "F.Cu"), (island_cx, vss[1], island_cx, island_cy, "GND", w, "F.Cu")]


def nc_terminator_placements(
    u1: tuple[float, float],
) -> list[tuple[str, str, float, float, float, float]]:
    """Return (ref, net, rcx, rcy, pad_x, pad_y) for each B.Cu DNP pull-down."""
    u1_x, u1_y = u1
    rcx = u1_x + NC_R_COL_DX_MM
    return [
        (
            term.ref,
            term.net,
            rcx,
            u1_y + NC_FANOUT[term.net].row,
            u1_x + NC_FANOUT[term.net].pad[0],
            u1_y + NC_FANOUT[term.net].pad[1],
        )
        for term in NC_TERMINATORS
    ]


def nc_terminator_routes(
    u1: tuple[float, float],
) -> tuple[list[tuple[float, float, float, float, str, float, str]], list[tuple[float, float, str, float, float]]]:
    """NC network: short F.Cu stubs → vias → B.Cu HV channels → R pad 1.

    Resistor pad 2 sits on a B.Cu GND trunk; one via stitches the trunk to the
    F.Cu GND island (no long F.Cu NC runs, no F.Cu VOUT trunk).
    """
    u1_x, u1_y = u1
    rcx = u1_x + NC_R_COL_DX_MM
    pad1_x = rcx + R0402_PAD_OFFSET_MM
    pad2_x = rcx - R0402_PAD_OFFSET_MM
    trunk_x = pad2_x
    w = FEED_TRACE_W
    wn = NC_STUB_NARROW_W_MM
    segs: list[tuple[float, float, float, float, str, float, str]] = []
    vias: list[tuple[float, float, str, float, float]] = []
    rows: list[float] = []

    for term in NC_TERMINATORS:
        net = term.net
        f = NC_FANOUT[net]
        vx, vy = u1_x + f.via[0], u1_y + f.via[1]
        col_x = u1_x + f.col
        rcy = u1_y + f.row
        stub_w = wn if f.narrow else w
        vias.append((vx, vy, net, NC_VIA_SIZE_MM, NC_VIA_DRILL_MM))
        stub = [(u1_x + x, u1_y + y) for x, y in f.stub]
        segs += [(*a, *b, net, stub_w, "F.Cu") for a, b in zip(stub, stub[1:])]
        # B.Cu: optional north jog into a clear lane, then to column, south, to pad 1.
        # Skip duplicate points (e.g. VOUT via.x == col.x) to avoid zero-length tracks.
        bc_pts = [(vx, vy)]
        if f.bc_via_y is not None:
            lane_y = u1_y + f.bc_via_y
            bc_pts.append((vx, lane_y))
            if abs(col_x - vx) > 1e-9:
                bc_pts.append((col_x, lane_y))
        elif abs(vx - col_x) > 1e-9:
            bc_pts.append((col_x, vy))
        bc_pts.append((col_x, rcy))
        bc_pts.append((pad1_x, rcy))
        for a, b in zip(bc_pts, bc_pts[1:]):
            if abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9:
                continue
            segs.append((*a, *b, net, w, "B.Cu"))
        rows.append(rcy)

    if rows:
        y1 = max(rows)
        island_cx = u1_x - GND_ISLAND_DX_MM
        island_cy = u1_y + GND_ISLAND_DY_MM
        segs.append((trunk_x, island_cy, trunk_x, y1, "GND", w, "B.Cu"))
        vias.append((trunk_x, island_cy, "GND", NC_VIA_SIZE_MM, NC_VIA_DRILL_MM))
        if abs(trunk_x - island_cx) > 1e-9:
            segs.append((trunk_x, island_cy, island_cx, island_cy, "GND", w, "F.Cu"))

    return segs, vias


def feed_routes_sexpr(
    routes: list[tuple[float, float, float, float, str, float, str]],
) -> list[str]:
    return [segment(x0, y0, x1, y1, net, width=w, layer=layer) for x0, y0, x1, y1, net, w, layer in routes]


def uid() -> str:
    return str(uuid.uuid4())


def ensure_dirs() -> None:
    (LIB / "symbols").mkdir(parents=True, exist_ok=True)
    (LIB / "footprints" / "NFC_BusinessCard.pretty").mkdir(parents=True, exist_ok=True)
    FAB.mkdir(parents=True, exist_ok=True)
    (ROOT / "antenna").mkdir(parents=True, exist_ok=True)


def write_symbol_lib() -> None:
    path = LIB / "symbols" / "NFC_BusinessCard.kicad_sym"
    path.write_text(
        "(kicad_symbol_lib\n"
        "\t(version 20231120)\n"
        '\t(generator "nfc_business_card")\n'
        '\t(generator_version "1.0")\n'
        f"{symbol_bodies()}\n"
        ")",
        encoding="utf-8",
    )


def write_xqfn_footprint() -> None:
    """XQFN-8 1.6x1.6 P0.4mm, no EP solder (NXP SOT902-3)."""
    lines = [
        '(footprint "XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111"',
        f'\t(version {PCB_FORMAT_VERSION})',
        '\t(generator "nfc_business_card")',
        '\t(layer "F.Cu")',
        '\t(descr "NXP SOT902-3 XQFN8 1.6x1.6mm P0.4mm; EP not soldered")',
        '\t(tags "xqfn ntag nt3h2111")',
        '\t(attr smd)',
        '\t(fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS")',
        '\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))',
        "\t)",
        '\t(fp_text value "NT3H2111" (at 0 1.8) (layer "F.Fab")',
        '\t\t(effects (font (size 0.6 0.6) (thickness 0.08)))',
        "\t)",
        # Fab outline
        '\t(fp_rect (start -0.8 -0.8) (end 0.8 0.8) (layer "F.Fab") (stroke (width 0.1) (type solid)) (fill none))',
        # Courtyard
        '\t(fp_rect (start -1.2 -1.2) (end 1.2 1.2) (layer "F.CrtYd") (stroke (width 0.05) (type solid)) (fill none))',
        # Pin 1 marker
        '\t(fp_circle (center -0.55 0.55) (end -0.45 0.55) (layer "F.SilkS") (stroke (width 0.12) (type solid)) (fill none))',
    ]
    for num, (x, y, rot, _net) in XQFN_PADS.items():
        pw, ph = xqfn_pad_wh(rot)
        lines.append(
            f'\t(pad "{num}" smd roundrect (at {x} {y} {rot}) (size {pw} {ph}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) (uuid {uid()}))'
        )
    lines.append(")")
    path = LIB / "footprints" / "NFC_BusinessCard.pretty" / "XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111.kicad_mod"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_antenna_footprint() -> None:
    lay = nfc_layout()
    write_antenna_footprint_sized(lay["ant_w"], lay["ant_h"])


def write_r0402_footprint() -> None:
    path = LIB / "footprints" / "NFC_BusinessCard.pretty" / "R_0402_1005Metric.kicad_mod"
    path.write_text(
        f"""(footprint "R_0402_1005Metric"
\t(version {PCB_FORMAT_VERSION})
\t(generator "nfc_business_card")
\t(layer "B.Cu")
\t(descr "Resistor SMD 0402, DNP NC pin pull-down on B.Cu")
\t(tags "resistor")
\t(attr smd exclude_from_pos_files exclude_from_bom dnp)
\t(fp_text reference "REF**" (at 0 -1.2) (layer "B.SilkS")
\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))
\t)
\t(fp_text value "DNP" (at 0 1.2) (layer "B.Fab")
\t\t(effects (font (size 0.6 0.6) (thickness 0.08)))
\t)
\t(fp_line (start -0.1 -0.35) (end 0.1 -0.35) (layer "B.Fab") (stroke (width 0.1) (type solid)))
\t(fp_line (start -0.1 0.35) (end 0.1 0.35) (layer "B.Fab") (stroke (width 0.1) (type solid)))
\t(fp_rect (start -1.0 -0.6) (end 1.0 0.6) (layer "B.CrtYd") (stroke (width 0.05) (type solid)) (fill none))
\t(pad "1" smd roundrect (at 0.48 0) (size 0.52 0.62) (layers "B.Cu" "B.Paste" "B.Mask") (roundrect_rratio 0.15) (uuid {uid()}))
\t(pad "2" smd roundrect (at -0.48 0) (size 0.52 0.62) (layers "B.Cu" "B.Paste" "B.Mask") (roundrect_rratio 0.15) (uuid {uid()}))
)
""",
        encoding="utf-8",
    )


def write_c0402_footprint() -> None:
    path = LIB / "footprints" / "NFC_BusinessCard.pretty" / "C_0402_1005Metric.kicad_mod"
    path.write_text(
        f"""(footprint "C_0402_1005Metric"
\t(version {PCB_FORMAT_VERSION})
\t(generator "nfc_business_card")
\t(layer "F.Cu")
\t(descr "Capacitor SMD 0402, reexported local for DNP C1")
\t(tags "capacitor")
\t(attr smd exclude_from_pos_files exclude_from_bom dnp)
\t(fp_text reference "REF**" (at 0 -1.2) (layer "F.SilkS")
\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))
\t)
\t(fp_text value "DNP" (at 0 1.2) (layer "F.Fab")
\t\t(effects (font (size 0.6 0.6) (thickness 0.08)))
\t)
\t(fp_line (start -0.1 -0.35) (end 0.1 -0.35) (layer "F.Fab") (stroke (width 0.1) (type solid)))
\t(fp_line (start -0.1 0.35) (end 0.1 0.35) (layer "F.Fab") (stroke (width 0.1) (type solid)))
\t(fp_rect (start -1.0 -0.6) (end 1.0 0.6) (layer "F.CrtYd") (stroke (width 0.05) (type solid)) (fill none))
\t(pad "1" smd roundrect (at -0.48 0) (size 0.52 0.62) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15) (uuid {uid()}))
\t(pad "2" smd roundrect (at 0.48 0) (size 0.52 0.62) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.15) (uuid {uid()}))
)
""",
        encoding="utf-8",
    )


def write_project(schematic_uuid: str) -> None:
    from jlcpcb_limits import (
        FEED_TRACE_W_MM,
        JLC_MIN_TRACE_WIDTH_MM,
        KICAD_DRC_MIN_CLEARANCE_MM,
    )

    clr = KICAD_DRC_MIN_CLEARANCE_MM
    # Allow intentional NC stubs (0.15 mm); floor is JLC capability, not feed default.
    min_tw = JLC_MIN_TRACE_WIDTH_MM
    project_json = f"""{{
  "board": {{
    "design_settings": {{
      "defaults": {{
        "board_outline_line_width": 0.1,
        "copper_line_width": {FEED_TRACE_W_MM},
        "copper_text_size_h": 1.0,
        "copper_text_size_v": 1.0,
        "copper_text_thickness": 0.15,
        "other_line_width": 0.15,
        "silk_line_width": 0.15,
        "silk_text_size_h": 0.8,
        "silk_text_size_v": 0.8,
        "silk_text_thickness": 0.12
      }},
      "rules": {{
        "min_clearance": {clr},
        "min_track_width": {min_tw},
        "min_via_diameter": 0.4,
        "min_through_hole_diameter": 0.2,
        "solder_mask_clearance": 0.0,
        "solder_mask_min_width": 0.0
      }}
    }}
  }},
  "meta": {{
    "filename": "nfc-business-card.kicad_pro",
    "version": 1
  }},
  "net_settings": {{
    "classes": [
      {{
        "name": "Default",
        "clearance": {clr},
        "track_width": {FEED_TRACE_W_MM},
        "via_diameter": 0.6,
        "via_drill": 0.3,
        "diff_pair_width": 0.2,
        "diff_pair_gap": 0.25,
        "priority": 2147483647
      }}
    ],
    "meta": {{ "version": 5 }}
  }},
  "sheets": [
    ["{schematic_uuid}", "Root"]
  ],
  "text_variables": {{}}
}}
"""
    (ROOT / "nfc-business-card.kicad_pro").write_text(project_json, encoding="utf-8")


# Schematic layout (1.27 mm grid). Sheet Y increases downward.
SCH_G = 1.27
U1_SCH_X = 100 * SCH_G  # 127.00
U1_SCH_Y = 60 * SCH_G  # 76.20
U1_SCH_PIN_LEN = 2.54
R_SCH_PIN_SPAN = 3.81  # pin tip ↔ body centre for R_0402
ANT_SCH_X = 45 * SCH_G  # 57.15
ANT_SCH_Y = U1_SCH_Y
C1_SCH_X = 75 * SCH_G  # 95.25 — between ANT and U1, label-joined to LA/LB
C1_SCH_Y = U1_SCH_Y
GND_SCH_Y = 95 * SCH_G  # 120.65 — below R bank pin2
R_BELOW_DY = 18 * SCH_G  # 22.86 — clear of U1 body
NOTE_SCH_X = 20 * SCH_G
NOTE_SCH_Y = 105 * SCH_G


def _sch_snap(v: float) -> float:
    return round(round(v / SCH_G) * SCH_G, 2)


def _u1_sch_pin_xy(net: str) -> tuple[float, float]:
    """Electrical connection point on the U1 schematic symbol (pin tip).

    Eeschema sheet Y increases downward, while symbol-local +Y is drawn upward,
    so sheet_y = U1_SCH_Y - local_y.
    """
    local = {
        "LA": (-10.16, 5.08),
        "VSS": (-10.16, 2.54),
        "SCL": (-10.16, 0.0),
        "FD": (-10.16, -2.54),
        "SDA": (10.16, -2.54),
        "VCC": (10.16, 0.0),
        "VOUT": (10.16, 2.54),
        "LB": (10.16, 5.08),
    }
    dx, dy = local[net]
    return (_sch_snap(U1_SCH_X + dx), _sch_snap(U1_SCH_Y - dy))


def _sch_wire(x0: float, y0: float, x1: float, y1: float) -> str:
    return (
        f'\t(wire (pts (xy {x0} {y0}) (xy {x1} {y1})) '
        f'(stroke (width 0) (type default)) (uuid {uid()}))'
    )


def _sch_label(name: str, x: float, y: float, angle: int, justify: str) -> str:
    return (
        f'\t(global_label "{name}" (shape input) (at {x} {y} {angle}) '
        f'(effects (font (size 1.27 1.27)) (justify {justify} bottom)) '
        f'(uuid {uid()}))'
    )


def _schematic_nc_terminator_symbols(sheet_path: str) -> str:
    """R2–R6 as a spaced vertical DNP bank under U1 to one GND rail.

    Same-side U1 pins share an X, so resistors cannot sit on the pin column —
    place every R column OUTSIDE the U1 body span so no vertical/jog crosses
    the symbol rectangle: left columns ≤ pin column (116.84), right columns
    ≥ pin column (137.16). One net per side keeps its pin column; the other
    jogs one pitch outward and drops clear of the body.
    """
    # L→R: FD/SCL left of the body, SDA/VCC/VOUT right of the body.
    placements = (
        ("R4", "FD", U1_SCH_X - 3 * 5.08),   # 111.76 — jog L of body
        ("R2", "SCL", U1_SCH_X - 2 * 5.08),  # 116.84 — left pin column
        ("R3", "SDA", U1_SCH_X + 2 * 5.08),  # 137.16 — right pin column
        ("R5", "VCC", U1_SCH_X + 3 * 5.08),  # 142.24 — jog R of body
        ("R6", "VOUT", U1_SCH_X + 4 * 5.08),  # 147.32 — jog R of body
    )
    ry = _sch_snap(U1_SCH_Y + R_BELOW_DY)
    pin1_y = _sch_snap(ry - R_SCH_PIN_SPAN)
    pin2_y = _sch_snap(ry + R_SCH_PIN_SPAN)
    desc = f"{NC_TERM_R_KOHM}k NC pull-down"
    lines: list[str] = []
    rail_xs: list[float] = []

    for ref, net, rx in placements:
        px, py = _u1_sch_pin_xy(net)
        rx = _sch_snap(rx)
        rail_xs.append(rx)
        outside = -2.54 if rx <= U1_SCH_X else 2.54
        just = "right" if outside < 0 else "left"
        lines.append(
            f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:R_0402")
\t\t(at {rx} {ry} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp yes)
\t\t(uuid {uid()})
\t\t(property "Reference" "{ref}" (at {rx + outside} {ry - 1.27} 0) (effects (font (size 1.27 1.27)) (justify {just})))
\t\t(property "Value" "DNP" (at {rx + outside} {ry + 1.27} 0) (effects (font (size 1.27 1.27)) (justify {just})))
\t\t(property "Footprint" "NFC_BusinessCard:R_0402_1005Metric" (at {rx} {ry} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Description" "{desc}" (at {rx} {ry} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "LCSC Part #" "{NC_TERM_R_LCSC}" (at {rx} {ry} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "{ref}") (unit 1))))
\t)"""
        )
        # Outward jog at the pin's own Y (never shares a horizontal across nets),
        # then drop clear of the body. The net label sits on the outward
        # jog/stub so the pin↔net link is readable in one glance.
        ang = 180 if px < U1_SCH_X else 0
        lab_just = "right" if px < U1_SCH_X else "left"
        if abs(px - rx) > 1e-9:
            # pin-column drop impossible (jogs outward) → label on the jog
            lines.append(_sch_wire(px, py, rx, py))
            lab_x = _sch_snap((px + rx) / 2)
        else:
            # pin column drop at the R column → short outward label stub
            lab_x = _sch_snap(px + (-2.54 if px < U1_SCH_X else 2.54))
            lines.append(_sch_wire(px, py, lab_x, py))
        lines.append(_sch_wire(rx, py, rx, pin1_y))
        lines.append(_sch_label(net, lab_x, py, ang, lab_just))
        lines.append(_sch_wire(rx, pin2_y, rx, GND_SCH_Y))

    # Shared GND rail. Power symbols (and reliable T-joins) need wire endpoints,
    # so segment the rail at every resistor X and at the VSS/GND junction.
    x0, x1 = min(rail_xs), max(rail_xs)
    vss_x, vss_y = _u1_sch_pin_xy("VSS")
    gnd0_x = _sch_snap(x0 - 2 * SCH_G)
    gnd1_x = _sch_snap(x1 + 2 * SCH_G)
    lines.append(_sch_wire(vss_x, vss_y, gnd0_x, vss_y))
    lines.append(_sch_wire(gnd0_x, vss_y, gnd0_x, GND_SCH_Y))
    rail_nodes = sorted({_sch_snap(x) for x in (*rail_xs, gnd0_x, gnd1_x)})
    for a, b in zip(rail_nodes, rail_nodes[1:]):
        lines.append(_sch_wire(a, GND_SCH_Y, b, GND_SCH_Y))
    flag_x = _sch_snap(gnd0_x - SCH_G)
    lines.append(_sch_wire(flag_x, GND_SCH_Y, gnd0_x, GND_SCH_Y))
    lines.append(
        f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:GND")
\t\t(at {gnd0_x} {GND_SCH_Y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "#PWR01" (at {gnd0_x} {GND_SCH_Y + 5.08} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "GND" (at {gnd0_x} {GND_SCH_Y + 3.81} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "" (at {gnd0_x} {GND_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "#PWR01") (unit 1))))
\t)"""
    )
    lines.append(
        f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:GND")
\t\t(at {gnd1_x} {GND_SCH_Y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "#PWR02" (at {gnd1_x} {GND_SCH_Y + 5.08} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "GND" (at {gnd1_x} {GND_SCH_Y + 3.81} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "" (at {gnd1_x} {GND_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "#PWR02") (unit 1))))
\t)"""
    )
    lines.append(
        f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:PWR_FLAG")
\t\t(at {flag_x} {GND_SCH_Y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "#FLG01" (at {flag_x} {GND_SCH_Y - 2.54} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "PWR_FLAG" (at {flag_x} {GND_SCH_Y - 2.54} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Footprint" "" (at {flag_x} {GND_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "#FLG01") (unit 1))))
\t)"""
    )
    return "\n".join(lines)


def _schematic_rf_symbols(sheet_path: str) -> str:
    """Antenna + C1 + U1 with LA/LB joined by labels (no crossing trunks)."""
    lines: list[str] = []
    # U1
    lines.append(
        f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:NT3H2111W0FHKH")
\t\t(at {U1_SCH_X} {U1_SCH_Y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "U1" (at {U1_SCH_X} {U1_SCH_Y - 10.16} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "NT3H2111W0FHKH" (at {U1_SCH_X + 20.32} {U1_SCH_Y} 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111" (at {U1_SCH_X} {U1_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "LCSC Part #" "C710403" (at {U1_SCH_X} {U1_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(pin "3" (uuid {uid()}))
\t\t(pin "4" (uuid {uid()}))
\t\t(pin "5" (uuid {uid()}))
\t\t(pin "6" (uuid {uid()}))
\t\t(pin "7" (uuid {uid()}))
\t\t(pin "8" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "U1") (unit 1))))
\t)"""
    )
    # Antenna
    lines.append(
        f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:Antenna_NFC")
\t\t(at {ANT_SCH_X} {ANT_SCH_Y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "ANT1" (at {ANT_SCH_X} {ANT_SCH_Y - 7.62} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "Antenna_NFC" (at {ANT_SCH_X} {ANT_SCH_Y + 7.62} 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "NFC_BusinessCard:Antenna_Spiral_29x45_5T" (at {ANT_SCH_X} {ANT_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "ANT1") (unit 1))))
\t)"""
    )
    # C1 DNP — joins LA/LB only via labels
    lines.append(
        f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:C_0402")
\t\t(at {C1_SCH_X} {C1_SCH_Y} 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp yes)
\t\t(uuid {uid()})
\t\t(property "Reference" "C1" (at {C1_SCH_X + 3.81} {C1_SCH_Y - 1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "DNP" (at {C1_SCH_X + 3.81} {C1_SCH_Y + 1.27} 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "NFC_BusinessCard:C_0402_1005Metric" (at {C1_SCH_X} {C1_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "LCSC Part #" "{C1_LCSC}" (at {C1_SCH_X} {C1_SCH_Y} 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "C1") (unit 1))))
\t)"""
    )

    # ANT stubs + labels (pin1 left / pin2 right at ±5.08)
    ant1 = (_sch_snap(ANT_SCH_X - 5.08), ANT_SCH_Y)
    ant2 = (_sch_snap(ANT_SCH_X + 5.08), ANT_SCH_Y)
    la_ant = (_sch_snap(ant1[0] - 5.08), ANT_SCH_Y)
    lb_ant = (_sch_snap(ant2[0] + 5.08), ANT_SCH_Y)
    lines.append(_sch_wire(ant1[0], ant1[1], la_ant[0], la_ant[1]))
    lines.append(_sch_label("LA", la_ant[0], la_ant[1], 180, "right"))
    lines.append(_sch_wire(ant2[0], ant2[1], lb_ant[0], lb_ant[1]))
    lines.append(_sch_label("LB", lb_ant[0], lb_ant[1], 0, "left"))

    # U1 LA/LB stubs + labels
    la_u1 = _u1_sch_pin_xy("LA")
    lb_u1 = _u1_sch_pin_xy("LB")
    la_stub = (_sch_snap(la_u1[0] - 5.08), la_u1[1])
    lb_stub = (_sch_snap(lb_u1[0] + 5.08), lb_u1[1])
    lines.append(_sch_wire(la_u1[0], la_u1[1], la_stub[0], la_stub[1]))
    lines.append(_sch_label("LA", la_stub[0], la_stub[1], 180, "right"))
    lines.append(_sch_wire(lb_u1[0], lb_u1[1], lb_stub[0], lb_stub[1]))
    lines.append(_sch_label("LB", lb_stub[0], lb_stub[1], 0, "left"))

    # C1 pin1 (north) → LA, pin2 (south) → LB
    c1_p1 = (C1_SCH_X, _sch_snap(C1_SCH_Y - R_SCH_PIN_SPAN))
    c1_p2 = (C1_SCH_X, _sch_snap(C1_SCH_Y + R_SCH_PIN_SPAN))
    c1_la = (C1_SCH_X, _sch_snap(c1_p1[1] - 2.54))
    c1_lb = (C1_SCH_X, _sch_snap(c1_p2[1] + 2.54))
    lines.append(_sch_wire(c1_p1[0], c1_p1[1], c1_la[0], c1_la[1]))
    lines.append(_sch_label("LA", c1_la[0], c1_la[1], 90, "left"))
    lines.append(_sch_wire(c1_p2[0], c1_p2[1], c1_lb[0], c1_lb[1]))
    lines.append(_sch_label("LB", c1_lb[0], c1_lb[1], 270, "right"))

    return "\n".join(lines)


def _schematic_lib_symbols() -> str:
    """Embedded lib_symbols for the root schematic sheet (one node per line)."""
    return "\t(lib_symbols\n" + symbol_bodies_embedded() + "\n\t)"



def write_schematic(schematic_uuid: str) -> None:
    """U1 + ANT1 + C1(DNP) + R2–R6(DNP): label-joined RF, vertical NC pull-downs."""
    sheet_path = f"/{schematic_uuid}"
    note_uuid = uid()
    note = f"""\t(text "Passive NFC business card\\nU1=NT3H2111 (C710403)\\nC1=DNP tuning LA-LB (10-22 pF NP0)\\nR2-R6=DNP 100k to GND (SCL/SDA/FD/VCC/VOUT)\\nVSS=local GND island"
\t\t(at {NOTE_SCH_X} {NOTE_SCH_Y} 0)
\t\t(effects (font (size 1.27 1.27)) (justify left top))
\t\t(uuid {note_uuid})
\t)"""
    body = "\n".join(
        [
            "(kicad_sch",
            "\t(version 20231120)",
            '\t(generator "nfc_business_card")',
            '\t(generator_version "1.0")',
            f"\t(uuid {schematic_uuid})",
            '\t(paper "A4")',
            "\t(title_block",
            '\t\t(title "NFC Business Card")',
            f'\t\t(date "{date.today().isoformat()}")',
            '\t\t(rev "B")',
            '\t\t(company "")',
            '\t\t(comment 1 "89x51mm passive NFC URL tag")',
            '\t\t(comment 2 "NT3H2111W0FHKH LCSC C710403")',
            "\t)",
            _schematic_lib_symbols().rstrip(),
            _schematic_rf_symbols(sheet_path),
            _schematic_nc_terminator_symbols(sheet_path),
            note,
            "\t(sheet_instances",
            f'\t\t(path "{sheet_path}" (page "1"))',
            "\t)",
            ")",
            "",
        ]
    )
    (ROOT / "nfc-business-card.kicad_sch").write_text(body, encoding="utf-8")



def build_silk_bitmaps(ant_cx: float, ant_cy: float) -> str:
    """Front QR + NFC icon + Pillow silk PNGs, back 2x2 logos as KiCad images."""
    required = [
        (ASSETS / "qr-silk.png", "qr-silk.png"),
        (ASSETS / "nfc-n-mark-silk.png", "nfc-n-mark-silk.png"),
        (ASSETS / "roles-silk.png", "roles-silk.png"),
        (ASSETS / "contacts-silk.png", "contacts-silk.png"),
    ]
    for path, label in required:
        match require_existing_file(path, label=label):
            case Err(error=msg):
                raise FileNotFoundError(f"{msg} — run make_qr_silk.py / make_nfc_logo.py / make_text_silk.py")
            case _:
                pass

    parts = [
        bitmap_sexpr_rgba(
            ASSETS / "roles-silk.png",
            at_x_mm=TEXT_LEFT_MM,
            at_y_mm=ROLES_Y0_MM,
            layer="F.SilkS",
            preview_coords=True,
        ),
        bitmap_sexpr_rgba(
            ASSETS / "contacts-silk.png",
            at_x_mm=CONTACT_X_MM,
            at_y_mm=contact_top_y_mm(),
            layer="F.SilkS",
            preview_coords=True,
        ),
        bitmap_sexpr(
            ASSETS / "qr-silk.png",
            at_x_mm=QR_X_MM,
            at_y_mm=qr_top_y_mm(),
            size_mm=qr_size_mm(),
            layer="F.SilkS",
            preview_coords=True,
        ),
        bitmap_sexpr(
            ASSETS / "nfc-n-mark-silk.png",
            at_x_mm=ant_cx,
            at_y_mm=ant_cy,
            size_mm=NFC_LOGO_SIZE_MM,
            layer="F.SilkS",
            center=True,
        ),
    ]
    logo_mm, back_items = back_logo_grid()
    for filename, cx, cy in back_items:
        path = LOGOS / filename
        unwrap(require_existing_file(path, label=filename), context="back logo")
        parts.append(
            bitmap_sexpr(
                path,
                at_x_mm=cx,
                at_y_mm=cy,
                size_mm=logo_mm,
                layer="B.SilkS",
                center=True,
                preview_coords=True,
            )
        )
    return "\n".join(parts) + "\n"


def _fp_hidden_fields(*, description: str = "") -> str:
    return (
        footprint_property("Datasheet", "", 0, 0, 0, "F.Fab", hide=True)
        + footprint_property("Description", description, 0, 0, 0, "F.Fab", hide=True)
    )


def build_u1_footprint(x: float, y: float) -> str:
    parts = [
        '\t(footprint "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111"',
        '\t\t(layer "F.Cu")',
        f"\t\t(uuid {quuid()})",
        f"\t\t(at {x} {y})",
        footprint_property("Reference", "U1", 0, -2.2, 0, "F.SilkS", hide=True, font_size=(0.7, 0.7), thickness=0.1),
        footprint_property("Value", "NT3H2111W0FHKH", 0, 2.2, 0, "F.Fab", font_size=(0.5, 0.5), thickness=0.08),
        _fp_hidden_fields(),
        footprint_property("LCSC Part #", "C710403", 0, 0, 0, "F.Fab", hide=True, thickness=0.15),
        "\t\t(attr smd)",
        "\t\t(duplicate_pad_numbers_are_jumpers no)",
        fp_circle(-0.55, 0.55, -0.45, 0.55, "F.SilkS"),
        fp_rect(-1.2, -1.2, 1.2, 1.2, "F.CrtYd"),
        fp_rect(-0.8, -0.8, 0.8, 0.8, "F.Fab", width=0.1),
    ]
    # Numeric pad order (1..8) to keep regenerated PCB byte-stable.
    for num in sorted(XQFN_PADS):
        px, py, rot, net = XQFN_PADS[num]
        parts.append(fp_pad_roundrect(num, px, py, rot, *xqfn_pad_wh(rot), net=net))
    parts += [
        "\t\t(embedded_fonts no)",
        "\t)",
    ]
    return "\n".join(parts) + "\n"


def build_ant_footprint(x: float, y: float, ant_pts: list[tuple[float, float]]) -> str:
    """Net-tie junction at the coil inner end.

    The spiral itself is drawn as netted F.Cu tracks (net LA) in write_pcb, so no
    un-netted footprint copper exists and DRC is deterministic. The physical bridge
    that closes the coil to the LB feed lives in this footprint as two overlapping
    connect pads (net_tie_pad_groups "1,2"):

      pad 1 (LA): roundrect spanning from the coil inner end to the take-off
      pad 2 (LB): roundrect from the take-off down to via_in

    Overlapping pads in the same tie group are exempt from the DRC short test, so
    net LA meets net LB here without a track↔pad short.  Pads are trace-width
    roundrects with rratio 0 for a clean 90° elbow.
    """
    tie = ant_tie_geometry(ant_pts)
    end_x, end_y = tie["end"]
    takeoff_x = tie["takeoff_x"]
    w = tie["w"]
    parts = [
        '\t(footprint "NFC_BusinessCard:Antenna_Spiral_29x45_5T"',
        '\t\t(layer "F.Cu")',
        f"\t\t(uuid {quuid()})",
        f"\t\t(at {x} {y})",
        footprint_property("Reference", "ANT1", 0, 0, 0, "F.SilkS", hide=True, font_size=(0.8, 0.8), thickness=0.12),
        footprint_property("Value", "Antenna_NFC", 0, 0, 0, "F.Fab", hide=True, font_size=(0.8, 0.8), thickness=0.12),
        _fp_hidden_fields(),
        # net-tie: coil end (LA, pad 1) bridges to the LB feed take-off (pad 2)
        '\t\t(attr board_only exclude_from_pos_files exclude_from_bom allow_missing_courtyard)',
        '\t\t(net_tie_pad_groups "1,2")',
        "\t\t(duplicate_pad_numbers_are_jumpers no)",
        fp_pad_connect_roundrect(
            "1",
            end_x + ANT_TIE_TAKEOFF_DX_MM / 2,
            end_y,
            ANT_TIE_TAKEOFF_DX_MM,
            w,
            net="LA",
        ),
        fp_pad_connect_roundrect(
            "2",
            takeoff_x,
            end_y + ANT_TIE_VIA_DY_MM / 2,
            w,
            ANT_TIE_VIA_DY_MM,
            net="LB",
        ),
        "\t\t(embedded_fonts no)",
        "\t)",
    ]
    return "\n".join(parts) + "\n"


def build_gnd_island(u1: tuple[float, float]) -> str:
    """Local VSS copper island in the component strip (not under the spiral)."""
    u1_x, u1_y = u1
    x = u1_x - GND_ISLAND_DX_MM
    y = u1_y + GND_ISLAND_DY_MM
    w, h = GND_ISLAND_W_MM, GND_ISLAND_H_MM
    parts = [
        '\t(footprint "NFC_BusinessCard:GND_Island"',
        '\t\t(layer "F.Cu")',
        f"\t\t(uuid {quuid()})",
        f"\t\t(at {x} {y})",
        footprint_property("Reference", "GND1", 0, -1.0, 0, "F.SilkS", hide=True, font_size=(0.5, 0.5), thickness=0.08),
        footprint_property("Value", "GND", 0, 1.0, 0, "F.Fab", hide=True, font_size=(0.5, 0.5), thickness=0.08),
        _fp_hidden_fields(),
        "\t\t(attr board_only exclude_from_pos_files exclude_from_bom)",
        "\t\t(duplicate_pad_numbers_are_jumpers no)",
        fp_rect(-w / 2 - 0.15, -h / 2 - 0.15, w / 2 + 0.15, h / 2 + 0.15, "F.CrtYd", width=0.05),
        # Copper + mask only (no paste — local reference island, not a soldered land)
        f'\t\t(pad "1" smd roundrect\n'
        f'\t\t\t(at 0 0)\n'
        f'\t\t\t(size {w} {h})\n'
        f'\t\t\t(layers "F.Cu" "F.Mask")\n'
        f'\t\t\t(roundrect_rratio 0.2)\n'
        f'\t\t\t(net "GND")\n'
        f'\t\t\t(uuid {quuid()})\n'
        f'\t\t)',
        "\t\t(embedded_fonts no)",
        "\t)",
    ]
    return "\n".join(parts) + "\n"


def write_gnd_island_footprint() -> None:
    w, h = GND_ISLAND_W_MM, GND_ISLAND_H_MM
    path = LIB / "footprints" / "NFC_BusinessCard.pretty" / "GND_Island.kicad_mod"
    path.write_text(
        f"""(footprint "GND_Island"
\t(version {PCB_FORMAT_VERSION})
\t(generator "nfc_business_card")
\t(layer "F.Cu")
\t(descr "Local VSS copper island for NT3H2111 (component strip only)")
\t(tags "gnd vss nfc")
\t(attr board_only exclude_from_pos_files exclude_from_bom)
\t(fp_text reference "GND**" (at 0 -1.0) (layer "F.SilkS") (hide yes)
\t\t(effects (font (size 0.5 0.5) (thickness 0.08)))
\t)
\t(fp_text value "GND" (at 0 1.0) (layer "F.Fab") (hide yes)
\t\t(effects (font (size 0.5 0.5) (thickness 0.08)))
\t)
\t(fp_rect (start {-w / 2 - 0.15} {-h / 2 - 0.15}) (end {w / 2 + 0.15} {h / 2 + 0.15}) (layer "F.CrtYd") (stroke (width 0.05) (type solid)) (fill none))
\t(pad "1" smd roundrect (at 0 0) (size {w} {h}) (layers "F.Cu" "F.Mask") (roundrect_rratio 0.2) (uuid {uid()}))
)
""",
        encoding="utf-8",
    )


def build_r_footprint(ref: str, x: float, y: float, net_sig: str) -> str:
    """B.Cu DNP 100 kΩ: pad 1 (east) = NC net, pad 2 (west) = GND."""
    parts = [
        '\t(footprint "NFC_BusinessCard:R_0402_1005Metric"',
        '\t\t(layer "B.Cu")',
        f"\t\t(uuid {quuid()})",
        f"\t\t(at {x} {y})",
        footprint_property("Reference", ref, 0, -1.2, 0, "B.SilkS", hide=True, font_size=(0.6, 0.6), thickness=0.1),
        footprint_property("Value", "DNP", 0, 1.2, 0, "B.Fab", font_size=(0.5, 0.5), thickness=0.08),
        _fp_hidden_fields(description=f"{NC_TERM_R_KOHM}k NC pull-down"),
        footprint_property("LCSC Part #", NC_TERM_R_LCSC, 0, 0, 0, "B.Fab", hide=True, font_size=(1.27, 1.27), thickness=0),
        "\t\t(attr smd exclude_from_pos_files exclude_from_bom dnp)",
        "\t\t(duplicate_pad_numbers_are_jumpers no)",
        fp_rect(-1.0, -0.6, 1.0, 0.6, "B.CrtYd"),
        fp_line(-0.1, -0.35, 0.1, -0.35, "B.Fab", width=0.1),
        fp_line(-0.1, 0.35, 0.1, 0.35, "B.Fab", width=0.1),
        fp_pad_roundrect("1", R0402_PAD_OFFSET_MM, 0, 0, 0.52, 0.62, net=net_sig, side="B", rratio=0.15),
        fp_pad_roundrect("2", -R0402_PAD_OFFSET_MM, 0, 0, 0.52, 0.62, net="GND", side="B", rratio=0.15),
        "\t\t(embedded_fonts no)",
        "\t)",
    ]
    return "\n".join(parts) + "\n"


def build_c1_footprint(x: float, y: float) -> str:
    parts = [
        '\t(footprint "NFC_BusinessCard:C_0402_1005Metric"',
        '\t\t(layer "F.Cu")',
        f"\t\t(uuid {quuid()})",
        f"\t\t(at {x} {y})",
        footprint_property("Reference", "C1", 0, -1.2, 0, "F.SilkS", hide=True, font_size=(0.6, 0.6), thickness=0.1),
        footprint_property("Value", "DNP", 0, 1.2, 0, "F.Fab", font_size=(0.5, 0.5), thickness=0.08),
        _fp_hidden_fields(),
        footprint_property("LCSC Part #", C1_LCSC, 0, 0, 0, "F.Fab", hide=True, font_size=(1.27, 1.27), thickness=0),
        "\t\t(attr smd exclude_from_pos_files exclude_from_bom dnp)",
        "\t\t(duplicate_pad_numbers_are_jumpers no)",
        fp_rect(-1.0, -0.6, 1.0, 0.6, "F.CrtYd"),
        fp_line(-0.1, -0.35, 0.1, -0.35, "F.Fab", width=0.1),
        fp_line(-0.1, 0.35, 0.1, 0.35, "F.Fab", width=0.1),
        fp_pad_roundrect("1", -0.48, 0, 0, 0.52, 0.62, net="LA", rratio=0.15),
        fp_pad_roundrect("2", 0.48, 0, 0, 0.52, 0.62, net="LB", rratio=0.15),
        "\t\t(embedded_fonts no)",
        "\t)",
    ]
    return "\n".join(parts) + "\n"


def write_pcb() -> None:
    """PCB: left text zone (no copper), centre components, right antenna."""
    lay = nfc_layout()
    ant_w, ant_h = lay["ant_w"], lay["ant_h"]
    ant_cx, ant_cy = lay["ant_cx"], lay["ant_cy"]
    u1_x, u1_y = lay["u1"]
    c1_x, c1_y = lay["c1"]

    ant_pts = lay["ant_pts"]
    ant1_abs = (ant_cx + ant_pts[0][0], ant_cy + ant_pts[0][1])
    ant2_abs = (ant_cx + ant_pts[-1][0], ant_cy + ant_pts[-1][1])
    tw = TEXT_ZONE_W

    silk_bitmaps = build_silk_bitmaps(ant_cx, ant_cy)
    name_copper = bake_name_enig_sexpr(
        NAME,
        x_mm=NAME_X_MM,
        y_mm=NAME_Y_MM,
        size_mm=NAME_CAP_HEIGHT_MM,
        face=NAME_FONT_FACE,
    )
    segments = feed_routes_sexpr(
        feed_routes(ant1_abs, ant2_abs, lay["u1"], lay["c1"]) + gnd_island_route(lay["u1"])
    )
    nc_segs, nc_vias = nc_terminator_routes(lay["u1"])
    segments += feed_routes_sexpr(nc_segs)
    # Spiral as netted F.Cu tracks (net LA) — no un-netted copper, deterministic DRC.
    # Outer start (=ant1_abs) meets the LA feed; inner end (=ant2_abs) meets net-tie pad 1.
    coil_segs = [
        segment(
            ant_cx + a[0],
            ant_cy + a[1],
            ant_cx + b[0],
            ant_cy + b[1],
            "LA",
            width=TRACE_W,
        )
        for a, b in zip(ant_pts, ant_pts[1:])
    ]
    vias = [
        via(x, y, net, size=FEED_VIA_SIZE_MM, drill=FEED_VIA_DRILL_MM)
        for x, y, net in feed_vias(ant2_abs, lay["u1"], lay["c1"])
    ]
    vias += [via(x, y, net, size=sz, drill=dr) for x, y, net, sz, dr in nc_vias]

    r_fps = [
        build_r_footprint(ref, rcx, rcy, net)
        for ref, net, rcx, rcy, _pad_x, _pad_y in nc_terminator_placements(lay["u1"])
    ]

    content = "\n".join(
        [
            pcb_header(
                title="NFC Business Card",
                date="2026-07-14",
                rev="B",
                comment="89x51mm NT3H2111 — NFC on right, text zone left",
            ),
            pcb_layers(),
            pcb_setup(),
            build_u1_footprint(u1_x, u1_y),
            build_ant_footprint(ant_cx, ant_cy, ant_pts),
            build_c1_footprint(c1_x, c1_y),
            build_gnd_island(lay["u1"]),
            *r_fps,
            name_copper.rstrip("\n"),
            gr_line(tw, 0, tw, BOARD_H, "Dwgs.User", dash=True),
            gr_line(lay["ant_x0"], 0, lay["ant_x0"], BOARD_H, "Dwgs.User", dash=True),
            gr_rect(0, 0, BOARD_W, BOARD_H, "Edge.Cuts"),
            silk_bitmaps.rstrip("\n"),
            gr_text("TEXT ZONE (no copper)", tw / 2, 4, "Dwgs.User"),
            gr_text("NFC", ant_cx, 4, "Dwgs.User"),
            *segments,
            *coil_segs,
            *vias,
            "\t(embedded_fonts yes)",
            ")",
        ]
    ) + "\n"
    (ROOT / "nfc-business-card.kicad_pcb").write_text(content, encoding="utf-8")
    write_antenna_footprint_sized(ant_w, ant_h)


def write_antenna_footprint_sized(outer_w: float, outer_h: float) -> None:
    pts = rectangular_spiral(0, 0, outer_w, outer_h, TURNS, TRACE_W, GAP)
    tie = ant_tie_geometry(pts)
    end_x, end_y = tie["end"]
    takeoff_x = tie["takeoff_x"]
    w = tie["w"]
    fp_name = f"Antenna_Spiral_{outer_w:.0f}x{outer_h:.0f}_{TURNS}T"
    lines = [
        f'(footprint "{fp_name}"',
        f'\t(version {PCB_FORMAT_VERSION})',
        '\t(generator "nfc_business_card")',
        '\t(layer "F.Cu")',
        f'\t(descr "Rect spiral NFC antenna ~{outer_w:.0f}x{outer_h:.0f}mm {TURNS} turns {TRACE_W}/{GAP}; overlapping net-tie pads 1-2 (spiral = board tracks net LA)")',
        '\t(tags "net tie nfc antenna spiral")',
        '\t(attr exclude_from_pos_files exclude_from_bom allow_missing_courtyard)',
        '\t(net_tie_pad_groups "1,2")',
        '\t(fp_text reference "ANT**" (at 0 0) (layer "F.SilkS") (hide yes)',
        '\t\t(effects (font (size 1 1) (thickness 0.15)))',
        "\t)",
        '\t(fp_text value "Antenna" (at 0 0) (layer "F.Fab") (hide yes)',
        '\t\t(effects (font (size 1 1) (thickness 0.15)))',
        "\t)",
        fp_pad_connect_roundrect(
            "1",
            end_x + ANT_TIE_TAKEOFF_DX_MM / 2,
            end_y,
            ANT_TIE_TAKEOFF_DX_MM,
            w,
            net="LA",
            indent="\t",
        ),
        fp_pad_connect_roundrect(
            "2",
            takeoff_x,
            end_y + ANT_TIE_VIA_DY_MM / 2,
            w,
            ANT_TIE_VIA_DY_MM,
            net="LB",
            indent="\t",
        ),
        ")",
    ]
    pretty = LIB / "footprints" / "NFC_BusinessCard.pretty"
    path = pretty / f"{fp_name}.kicad_mod"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Drop legacy misnamed footprint if present
    legacy = pretty / "Antenna_Spiral_84x46_4T.kicad_mod"
    if legacy.exists() and legacy.resolve() != path.resolve():
        legacy.unlink()

    (ROOT / "antenna" / "spiral_points.csv").write_text(
        "x_mm,y_mm\n" + "\n".join(f"{x:.4f},{y:.4f}" for x, y in pts) + "\n",
        encoding="utf-8",
    )
    n = TURNS
    d_out = (outer_w + outer_h) / 2
    d_in = d_out - 2 * n * (TRACE_W + GAP)
    d_avg = (d_out + d_in) / 2
    fill = (d_out - d_in) / (d_out + d_in)
    L_uh = estimate_l_uh(outer_w, outer_h, n, TRACE_W, GAP)
    f_mhz = f_res_mhz(L_uh, 50.0)
    (ROOT / "antenna" / "estimate.txt").write_text(
        f"outer_w={outer_w} mm\nouter_h={outer_h} mm\nturns={n}\n"
        f"width={TRACE_W} gap={GAP}\nd_avg={d_avg:.2f} fill={fill:.3f}\n"
        f"L_estimate≈{L_uh:.2f} uH (rough)\n"
        f"f_res≈{f_mhz:.1f} MHz with Cin=50 pF only (parasitics lower this)\n"
        f"target L≈2.2–2.8 µH; first article may need C1≈10–22 pF\n"
        f"chip_island_w=n/a\n"
        f"text_zone_w={TEXT_ZONE_W} mm\n"
        f"comp_strip_w={COMP_STRIP_W} mm\n",
        encoding="utf-8",
    )


def write_fp_lib_table() -> None:
    (ROOT / "fp-lib-table").write_text(
        f"""(fp_lib_table
\t(version 7)
\t(lib (name "NFC_BusinessCard")(type "KiCad")(uri "${{KIPRJMOD}}/lib/footprints/NFC_BusinessCard.pretty")(options "")(descr "NFC business card footprints"))
)
""",
        encoding="utf-8",
    )
    (ROOT / "sym-lib-table").write_text(
        f"""(sym_lib_table
\t(version 7)
\t(lib (name "NFC_BusinessCard")(type "KiCad")(uri "${{KIPRJMOD}}/lib/symbols/NFC_BusinessCard.kicad_sym")(options "")(descr "NFC business card symbols"))
)
""",
        encoding="utf-8",
    )


def main() -> None:
    ensure_dirs()
    write_symbol_lib()
    write_xqfn_footprint()
    write_gnd_island_footprint()
    write_antenna_footprint()
    write_c0402_footprint()
    write_r0402_footprint()
    write_fp_lib_table()
    write_project(SCHEMATIC_ROOT_UUID)
    write_schematic(SCHEMATIC_ROOT_UUID)
    write_pcb()
    print(f"Generated KiCad project under {ROOT}")


if __name__ == "__main__":
    main()
