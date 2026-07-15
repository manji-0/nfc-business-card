#!/usr/bin/env python3
"""Export JLCPCB-oriented fab files (Gerbers, BOM, CPL).

Runs KiCad CLI for copper/mask/paste/outline, then appends PNG silk graphics
because KiCad does not export embedded PCB images to Gerber.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_kicad_project import ASSETS, LOGOS, nfc_layout  # noqa: E402
from gerber_silk import SilkBitmap, append_bitmaps_to_gerber  # noqa: E402
from silk_layout import (  # noqa: E402
    CONTACT_X_MM,
    NFC_LOGO_SIZE_MM,
    QR_X_MM,
    ROLES_Y0_MM,
    TEXT_LEFT_MM,
    contact_top_y_mm,
    back_logo_grid,
    qr_size_mm,
    qr_top_y_mm,
)

FAB = ROOT / "fab"
GERBER_DIR = FAB / "gerber"
PCB = ROOT / "nfc-business-card.kicad_pcb"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")

JLC_GERBER_GLOBS = (
    "*-F_Cu.gbr",
    "*-B_Cu.gbr",
    "*-F_Mask.gbr",
    "*-B_Mask.gbr",
    "*-F_Silkscreen.gbr",
    "*-B_Silkscreen.gbr",
    "*-F_Paste.gbr",
    "*-Edge_Cuts.gbr",
    "*.drl",
)


def _clean_fab_stale() -> None:
    """Remove duplicate Gerbers and scratch dirs under fab/."""
    for path in FAB.glob("nfc-business-card-*"):
        if path.is_file() and path.suffix in {".gbr", ".gbo", ".gto", ".drl"}:
            path.unlink()
        elif path.suffix == ".gbrjob":
            path.unlink()
    for name in ("gerber-kicad-test", "gerber-kicad-test2", "nfc-business-card-gerbers"):
        stale = FAB / name
        if stale.is_dir():
            shutil.rmtree(stale)
    for name in ("test-silk.svg", "preview.svg"):
        scratch = FAB / name
        if scratch.is_file():
            scratch.unlink()


def _require_kicad_cli() -> None:
    if not KICAD_CLI.is_file():
        raise FileNotFoundError(
            f"KiCad CLI not found at {KICAD_CLI}. Install KiCad or set KICAD_CLI."
        )


def _run_kicad_export() -> None:
    _require_kicad_cli()
    if GERBER_DIR.exists():
        shutil.rmtree(GERBER_DIR)
    GERBER_DIR.mkdir(parents=True)

    subprocess.run(
        [
            str(KICAD_CLI),
            "pcb",
            "export",
            "gerbers",
            "--board-plot-params",
            "--exclude-refdes",
            "-o",
            str(GERBER_DIR),
            str(PCB),
        ],
        check=True,
    )
    subprocess.run(
        [str(KICAD_CLI), "pcb", "export", "drill", "-o", str(GERBER_DIR), str(PCB)],
        check=True,
    )


def _silk_placements() -> tuple[list[SilkBitmap], list[SilkBitmap]]:
    lay = nfc_layout()
    ant_cx, ant_cy = lay["ant_cx"], lay["ant_cy"]
    front = [
        SilkBitmap(ASSETS / "roles-silk.png", TEXT_LEFT_MM, ROLES_Y0_MM, "F.SilkS"),
        SilkBitmap(
            ASSETS / "contacts-silk.png",
            CONTACT_X_MM,
            contact_top_y_mm(),
            "F.SilkS",
        ),
        SilkBitmap(
            ASSETS / "qr-silk.png",
            QR_X_MM,
            qr_top_y_mm(),
            "F.SilkS",
            size_mm=qr_size_mm(),
        ),
        SilkBitmap(
            ASSETS / "nfc-n-mark-silk.png",
            ant_cx,
            ant_cy,
            "F.SilkS",
            center=True,
            size_mm=NFC_LOGO_SIZE_MM,
        ),
    ]
    logo_mm, back_items = back_logo_grid()
    back = [
        SilkBitmap(LOGOS / filename, cx, cy, "B.SilkS", center=True, size_mm=logo_mm)
        for filename, cx, cy in back_items
    ]
    return front, back


def _merge_silk_graphics() -> None:
    front, back = _silk_placements()
    f_silk = next(GERBER_DIR.glob("*-F_Silkscreen.gbr"))
    b_silk = next(GERBER_DIR.glob("*-B_Silkscreen.gbr"))
    n_front = append_bitmaps_to_gerber(f_silk, front)
    n_back = append_bitmaps_to_gerber(b_silk, back)
    print(f"  Silk regions appended: front={n_front}, back={n_back}")


def _write_bom() -> None:
    (FAB / "bom.csv").write_text(
        "Designator,Footprint,Quantity,Value,LCSC Part #\n"
        "U1,XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111,1,NT3H2111W0FHKH,C710403\n",
        encoding="utf-8",
    )


def _write_positions() -> list[tuple[str, float, float, float, str]]:
    """Export CPL via KiCad CLI (JLCPCB expects KiCad pos coords, not preview Y)."""
    tmp = FAB / ".kicad-pos.csv"
    subprocess.run(
        [
            str(KICAD_CLI),
            "pcb",
            "export",
            "pos",
            "-o",
            str(tmp),
            "--format",
            "csv",
            "--units",
            "mm",
            "--side",
            "front",
            "--exclude-dnp",
            "--smd-only",
            str(PCB),
        ],
        check=True,
    )
    rows: list[tuple[str, float, float, float, str]] = []
    with tmp.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    row["Ref"].strip('"'),
                    float(row["PosX"]),
                    float(row["PosY"]),
                    float(row["Rot"]),
                    row["Side"].strip('"').lower(),
                )
            )
    tmp.unlink()

    out = FAB / "positions.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Designator", "Mid X", "Mid Y", "Rotation", "Layer"])
        for ref, x, y, rot, side in rows:
            writer.writerow([ref, f"{x:.4f}", f"{y:.4f}", f"{rot:.0f}", side])
    return rows


def _write_checklist() -> None:
    (FAB / "ORDER_CHECKLIST.md").write_text(
        """# JLCPCB order checklist

## PCB

- Layers: 2
- Dimensions: 89 × 51 mm
- Thickness: **0.8 mm**
- Surface finish: **ENIG**
- Solder mask: **Black**
- Silkscreen: **White**
- Layout: left text zone (ENIG name on F.Cu), right NFC antenna + chip at feed
- Upload **`fab/nfc-business-card-gerbers.zip`** (generated by `./task export` or `./task fab`)
- ENIG name is on **F.Cu** + **F.Mask** opening (not a separate layer)

## SMT Assembly

- Qty: start with **5**
- Side: Top
- BOM: `fab/bom.csv` (U1 = C710403)
- CPL: `fab/positions.csv` (KiCad pos export — **Mid Y negative**, matches Gerber top-origin)
- C1 is DNP

## Directory layout

```
fab/
  nfc-business-card-gerbers.zip   ← upload to JLCPCB
  bom.csv / positions.csv
  preview.png / preview-front.png
  gerber/                         ← full KiCad export (reference)
```

## Regenerate fab outputs

```bash
./task fab
# or full pipeline:
./task export
```

Requires KiCad 10+ at `/Applications/KiCad/KiCad.app`.

## JLCPCB options

- Copper: 1 oz (default)
- Board outline tolerance: **Precision** (±0.1 mm) recommended for card size
- Run online DFM before checkout
""",
        encoding="utf-8",
    )


def _zip_gerbers() -> Path:
    zip_path = FAB / "nfc-business-card-gerbers.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pattern in JLC_GERBER_GLOBS:
            for path in sorted(GERBER_DIR.glob(pattern)):
                zf.write(path, arcname=path.name)
    return zip_path


def main() -> None:
    FAB.mkdir(parents=True, exist_ok=True)
    _clean_fab_stale()

    print("Exporting Gerbers via KiCad CLI...")
    _run_kicad_export()
    _merge_silk_graphics()
    _write_bom()
    placements = _write_positions()
    _write_checklist()
    zip_path = _zip_gerbers()

    print(f"Wrote fab outputs to {FAB}")
    print(f"  Gerbers: {GERBER_DIR}")
    print(f"  Zip: {zip_path}")
    for ref, x, y, rot, side in placements:
        print(f"  CPL {ref}: ({x:.4f}, {y:.4f}) mm rot {rot:.0f}° {side}")


if __name__ == "__main__":
    main()
