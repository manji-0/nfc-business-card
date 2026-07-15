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
# 0.40 mm pitch − 0.18 mm trace = 0.22 mm gap (was 0.15 mm with 0.25 trace)
FEED_BUS_PITCH_MM = 0.40
FEED_BUS_HALF_PITCH_MM = 0.20
FEED_TRACE_W_MM = 0.18

# XQFN-8 row pads: 0.40 mm pitch − 0.18 mm pad = 0.22 mm mask bridge
XQFN_PITCH_MM = 0.40
XQFN_PAD_ROW_MM = 0.18
XQFN_PAD_EDGE_MM = 0.42

# Antenna spiral: 0.25 mm trace, 0.30 mm gap between turns
ANTENNA_TRACE_W_MM = 0.25
ANTENNA_GAP_MM = 0.30
ANT_INSET_MM = 3.0  # outer turn to board edge (spec ≥ 2 mm)
