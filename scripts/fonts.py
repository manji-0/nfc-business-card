#!/usr/bin/env python3
"""Font registry — single source of truth for preview and KiCad bake fonts.

Face names come from SilkLayout (scripts/silk_layout.py: NAME_FONT_FACE /
SILK_FONT_FACE). This module maps a face name to its concrete font file
(TTF/TTC) so the preview (Pillow), the KiCad pcbnew bake, and the layout
checkers all render the same typeface. To change a card font, edit FONTS here
and the face name in silk_layout.py — do not hardcode font paths in consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
FONT_SYS = Path("/System/Library/Fonts")
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class FontFile:
    """A concrete font file; index selects the face inside a TTC."""

    path: Path
    index: int = 0


# The ENIG name font is prepared by scripts/split_font.py: its name table is
# rewritten to the unique family 'GeorgiaBold' because KiCad cannot resolve
# weight-suffixed names like 'Georgia Bold' (wx only exposes the family
# 'Georgia') and would silently fall back to the built-in stroke font. Pillow
# preview and KiCad bake read this same file, so the name is one source of
# truth.
_SPLIT = ROOT / "assets" / "fonts" / "Georgia-Bold.ttf"
_FALLBACK_GEORGIA = FontFile(FONT_DIR / "Georgia Bold.ttf")

# Face name KiCad must receive for SetFontProp to resolve the font.
KICAD_FACE_NAMES: dict[str, str] = {
    "Georgia Bold": "GeorgiaBold",
}

FONTS: dict[str, FontFile] = {
    "Georgia Bold": (
        FontFile(_SPLIT, index=0) if _SPLIT.is_file() else _FALLBACK_GEORGIA
    ),
    "Arial": FontFile(FONT_DIR / "Arial.ttf"),
    "Helvetica Neue": FontFile(FONT_SYS / "HelveticaNeue.ttc"),
}


def font_file(face: str) -> FontFile:
    """Resolve a font face name (SilkLayout) to its font file."""
    try:
        return FONTS[face]
    except KeyError:
        raise KeyError(
            f"Font face {face!r} not registered in scripts/fonts.py FONTS"
        ) from None


def font_path(face: str) -> Path:
    """Resolve a font face name to its TTF/TTC path (index via font_index())."""
    return font_file(face).path


def font_index(face: str) -> int:
    """Face index inside a TTC (0 for plain TTF)."""
    return font_file(face).index


def kicad_face_name(face: str) -> str:
    """Face name to hand to KiCad's SetFontProp so it resolves the font.

    Identity by default; 'Baskerville SemiBold' maps to the unique
    'BaskervilleSemiBold' family that the split TTF (and KiCad) understands.
    """
    return KICAD_FACE_NAMES.get(face, face)
