#!/usr/bin/env python3
"""Prepare the ENIG name font for KiCad.

KiCad resolves a font only when its FAMILY name is unique / exactly
resolvable. Weight-suffixed names like 'Georgia Bold' are not resolvable (wx
exposes only the family 'Georgia'), so pcbnew silently falls back to the
built-in stroke font. This script copies the name font and rewrites its name
table to a unique family ('GeorgiaBold') that KiCad resolves without ambiguity.

Both Pillow (preview) and KiCad (bake / gerber) then share one face. Run with
--install to register the renamed font in ~/Library/Fonts so the KiCad GUI and
kicad-cli can resolve it too.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import NameRecord

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class NameFontSpec:
    face: str                  # key in scripts/fonts.py (SilkLayout NAME_FONT_FACE)
    src: Path                   # system source font
    out: Path                   # repo-local renamed copy
    unique_family: str          # family name KiCad can resolve
    install_name: str           # filename under ~/Library/Fonts


NAME_FONT = NameFontSpec(
    face="Georgia Bold",
    src=Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf"),
    out=ROOT / "assets" / "fonts" / "Georgia-Bold.ttf",
    unique_family="GeorgiaBold",
    install_name="Georgia-Bold.ttf",
)


def _rename_face(font, *, family: str, style: str = "Regular") -> None:
    """Rewrite name fields so KiCad resolves the face uniquely."""
    name = font["name"]
    ids = {1: family, 2: style, 4: family, 6: family, 16: family, 17: style}
    targets = ((3, 1, 0x409), (3, 10, 0x409), (1, 0, 0))
    for rec in list(name.names):
        if (rec.platformID, rec.platEncID, rec.langID) in targets and rec.nameID in ids:
            name.names.remove(rec)
    for pid, eid, lang in targets:
        for nid, val in ids.items():
            rec = NameRecord()
            rec.platformID, rec.platEncID, rec.langID = pid, eid, lang
            rec.nameID = nid
            rec.string = val.encode("utf-16-be") if pid == 3 else val.encode("mac_roman")
            name.names.append(rec)
    name.names.sort()


def main() -> None:
    spec = NAME_FONT
    if not spec.src.is_file():
        sys.exit(f"Missing {spec.src} — install the font first")
    font = TTFont(str(spec.src))
    _rename_face(font, family=spec.unique_family)
    spec.out.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(spec.out))
    print(
        f"Wrote {spec.out} — face: {font['name'].getDebugName(1)} / "
        f"{font['name'].getDebugName(2)} (src {spec.src.name})"
    )

    if "--install" in sys.argv:
        dest = Path.home() / "Library" / "Fonts" / spec.install_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(spec.out), str(dest))
        print(f"Installed {dest}")
        print("Note: restart any running KiCad so it re-scans fonts.")


if __name__ == "__main__":
    main()
