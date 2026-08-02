"""JLCPCB fab limits and conservative design targets (mm)."""

# JLC standard 2-layer absolutes — never go below
JLC_MIN_MASK_BRIDGE_MM = 0.10
JLC_MIN_TRACE_WIDTH_MM = 0.127
JLC_MIN_TRACE_CLEARANCE_MM = 0.127

# KiCad DRC uses JLC fab minimum; check_layout.py still warns below DESIGN target.
KICAD_DRC_MIN_CLEARANCE_MM = JLC_MIN_TRACE_CLEARANCE_MM
DESIGN_MASK_BRIDGE_MM = 0.15
DESIGN_TRACE_CLEARANCE_MM = 0.20
DESIGN_MIN_FEATURE_MM = 0.18

# LA/LB feed buses: pad centers fixed at ±0.20 mm (XQFN pitch)
# Buses stay at the antenna trace width so the LA/LB connection has no width
# step. Only the co-located bus columns (0.40 mm pitch) narrow to the XQFN ROW
# width so the parallel pair clears the 0.20 mm design target:
# 0.40 mm pitch − 0.18 mm bus = 0.22 mm gap (JLC min 0.127, design target 0.20).
FEED_BUS_PITCH_MM = 0.40
FEED_BUS_HALF_PITCH_MM = 0.20
FEED_TRACE_W_MM = 0.25
# LA vertical skirts left of U1 so it never crosses FD (pad 4)
FEED_LA_BYPASS_DX_MM = 2.6
# Leave spiral start west before rising — must not share the outer left-edge
# centerline (that shorts turn 1). Center gap ≥ trace + design clearance.
FEED_LA_TAKEOFF_DX_MM = FEED_TRACE_W_MM + DESIGN_TRACE_CLEARANCE_MM  # 0.45

# XQFN-8: short axis along the side (ROW), long axis toward package center (EDGE)
# Pitch 0.40 − ROW 0.18 = 0.22 mm mask bridge between adjacent pads on a side
XQFN_PITCH_MM = 0.40
XQFN_PAD_ROW_MM = 0.18
XQFN_PAD_EDGE_MM = 0.42
XQFN_COURTYARD_HALF_MM = 1.2
# Bus width where two feeds share the 0.40 mm pad pitch: match the XQFN pad
# width (no step at the land) and widen the bus-to-bus gap (0.40 − 0.18 = 0.22).
FEED_BUS_W_MM = XQFN_PAD_ROW_MM

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
# Local VSS island west of U1 (clear of SCL pad 3 and LA bypass)
GND_ISLAND_DX_MM = 1.95
GND_ISLAND_DY_MM = 0.375
GND_ISLAND_W_MM = 0.50
GND_ISLAND_H_MM = 0.35
# LB B.Cu underpass exit via (east of U1, clear of the NC fan-out vias)
FEED_VIA_OUT_DX_MM = 2.9  # LB underpass exit via x offset from U1
FEED_VIA_OUT_DY_MM = 1.45  # south of pad_y so Ø0.5 clears LA skirt at pad_y+0.65
FEED_LB_JOIN_DX_MM = 1.80  # legacy — C1 LB now stays on F.Cu
FEED_VIA_SIZE_MM = 0.5
FEED_VIA_DRILL_MM = 0.3

# NC pin weak pull-downs to VSS (B.Cu DNP 0402)
NC_TERM_R_KOHM = 100
NC_TERM_R_LCSC = "C60491"  # YAGEO RC0402FR-07100KL 100 kΩ 0402 ±1% (verified 2026-08-02)
# Obsolete/wrong: C25744 = Uni-Royal 0402WGF1002TCE = 10 kΩ, not 100 kΩ.
R0402_PAD_OFFSET_MM = 0.48
NC_TERM_R_OFFSET_MM = 0.85  # legacy — replaced by NC_R_COL_DX_MM column layout
NC_TERM_GND_BUS_INSET_MM = 0.85  # B.Cu GND bus west of R pad 2 (room for NC channels east of bus)
# NC fan-out vias: Ø0.5 cannot sit on a 0.18 mm-wide pad at 0.4 mm pitch,
# so each net leaves U1 via an F.Cu stub; vias stay ≥ 0.7 mm apart.
NC_VIA_SIZE_MM = 0.5
NC_VIA_DRILL_MM = 0.3
NC_R_COL_DX_MM = -2.60  # DNP resistor column centre relative to U1
NC_BELOW_LA_Y_MM = -1.48  # legacy ref for docs
NC_VIA_GND_DY_MM = 0.0  # GND trunk→island via sits on the island y
NC_STUB_NARROW_W_MM = 0.15  # F.Cu escapes between 0.4 mm-pitch pads
