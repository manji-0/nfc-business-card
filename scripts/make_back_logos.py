#!/usr/bin/env python3
"""Rasterize back-side tech logos to white silk PNGs (2x2 grid on board back)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from svg_to_silk import rasterize_svg

ROOT = Path(__file__).resolve().parents[1]
LOGOS = ROOT / "assets" / "logos"

# 2x2 order: top-left → top-right → bottom-left → bottom-right
LOGO_FILES = (
    ("openstack", "openstack.svg"),
    ("kubernetes", "kubernetes.svg"),
    ("prometheus", "prometheus.svg"),
    ("oidc", "oidc.svg"),
)


def main() -> None:
    LOGOS.mkdir(parents=True, exist_ok=True)
    for name, filename in LOGO_FILES:
        svg = LOGOS / filename
        if not svg.exists():
            raise FileNotFoundError(f"Missing {svg}")
        silk = rasterize_svg(svg, size_px=512)
        out = LOGOS / f"{name}-silk.png"
        silk.save(out)
        prev = Image.new("RGB", silk.size, (14, 14, 16))
        prev.paste(silk, mask=silk.split()[-1])
        prev.save(LOGOS / f"{name}-preview.png")
        print(f"Wrote {out.name} {silk.size}")


if __name__ == "__main__":
    main()
