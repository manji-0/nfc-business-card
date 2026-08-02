#!/usr/bin/env python3
"""Generate KiCad 10 project for NFC business card (89x51 mm)."""

from __future__ import annotations

import math
import uuid
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
    FEED_LA_BYPASS_DX_MM,
    FEED_TRACE_W_MM,
    GND_ISLAND_DX_MM,
    GND_ISLAND_H_MM,
    GND_ISLAND_W_MM,
    NC_TERM_GND_BUS_INSET_MM,
    NC_TERM_R_LCSC,
    NC_TERM_R_OFFSET_MM,
    NC_TERM_R_KOHM,
    R0402_PAD_OFFSET_MM,
    XQFN_PAD_EDGE_MM,
    XQFN_PAD_ROW_MM,
)
from bake_name_enig import bake_name_enig_sexpr
from kamae.boundary import require_existing_file
from kamae.result import Err, unwrap
from kicad10 import (
    PCB_FORMAT_VERSION,
    fp_circle,
    fp_line,
    fp_pad_circle,
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
NC_TERMINATORS: tuple[tuple[str, str, float, float], ...] = (
    ("R2", "SCL", -0.75, -0.20),
    ("R4", "FD", -0.20, -0.75),
    ("R3", "SDA", 0.20, -0.75),
    ("R5", "VCC", 0.75, -0.20),
    ("R6", "VOUT", 0.75, 0.20),
)
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


def feed_routes(
    ant1_abs: tuple[float, float],
    ant2_abs: tuple[float, float],
    u1: tuple[float, float],
    c1: tuple[float, float],
) -> list[tuple[float, float, float, float, str, float, str]]:
    """Return feed polylines as (x0, y0, x1, y1, net, width_mm, layer).

    LA skirts left of U1 (bypass) so the vertical bus never crosses FD (pad 4).
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
    la_bypass_x = u1_x - FEED_LA_BYPASS_DX_MM
    c1_la = (c1_x - 0.48, c1_y)
    c1_lb = (c1_x + 0.48, c1_y)
    w = FEED_TRACE_W
    # Inner via: step into spiral hollow; outer via: component strip east of U1
    via_in = (ant2_abs[0] + ANT_TIE_TAKEOFF_DX_MM, ant2_abs[1] + ANT_TIE_VIA_DY_MM)
    via_out = (u1_x + 2.0, pad_y)
    return [
        # LA antenna → skirt left of chip → enter pad 1 from the left
        (ant1_abs[0], ant1_abs[1], la_bypass_x, ant1_abs[1], "LA", w, "F.Cu"),
        (la_bypass_x, ant1_abs[1], la_bypass_x, pad_y, "LA", w, "F.Cu"),
        (la_bypass_x, pad_y, la_x, pad_y, "LA", w, "F.Cu"),
        # LA from C1 (above chip — la_x vertical is clear of FD)
        (c1_la[0], c1_la[1], la_x, c1_la[1], "LA", w, "F.Cu"),
        (la_x, c1_la[1], la_x, pad_y, "LA", w, "F.Cu"),
        # LB: B.Cu underpass from via_in (net-tie pad 2 covers take-off→via) → pad 8
        (via_in[0], via_in[1], via_out[0], via_in[1], "LB", w, "B.Cu"),
        (via_out[0], via_in[1], via_out[0], via_out[1], "LB", w, "B.Cu"),
        (via_out[0], via_out[1], lb_x, pad_y, "LB", w, "F.Cu"),
        # LB from C1
        (c1_lb[0], c1_lb[1], lb_x, c1_lb[1], "LB", w, "F.Cu"),
        (lb_x, c1_lb[1], lb_x, pad_y, "LB", w, "F.Cu"),
    ]


def feed_vias(
    ant2_abs: tuple[float, float],
    u1: tuple[float, float],
) -> list[tuple[float, float, str]]:
    """Vias for the LB underpass (inner hollow + component strip)."""
    u1_x, u1_y = u1
    pad_y = u1_y + 0.75
    via_in = (ant2_abs[0] + ANT_TIE_TAKEOFF_DX_MM, ant2_abs[1] + ANT_TIE_VIA_DY_MM)
    via_out = (u1_x + 2.0, pad_y)
    return [(via_in[0], via_in[1], "LB"), (via_out[0], via_out[1], "LB")]


def gnd_island_route(u1: tuple[float, float]) -> list[tuple[float, float, float, float, str, float, str]]:
    """Short stub from VSS (pad 2) to a local copper island in the component strip."""
    u1_x, u1_y = u1
    vss = (u1_x - 0.75, u1_y + 0.20)
    island = (u1_x - GND_ISLAND_DX_MM, u1_y + 0.20)
    return [(vss[0], vss[1], island[0], island[1], "GND", FEED_TRACE_W, "F.Cu")]


def nc_terminator_placements(
    u1: tuple[float, float],
) -> list[tuple[str, str, float, float, float, float]]:
    """Return (ref, net, rcx, rcy, pad_x, pad_y) for each B.Cu DNP pull-down."""
    u1_x, u1_y = u1
    return [
        (
            ref,
            net,
            u1_x + dx - NC_TERM_R_OFFSET_MM,
            u1_y + dy,
            u1_x + dx,
            u1_y + dy,
        )
        for ref, net, dx, dy in NC_TERMINATORS
    ]


def nc_terminator_routes(
    u1: tuple[float, float],
) -> tuple[list[tuple[float, float, float, float, str, float, str]], list[tuple[float, float, str]]]:
    """B.Cu pull-down routes: U1 NC pad via → R → shared GND bus → island via."""
    u1_x, u1_y = u1
    gnd_x = u1_x - GND_ISLAND_DX_MM
    gnd_y = u1_y + 0.20
    gnd_bus_x = gnd_x - GND_ISLAND_W_MM / 2 - NC_TERM_GND_BUS_INSET_MM
    w = FEED_TRACE_W
    segs: list[tuple[float, float, float, float, str, float, str]] = []
    vias: list[tuple[float, float, str]] = []
    bus_ys: list[float] = []
    for _ref, net, rcx, rcy, pad_x, pad_y in nc_terminator_placements(u1):
        r_pad1_x = rcx + R0402_PAD_OFFSET_MM
        r_pad2_x = rcx - R0402_PAD_OFFSET_MM
        vias.append((pad_x, pad_y, net))
        segs.append((pad_x, pad_y, r_pad1_x, rcy, net, w, "B.Cu"))
        segs.append((r_pad2_x, rcy, gnd_bus_x, rcy, "GND", w, "B.Cu"))
        bus_ys.append(rcy)
    if bus_ys:
        y0, y1 = min(bus_ys), max(bus_ys)
        if y1 > y0:
            segs.append((gnd_bus_x, y0, gnd_bus_x, y1, "GND", w, "B.Cu"))
        segs.append((gnd_bus_x, gnd_y, gnd_x, gnd_y, "GND", w, "B.Cu"))
        vias.append((gnd_x, gnd_y, "GND"))
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
        f"""(kicad_symbol_lib
\t(version 20231120)
\t(generator "nfc_business_card")
\t(generator_version "1.0")
\t(symbol "NT3H2111W0FHKH"
\t\t(pin_names (offset 1.016))
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(property "Reference" "U"
\t\t\t(at 0 8.89 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Value" "NT3H2111W0FHKH"
\t\t\t(at 0 -8.89 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Datasheet" "https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Description" "NTAG I2C plus Type 2 Tag, 1kB, 50pF"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "LCSC Part #" "C710403"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "ki_keywords" "NFC NTAG Type2"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(symbol "NT3H2111W0FHKH_0_1"
\t\t\t(rectangle
\t\t\t\t(start -7.62 7.62)
\t\t\t\t(end 7.62 -7.62)
\t\t\t\t(stroke (width 0.254) (type default))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t)
\t\t(symbol "NT3H2111W0FHKH_1_1"
\t\t\t(pin passive line (at -10.16 5.08 0) (length 2.54)
\t\t\t\t(name "LA" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at -10.16 2.54 0) (length 2.54)
\t\t\t\t(name "VSS" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at -10.16 0 0) (length 2.54)
\t\t\t\t(name "SCL" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "3" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at -10.16 -2.54 0) (length 2.54)
\t\t\t\t(name "FD" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "4" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at 10.16 -2.54 180) (length 2.54)
\t\t\t\t(name "SDA" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "5" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at 10.16 0 180) (length 2.54)
\t\t\t\t(name "VCC" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "6" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at 10.16 2.54 180) (length 2.54)
\t\t\t\t(name "VOUT" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "7" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at 10.16 5.08 180) (length 2.54)
\t\t\t\t(name "LB" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "8" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t)
\t)
\t(symbol "Antenna_NFC"
\t\t(pin_names (offset 1.016))
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(property "Reference" "ANT"
\t\t\t(at 0 5.08 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Value" "Antenna_NFC"
\t\t\t(at 0 -5.08 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "NFC_BusinessCard:Antenna_Spiral_29x45_5T"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Datasheet" "~"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Description" "PCB spiral NFC antenna net-tie"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(symbol "Antenna_NFC_0_1"
\t\t\t(arc
\t\t\t\t(start -2.54 0)
\t\t\t\t(mid 0 2.54)
\t\t\t\t(end 2.54 0)
\t\t\t\t(stroke (width 0) (type default))
\t\t\t\t(fill (type none))
\t\t\t)
\t\t\t(arc
\t\t\t\t(start -1.27 0)
\t\t\t\t(mid 0 1.27)
\t\t\t\t(end 1.27 0)
\t\t\t\t(stroke (width 0) (type default))
\t\t\t\t(fill (type none))
\t\t\t)
\t\t)
\t\t(symbol "Antenna_NFC_1_1"
\t\t\t(pin passive line (at -5.08 0 0) (length 2.54)
\t\t\t\t(name "1" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t\t(pin passive line (at 5.08 0 180) (length 2.54)
\t\t\t\t(name "2" (effects (font (size 1.27 1.27))))
\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))
\t\t\t)
\t\t)
\t)
\t(symbol "C_0402"
\t\t(pin_numbers (hide yes))
\t\t(pin_names (offset 0.254))
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(property "Reference" "C" (at 0.635 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "C_0402" (at 0.635 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "NFC_BusinessCard:C_0402_1005Metric" (at 0.9652 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(symbol "C_0402_0_1"
\t\t\t(polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
\t\t\t(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
\t\t)
\t\t(symbol "C_0402_1_1"
\t\t\t(pin passive line (at 0 3.81 270) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t(pin passive line (at 0 -3.81 90) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
\t\t)
\t)
\t(symbol "GND"
\t\t(power)
\t\t(pin_numbers (hide yes))
\t\t(pin_names (offset 0))
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "GND" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(symbol "GND_0_1"
\t\t\t(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27))
\t\t\t\t(stroke (width 0) (type default)) (fill (type none)))
\t\t)
\t\t(symbol "GND_1_1"
\t\t\t(pin power_in line (at 0 0 0) (length 0) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t)
\t)
\t(symbol "PWR_FLAG"
\t\t(power)
\t\t(pin_numbers (hide yes))
\t\t(pin_names (offset 0))
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "PWR_FLAG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(symbol "PWR_FLAG_0_0"
\t\t\t(pin power_out line (at 0 0 0) (length 0) (name "pwr" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t)
\t)
)
""",
        encoding="utf-8",
    )


def xqfn_pad_wh(_rot_deg: float) -> tuple[float, float]:
    """Return KiCad pad (width, height) before rotation.

    Long axis toward package centre: size is always (EDGE, ROW). Top/bottom pads
    use rot=90 so the long axis lands on Y; side pads use rot=0 (long on X).
    """
    return XQFN_PAD_EDGE_MM, XQFN_PAD_ROW_MM


def write_xqfn_footprint() -> None:
    """XQFN-8 1.6x1.6 P0.4mm, no EP solder (NXP SOT902-3)."""
    # Pad centers: 2 pads per side, pitch 0.4, body 1.6
    # Pin 1 at top-left going counterclockwise (NXP XQFN8 convention used here):
    # Top: 1(left), 8(right); Right: 7(top), 6(bot); Bottom: 5(right), 4(left); Left: 3(bot), 2(top)
    # Actually NXP Fig.3 typically: pin1 LA top-left, CCW.
    pads = {
        # (num, x, y, rot_deg) — pad long axis toward package center
        "1": (-0.20, 0.75, 90),   # top, left  -> LA
        "8": (0.20, 0.75, 90),    # top, right -> LB
        "7": (0.75, 0.20, 0),     # right, top -> VOUT
        "6": (0.75, -0.20, 0),    # right, bot -> VCC
        "5": (0.20, -0.75, 90),   # bot, right -> SDA
        "4": (-0.20, -0.75, 90),  # bot, left  -> FD
        "3": (-0.75, -0.20, 0),   # left, bot  -> SCL
        "2": (-0.75, 0.20, 0),    # left, top  -> VSS
    }
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
    for num, (x, y, rot) in pads.items():
        pw, ph = xqfn_pad_wh(rot)
        lines.append(
            f'\t(pad "{num}" smd roundrect (at {x} {y} {rot}) (size {pw} {ph}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio 0.25) (uuid {uid()}))'
        )
    lines.append(")")
    path = LIB / "footprints" / "NFC_BusinessCard.pretty" / "XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111.kicad_mod"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
\t(pad "1" smd roundrect (at -0.48 0) (size 0.52 0.62) (layers "B.Cu" "B.Paste" "B.Mask") (roundrect_rratio 0.15) (uuid {uid()}))
\t(pad "2" smd roundrect (at 0.48 0) (size 0.52 0.62) (layers "B.Cu" "B.Paste" "B.Mask") (roundrect_rratio 0.15) (uuid {uid()}))
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
    from jlcpcb_limits import DESIGN_TRACE_CLEARANCE_MM, FEED_TRACE_W_MM

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
        "min_clearance": {DESIGN_TRACE_CLEARANCE_MM},
        "min_track_width": {FEED_TRACE_W_MM},
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
  "sheets": [
    ["{schematic_uuid}", "Root"]
  ],
  "text_variables": {{}}
}}
"""
    (ROOT / "nfc-business-card.kicad_pro").write_text(project_json, encoding="utf-8")


def _schematic_nc_terminator_symbols(sheet_path: str) -> str:
    """R2–R6: 100 kΩ DNP pull-downs from NC pins to GND."""
    pins = [
        ("R2", "SCL", 116.84, 85.09, 114.3),
        ("R4", "FD", 116.84, 82.55, 114.3),
        ("R3", "SDA", 137.16, 82.55, 139.7),
        ("R5", "VCC", 137.16, 85.09, 139.7),
        ("R6", "VOUT", 137.16, 87.63, 139.7),
    ]
    gnd_y = 93.98
    pin_span = 3.81
    lines: list[str] = []
    for ref, _net, ux, uy, rx in pins:
        rot = 90 if rx < ux else 270
        if rot == 90:
            pin_u1_x = rx + pin_span
            pin_gnd_x = rx - pin_span
        else:
            pin_u1_x = rx - pin_span
            pin_gnd_x = rx + pin_span
        label_dx = 2.54 if rot == 90 else -2.54
        lines.append(
            f"""\t(symbol
\t\t(lib_id "NFC_BusinessCard:R_0402")
\t\t(at {rx} {uy} {rot})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp yes)
\t\t(uuid {uid()})
\t\t(property "Reference" "{ref}" (at {rx + label_dx} {uy - 1.27} {rot}) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "DNP" (at {rx + label_dx} {uy + 1.27} {rot}) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "NFC_BusinessCard:R_0402_1005Metric" (at {rx} {uy} {rot}) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "LCSC Part #" "{NC_TERM_R_LCSC}" (at {rx} {uy} {rot}) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "{ref}") (unit 1))))
\t)"""
        )
        lines.append(f'\t(wire (pts (xy {ux} {uy}) (xy {pin_u1_x} {uy})) (stroke (width 0) (type default)) (uuid {uid()}))')
        lines.append(f'\t(wire (pts (xy {pin_gnd_x} {uy}) (xy {pin_gnd_x} {gnd_y})) (stroke (width 0) (type default)) (uuid {uid()}))')
    lines.append(f'\t(wire (pts (xy 110.49 {gnd_y}) (xy 116.84 {gnd_y})) (stroke (width 0) (type default)) (uuid {uid()}))')
    lines.append(f'\t(wire (pts (xy 116.84 {gnd_y}) (xy 116.84 93.98)) (stroke (width 0) (type default)) (uuid {uid()}))')
    lines.append(f'\t(wire (pts (xy 143.51 {gnd_y}) (xy 137.16 {gnd_y})) (stroke (width 0) (type default)) (uuid {uid()}))')
    lines.append(f'\t(wire (pts (xy 137.16 {gnd_y}) (xy 137.16 93.98)) (stroke (width 0) (type default)) (uuid {uid()}))')
    return "\n".join(lines)


def write_schematic(schematic_uuid: str) -> None:
    """Minimal schematic: U1 + ANT1 + C1(DNP) + R2–R6(DNP), on 1.27 mm grid."""
    sheet_path = f"/{schematic_uuid}"
    nc_terms = _schematic_nc_terminator_symbols(sheet_path)
    path = ROOT / "nfc-business-card.kicad_sch"
    path.write_text(
        f"""(kicad_sch
\t(version 20231120)
\t(generator "nfc_business_card")
\t(generator_version "1.0")
\t(uuid {schematic_uuid})
\t(paper "A4")
\t(title_block
\t\t(title "NFC Business Card")
\t\t(date "2026-07-14")
\t\t(rev "B")
\t\t(company "")
\t\t(comment 1 "89x51mm passive NFC URL tag")
\t\t(comment 2 "NT3H2111W0FHKH LCSC C710403")
\t)
\t(lib_symbols
\t\t(symbol "NFC_BusinessCard:NT3H2111W0FHKH"
\t\t\t(pin_names (offset 1.016))
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom yes)
\t\t\t(on_board yes)
\t\t\t(property "Reference" "U" (at 0 8.89 0) (effects (font (size 1.27 1.27))))
\t\t\t(property "Value" "NT3H2111W0FHKH" (at 0 -8.89 0) (effects (font (size 1.27 1.27))))
\t\t\t(property "Footprint" "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Datasheet" "https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Description" "NTAG I2C plus Type 2 Tag, 1kB, 50pF" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "LCSC Part #" "C710403" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "ki_keywords" "NFC NTAG Type2" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "NT3H2111W0FHKH_0_1"
\t\t\t\t(rectangle (start -7.62 7.62) (end 7.62 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))
\t\t\t)
\t\t\t(symbol "NT3H2111W0FHKH_1_1"
\t\t\t\t(pin passive line (at -10.16 5.08 0) (length 2.54) (name "LA" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at -10.16 2.54 0) (length 2.54) (name "VSS" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at -10.16 0 0) (length 2.54) (name "SCL" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at -10.16 -2.54 0) (length 2.54) (name "FD" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 10.16 -2.54 180) (length 2.54) (name "SDA" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 10.16 0 180) (length 2.54) (name "VCC" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 10.16 2.54 180) (length 2.54) (name "VOUT" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 10.16 5.08 180) (length 2.54) (name "LB" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
\t\t\t)
\t\t)
\t\t(symbol "NFC_BusinessCard:Antenna_NFC"
\t\t\t(pin_names (offset 1.016))
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom no)
\t\t\t(on_board yes)
\t\t\t(property "Reference" "ANT" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
\t\t\t(property "Value" "Antenna_NFC" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
\t\t\t(property "Footprint" "NFC_BusinessCard:Antenna_Spiral_29x45_5T" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Datasheet" "~" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Description" "PCB spiral NFC antenna net-tie" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "Antenna_NFC_0_1"
\t\t\t\t(arc (start -2.54 0) (mid 0 2.54) (end 2.54 0) (stroke (width 0) (type default)) (fill (type none)))
\t\t\t\t(arc (start -1.27 0) (mid 0 1.27) (end 1.27 0) (stroke (width 0) (type default)) (fill (type none)))
\t\t\t)
\t\t\t(symbol "Antenna_NFC_1_1"
\t\t\t\t(pin passive line (at -5.08 0 0) (length 2.54) (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 5.08 0 180) (length 2.54) (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
\t\t\t)
\t\t)
\t\t(symbol "NFC_BusinessCard:C_0402"
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 0.254))
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom yes)
\t\t\t(on_board yes)
\t\t\t(property "Reference" "C" (at 0.635 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t\t(property "Value" "C_0402" (at 0.635 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t\t(property "Footprint" "NFC_BusinessCard:C_0402_1005Metric" (at 0.9652 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "C_0402_0_1"
\t\t\t\t(polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
\t\t\t\t(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
\t\t\t)
\t\t\t(symbol "C_0402_1_1"
\t\t\t\t(pin passive line (at 0 3.81 270) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 0 -3.81 90) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
\t\t\t)
\t\t)
\t\t(symbol "NFC_BusinessCard:R_0402"
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 0.254))
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom yes)
\t\t\t(on_board yes)
\t\t\t(property "Reference" "R" (at 0.635 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t\t(property "Value" "R_0402" (at 0.635 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t\t(property "Footprint" "NFC_BusinessCard:R_0402_1005Metric" (at 0.9652 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "R_0402_0_1"
\t\t\t\t(rectangle (start -1.016 -0.508) (end 1.016 0.508) (stroke (width 0.254) (type default)) (fill (type none)))
\t\t\t)
\t\t\t(symbol "R_0402_1_1"
\t\t\t\t(pin passive line (at 0 3.81 270) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t\t(pin passive line (at 0 -3.81 90) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
\t\t\t)
\t\t)
\t\t(symbol "NFC_BusinessCard:GND"
\t\t\t(power)
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 0))
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom no)
\t\t\t(on_board no)
\t\t\t(property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Value" "GND" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
\t\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "GND_0_1"
\t\t\t\t(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27))
\t\t\t\t\t(stroke (width 0) (type default)) (fill (type none)))
\t\t\t)
\t\t\t(symbol "GND_1_1"
\t\t\t\t(pin power_in line (at 0 0 0) (length 0) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t)
\t\t)
\t\t(symbol "NFC_BusinessCard:PWR_FLAG"
\t\t\t(power)
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 0))
\t\t\t(exclude_from_sim no)
\t\t\t(in_bom no)
\t\t\t(on_board no)
\t\t\t(property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Value" "PWR_FLAG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t\t(symbol "PWR_FLAG_0_0"
\t\t\t\t(pin power_out line (at 0 0 0) (length 0) (name "pwr" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
\t\t\t)
\t\t)
\t)
\t(symbol
\t\t(lib_id "NFC_BusinessCard:NT3H2111W0FHKH")
\t\t(at 127 85.09 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "U1" (at 127 74.93 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "NT3H2111W0FHKH" (at 127 95.25 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111" (at 127 85.09 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "LCSC Part #" "C710403" (at 127 85.09 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(pin "3" (uuid {uid()}))
\t\t(pin "4" (uuid {uid()}))
\t\t(pin "5" (uuid {uid()}))
\t\t(pin "6" (uuid {uid()}))
\t\t(pin "7" (uuid {uid()}))
\t\t(pin "8" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "U1") (unit 1))))
\t)
\t(symbol
\t\t(lib_id "NFC_BusinessCard:Antenna_NFC")
\t\t(at 88.9 78.74 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "ANT1" (at 88.9 71.12 0) (effects (font (size 1.27 1.27))))
\t\t(property "Value" "Antenna_NFC" (at 88.9 86.36 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "NFC_BusinessCard:Antenna_Spiral_29x45_5T" (at 88.9 78.74 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "ANT1") (unit 1))))
\t)
\t(symbol
\t\t(lib_id "NFC_BusinessCard:C_0402")
\t\t(at 106.68 68.58 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp yes)
\t\t(uuid {uid()})
\t\t(property "Reference" "C1" (at 109.22 67.31 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "DNP" (at 109.22 69.85 0) (effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "NFC_BusinessCard:C_0402_1005Metric" (at 106.68 68.58 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "LCSC Part #" "{C1_LCSC}" (at 106.68 68.58 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(pin "2" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "C1") (unit 1))))
\t)
\t(symbol
\t\t(lib_id "NFC_BusinessCard:GND")
\t\t(at 116.84 93.98 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "#PWR01" (at 116.84 100.33 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "GND" (at 116.84 97.79 0) (effects (font (size 1.27 1.27))))
\t\t(property "Footprint" "" (at 116.84 93.98 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "#PWR01") (unit 1))))
\t)
\t(symbol
\t\t(lib_id "NFC_BusinessCard:PWR_FLAG")
\t\t(at 114.3 93.98 0)
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board no)
\t\t(dnp no)
\t\t(uuid {uid()})
\t\t(property "Reference" "#FLG01" (at 114.3 91.44 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Value" "PWR_FLAG" (at 114.3 91.44 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(property "Footprint" "" (at 114.3 93.98 0) (effects (font (size 1.27 1.27)) (hide yes)))
\t\t(pin "1" (uuid {uid()}))
\t\t(instances (project "nfc-business-card" (path "{sheet_path}" (reference "#FLG01") (unit 1))))
\t)
\t(wire (pts (xy 83.82 78.74) (xy 81.28 78.74)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(global_label "LA" (shape input) (at 81.28 78.74 180) (effects (font (size 1.27 1.27)) (justify right bottom)) (uuid {uid()}))
\t(wire (pts (xy 116.84 80.01) (xy 114.3 80.01)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(global_label "LA" (shape input) (at 114.3 80.01 180) (effects (font (size 1.27 1.27)) (justify right bottom)) (uuid {uid()}))
\t(wire (pts (xy 106.68 72.39) (xy 106.68 74.93)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(global_label "LB" (shape input) (at 106.68 74.93 270) (effects (font (size 1.27 1.27)) (justify right bottom)) (uuid {uid()}))
\t(wire (pts (xy 93.98 78.74) (xy 96.52 78.74)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(global_label "LB" (shape input) (at 96.52 78.74 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))
\t(wire (pts (xy 137.16 80.01) (xy 139.7 80.01)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(global_label "LB" (shape input) (at 139.7 80.01 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))
\t(wire (pts (xy 106.68 64.77) (xy 106.68 62.23)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(global_label "LA" (shape input) (at 106.68 62.23 90) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {uid()}))
\t(wire (pts (xy 116.84 82.55) (xy 116.84 93.98)) (stroke (width 0) (type default)) (uuid {uid()}))
\t(wire (pts (xy 116.84 93.98) (xy 114.3 93.98)) (stroke (width 0) (type default)) (uuid {uid()}))
{nc_terms}
\t(text "Passive NFC business card\\nU1=NT3H2111 (C710403)\\nC1=DNP tuning LA-LB (10-22 pF NP0)\\nR2-R6=DNP 100k to GND (SCL/SDA/FD/VCC/VOUT)\\nVSS=local GND island"
\t\t(at 88.9 104.14 0)
\t\t(effects (font (size 1.27 1.27)) (justify left bottom))
\t\t(uuid {uid()})
\t)
\t(sheet_instances
\t\t(path "{sheet_path}" (page "1"))
\t)
)
""",
        encoding="utf-8",
    )


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


def _fp_hidden_fields() -> str:
    return (
        footprint_property("Datasheet", "", 0, 0, 0, "F.Fab", hide=True)
        + footprint_property("Description", "", 0, 0, 0, "F.Fab", hide=True)
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
        fp_pad_roundrect("1", -0.2, 0.75, 90, *xqfn_pad_wh(90), net="LA"),
        fp_pad_roundrect("2", -0.75, 0.2, 0, *xqfn_pad_wh(0), net="GND"),
        fp_pad_roundrect("3", -0.75, -0.2, 0, *xqfn_pad_wh(0), net="SCL"),
        fp_pad_roundrect("4", -0.2, -0.75, 90, *xqfn_pad_wh(90), net="FD"),
        fp_pad_roundrect("5", 0.2, -0.75, 90, *xqfn_pad_wh(90), net="SDA"),
        fp_pad_roundrect("6", 0.75, -0.2, 0, *xqfn_pad_wh(0), net="VCC"),
        fp_pad_roundrect("7", 0.75, 0.2, 0, *xqfn_pad_wh(0), net="VOUT"),
        fp_pad_roundrect("8", 0.2, 0.75, 90, *xqfn_pad_wh(90), net="LB"),
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
    net LA meets net LB here without a track↔pad short.
    """
    end = ant_pts[-1]
    end_x, end_y = end
    pad_d = ANTENNA_FEED_PAD_D_MM
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
        # pad 1 (LA): copper from coil inner end to the LB take-off
        f'\t\t(pad "1" connect roundrect\n'
        f'\t\t\t(at {end_x + ANT_TIE_TAKEOFF_DX_MM / 2:.4f} {end_y:.4f})\n'
        f'\t\t\t(size {ANT_TIE_TAKEOFF_DX_MM} {pad_d})\n'
        f'\t\t\t(layers "F.Cu")\n'
        f'\t\t\t(roundrect_rratio 0.2)\n'
        f'\t\t\t(net "LA")\n'
        f'\t\t\t(uuid {quuid()})\n'
        f'\t\t)',
        # pad 2 (LB): take-off down to via_in (overlaps pad 1 by design)
        f'\t\t(pad "2" connect roundrect\n'
        f'\t\t\t(at {end_x + ANT_TIE_TAKEOFF_DX_MM:.4f} {end_y + ANT_TIE_VIA_DY_MM / 2:.4f})\n'
        f'\t\t\t(size {pad_d} {ANT_TIE_VIA_DY_MM})\n'
        f'\t\t\t(layers "F.Cu")\n'
        f'\t\t\t(roundrect_rratio 0.2)\n'
        f'\t\t\t(net "LB")\n'
        f'\t\t\t(uuid {quuid()})\n'
        f'\t\t)',
        "\t\t(embedded_fonts no)",
        "\t)",
    ]
    return "\n".join(parts) + "\n"


def build_gnd_island(u1: tuple[float, float]) -> str:
    """Local VSS copper island in the component strip (not under the spiral)."""
    u1_x, u1_y = u1
    x = u1_x - GND_ISLAND_DX_MM
    y = u1_y + 0.20
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
        _fp_hidden_fields(),
        footprint_property("LCSC Part #", NC_TERM_R_LCSC, 0, 0, 0, "B.Fab", hide=True, font_size=(1.27, 1.27), thickness=0),
        f'\t\t(property "Description" "{NC_TERM_R_KOHM}k NC pull-down" (at 0 0 0)',
        '\t\t\t(layer "B.Fab")',
        "\t\t\t(hide yes)",
        '\t\t\t(effects (font (size 1.27 1.27) (thickness 0.15)))',
        "\t\t)",
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
    vias = [via(x, y, net) for x, y, net in feed_vias(ant2_abs, lay["u1"])]
    vias += [via(x, y, net) for x, y, net in nc_vias]

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
    end = pts[-1]
    end_x, end_y = end
    pad_d = ANTENNA_FEED_PAD_D_MM
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
        f'\t(pad "1" connect roundrect (at {end_x + ANT_TIE_TAKEOFF_DX_MM / 2:.4f} {end_y:.4f}) '
        f'(size {ANT_TIE_TAKEOFF_DX_MM} {pad_d}) (layers "F.Cu") (roundrect_rratio 0.2) (uuid {uid()}))',
        f'\t(pad "2" connect roundrect (at {end_x + ANT_TIE_TAKEOFF_DX_MM:.4f} {end_y + ANT_TIE_VIA_DY_MM / 2:.4f}) '
        f'(size {pad_d} {ANT_TIE_VIA_DY_MM}) (layers "F.Cu") (roundrect_rratio 0.2) (uuid {uid()}))',
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
    L_uh = 0.027 * (n**2) * (d_avg / 10) / (1 + 2.75 * fill)
    f_mhz = 1e3 / (2 * math.pi * math.sqrt(L_uh * 50.0)) if L_uh > 0 else 0.0
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
