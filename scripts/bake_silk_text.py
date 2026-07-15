#!/usr/bin/env python3
"""Bake front silk text (roles, contacts) as KiCad vector gr_text."""

from __future__ import annotations

from bake_kicad_text import bake_line_block_sexpr
from card_copy import CONTACTS, ROLES
from layout_metrics import ARIAL, block_max_ink_width_mm
from silk_layout import (
    CONTACT_FONT_SIZE_MM,
    CONTACT_LINE_STEP_MM,
    CONTACT_X_MM,
    ROLE_FONT_SIZE_MM,
    ROLES_LINE_STEP_MM,
    ROLES_Y0_MM,
    SILK_FONT_FACE,
    SILK_TEXT_THICKNESS_MM,
    TEXT_LEFT_MM,
    contact_top_y_mm,
)


def build_roles_silk_sexpr() -> str:
    return bake_line_block_sexpr(
        ROLES,
        x_mm=TEXT_LEFT_MM,
        y0_mm=ROLES_Y0_MM,
        line_step_mm=ROLES_LINE_STEP_MM,
        size_mm=ROLE_FONT_SIZE_MM,
        face=SILK_FONT_FACE,
        layer="F.SilkS",
        thickness_mm=SILK_TEXT_THICKNESS_MM,
        align_left_mm=TEXT_LEFT_MM,
        target_block_width_mm=block_max_ink_width_mm(
            ROLES,
            origin_x_mm=TEXT_LEFT_MM,
            font_size_mm=ROLE_FONT_SIZE_MM,
            font_path=ARIAL,
        ),
    )


def build_contacts_silk_sexpr() -> str:
    return bake_line_block_sexpr(
        CONTACTS,
        x_mm=CONTACT_X_MM,
        y0_mm=contact_top_y_mm(),
        line_step_mm=CONTACT_LINE_STEP_MM,
        size_mm=CONTACT_FONT_SIZE_MM,
        face=SILK_FONT_FACE,
        layer="F.SilkS",
        thickness_mm=SILK_TEXT_THICKNESS_MM,
        align_left_mm=CONTACT_X_MM,
        target_block_width_mm=block_max_ink_width_mm(
            CONTACTS,
            origin_x_mm=CONTACT_X_MM,
            font_size_mm=CONTACT_FONT_SIZE_MM,
            font_path=ARIAL,
        ),
    )
