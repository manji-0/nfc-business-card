#!/usr/bin/env python3
"""Convert profile art to 1-bit silkscreen (white on black PCB).

Light/colored pixels → white silk. Near-white background → empty (black mask).
Dark outlines/clothing → black mask (no silk) for contrast.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "profile.png"
OUT_RGBA = ROOT / "assets" / "profile-silk.png"  # white silk + alpha
OUT_PREVIEW = ROOT / "assets" / "profile-mono-preview.png"  # B/W preview on black


def convert(
    src: Path = SRC,
    bg_threshold: int = 245,
    silk_threshold: int = 55,
) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    opx = out.load()

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                continue
            # Treat near-white as background
            if r >= bg_threshold and g >= bg_threshold and b >= bg_threshold:
                continue
            # Luminance
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            # Dark lines / navy uniform stay as mask (no silk)
            if lum < silk_threshold:
                continue
            # Everything else becomes solid white silk (pixel-art friendly)
            opx[x, y] = (255, 255, 255, 255)

    return out


def main() -> None:
    silk = convert()
    # Tight crop to non-transparent bounds
    bbox = silk.getbbox()
    if bbox:
        silk = silk.crop(bbox)
    silk.save(OUT_RGBA)
    # Preview: white silk on black
    preview = Image.new("RGB", silk.size, (10, 10, 12))
    preview.paste(silk, (0, 0), silk)
    preview.save(OUT_PREVIEW)
    print(f"Wrote {OUT_RGBA} {silk.size}")
    print(f"Wrote {OUT_PREVIEW}")


if __name__ == "__main__":
    main()
