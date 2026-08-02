#!/usr/bin/env python3
"""Near-photorealistic PNG mockup of the finished NFC business card.

Renders front + back like a product photo: black soldermask, ENIG gold,
white silkscreen, SMT packages, soft shadow. Uses Pillow (.venv).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_kicad_project import (  # noqa: E402
    BOARD_H,
    BOARD_W,
    FEED_TRACE_W,
    GAP,
    TEXT_ZONE_W,
    TRACE_W,
    TURNS,
    ant_tie_geometry,
    feed_routes,
    feed_vias,
    gnd_island_route,
    nc_terminator_routes,
    nfc_layout,
    rectangular_spiral,
)
from jlcpcb_limits import (  # noqa: E402
    GND_ISLAND_DX_MM,
    GND_ISLAND_H_MM,
    GND_ISLAND_W_MM,
    XQFN_PAD_EDGE_MM,
    XQFN_PAD_ROW_MM,
)
from card_copy import CONTACTS, NAME, QR_URL, ROLES  # noqa: E402
from fonts import FontFile, font_file  # noqa: E402
from silk_layout import (  # noqa: E402
    CONTACT_FONT_SIZE_MM,
    CONTACT_LINE_STEP_MM,
    CONTACT_X_MM,
    NAME_CAP_HEIGHT_MM,
    NAME_FONT_FACE,
    NAME_Y_MM,
    NFC_LOGO_SIZE_MM,
    QR_X_MM,
    ROLE_FONT_SIZE_MM,
    ROLES_LINE_STEP_MM,
    ROLES_Y0_MM,
    SILK_BITMAP_PX_PER_MM,
    SILK_FONT_FACE,
    TEXT_LEFT_MM,
    back_logo_grid,
    contact_top_y_mm,
    qr_size_mm,
    qr_top_y_mm,
)
from text_silk import render_silk_text_block  # noqa: E402

OUT = ROOT / "fab"
ASSETS = ROOT / "assets"

# Pixels per mm — high res for crisp text
PPM = 28
CORNER_R_MM = 1.8

# Colors (sRGB) — matte black soldermask + ENIG
MASK = (14, 14, 16)
MASK_DARK = (6, 6, 8)
MASK_LIGHT = (32, 32, 36)
COPPER_ENIG = (212, 175, 55)
COPPER_DIM = (168, 138, 45)
COPPER_UNDER = (48, 42, 28)  # antenna under black mask (warm hint)
SILK = (245, 248, 245)
SILK_DIM = (180, 185, 185)
GOLD_TEXT = (218, 185, 70)
GOLD_HI = (240, 215, 120)
PKG_BODY = (22, 22, 24)
PKG_MARK = (160, 160, 160)
PAD_ENIG = (200, 165, 50)
SHADOW = (0, 0, 0)
BG = (228, 226, 222)

def font(file: FontFile, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(file.path), size, index=file.index)


def fonts():
    name = font(font_file(NAME_FONT_FACE), int(NAME_CAP_HEIGHT_MM * PPM))
    tiny = font(font_file(SILK_FONT_FACE), int(1.0 * PPM))
    return name, tiny


def draw_name_enig(card: Image.Image, name_f: ImageFont.FreeTypeFont) -> None:
    """Filled Georgia Bold — matches copper_name on the PCB."""
    d = ImageDraw.Draw(card)
    d.text(mm(TEXT_LEFT_MM, NAME_Y_MM), NAME, font=name_f, fill=GOLD_TEXT + (255,), anchor="lt")


def mm(x: float, y: float, ox: int = 0, oy: int = 0) -> tuple[int, int]:
    return ox + int(round(x * PPM)), oy + int(round(y * PPM))


def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


def draw_soft_shadow(canvas: Image.Image, card_w: int, card_h: int, ox: int, oy: int, r: int) -> None:
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    pad = int(4 * PPM)
    sd.rounded_rectangle(
        (ox + int(1.2 * PPM), oy + int(1.8 * PPM), ox + card_w + pad // 3, oy + card_h + pad // 2),
        radius=r,
        fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=PPM * 0.55))
    canvas.alpha_composite(shadow)


def draw_board_base(card: Image.Image) -> None:
    """Soldermask with subtle vignette / fiber noise."""
    w, h = card.size
    d = ImageDraw.Draw(card)
    d.rectangle((0, 0, w, h), fill=MASK + (255,))
    # Soft radial lighter center
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(12):
        inset = int(i * PPM * 0.8)
        alpha = 6
        od.ellipse(
            (inset - w // 6, inset - h // 4, w - inset + w // 6, h - inset + h // 4),
            fill=(*MASK_LIGHT, alpha),
        )
    card.alpha_composite(overlay)
    # Micro texture
    import random

    rng = random.Random(42)
    pix = card.load()
    for _ in range(w * h // 40):
        x, y = rng.randrange(w), rng.randrange(h)
        r, g, b, a = pix[x, y]
        n = rng.randint(-4, 4)
        pix[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)), a)
    # Edge bevel (darker rim)
    rim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    rd.rounded_rectangle((0, 0, w - 1, h - 1), radius=int(CORNER_R_MM * PPM), outline=(*MASK_DARK, 140), width=max(2, PPM // 10))
    rd.rounded_rectangle((2, 2, w - 3, h - 3), radius=int(CORNER_R_MM * PPM) - 1, outline=(255, 255, 255, 25), width=1)
    card.alpha_composite(rim)


def stroke_poly(draw: ImageDraw.ImageDraw, pts: list[tuple[float, float]], width_mm: float, fill, ox=0, oy=0):
    if len(pts) < 2:
        return
    xy = [mm(x, y, ox, oy) for x, y in pts]
    draw.line(xy, fill=fill, width=max(1, int(round(width_mm * PPM))), joint="curve")


def draw_antenna_under_mask(card: Image.Image, segs, ox=0, oy=0) -> None:
    """Subtle coil visible through soldermask + ENIG feed traces."""
    draw_copper_under_mask(card, segs, TRACE_W * 1.15, ox=ox, oy=oy)


def draw_copper_under_mask(
    card: Image.Image,
    segs,
    width_mm: float,
    ox=0,
    oy=0,
    *,
    alpha: int = 255,
    blur: float = 0.35,
) -> None:
    """Copper under the black mask: faint warm hint, like the real board."""
    layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for a, b in segs:
        stroke_poly(d, [a, b], width_mm, (*COPPER_UNDER, alpha), ox, oy)
    layer = layer.filter(ImageFilter.GaussianBlur(radius=blur))
    card.alpha_composite(layer)


def draw_roundrect_under_mask(
    card: Image.Image,
    cx_mm: float,
    cy_mm: float,
    w_mm: float,
    h_mm: float,
    ox=0,
    oy=0,
    *,
    alpha: int = 255,
) -> None:
    """Filled net-tie / pad copper under the mask (no mask opening)."""
    layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0 = mm(cx_mm - w_mm / 2, cy_mm - h_mm / 2, ox, oy)
    x1, y1 = mm(cx_mm + w_mm / 2, cy_mm + h_mm / 2, ox, oy)
    r = max(2, int(0.2 * min(w_mm, h_mm) / 2 * PPM))
    d.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=(*COPPER_UNDER, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.35))
    card.alpha_composite(layer)


def draw_poly_under_mask(
    card: Image.Image,
    poly: list[tuple[float, float]],
    ox=0,
    oy=0,
    *,
    alpha: int = 255,
) -> None:
    """Filled polygon copper under the mask (net-tie pads)."""
    layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    xy = [mm(x, y, ox, oy) for x, y in poly]
    d.polygon(xy, fill=(*COPPER_UNDER, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.35))
    card.alpha_composite(layer)


def draw_vias(card: Image.Image, vias, ox=0, oy=0) -> None:
    """Tented through-vias (front view: covered, subtle dark ring)."""
    d = ImageDraw.Draw(card)
    for item in vias:
        x, y, _net = item[0], item[1], item[2]
        cx, cy = mm(x, y, ox, oy)
        r = max(2, int(0.3 * PPM))  # via pad Ø0.6 mm
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(46, 46, 52, 140), width=1)
        d.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=(200, 165, 50, 90))


def draw_gnd_island(card: Image.Image, gnd, ox=0, oy=0) -> None:
    """Local VSS island: F.Cu + F.Mask => ENIG gold opening."""
    cx, cy, w, h = gnd
    d = ImageDraw.Draw(card)
    x0, y0 = mm(cx - w / 2, cy - h / 2, ox, oy)
    x1, y1 = mm(cx + w / 2, cy + h / 2, ox, oy)
    r = max(2, int(0.2 * min(w, h) / 2 * PPM))
    d.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=COPPER_ENIG + (235,))


def draw_xqfn(card: Image.Image, u1, ox=0, oy=0) -> None:
    d = ImageDraw.Draw(card)
    cx, cy = u1
    # Body 1.6x1.6 mm
    x0, y0 = mm(cx - 0.85, cy - 0.85, ox, oy)
    x1, y1 = mm(cx + 0.85, cy + 0.85, ox, oy)
    # Soft package shadow
    d.rounded_rectangle((x0 + 2, y0 + 2, x1 + 2, y1 + 2), radius=2, fill=(0, 0, 0, 60))
    d.rounded_rectangle((x0, y0, x1, y1), radius=2, fill=PKG_BODY + (255,))
    # Pads (visible around body)
    pads = [
        (cx - 0.20, cy + 0.75, 90),
        (cx + 0.20, cy + 0.75, 90),
        (cx - 0.75, cy + 0.20, 0),
        (cx - 0.75, cy - 0.20, 0),
        (cx + 0.75, cy + 0.20, 0),
        (cx + 0.75, cy - 0.20, 0),
        (cx - 0.20, cy - 0.75, 90),
        (cx + 0.20, cy - 0.75, 90),
    ]
    for px, py, rot in pads:
        if rot == 90:
            hw, hh = XQFN_PAD_ROW_MM / 2, XQFN_PAD_EDGE_MM / 2
        else:
            hw, hh = XQFN_PAD_EDGE_MM / 2, XQFN_PAD_ROW_MM / 2
        a, b = mm(px - hw, py - hh, ox, oy)
        c, e = mm(px + hw, py + hh, ox, oy)
        d.rounded_rectangle((a, b, c, e), radius=1, fill=PAD_ENIG + (255,))
    # Pin-1 dot
    p1 = mm(cx - 0.45, cy - 0.45, ox, oy)
    d.ellipse((p1[0] - 2, p1[1] - 2, p1[0] + 2, p1[1] + 2), fill=(220, 60, 50, 255))
    # Laser mark
    tiny = font(font_file(SILK_FONT_FACE), max(8, int(0.55 * PPM)))
    d.text(mm(cx, cy + 0.15, ox, oy), "211", font=tiny, fill=PKG_MARK + (200,), anchor="mm")


def draw_c0402(card: Image.Image, c1, dnp: bool = True, ox=0, oy=0) -> None:
    d = ImageDraw.Draw(card)
    cx, cy = c1
    # Pads only if DNP (empty land pattern)
    for dx in (-0.48, 0.48):
        a, b = mm(cx + dx - 0.26, cy - 0.31, ox, oy)
        c, e = mm(cx + dx + 0.26, cy + 0.31, ox, oy)
        d.rounded_rectangle((a, b, c, e), radius=2, fill=PAD_ENIG + (220,))
    if dnp:
        # dashed outline hint
        a, b = mm(cx - 0.55, cy - 0.35, ox, oy)
        c, e = mm(cx + 0.55, cy + 0.35, ox, oy)
        d.rectangle((a, b, c, e), outline=(*SILK_DIM, 120), width=1)


def draw_qr(card: Image.Image, x_mm: float, y_mm: float, size_mm: float = 8.5, ox=0, oy=0) -> None:
    """Inverted QR (white modules, no white box) for black soldermask."""
    from qr_silk import make_qr_silk

    qr = make_qr_silk(QR_URL)
    target = int(size_mm * PPM)
    qr = qr.resize((target, target), Image.Resampling.NEAREST)
    x0, y0 = mm(x_mm, y_mm, ox, oy)
    card.alpha_composite(qr, (x0, y0))


def draw_nfc_logo(card: Image.Image, cx, cy, size_mm: float = 14.0, ox=0, oy=0) -> None:
    """NFC icon (white silk from assets/nfc-symbol.svg) at (cx, cy) mm."""
    silk_path = ASSETS / "nfc-n-mark-silk.png"
    if not silk_path.exists():
        raise FileNotFoundError(f"Missing {silk_path} — run logo generation first")
    logo = Image.open(silk_path).convert("RGBA")
    target = int(size_mm * PPM)
    # Keep aspect ratio
    scale = target / max(logo.size)
    nw, nh = max(1, int(logo.width * scale)), max(1, int(logo.height * scale))
    logo = logo.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = ox + int(cx * PPM) - nw // 2
    y0 = oy + int(cy * PPM) - nh // 2
    card.alpha_composite(logo, (x0, y0))


def draw_silk_at_tl(card: Image.Image, silk: Image.Image, x_mm: float, y_mm: float) -> None:
    """Place silk PNG authored at SILK_BITMAP_PX_PER_MM onto the preview canvas."""
    scale = PPM / SILK_BITMAP_PX_PER_MM
    nw = max(1, int(round(silk.width * scale)))
    nh = max(1, int(round(silk.height * scale)))
    if (nw, nh) != silk.size:
        silk = silk.resize((nw, nh), Image.Resampling.LANCZOS)
    x0, y0 = mm(x_mm, y_mm)
    card.alpha_composite(silk, (x0, y0))


def draw_front(card: Image.Image, lay, ant_segs, feed_segs, vias, tie_pads, gnd_island) -> None:
    name_f, _tiny_f = fonts()
    d = ImageDraw.Draw(card)
    draw_board_base(card)

    # Copper under mask (right zone): coil + LA/LB feeds + net-tie bridge
    draw_antenna_under_mask(card, ant_segs)
    draw_copper_under_mask(card, feed_segs, FEED_TRACE_W)
    for poly in tie_pads:
        draw_poly_under_mask(card, poly)

    # Components
    draw_xqfn(card, lay["u1"])
    draw_c0402(card, lay["c1"], dnp=True)

    # ENIG mask openings (gold surfaces)
    draw_gnd_island(card, gnd_island)
    draw_vias(card, vias)

    # --- Silkscreen / ENIG text (left zone) ---
    draw_name_enig(card, name_f)

    roles_img = render_silk_text_block(
        ROLES,
        font_size_mm=ROLE_FONT_SIZE_MM,
        line_step_mm=ROLES_LINE_STEP_MM,
    )
    contacts_img = render_silk_text_block(
        CONTACTS,
        font_size_mm=CONTACT_FONT_SIZE_MM,
        line_step_mm=CONTACT_LINE_STEP_MM,
    )
    draw_silk_at_tl(card, roles_img, TEXT_LEFT_MM, ROLES_Y0_MM)
    draw_silk_at_tl(card, contacts_img, CONTACT_X_MM, contact_top_y_mm())

    draw_qr(card, QR_X_MM, qr_top_y_mm(), qr_size_mm())

    # NFC logo centered on antenna
    draw_nfc_logo(card, lay["ant_cx"], lay["ant_cy"], size_mm=NFC_LOGO_SIZE_MM)


def draw_logo_at(card: Image.Image, silk: Image.Image, cx_mm: float, cy_mm: float, size_mm: float) -> None:
    """Place a silk logo centered at (cx_mm, cy_mm) with max dimension size_mm."""
    target = int(size_mm * PPM)
    scale = target / max(silk.size)
    nw, nh = max(1, int(silk.width * scale)), max(1, int(silk.height * scale))
    logo = silk.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = int(cx_mm * PPM) - nw // 2
    y0 = int(cy_mm * PPM) - nh // 2
    card.alpha_composite(logo, (x0, y0))


def draw_back(card: Image.Image) -> None:
    """Black back: B.Cu copper hints + OpenStack / K8s / Prometheus / OIDC grid."""
    draw_board_base(card)

    # Faint B.Cu under-mask copper: LB underpass + NC pull-down routes
    lay = nfc_layout()
    ant_abs = [(lay["ant_cx"] + x, lay["ant_cy"] + y) for x, y in lay["ant_pts"]]
    ant1, ant2 = ant_abs[0], ant_abs[-1]
    routes = feed_routes(ant1, ant2, lay["u1"], lay["c1"])
    underpass = [(x0, y0, x1, y1) for x0, y0, x1, y1, _n, _w, l in routes if l == "B.Cu"]
    nc_segs, nc_vias = nc_terminator_routes(lay["u1"])
    nc_segs_pts = [(x0, y0, x1, y1) for x0, y0, x1, y1, _n, _w, l in nc_segs]
    bcu = [((x0, y0), (x1, y1)) for x0, y0, x1, y1 in underpass + nc_segs_pts]
    if bcu:
        draw_copper_under_mask(card, bcu, FEED_TRACE_W, alpha=120, blur=0.6)
    draw_vias(card, feed_vias(ant2, lay["u1"], lay["c1"]) + list(nc_vias))

    logos_dir = ASSETS / "logos"
    logo_mm, back_items = back_logo_grid()
    for (filename, cx, cy) in back_items:
        name = filename.removesuffix("-silk.png")
        path = logos_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing {path} — run scripts/make_back_logos.py")
        draw_logo_at(card, Image.open(path).convert("RGBA"), cx, cy, logo_mm)


def net_tie_pads(ant_cx: float, ant_cy: float, ant_pts: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """ANT1 net-tie pads as absolute-mm polygons."""
    tie = ant_tie_geometry(ant_pts)
    return [
        [(ant_cx + x, ant_cy + y) for x, y in tie["la_poly"]],
        [(ant_cx + x, ant_cy + y) for x, y in tie["lb_poly"]],
    ]


def gnd_island_rect(u1: tuple[float, float]) -> tuple[float, float, float, float]:
    u1_x, u1_y = u1
    return (u1_x - GND_ISLAND_DX_MM, u1_y + 0.20, GND_ISLAND_W_MM, GND_ISLAND_H_MM)


def build_geometry():
    lay = nfc_layout()
    ant_abs = [(lay["ant_cx"] + x, lay["ant_cy"] + y) for x, y in lay["ant_pts"]]
    ant_segs = list(zip(ant_abs, ant_abs[1:]))
    ant1, ant2 = ant_abs[0], ant_abs[-1]
    routes = feed_routes(ant1, ant2, lay["u1"], lay["c1"]) + gnd_island_route(lay["u1"])
    feed_segs = [
        ((x0, y0), (x1, y1))
        for x0, y0, x1, y1, _net, _w, layer in routes
        if layer == "F.Cu"
    ]
    vias = feed_vias(ant2, lay["u1"], lay["c1"])
    tie_pads = net_tie_pads(lay["ant_cx"], lay["ant_cy"], lay["ant_pts"])
    gnd_island = gnd_island_rect(lay["u1"])
    return lay, ant_segs, feed_segs, vias, tie_pads, gnd_island


def render_card_face(drawer, *args) -> Image.Image:
    w, h = int(BOARD_W * PPM), int(BOARD_H * PPM)
    r = int(CORNER_R_MM * PPM)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    drawer(card, *args)
    # Apply rounded corner alpha
    mask = rounded_mask(w, h, r)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(card, (0, 0))
    out.putalpha(mask)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    lay, ant_segs, feed_segs, vias, tie_pads, gnd_island = build_geometry()

    front = render_card_face(draw_front, lay, ant_segs, feed_segs, vias, tie_pads, gnd_island)
    back = render_card_face(draw_back)

    gap = int(8 * PPM)
    margin = int(10 * PPM)
    label_h = int(7 * PPM)
    canvas_w = front.width + 2 * margin
    canvas_h = margin + label_h + front.height + gap + label_h + back.height + margin
    canvas = Image.new("RGBA", (canvas_w, canvas_h), BG + (255,))

    # Labels
    d = ImageDraw.Draw(canvas)
    label_f = font(font_file(SILK_FONT_FACE), int(2.0 * PPM))
    d.text((margin, margin // 2), "Front (component / silk side)", font=label_f, fill=(80, 80, 80, 255))
    d.text(
        (margin, margin + label_h + front.height + gap // 2),
        "Back (branding side)",
        font=label_f,
        fill=(80, 80, 80, 255),
    )

    ox = margin
    oy_front = margin + label_h
    oy_back = oy_front + front.height + gap + label_h

    draw_soft_shadow(canvas, front.width, front.height, ox, oy_front, int(CORNER_R_MM * PPM))
    canvas.alpha_composite(front, (ox, oy_front))
    draw_soft_shadow(canvas, back.width, back.height, ox, oy_back, int(CORNER_R_MM * PPM))
    canvas.alpha_composite(back, (ox, oy_back))

    # Flatten to RGB for smaller PNG
    final = Image.new("RGB", canvas.size, BG)
    final.paste(canvas, mask=canvas.split()[-1])

    png_path = OUT / "preview.png"
    final.save(png_path, "PNG", optimize=True)
    # Also write a front-only closeup
    front_rgb = Image.new("RGB", front.size, BG)
    # with shadow backdrop
    front_only = Image.new("RGB", (front.width + 2 * margin, front.height + 2 * margin), BG)
    tmp = Image.new("RGBA", front_only.size, BG + (255,))
    draw_soft_shadow(tmp, front.width, front.height, margin, margin, int(CORNER_R_MM * PPM))
    tmp.alpha_composite(front, (margin, margin))
    front_only = Image.new("RGB", tmp.size, BG)
    front_only.paste(tmp, mask=tmp.split()[-1])
    front_only.save(OUT / "preview-front.png", "PNG", optimize=True)

    # SVG kept simple for editability
    (OUT / "preview.svg").write_text(
        f"<!-- See preview.png for photoreal mockup. Board {BOARD_W}x{BOARD_H}mm. -->\n",
        encoding="utf-8",
    )

    print(f"Wrote {png_path} ({final.size[0]}×{final.size[1]})")
    print(f"Wrote {OUT / 'preview-front.png'}")


if __name__ == "__main__":
    main()
