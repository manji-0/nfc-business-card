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

from generate_kicad_project import ASSETS, C1_LCSC, LOGOS, nfc_layout  # noqa: E402
from gerber_silk import SilkBitmap, append_bitmaps_to_gerber  # noqa: E402
from kicad_paths import find_kicad_cli, kicad_fontconfig_env  # noqa: E402
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

BOM_HEADER = "Designator,Footprint,Quantity,Value,LCSC Part #\n"
U1_BOM_ROW = "U1,XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111,1,NT3H2111W0FHKH,C710403"
C1_BOM_ROW = f"C1,C_0402_1005Metric,1,10pF NP0,{C1_LCSC}"


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


def _require_kicad_cli() -> Path:
    try:
        return find_kicad_cli()
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{exc} Install KiCad 10+ or set KICAD_CLI."
        ) from exc


def _run_kicad_export() -> None:
    kicad_cli = _require_kicad_cli()
    if GERBER_DIR.exists():
        shutil.rmtree(GERBER_DIR)
    GERBER_DIR.mkdir(parents=True)

    subprocess.run(
        [
            str(kicad_cli),
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
        env=kicad_fontconfig_env(),
    )
    subprocess.run(
        [str(kicad_cli), "pcb", "export", "drill", "-o", str(GERBER_DIR), str(PCB)],
        check=True,
        env=kicad_fontconfig_env(),
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
    """Write DNP and C1-populated JLCPCB BOM variants."""
    (FAB / "bom.csv").write_text(BOM_HEADER + U1_BOM_ROW + "\n", encoding="utf-8")
    (FAB / "bom-c1.csv").write_text(
        BOM_HEADER + U1_BOM_ROW + "\n" + C1_BOM_ROW + "\n",
        encoding="utf-8",
    )


def _export_kicad_positions(*, exclude_dnp: bool) -> list[tuple[str, float, float, float, str]]:
    """Return (ref, x, y, rot, side) from KiCad pos export."""
    kicad_cli = _require_kicad_cli()
    tmp = FAB / ".kicad-pos.csv"
    cmd = [
        str(kicad_cli),
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
        "--smd-only",
        str(PCB),
    ]
    if exclude_dnp:
        cmd.insert(-1, "--exclude-dnp")
    subprocess.run(cmd, check=True, env=kicad_fontconfig_env())

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
    return rows


def _write_positions_csv(
    path: Path,
    rows: list[tuple[str, float, float, float, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Designator", "Mid X", "Mid Y", "Rotation", "Layer"])
        for ref, x, y, rot, side in rows:
            writer.writerow([ref, f"{x:.4f}", f"{y:.4f}", f"{rot:.0f}", side])


def _c1_placement_row(
    u1_row: tuple[str, float, float, float, str],
) -> tuple[str, float, float, float, str]:
    """C1 is exclude_from_pos_files; derive KiCad CPL coords from layout offset to U1."""
    lay = nfc_layout()
    _u1_x, u1_y = lay["u1"]
    _c1_x, c1_y = lay["c1"]
    _ref, x, y, rot, side = u1_row
    return ("C1", x, y - (c1_y - u1_y), rot, side)


def _write_positions() -> tuple[list[tuple[str, float, float, float, str]], list[tuple[str, float, float, float, str]]]:
    """Export CPL for DNP (U1) and C1-populated (U1 + C1) assembly."""
    dnp_rows = _export_kicad_positions(exclude_dnp=True)
    u1_rows = [r for r in dnp_rows if r[0] == "U1"]
    if len(u1_rows) != 1:
        raise RuntimeError("Expected exactly one U1 in KiCad pos export")
    c1_rows = [u1_rows[0], _c1_placement_row(u1_rows[0])]

    _write_positions_csv(FAB / "positions.csv", dnp_rows)
    _write_positions_csv(FAB / "positions-c1.csv", c1_rows)
    return dnp_rows, c1_rows


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

### Variant A — C1 DNP (hand-tune after test)

- BOM: `fab/bom.csv` (U1 = C710403)
- CPL: `fab/positions.csv`

### Variant B — C1 populated (10 pF NP0, recommended first tuned build)

- BOM: `fab/bom-c1.csv` (U1 = C710403, **C1 = C301961** Walsin 10 pF NP0)
- CPL: `fab/positions-c1.csv` (U1 + C1, F.Cu top)
- C1 value targets ~14.6 MHz resonance (see `scripts/tune_antenna.py`)

CPL uses KiCad pos export (**Mid Y negative**, matches Gerber top-origin).

## Directory layout

```
fab/
  nfc-business-card-gerbers.zip   ← upload to JLCPCB
  bom.csv / positions.csv         ← C1 DNP assembly
  bom-c1.csv / positions-c1.csv   ← C1 populated assembly
  preview.png / preview-front.png
  gerber/                         ← full KiCad export (reference)
```

## Regenerate fab outputs

```bash
./task fab
# or full pipeline:
./task export
```

Requires KiCad 10+ (`kicad-cli` on PATH or macOS app bundle). See [SETUP.md](../SETUP.md).

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
    dnp_placements, c1_placements = _write_positions()
    _write_checklist()
    zip_path = _zip_gerbers()

    print(f"Wrote fab outputs to {FAB}")
    print(f"  Gerbers: {GERBER_DIR}")
    print(f"  Zip: {zip_path}")
    print("  BOM/CPL (C1 DNP): bom.csv, positions.csv")
    print(f"  BOM/CPL (C1 populated): bom-c1.csv, positions-c1.csv (C1={C1_LCSC} 10pF NP0)")
    for ref, x, y, rot, side in c1_placements:
        print(f"  CPL {ref}: ({x:.4f}, {y:.4f}) mm rot {rot:.0f}° {side}")


if __name__ == "__main__":
    main()
