#!/usr/bin/env python3
"""Export inverted QR silk PNG for KiCad / preview."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from qr_silk import make_qr_silk

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "qr-silk.png"
PREVIEW = ROOT / "assets" / "qr-preview.png"
EXPORT_PX = 512


def main() -> None:
    silk = make_qr_silk()
    silk = silk.resize((EXPORT_PX, EXPORT_PX), Image.Resampling.NEAREST)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    silk.save(OUT)
    prev = Image.new("RGB", (EXPORT_PX, EXPORT_PX), (14, 14, 16))
    prev.paste(silk, mask=silk.split()[-1])
    prev.save(PREVIEW)
    print(f"Wrote {OUT} ({silk.size[0]}x{silk.size[1]})")


if __name__ == "__main__":
    main()
