#!/usr/bin/env python3
"""Render silk text blocks to PNG (shared by preview and KiCad)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from fonts import FontFile, font_file
from silk_layout import (
    CONTACT_FONT_SIZE_MM,
    CONTACT_LINE_STEP_MM,
    ROLE_FONT_SIZE_MM,
    ROLES_LINE_STEP_MM,
    SILK_BITMAP_PX_PER_MM,
    SILK_FONT_FACE,
)

SILK_FONT = font_file(SILK_FONT_FACE)


def render_silk_text_block(
    lines: tuple[str, ...],
    *,
    font_file: FontFile = SILK_FONT,
    font_size_mm: float,
    line_step_mm: float,
    px_per_mm: float = SILK_BITMAP_PX_PER_MM,
    pad_px: int = 1,
) -> Image.Image:
    """White text on transparent RGBA, rendered at px_per_mm."""
    if not font_file.path.exists():
        raise FileNotFoundError(f"Missing font {font_file.path}")

    font_px = max(8, int(round(font_size_mm * px_per_mm)))
    font = ImageFont.truetype(str(font_file.path), font_px, index=font_file.index)

    metrics: list[tuple[int, int, int, int]] = []
    for line in lines:
        bbox = font.getbbox(line)
        metrics.append(bbox)

    text_w = max(b[2] - b[0] for b in metrics)
    text_h = (len(lines) - 1) * int(round(line_step_mm * px_per_mm)) + max(b[3] - b[1] for b in metrics)
    w = text_w + 2 * pad_px
    h = text_h + 2 * pad_px
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    y = pad_px
    line_advance = int(round(line_step_mm * px_per_mm))
    for line, bbox in zip(lines, metrics):
        x = pad_px - bbox[0]
        y_draw = y - bbox[1]
        draw.text((x, y_draw), line, font=font, fill=(255, 255, 255, 255))
        y += line_advance

    return im


def crop_to_ink(im: Image.Image, *, alpha_threshold: int = 10) -> Image.Image:
    """Trim transparent margins so the leftmost ink sits at x=0."""
    alpha = im.getchannel("A")
    bbox = alpha.point(lambda a: 255 if a > alpha_threshold else 0).getbbox()
    if not bbox:
        return im
    return im.crop(bbox)


def image_size_mm(im: Image.Image, px_per_mm: float = SILK_BITMAP_PX_PER_MM) -> tuple[float, float]:
    w, h = im.size
    return w / px_per_mm, h / px_per_mm
