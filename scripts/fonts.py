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


@dataclass(frozen=True, slots=True)
class FontFile:
    """A concrete font file; index selects the face inside a TTC."""

    path: Path
    index: int = 0


FONTS: dict[str, FontFile] = {
    "Georgia Bold": FontFile(FONT_DIR / "Georgia Bold.ttf"),
    "Arial": FontFile(FONT_DIR / "Arial.ttf"),
    "Baskerville SemiBold": FontFile(FONT_DIR / "Baskerville.ttc", index=4),
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
