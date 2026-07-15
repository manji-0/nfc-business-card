#!/usr/bin/env python3
"""Rasterize SVG to white-on-transparent silk PNG via rsvg-convert."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ALPHA_THRESHOLD = 160


def rasterize_svg(svg_path: Path, size_px: int = 2048) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out_png = Path(tmp.name)

    if shutil.which("rsvg-convert"):
        cmd = [
            "rsvg-convert",
            "-w",
            str(size_px),
            "-h",
            str(size_px),
            "--background-color=transparent",
            str(svg_path),
            "-o",
            str(out_png),
        ]
    elif shutil.which("nix-shell"):
        cmd = [
            "nix-shell",
            "-p",
            "librsvg",
            "--run",
            (
                f"rsvg-convert -w {size_px} -h {size_px} "
                f"--background-color=transparent {svg_path} -o {out_png}"
            ),
        ]
    else:
        raise RuntimeError("rsvg-convert not found — install librsvg or use Nix")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"rsvg-convert failed: {result.stderr.strip()}")

    try:
        rgba = Image.open(out_png).convert("RGBA")
    finally:
        out_png.unlink(missing_ok=True)

    return rgba_to_white_silk(rgba)


def rgba_to_white_silk(rgba: Image.Image) -> Image.Image:
    w, h = rgba.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    src, dst = rgba.load(), out.load()
    for y in range(h):
        for x in range(w):
            _, _, _, a = src[x, y]
            if a >= ALPHA_THRESHOLD:
                dst[x, y] = (255, 255, 255, 255)
    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)
    return out
