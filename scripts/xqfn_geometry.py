"""XQFN-8 pad geometry — single source for footprint writer, PCB builder, checks.

NXP XQFN8 (SOT902-3), 1.6 x 1.6 mm body, 0.40 mm pitch, no EP solder.
Pad long axis points toward the package centre: (x, y) are U1-relative in mm.
"""

from __future__ import annotations

from jlcpcb_limits import XQFN_PAD_EDGE_MM, XQFN_PAD_ROW_MM, XQFN_PITCH_MM

# num → (x, y, rot_deg, net).  Insertion order mirrors the footprint file pad
# order (1, 8, 7, 6, 5, 4, 3, 2 — pin 1 top-left, CCW).  The PCB builder
# iterates in numeric order; KiCad is order-insensitive, but keeping both
# orders stable keeps regenerated files diffable.
XQFN_PADS: dict[str, tuple[float, float, float, str]] = {
    "1": (-0.20, 0.75, 90, "LA"),
    "8": (0.20, 0.75, 90, "LB"),
    "7": (0.75, 0.20, 0, "VOUT"),
    "6": (0.75, -0.20, 0, "VCC"),
    "5": (0.20, -0.75, 90, "SDA"),
    "4": (-0.20, -0.75, 90, "FD"),
    "3": (-0.75, -0.20, 0, "SCL"),
    "2": (-0.75, 0.20, 0, "GND"),
}


def xqfn_pad_wh(rot_deg: float) -> tuple[float, float]:
    """KiCad pad (width, height) before rotation: size is always (EDGE, ROW)."""
    return XQFN_PAD_EDGE_MM, XQFN_PAD_ROW_MM


def xqfn_pad_bbox(
    cx: float, cy: float, rot_deg: float
) -> tuple[float, float, float, float]:
    """Axis-aligned copper bbox (x0, y0, x1, y1) of a pad centred at (cx, cy)."""
    pw, ph = xqfn_pad_wh(rot_deg)
    if int(rot_deg) % 180 == 90:
        hw, hh = ph / 2, pw / 2
    else:
        hw, hh = pw / 2, ph / 2
    return cx - hw, cy - hh, cx + hw, cy + hh


def xqfn_side_pad_gap() -> float:
    """Gap between adjacent pads on the same side (mask bridge)."""
    return XQFN_PITCH_MM - XQFN_PAD_ROW_MM
