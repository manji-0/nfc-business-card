"""Shared silk layout (mm) for preview and KiCad generator.

Vertical positions use preview coordinates: Y measured downward from the top
board edge. KiCad PCB, preview PNG, and layout constants share this system.
"""

from __future__ import annotations

from dataclasses import dataclass

from card_copy import CONTACTS
from kamae.types import Mm, PreviewY


@dataclass(frozen=True, slots=True)
class BoardSize:
    width: Mm
    height: Mm


@dataclass(frozen=True, slots=True)
class SilkLayout:
    board: BoardSize
    text_zone_w: Mm
    name_right_margin_mm: Mm
    contact_line_step_mm: Mm
    contact_line_h_mm: Mm
    contact_qr_center_y_mm: PreviewY
    text_left_mm: Mm
    contact_x_mm: Mm
    name_y_mm: PreviewY
    name_cap_height_mm: Mm
    name_font_face: str
    name_text_thickness_mm: Mm
    silk_font_face: str
    silk_text_thickness_mm: Mm
    name_dilate_k: int
    roles_y0_mm: PreviewY
    roles_line_step_mm: Mm
    role_font_size_mm: Mm
    contact_font_size_mm: Mm
    nfc_logo_size_mm: Mm
    qr_oversize_mm: Mm
    silk_bitmap_px_per_mm: float
    back_logo_margin_x: Mm
    back_logo_gap: Mm
    back_logo_margin_y: Mm

    def name_max_width_mm(self) -> Mm:
        return Mm(self.text_zone_w - self.text_left_mm - self.name_right_margin_mm)

    def contact_block_h_mm(self) -> Mm:
        return Mm((len(CONTACTS) - 1) * self.contact_line_step_mm + self.contact_line_h_mm)

    def qr_size_mm(self) -> Mm:
        return Mm(self.contact_block_h_mm() + self.qr_oversize_mm)

    def qr_top_y_mm(self) -> PreviewY:
        return PreviewY(self.contact_qr_center_y_mm - self.qr_size_mm() / 2)

    def contact_top_y_mm(self) -> PreviewY:
        return PreviewY(self.contact_qr_center_y_mm - self.contact_block_h_mm() / 2)

    def back_logo_grid(self) -> tuple[Mm, list[tuple[str, Mm, PreviewY]]]:
        """Return logo size mm and (filename, cx, cy) for a centered 2x2 back grid."""
        board_h = self.board.height
        board_w = self.board.width
        grid_w = board_w - 2 * self.back_logo_margin_x
        cell_w = (grid_w - self.back_logo_gap) / 2
        max_logo_mm = (board_h - 2 * self.back_logo_margin_y - self.back_logo_gap) / 2
        logo_mm = min(cell_w * 0.88, max_logo_mm)
        block_h = 2 * logo_mm + self.back_logo_gap
        y0 = (board_h - block_h) / 2
        y_top = y0 + logo_mm / 2
        y_bottom = y0 + logo_mm + self.back_logo_gap + logo_mm / 2
        x_left = self.back_logo_margin_x + cell_w / 2
        x_right = self.back_logo_margin_x + cell_w + self.back_logo_gap + cell_w / 2
        names = ("openstack", "kubernetes", "prometheus", "oidc")
        positions = (
            (x_left, y_top),
            (x_right, y_top),
            (x_left, y_bottom),
            (x_right, y_bottom),
        )
        items = [
            (f"{n}-silk.png", Mm(cx), PreviewY(cy)) for n, (cx, cy) in zip(names, positions)
        ]
        return Mm(logo_mm), items


DEFAULT = SilkLayout(
    board=BoardSize(width=Mm(89.0), height=Mm(51.0)),
    text_zone_w=Mm(50.0),
    name_right_margin_mm=Mm(8.0),
    contact_line_step_mm=Mm(2.4),
    contact_line_h_mm=Mm(1.25),
    contact_qr_center_y_mm=PreviewY(28.5),
    text_left_mm=Mm(5.0),
    contact_x_mm=Mm(16.5),
    name_y_mm=PreviewY(10.5),
    name_cap_height_mm=Mm(5.2),
    name_font_face="Georgia Bold",
    name_text_thickness_mm=Mm(0.65),
    silk_font_face="Arial",
    silk_text_thickness_mm=Mm(0.12),
    name_dilate_k=3,
    roles_y0_mm=PreviewY(18.5),
    roles_line_step_mm=Mm(2.5),
    role_font_size_mm=Mm(1.6),
    contact_font_size_mm=Mm(1.5),
    nfc_logo_size_mm=Mm(12.0),
    qr_oversize_mm=Mm(1.5),
    silk_bitmap_px_per_mm=40.0,
    back_logo_margin_x=Mm(8.0),
    back_logo_gap=Mm(3.0),
    back_logo_margin_y=Mm(5.0),
)

# Backward-compatible aliases
BOARD_W = DEFAULT.board.width
BOARD_H = DEFAULT.board.height
TEXT_ZONE_W = DEFAULT.text_zone_w
NAME_RIGHT_MARGIN_MM = DEFAULT.name_right_margin_mm
CONTACT_LINE_STEP_MM = DEFAULT.contact_line_step_mm
CONTACT_LINE_H_MM = DEFAULT.contact_line_h_mm
CONTACT_QR_CENTER_Y_MM = DEFAULT.contact_qr_center_y_mm
TEXT_LEFT_MM = DEFAULT.text_left_mm
QR_X_MM = DEFAULT.text_left_mm
CONTACT_X_MM = DEFAULT.contact_x_mm
NAME_X_MM = DEFAULT.text_left_mm
NAME_Y_MM = DEFAULT.name_y_mm
NAME_CAP_HEIGHT_MM = DEFAULT.name_cap_height_mm
NAME_FONT_FACE = DEFAULT.name_font_face
NAME_TEXT_THICKNESS_MM = DEFAULT.name_text_thickness_mm
SILK_FONT_FACE = DEFAULT.silk_font_face
SILK_TEXT_THICKNESS_MM = DEFAULT.silk_text_thickness_mm
NAME_DILATE_K = DEFAULT.name_dilate_k
ROLES_Y0_MM = DEFAULT.roles_y0_mm
ROLES_LINE_STEP_MM = DEFAULT.roles_line_step_mm
ROLE_FONT_SIZE_MM = DEFAULT.role_font_size_mm
CONTACT_FONT_SIZE_MM = DEFAULT.contact_font_size_mm
NFC_LOGO_SIZE_MM = DEFAULT.nfc_logo_size_mm
SILK_BITMAP_PX_PER_MM = DEFAULT.silk_bitmap_px_per_mm
ROLES_SILK_PNG = "roles-silk.png"
CONTACTS_SILK_PNG = "contacts-silk.png"
BACK_LOGO_MARGIN_X = DEFAULT.back_logo_margin_x
BACK_LOGO_GAP = DEFAULT.back_logo_gap
BACK_LOGO_MARGIN_Y = DEFAULT.back_logo_margin_y


def y_kicad(y_from_top: float) -> float:
    """Preview Y (down from top) → legacy bottom-origin Y."""
    return float(BOARD_H) - y_from_top


def y_preview(y_kicad_mm: float) -> float:
    """Legacy bottom-origin Y → preview Y (down from top)."""
    return float(BOARD_H) - y_kicad_mm


def name_max_width_mm() -> float:
    return float(DEFAULT.name_max_width_mm())


def contact_block_h_mm() -> float:
    return float(DEFAULT.contact_block_h_mm())


def qr_size_mm() -> float:
    return float(DEFAULT.qr_size_mm())


def qr_top_y_mm() -> float:
    return float(DEFAULT.qr_top_y_mm())


def contact_top_y_mm() -> float:
    return float(DEFAULT.contact_top_y_mm())


def back_logo_grid() -> tuple[float, list[tuple[str, float, float]]]:
    logo_mm, items = DEFAULT.back_logo_grid()
    return float(logo_mm), [(name, float(cx), float(cy)) for name, cx, cy in items]
