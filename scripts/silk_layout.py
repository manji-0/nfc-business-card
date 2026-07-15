"""Shared silk layout (mm) for preview and KiCad generator.

Vertical positions use **preview coordinates**: Y measured downward from the top
board edge.  KiCad PCB, preview PNG, and layout constants all share this system.
The :func:`y_kicad` helper converts to bottom-origin Y only for legacy callers.
"""

from card_copy import CONTACTS

BOARD_W = 89.0
BOARD_H = 51.0


def y_kicad(y_from_top: float) -> float:
    """Preview Y (down from top) → KiCad Y (up from bottom)."""
    return BOARD_H - y_from_top


def y_preview(y_kicad_mm: float) -> float:
    """KiCad Y (up from bottom) → preview Y (down from top)."""
    return BOARD_H - y_kicad_mm

# Left zone: no antenna copper. Right = NFC spiral + chip strip.
TEXT_ZONE_W = 50.0
NAME_RIGHT_MARGIN_MM = 8.0  # gap from name right edge to text-zone / circuit boundary

CONTACT_LINE_STEP_MM = 2.4
CONTACT_LINE_H_MM = 1.25
CONTACT_QR_CENTER_Y_MM = 28.0
TEXT_LEFT_MM = 5.0
QR_X_MM = TEXT_LEFT_MM
CONTACT_X_MM = 16.5
NAME_X_MM = TEXT_LEFT_MM
NAME_Y_MM = 10.5
NAME_CAP_HEIGHT_MM = 5.2
NAME_FONT_FACE = "Georgia Bold"
NAME_TEXT_THICKNESS_MM = 0.65  # legacy stroke target; TTF uses 0.15 in KiCad
SILK_FONT_FACE = "Arial"
SILK_TEXT_THICKNESS_MM = 0.12
# Light dilate only (k=3) — used by fab gerber preview raster only
NAME_DILATE_K = 3

ROLES_Y0_MM = 18.5
ROLES_LINE_STEP_MM = 2.5
ROLE_FONT_SIZE_MM = 1.6
CONTACT_FONT_SIZE_MM = 1.5
NFC_LOGO_SIZE_MM = 12.0
SILK_BITMAP_PX_PER_MM = 40.0

ROLES_SILK_PNG = "roles-silk.png"
CONTACTS_SILK_PNG = "contacts-silk.png"


def name_max_width_mm() -> float:
    """Max ENIG name width so right edge stays inside the text zone."""
    return TEXT_ZONE_W - TEXT_LEFT_MM - NAME_RIGHT_MARGIN_MM


def contact_block_h_mm() -> float:
    return (len(CONTACTS) - 1) * CONTACT_LINE_STEP_MM + CONTACT_LINE_H_MM


def qr_size_mm() -> float:
    return contact_block_h_mm() + 0.4


def qr_top_y_mm() -> float:
    return CONTACT_QR_CENTER_Y_MM - qr_size_mm() / 2


def contact_top_y_mm() -> float:
    return CONTACT_QR_CENTER_Y_MM - contact_block_h_mm() / 2


BACK_LOGO_MARGIN_X = 8.0
BACK_LOGO_GAP = 3.0
BACK_LOGO_MARGIN_Y = 5.0


def back_logo_grid() -> tuple[float, list[tuple[str, float, float]]]:
    """Return logo size mm and (filename, cx, cy) for a centered 2x2 back grid."""
    grid_w = BOARD_W - 2 * BACK_LOGO_MARGIN_X
    cell_w = (grid_w - BACK_LOGO_GAP) / 2
    max_logo_mm = (BOARD_H - 2 * BACK_LOGO_MARGIN_Y - BACK_LOGO_GAP) / 2
    logo_mm = min(cell_w * 0.88, max_logo_mm)
    block_h = 2 * logo_mm + BACK_LOGO_GAP
    y0 = (BOARD_H - block_h) / 2
    y_top = y0 + logo_mm / 2
    y_bottom = y0 + logo_mm + BACK_LOGO_GAP + logo_mm / 2
    x_left = BACK_LOGO_MARGIN_X + cell_w / 2
    x_right = BACK_LOGO_MARGIN_X + cell_w + BACK_LOGO_GAP + cell_w / 2
    names = ("openstack", "kubernetes", "prometheus", "oidc")
    positions = (
        (x_left, y_top),
        (x_right, y_top),
        (x_left, y_bottom),
        (x_right, y_bottom),
    )
    items = [(f"{n}-silk.png", cx, cy) for n, (cx, cy) in zip(names, positions)]
    return logo_mm, items
