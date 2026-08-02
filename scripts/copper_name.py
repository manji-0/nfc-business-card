#!/usr/bin/env python3
"""Convert display name to F.Cu polygons (ENIG gold via soldermask opening)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from fonts import FontFile, font_file
from jlcpcb_limits import JLC_MIN_MASK_BRIDGE_MM
from kicad10 import gr_poly_copper
from sexpr import SexprDoc
from silk_layout import NAME_CAP_HEIGHT_MM, NAME_DILATE_K, NAME_FONT_FACE

NAME_FONT = font_file(NAME_FONT_FACE)
RENDER_PX_PER_MM = 64.0
MIN_MASK_DAM_MM = JLC_MIN_MASK_BRIDGE_MM


def _ink_rectangles(im: Image.Image) -> list[tuple[int, int, int, int]]:
    w, h = im.size
    px = im.load()
    rects: list[tuple[int, int, int, int]] = []
    for y in range(h):
        x = 0
        while x < w:
            while x < w and not px[x, y]:
                x += 1
            if x >= w:
                break
            x0 = x
            while x < w and px[x, y]:
                x += 1
            rects.append((x0, y, x, y + 1))
    return rects


def _merge_row_rects(rects: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Merge horizontal runs per scanline only — never stack into vertical slabs."""
    if not rects:
        return []
    rects.sort(key=lambda r: (r[1], r[0]))
    merged = [rects[0]]
    for x0, y0, x1, y1 in rects[1:]:
        px0, py0, px1, py1 = merged[-1]
        if y0 == py0 and y1 == py1 and x0 <= px1 + 2:
            merged[-1] = (px0, py0, max(px1, x1), py1)
        else:
            merged.append((x0, y0, x1, y1))
    return merged


def _close_mask_slivers_mm(
    rects_mm: list[tuple[float, float, float, float]],
    max_gap_mm: float = MIN_MASK_DAM_MM,
) -> list[tuple[float, float, float, float]]:
    """Narrow mask webs only — extend facing edges, never merge into letter-spanning blobs."""
    rects = [list(r) for r in rects_mm]
    changed = True
    while changed:
        changed = False
        for i in range(len(rects)):
            x0, y0, x1, y1 = rects[i]
            for j in range(i + 1, len(rects)):
                a0, b0, a1, b1 = rects[j]
                if min(y1, b1) - max(y0, b0) > 0:
                    if a0 >= x1:
                        gap = a0 - x1
                        if 0 < gap < max_gap_mm:
                            mid = (x1 + a0) / 2
                            rects[i][2] = mid
                            rects[j][0] = mid
                            changed = True
                    elif x0 >= a1:
                        gap = x0 - a1
                        if 0 < gap < max_gap_mm:
                            mid = (a1 + x0) / 2
                            rects[i][0] = mid
                            rects[j][2] = mid
                            changed = True
                if min(x1, a1) - max(x0, a0) > 0:
                    if b0 >= y1:
                        gap = b0 - y1
                        if 0 < gap < max_gap_mm:
                            mid = (y1 + b0) / 2
                            rects[i][3] = mid
                            rects[j][1] = mid
                            changed = True
                    elif y0 >= b1:
                        gap = y0 - b1
                        if 0 < gap < max_gap_mm:
                            mid = (b1 + y0) / 2
                            rects[i][1] = mid
                            rects[j][3] = mid
                            changed = True
    return [tuple(r) for r in rects]


def name_copper_rects_mm(
    text: str,
    *,
    origin_x_mm: float,
    origin_y_mm: float,
    cap_height_mm: float = NAME_CAP_HEIGHT_MM,
    dilate_k: int = NAME_DILATE_K,
    font_file: FontFile = NAME_FONT,
) -> list[tuple[float, float, float, float]]:
    """Return axis-aligned copper rectangles in mm: (x0, y0, x1, y1)."""
    if not font_file.path.exists():
        raise FileNotFoundError(f"Missing font {font_file.path}")

    font_px = max(8, int(cap_height_mm * RENDER_PX_PER_MM * 0.92))
    font = ImageFont.truetype(str(font_file.path), font_px, index=font_file.index)
    bbox = font.getbbox(text)
    pad = max(2, int(0.25 * RENDER_PX_PER_MM))
    w = bbox[2] - bbox[0] + 2 * pad
    h = bbox[3] - bbox[1] + 2 * pad
    im = Image.new("1", (w, h), 0)
    draw = ImageDraw.Draw(im)
    draw.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=1)
    if dilate_k > 1:
        im = im.filter(ImageFilter.MaxFilter(dilate_k))

    ink_bbox = im.getbbox()
    if ink_bbox is None:
        return []
    im = im.crop(ink_bbox)
    mm_per_px = cap_height_mm / im.height
    rects_px = _merge_row_rects(_ink_rectangles(im))

    out: list[tuple[float, float, float, float]] = []
    for x0, y0, x1, y1 in rects_px:
        out.append(
            (
                origin_x_mm + x0 * mm_per_px,
                origin_y_mm + y0 * mm_per_px,
                origin_x_mm + x1 * mm_per_px,
                origin_y_mm + y1 * mm_per_px,
            )
        )
    return _close_mask_slivers_mm(out)


def copper_rects_to_sexpr(rects_mm: list[tuple[float, float, float, float]]) -> str:
    doc = SexprDoc(start_depth=1)  # top-level PCB elements
    for rect in rects_mm:
        doc.embed(gr_poly_copper(*rect))
    text = doc.render()
    return text + ("\n" if text else "")


def build_name_copper_sexpr(
    text: str,
    *,
    origin_x_mm: float,
    origin_y_mm: float,
) -> str:
    rects = name_copper_rects_mm(text, origin_x_mm=origin_x_mm, origin_y_mm=origin_y_mm)
    return copper_rects_to_sexpr(rects)
