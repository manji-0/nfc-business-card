"""JLCPCB fab limits and conservative design targets (mm)."""

# JLC standard 2-layer absolutes — never go below
JLC_MIN_MASK_BRIDGE_MM = 0.10
JLC_MIN_TRACE_WIDTH_MM = 0.127
JLC_MIN_TRACE_CLEARANCE_MM = 0.127

# Design targets — ~50% headroom over JLC minimum where practical
DESIGN_MASK_BRIDGE_MM = 0.15
DESIGN_TRACE_CLEARANCE_MM = 0.20
DESIGN_MIN_FEATURE_MM = 0.18

# LA/LB feed buses: pad centers fixed at ±0.20 mm (XQFN pitch)
# Matches antenna trace width so the LA/LB connection has no width step.
# 0.40 mm pitch − 0.25 mm trace = 0.15 mm gap (JLC min 0.127 OK; below 0.20 design target)
FEED_BUS_PITCH_MM = 0.40
FEED_BUS_HALF_PITCH_MM = 0.20
FEED_TRACE_W_MM = 0.25
# LA vertical skirts left of U1 so it never crosses FD (pad 4)
FEED_LA_BYPASS_DX_MM = 2.6

# XQFN-8: short axis along the side (ROW), long axis toward package center (EDGE)
# Pitch 0.40 − ROW 0.18 = 0.22 mm mask bridge between adjacent pads on a side
XQFN_PITCH_MM = 0.40
XQFN_PAD_ROW_MM = 0.18
XQFN_PAD_EDGE_MM = 0.42
XQFN_COURTYARD_HALF_MM = 1.2

# Antenna spiral: 0.25 mm trace, 0.30 mm gap between turns
ANTENNA_TRACE_W_MM = 0.25
ANTENNA_GAP_MM = 0.30
ANT_INSET_MM = 3.0  # outer turn to board edge (spec ≥ 2 mm)
# Feed pad Ø: pitch − half-trace − design clearance → ≤ 0.45 mm
ANTENNA_FEED_PAD_D_MM = 0.45
# Net-tie pad 2 (LB take-off) sits this far right of the coil inner end (pad 1, LA)
ANT_TIE_TAKEOFF_DX_MM = 1.3
# ...and pad 2 runs down to via_in this far below the take-off y
ANT_TIE_VIA_DY_MM = 0.75
# Local VSS island left of U1 (clear of SCL pad 3 and LA bypass)
GND_ISLAND_DX_MM = 1.7
GND_ISLAND_W_MM = 0.55
GND_ISLAND_H_MM = 0.40

# NC pin weak pull-downs to VSS (B.Cu DNP 0402)
NC_TERM_R_KOHM = 100
NC_TERM_R_LCSC = "C25744"  # 100 kΩ 0402 1%
R0402_PAD_OFFSET_MM = 0.48
NC_TERM_R_OFFSET_MM = 0.85  # resistor center west of U1 NC pad
NC_TERM_GND_BUS_INSET_MM = 0.25  # B.Cu GND bus left of island edge
