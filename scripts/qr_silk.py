#!/usr/bin/env python3
"""Build inverted QR silk (white modules, transparent quiet zone)."""

from __future__ import annotations

import qrcode
from PIL import Image

from card_copy import QR_URL


def make_qr_silk(url: str = QR_URL, border: int = 2) -> Image.Image:
    """White-on-transparent QR for black soldermask (inverted / no white box)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.ERROR_CORRECT_M,
        box_size=1,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px = out.load()
    for y, row in enumerate(matrix):
        for x, on in enumerate(row):
            if on:
                px[x, y] = (255, 255, 255, 255)
    return out
