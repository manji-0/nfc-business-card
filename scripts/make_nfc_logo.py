#!/usr/bin/env python3
"""Rasterize assets/nfc-symbol.svg to white silk PNG for PCB preview/KiCad."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from svg_to_silk import rasterize_svg

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE_SVG = ASSETS / "nfc-symbol.svg"


def main() -> None:
    if not SOURCE_SVG.exists():
        raise FileNotFoundError(f"Missing {SOURCE_SVG}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    logo = rasterize_svg(SOURCE_SVG, size_px=512)
    logo.save(ASSETS / "nfc-simplified-silk.png")
    logo.save(ASSETS / "nfc-n-mark-silk.png")
    prev = Image.new("RGB", logo.size, (14, 14, 16))
    prev.paste(logo, mask=logo.split()[-1])
    prev.save(ASSETS / "nfc-simplified-preview.png")
    prev.save(ASSETS / "nfc-n-mark-preview.png")
    print(f"Rasterized {SOURCE_SVG.name} via rsvg-convert -> silk {logo.size}")


if __name__ == "__main__":
    main()
