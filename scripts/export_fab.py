#!/usr/bin/env python3
"""Export JLCPCB-oriented fab files (BOM, CPL, copper preview Gerber).

Full production Gerbers (mask, silk, paste, ENIG name) must be exported from KiCad
(Fabrication Toolkit or plot dialog) — see fab/ORDER_CHECKLIST.md.
"""

from __future__ import annotations

import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from card_copy import NAME  # noqa: E402
from generate_kicad_project import (  # noqa: E402
    BOARD_H,
    BOARD_W,
    FEED_TRACE_W,
    TRACE_W,
    feed_routes,
    nfc_layout,
)
from jlcpcb_limits import XQFN_PAD_EDGE_MM, XQFN_PAD_ROW_MM  # noqa: E402
from silk_layout import NAME_CAP_HEIGHT_MM, NAME_X_MM, NAME_Y_MM  # noqa: E402

FAB = ROOT / "fab"


def mm_to_gerber(x: float, y: float) -> str:
    return f"X{int(round(x * 10000)):06d}Y{int(round(y * 10000)):06d}"


def write_gerber_copper(
    path: Path,
    segments_by_width: dict[float, list[tuple[tuple[float, float], tuple[float, float]]]],
    rects: list[tuple[float, float, float, float]],
    flashes: list[tuple[float, float, float]],
) -> None:
    """Write F.Cu preview: traces by width, filled rects, round flashes."""
    lines = ["%FSLAX46Y46*%", "%MOMM*%", "%LPD*%", "G01*"]
    dcode = 10
    width_to_d: dict[float, int] = {}
    for width in sorted(segments_by_width):
        width_to_d[width] = dcode
        lines.append(f"%ADD{dcode}C,{width:.3f}*%")
        dcode += 1
    flash_d = dcode
    flash_r = flashes[0][2] if flashes else 0.6
    lines.append(f"%ADD{flash_d}C,{flash_r:.3f}*%")
    dcode += 1

    for width, segs in segments_by_width.items():
        lines.append(f"D{width_to_d[width]}*")
        for a, b in segs:
            lines.append(f"{mm_to_gerber(*a)}D02*")
            lines.append(f"{mm_to_gerber(*b)}D01*")

    for x0, y0, x1, y1 in rects:
        lines.append("G36*")
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)):
            lines.append(f"{mm_to_gerber(x, y)}D02*")
            lines.append(f"{mm_to_gerber(x, y)}D01*")
        lines.append("G37*")

    if flashes:
        lines.append(f"D{flash_d}*")
        for x, y, _ in flashes:
            lines.append(f"{mm_to_gerber(x, y)}D03*")

    lines.append("M02*")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_edge_cuts(path: Path) -> None:
    lines = [
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "%ADD10C,0.100*%",
        "G01*",
        "D10*",
        f"{mm_to_gerber(0, 0)}D02*",
        f"{mm_to_gerber(BOARD_W, 0)}D01*",
        f"{mm_to_gerber(BOARD_W, BOARD_H)}D01*",
        f"{mm_to_gerber(0, BOARD_H)}D01*",
        f"{mm_to_gerber(0, 0)}D01*",
        "M02*",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def collect_geometry() -> tuple[
    dict[float, list[tuple[tuple[float, float], tuple[float, float]]]],
    list[tuple[float, float, float, float]],
    list[tuple[float, float, float]],
    tuple[float, float],
]:
    lay = nfc_layout()
    u1, c1 = lay["u1"], lay["c1"]
    ant_abs = [(lay["ant_cx"] + x, lay["ant_cy"] + y) for x, y in lay["ant_pts"]]
    ant1, ant2 = ant_abs[0], ant_abs[-1]

    segs_by_w: dict[float, list] = defaultdict(list)
    for a, b in zip(ant_abs, ant_abs[1:]):
        segs_by_w[TRACE_W].append((a, b))
    for x0, y0, x1, y1, _net, w in feed_routes(ant1, ant2, u1, c1):
        segs_by_w[w].append(((x0, y0), (x1, y1)))

    # Name ENIG is KiCad gr_text — omitted from raster preview gerber
    pad_y = u1[1] + 0.75
    flashes = [
        (ant1[0], ant1[1], 0.6),
        (ant2[0], ant2[1], 0.6),
        (u1[0] - 0.20, pad_y, XQFN_PAD_ROW_MM),
        (u1[0] + 0.20, pad_y, XQFN_PAD_ROW_MM),
        (u1[0] - 0.75, u1[1] + 0.20, XQFN_PAD_EDGE_MM),
        (c1[0] - 0.48, c1[1], 0.52),
        (c1[0] + 0.48, c1[1], 0.52),
    ]
    return segs_by_w, [], flashes, u1


def main() -> None:
    FAB.mkdir(parents=True, exist_ok=True)
    (FAB / "gerber").mkdir(exist_ok=True)

    segs_by_w, name_rects, flashes, u1 = collect_geometry()
    gdir = FAB / "gerber"
    write_gerber_copper(gdir / "nfc-business-card-F_Cu.gbr", segs_by_w, name_rects, flashes)
    write_edge_cuts(gdir / "nfc-business-card-Edge_Cuts.gbr")
    (gdir / "nfc-business-card-B_Cu.gbr").write_text("%FSLAX46Y46*%\n%MOMM*%\nM02*\n", encoding="utf-8")
    (gdir / "nfc-business-card-PTH.drl").write_text("M48\nMETRIC,TZ\n%\nM30\n", encoding="utf-8")

    # Placeholders — use KiCad plot for production mask/silk/paste
    for name in (
        "nfc-business-card-F_Mask.gbr",
        "nfc-business-card-B_Mask.gbr",
        "nfc-business-card-F_Silkscreen.gbr",
        "nfc-business-card-B_Silkscreen.gbr",
        "nfc-business-card-F_Paste.gbr",
    ):
        (gdir / name).write_text(
            f"%FSLAX46Y46*%\n%MOMM*%\n% Placeholder — export from KiCad for production\nM02*\n",
            encoding="utf-8",
        )

    (FAB / "bom.csv").write_text(
        "Designator,Footprint,Quantity,Value,LCSC Part #\n"
        "U1,XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111,1,NT3H2111W0FHKH,C710403\n",
        encoding="utf-8",
    )
    (FAB / "positions.csv").write_text(
        "Designator,Mid X,Mid Y,Rotation,Layer\n"
        f"U1,{u1[0]:.4f},{u1[1]:.4f},0,top\n",
        encoding="utf-8",
    )

    (FAB / "ORDER_CHECKLIST.md").write_text(
        """# JLCPCB order checklist

## PCB

- Layers: 2
- Dimensions: 89 × 51 mm
- Thickness: **0.8 mm**
- Surface finish: **ENIG**
- Solder mask: **Black**
- Silkscreen: **White**
- Layout: left text zone (ENIG name), right NFC antenna + chip at feed
- **Upload Gerbers from KiCad** (mask / silk / paste / ENIG name) — not the placeholder layers in `fab/gerber/`
- Optional copper preview: `fab/nfc-business-card-gerbers.zip` (F.Cu + outline only)

## SMT Assembly

- Qty: start with **5**
- Side: Top
- BOM: `fab/bom.csv` (U1 = C710403)
- CPL: `fab/positions.csv` (synced to U1 feed position)
- C1 is DNP

## JLCPCB options

- Copper: 1 oz (default)
- Board outline tolerance: **Precision** (±0.1 mm) recommended for card size
- Run online DFM before checkout
""",
        encoding="utf-8",
    )

    zip_path = FAB / "nfc-business-card-gerbers.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(gdir.iterdir()):
            zf.write(p, arcname=p.name)

    print(f"Wrote fab outputs to {FAB}")
    print(f"  U1 CPL: ({u1[0]:.4f}, {u1[1]:.4f}) mm")


if __name__ == "__main__":
    main()
