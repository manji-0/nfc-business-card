#!/usr/bin/env python3
"""Encode monochrome PNG as KiCad PCB image s-expression (KiCad 9+)."""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from kicad10 import fmt_mm, quuid
from sexpr import SexprDoc
from silk_layout import SILK_BITMAP_PX_PER_MM

PPI = 300
MM_PER_INCH = 25.4
BASE64_LINE_WIDTH = 76


def load_ink_mask(path: Path, alpha_threshold: int = 160) -> Image.Image:
    """Return 1-bit image: 1 = silk ink."""
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    out = Image.new("1", (w, h), 0)
    src, dst = im.load(), out.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a >= alpha_threshold and max(r, g, b) > 32:
                dst[x, y] = 1
    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)
    return out


def resize_for_silk(im: Image.Image, size_mm: float, px_per_mm: float = SILK_BITMAP_PX_PER_MM) -> Image.Image:
    target_px = max(16, int(size_mm * px_per_mm))
    w, h = im.size
    scale = target_px / max(w, h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((nw, nh), Image.Resampling.NEAREST)


def ink_mask_to_png_bytes(im: Image.Image) -> bytes:
    """White silk on transparent background."""
    w, h = im.size
    rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    src, dst = im.load(), rgba.load()
    for y in range(h):
        for x in range(w):
            if src[x, y]:
                dst[x, y] = (255, 255, 255, 255)
    buf = io.BytesIO()
    rgba.save(buf, format="PNG", dpi=(PPI, PPI))
    return buf.getvalue()


def image_scale_for_size(pixel_dim: int, size_mm: float, ppi: int = PPI) -> float:
    """User scale so the image's largest dimension equals size_mm on the board."""
    return size_mm * ppi / (pixel_dim * MM_PER_INCH)


def _image_center_mm(
    *,
    at_x_mm: float,
    at_y_mm: float,
    draw_w: float,
    draw_h: float,
    center: bool,
    preview_coords: bool,
) -> tuple[float, float]:
    """Return KiCad image center; preview_coords use Y down from board top."""
    if center:
        return at_x_mm, at_y_mm

    return at_x_mm + draw_w / 2, at_y_mm + draw_h / 2


def format_image_data(png_bytes: bytes) -> SexprDoc:
    encoded = base64.b64encode(png_bytes).decode("ascii")
    lines = [encoded[i : i + BASE64_LINE_WIDTH] for i in range(0, len(encoded), BASE64_LINE_WIDTH)]
    doc = SexprDoc()
    with doc.node("(data"):
        for line in lines:
            doc.line(f'"{line}"')
    return doc


def bitmap_sexpr_rgba(
    png_path: Path,
    *,
    at_x_mm: float,
    at_y_mm: float,
    px_per_mm: float = SILK_BITMAP_PX_PER_MM,
    layer: str,
    center: bool = False,
    preview_coords: bool = False,
) -> SexprDoc:
    """Place a PNG at native px_per_mm resolution (no rescale)."""
    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    draw_w = w / px_per_mm
    draw_h = h / px_per_mm
    center_x, center_y = _image_center_mm(
        at_x_mm=at_x_mm,
        at_y_mm=at_y_mm,
        draw_w=draw_w,
        draw_h=draw_h,
        center=center,
        preview_coords=preview_coords,
    )
    max_dim_mm = max(draw_w, draw_h)
    scale = image_scale_for_size(max(w, h), max_dim_mm)
    png_bytes = png_path.read_bytes()
    doc = SexprDoc()
    with doc.node("(image"):
        doc.line(f"(at {fmt_mm(center_x)} {fmt_mm(center_y)})")
        doc.line(f'(layer "{layer}")')
        if abs(scale - 1.0) > 1e-9:
            doc.line(f"(scale {scale:.6g})")
        doc.embed(format_image_data(png_bytes))
        doc.line(f"(uuid {quuid()})")
    return doc


def bitmap_sexpr(
    png_path: Path,
    *,
    at_x_mm: float,
    at_y_mm: float,
    size_mm: float,
    layer: str,
    center: bool = False,
    preview_coords: bool = False,
) -> SexprDoc:
    im = resize_for_silk(load_ink_mask(png_path), size_mm)
    w, h = im.size
    draw_w = size_mm * (w / max(w, h))
    draw_h = size_mm * (h / max(w, h))
    center_x, center_y = _image_center_mm(
        at_x_mm=at_x_mm,
        at_y_mm=at_y_mm,
        draw_w=draw_w,
        draw_h=draw_h,
        center=center,
        preview_coords=preview_coords,
    )
    scale = image_scale_for_size(max(w, h), size_mm)
    doc = SexprDoc()
    with doc.node("(image"):
        doc.line(f"(at {fmt_mm(center_x)} {fmt_mm(center_y)})")
        doc.line(f'(layer "{layer}")')
        if abs(scale - 1.0) > 1e-9:
            doc.line(f"(scale {scale:.6g})")
        doc.embed(format_image_data(ink_mask_to_png_bytes(im)))
        doc.line(f"(uuid {quuid()})")
    return doc
