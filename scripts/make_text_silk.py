#!/usr/bin/env python3
"""Export role + contact silk PNGs for KiCad / preview."""

from __future__ import annotations

from pathlib import Path

from card_copy import CONTACTS, ROLES
from silk_layout import (
    CONTACT_FONT_SIZE_MM,
    CONTACT_LINE_STEP_MM,
    ROLE_FONT_SIZE_MM,
    ROLES_LINE_STEP_MM,
)
from text_silk import crop_to_ink, render_silk_text_block

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ROLES_OUT = ASSETS / "roles-silk.png"
CONTACTS_OUT = ASSETS / "contacts-silk.png"


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    roles = crop_to_ink(
        render_silk_text_block(
            ROLES,
            font_size_mm=ROLE_FONT_SIZE_MM,
            line_step_mm=ROLES_LINE_STEP_MM,
        )
    )
    roles.save(ROLES_OUT)
    print(f"Wrote {ROLES_OUT} ({roles.size[0]}x{roles.size[1]})")

    contacts = crop_to_ink(
        render_silk_text_block(
            CONTACTS,
            font_size_mm=CONTACT_FONT_SIZE_MM,
            line_step_mm=CONTACT_LINE_STEP_MM,
        )
    )
    contacts.save(CONTACTS_OUT)
    print(f"Wrote {CONTACTS_OUT} ({contacts.size[0]}x{contacts.size[1]})")


if __name__ == "__main__":
    main()
