#!/usr/bin/env python3
"""KiCad 10 PCB s-expression formatting helpers."""

from __future__ import annotations

import uuid

PCB_FORMAT_VERSION = 20260206
GENERATOR = "pcbnew"
GENERATOR_VERSION = "10.0"


def quuid() -> str:
    return f'"{uuid.uuid4()}"'


def fmt_mm(v: float) -> str:
    """Trim trailing zeros like KiCad's save format."""
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def fmt_xy(x: float, y: float, rot: float | None = None) -> str:
    if rot is None:
        return f"{fmt_mm(x)} {fmt_mm(y)}"
    r = int(rot) if rot == int(rot) else rot
    return f"{fmt_mm(x)} {fmt_mm(y)} {r}"


def pcb_header(*, title: str, date: str, rev: str, comment: str) -> str:
    return f"""(kicad_pcb
\t(version {PCB_FORMAT_VERSION})
\t(generator "{GENERATOR}")
\t(generator_version "{GENERATOR_VERSION}")
\t(general
\t\t(thickness 0.8)
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(title_block
\t\t(title "{title}")
\t\t(date "{date}")
\t\t(rev "{rev}")
\t\t(comment 1 "{comment}")
\t)"""


def pcb_layers() -> str:
    return """\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(21 "Eco1.User" user "User.Eco1")
\t\t(23 "Eco2.User" user "User.Eco2")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user "F.Fabrication")
\t\t(33 "B.Fab" user "B.Fabrication")
\t)"""


def pcb_setup(*, output_directory: str = "fab/gerber") -> str:
    return f"""\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(tenting
\t\t\t(front yes)
\t\t\t(back yes)
\t\t)
\t\t(covering
\t\t\t(front no)
\t\t\t(back no)
\t\t)
\t\t(plugging
\t\t\t(front no)
\t\t\t(back no)
\t\t)
\t\t(capping no)
\t\t(filling no)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00000000_00000000_000010fc_ffffffff)
\t\t\t(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)
\t\t\t(disableapertmacros no)
\t\t\t(usegerberextensions no)
\t\t\t(usegerberattributes yes)
\t\t\t(usegerberadvancedattributes yes)
\t\t\t(creategerberjobfile yes)
\t\t\t(dashed_line_dash_ratio 12)
\t\t\t(dashed_line_gap_ratio 3)
\t\t\t(svgprecision 4)
\t\t\t(plotframeref no)
\t\t\t(mode 1)
\t\t\t(useauxorigin no)
\t\t\t(pdf_front_fp_property_popups yes)
\t\t\t(pdf_back_fp_property_popups yes)
\t\t\t(pdf_metadata yes)
\t\t\t(pdf_single_document no)
\t\t\t(dxfpolygonmode yes)
\t\t\t(dxfimperialunits yes)
\t\t\t(dxfusepcbnewfont yes)
\t\t\t(psnegative no)
\t\t\t(psa4output no)
\t\t\t(plot_black_and_white yes)
\t\t\t(sketchpadsonfab no)
\t\t\t(plotpadnumbers no)
\t\t\t(hidednponfab no)
\t\t\t(sketchdnponfab yes)
\t\t\t(crossoutdnponfab yes)
\t\t\t(subtractmaskfromsilk no)
\t\t\t(outputformat 1)
\t\t\t(mirror no)
\t\t\t(drillshape 1)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "{output_directory}")
\t\t)
\t)"""


def footprint_property(
    name: str,
    value: str,
    at_x: float,
    at_y: float,
    at_rot: float,
    layer: str,
    *,
    hide: bool = False,
    font_size: tuple[float, float] = (1.27, 1.27),
    thickness: float | None = None,
) -> str:
    hide_line = "\n\t\t\t(hide yes)" if hide else ""
    if thickness is not None:
        font = f"(font\n\t\t\t\t(size {font_size[0]} {font_size[1]})\n\t\t\t\t(thickness {thickness})\n\t\t\t)"
    else:
        font = f"(font\n\t\t\t\t(size {font_size[0]} {font_size[1]})\n\t\t\t)"
    return f"""\t\t(property "{name}" "{value}"
\t\t\t(at {fmt_xy(at_x, at_y, at_rot)})
\t\t\t(layer "{layer}"){hide_line}
\t\t\t(uuid {quuid()})
\t\t\t(effects
\t\t\t\t{font}
\t\t\t)
\t\t)"""


def fp_line(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.25) -> str:
    return f"""\t\t(fp_line
\t\t\t(start {fmt_xy(x0, y0)})
\t\t\t(end {fmt_xy(x1, y1)})
\t\t\t(stroke
\t\t\t\t(width {width})
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(layer "{layer}")
\t\t\t(uuid {quuid()})
\t\t)"""


def fp_rect(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.05) -> str:
    return f"""\t\t(fp_rect
\t\t\t(start {fmt_xy(x0, y0)})
\t\t\t(end {fmt_xy(x1, y1)})
\t\t\t(stroke
\t\t\t\t(width {width})
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(fill no)
\t\t\t(layer "{layer}")
\t\t\t(uuid {quuid()})
\t\t)"""


def fp_circle(cx: float, cy: float, ex: float, ey: float, layer: str, *, width: float = 0.12) -> str:
    return f"""\t\t(fp_circle
\t\t\t(center {fmt_xy(cx, cy)})
\t\t\t(end {fmt_xy(ex, ey)})
\t\t\t(stroke
\t\t\t\t(width {width})
\t\t\t\t(type solid)
\t\t\t)
\t\t\t(fill no)
\t\t\t(layer "{layer}")
\t\t\t(uuid {quuid()})
\t\t)"""


def fp_pad_roundrect(
    num: str,
    x: float,
    y: float,
    rot: float,
    w: float,
    h: float,
    *,
    net: str | None = None,
    rratio: float = 0.25,
) -> str:
    net_line = f'\n\t\t\t(net "{net}")' if net else ""
    return f"""\t\t(pad "{num}" smd roundrect
\t\t\t(at {fmt_xy(x, y, rot)})
\t\t\t(size {w} {h})
\t\t\t(layers "F.Cu" "F.Mask" "F.Paste")
\t\t\t(roundrect_rratio {rratio}){net_line}
\t\t\t(uuid {quuid()})
\t\t)"""


def fp_pad_circle(num: str, x: float, y: float, *, net: str | None = None, size: float = 0.6) -> str:
    net_line = f'\n\t\t\t(net "{net}")' if net else ""
    return f"""\t\t(pad "{num}" smd circle
\t\t\t(at {fmt_xy(x, y)})
\t\t\t(size {size} {size})
\t\t\t(layers "F.Cu" "F.Mask"){net_line}
\t\t\t(uuid {quuid()})
\t\t)"""


def segment(x0: float, y0: float, x1: float, y1: float, net: str, *, width: float = 0.3, layer: str = "F.Cu") -> str:
    return f"""\t(segment
\t\t(start {fmt_xy(x0, y0)})
\t\t(end {fmt_xy(x1, y1)})
\t\t(width {width})
\t\t(layer "{layer}")
\t\t(net "{net}")
\t\t(uuid {quuid()})
\t)"""


def gr_line(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.1, dash: bool = False) -> str:
    stroke_type = "dash" if dash else "solid"
    return f"""\t(gr_line
\t\t(start {fmt_xy(x0, y0)})
\t\t(end {fmt_xy(x1, y1)})
\t\t(stroke
\t\t\t(width {width})
\t\t\t(type {stroke_type})
\t\t)
\t\t(layer "{layer}")
\t\t(uuid {quuid()})
\t)"""


def gr_rect(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.1) -> str:
    return f"""\t(gr_rect
\t\t(start {fmt_xy(x0, y0)})
\t\t(end {fmt_xy(x1, y1)})
\t\t(stroke
\t\t\t(width {width})
\t\t\t(type solid)
\t\t)
\t\t(fill no)
\t\t(layer "{layer}")
\t\t(uuid {quuid()})
\t)"""


def gr_text(
    text: str,
    x: float,
    y: float,
    layer: str,
    *,
    size: float = 1.2,
    thickness: float = 0.15,
    justify: str | None = None,
    bold: bool = False,
) -> str:
    justify_line = f"\n\t\t\t(justify {justify})" if justify else ""
    bold_line = "\n\t\t\t\t(bold yes)" if bold else ""
    return f"""\t(gr_text "{text}"
\t\t(at {fmt_xy(x, y, 0)})
\t\t(layer "{layer}")
\t\t(uuid {quuid()})
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t\t(thickness {thickness}){bold_line}
\t\t\t){justify_line}
\t\t)
\t)"""


def build_name_enig_sexpr(
    text: str,
    *,
    x_mm: float,
    y_mm: float,
    size_mm: float,
    thickness_mm: float,
) -> str:
    """ENIG name via KiCad stroke text: F.Cu lettering + F.Mask opening."""
    anchor_y = y_mm + size_mm
    opts = dict(size=size_mm, thickness=thickness_mm, justify="left bottom", bold=True)
    cu = gr_text(text, x_mm, anchor_y, "F.Cu", **opts)
    mask = gr_text(text, x_mm, anchor_y, "F.Mask", **opts)
    return f"{cu}\n{mask}"


def gr_poly_copper(x0: float, y0: float, x1: float, y1: float) -> str:
    pts = (
        f"(xy {fmt_mm(x0)} {fmt_mm(y0)})",
        f"(xy {fmt_mm(x1)} {fmt_mm(y0)})",
        f"(xy {fmt_mm(x1)} {fmt_mm(y1)})",
        f"(xy {fmt_mm(x0)} {fmt_mm(y1)})",
    )
    return f"""\t(gr_poly
\t\t(pts
\t\t\t{' '.join(pts)}
\t\t)
\t\t(stroke
\t\t\t(width 0)
\t\t\t(type solid)
\t\t)
\t\t(fill yes)
\t\t(layers "F.Cu" "F.Mask")
\t\t(solder_mask_margin 0)
\t\t(uuid {quuid()})
\t)"""
