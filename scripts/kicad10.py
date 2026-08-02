#!/usr/bin/env python3
"""KiCad 10 PCB s-expression formatting helpers (indentation from nesting).

Every helper returns a relative `SexprDoc`; callers embed it at the depth the
node belongs to. No hand-typed tabs.
"""

from __future__ import annotations

import uuid

from sexpr import SexprDoc

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


def pcb_header(*, title: str, date: str, rev: str, comment: str) -> SexprDoc:
    """PCB header content below the `(kicad_pcb` root (relative)."""
    doc = SexprDoc()
    doc.line(f"(version {PCB_FORMAT_VERSION})")
    doc.line(f'(generator "{GENERATOR}")')
    doc.line(f'(generator_version "{GENERATOR_VERSION}")')
    with doc.node("(general"):
        doc.line("(thickness 0.8)")
        doc.line("(legacy_teardrops no)")
    doc.line('(paper "A4")')
    with doc.node("(title_block"):
        doc.line(f'(title "{title}")')
        doc.line(f'(date "{date}")')
        doc.line(f'(rev "{rev}")')
        doc.line(f'(comment 1 "{comment}")')
    return doc


def pcb_layers() -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(layers"):
        for num, name, layer_type, desc in (
            (0, "F.Cu", "signal", None),
            (2, "B.Cu", "signal", None),
            (9, "F.Adhes", "user", "F.Adhesive"),
            (11, "B.Adhes", "user", "B.Adhesive"),
            (13, "F.Paste", "user", None),
            (15, "B.Paste", "user", None),
            (5, "F.SilkS", "user", "F.Silkscreen"),
            (7, "B.SilkS", "user", "B.Silkscreen"),
            (1, "F.Mask", "user", None),
            (3, "B.Mask", "user", None),
            (17, "Dwgs.User", "user", "User.Drawings"),
            (19, "Cmts.User", "user", "User.Comments"),
            (21, "Eco1.User", "user", "User.Eco1"),
            (23, "Eco2.User", "user", "User.Eco2"),
            (25, "Edge.Cuts", "user", None),
            (27, "Margin", "user", None),
            (31, "F.CrtYd", "user", "F.Courtyard"),
            (29, "B.CrtYd", "user", "B.Courtyard"),
            (35, "F.Fab", "user", "F.Fabrication"),
            (33, "B.Fab", "user", "B.Fabrication"),
        ):
            desc_part = f' "{desc}"' if desc else ""
            doc.line(f'({num} "{name}" {layer_type}{desc_part})')
    return doc


def pcb_setup(*, output_directory: str = "fab/gerber") -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(setup"):
        doc.line("(pad_to_mask_clearance 0)")
        doc.line("(allow_soldermask_bridges_in_footprints no)")
        with doc.node("(tenting"):
            doc.line("(front yes)")
            doc.line("(back yes)")
        with doc.node("(covering"):
            doc.line("(front no)")
            doc.line("(back no)")
        with doc.node("(plugging"):
            doc.line("(front no)")
            doc.line("(back no)")
        doc.line("(capping no)")
        doc.line("(filling no)")
        with doc.node("(pcbplotparams"):
            doc.line("(layerselection 0x00000000_00000000_000010fc_ffffffff)")
            doc.line("(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)")
            doc.line("(disableapertmacros no)")
            doc.line("(usegerberextensions no)")
            doc.line("(usegerberattributes yes)")
            doc.line("(usegerberadvancedattributes yes)")
            doc.line("(creategerberjobfile yes)")
            doc.line("(dashed_line_dash_ratio 12)")
            doc.line("(dashed_line_gap_ratio 3)")
            doc.line("(svgprecision 4)")
            doc.line("(plotframeref no)")
            doc.line("(mode 1)")
            doc.line("(useauxorigin no)")
            doc.line("(pdf_front_fp_property_popups yes)")
            doc.line("(pdf_back_fp_property_popups yes)")
            doc.line("(pdf_metadata yes)")
            doc.line("(pdf_single_document no)")
            doc.line("(dxfpolygonmode yes)")
            doc.line("(dxfimperialunits yes)")
            doc.line("(dxfusepcbnewfont yes)")
            doc.line("(psnegative no)")
            doc.line("(psa4output no)")
            doc.line("(plot_black_and_white yes)")
            doc.line("(sketchpadsonfab no)")
            doc.line("(plotpadnumbers no)")
            doc.line("(hidednponfab no)")
            doc.line("(sketchdnponfab yes)")
            doc.line("(crossoutdnponfab yes)")
            doc.line("(subtractmaskfromsilk no)")
            doc.line("(outputformat 1)")
            doc.line("(mirror no)")
            doc.line("(drillshape 1)")
            doc.line("(scaleselection 1)")
            doc.line(f'(outputdirectory "{output_directory}")')
    return doc


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
) -> SexprDoc:
    doc = SexprDoc()
    with doc.node(f'(property "{name}" "{value}"'):
        doc.line(f"(at {fmt_xy(at_x, at_y, at_rot)})")
        doc.line(f'(layer "{layer}")')
        if hide:
            doc.line("(hide yes)")
        doc.line(f"(uuid {quuid()})")
        with doc.node("(effects"):
            with doc.node("(font"):
                doc.line(f"(size {font_size[0]} {font_size[1]})")
                if thickness is not None:
                    doc.line(f"(thickness {thickness})")
    return doc


def fp_line(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.25) -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(fp_line"):
        doc.line(f"(start {fmt_xy(x0, y0)})")
        doc.line(f"(end {fmt_xy(x1, y1)})")
        with doc.node("(stroke"):
            doc.line(f"(width {width})")
            doc.line("(type solid)")
        doc.line(f'(layer "{layer}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def fp_rect(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.05) -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(fp_rect"):
        doc.line(f"(start {fmt_xy(x0, y0)})")
        doc.line(f"(end {fmt_xy(x1, y1)})")
        with doc.node("(stroke"):
            doc.line(f"(width {width})")
            doc.line("(type solid)")
        doc.line("(fill no)")
        doc.line(f'(layer "{layer}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def fp_circle(cx: float, cy: float, ex: float, ey: float, layer: str, *, width: float = 0.12) -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(fp_circle"):
        doc.line(f"(center {fmt_xy(cx, cy)})")
        doc.line(f"(end {fmt_xy(ex, ey)})")
        with doc.node("(stroke"):
            doc.line(f"(width {width})")
            doc.line("(type solid)")
        doc.line("(fill no)")
        doc.line(f'(layer "{layer}")')
        doc.line(f"(uuid {quuid()})")
    return doc


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
    side: str = "F",
) -> SexprDoc:
    doc = SexprDoc()
    with doc.node(f'(pad "{num}" smd roundrect'):
        doc.line(f"(at {fmt_xy(x, y, rot)})")
        doc.line(f"(size {w} {h})")
        doc.line(f'(layers "{side}.Cu" "{side}.Mask" "{side}.Paste")')
        doc.line(f"(roundrect_rratio {rratio})")
        if net is not None:
            doc.line(f'(net "{net}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def fp_pad_connect_roundrect(
    num: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    net: str,
    rratio: float = 0,
) -> SexprDoc:
    """F.Cu connect pad (net-tie junction, no paste/mask)."""
    doc = SexprDoc()
    with doc.node(f'(pad "{num}" connect roundrect'):
        doc.line(f"(at {x:.4f} {y:.4f})")
        doc.line(f"(size {w:.4f} {h:.4f})")
        doc.line('(layers "F.Cu")')
        doc.line(f"(roundrect_rratio {rratio})")
        doc.line(f'(net "{net}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def fp_pad_circle(
    num: str,
    x: float,
    y: float,
    *,
    net: str | None = None,
    size: float = 0.45,
    pad_type: str = "smd",
    layers: str = '"F.Cu" "F.Mask"',
) -> SexprDoc:
    doc = SexprDoc()
    with doc.node(f'(pad "{num}" {pad_type} circle'):
        doc.line(f"(at {fmt_xy(x, y)})")
        doc.line(f"(size {size} {size})")
        doc.line(f"(layers {layers})")
        if net is not None:
            doc.line(f'(net "{net}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def via(x: float, y: float, net: str, *, size: float = 0.6, drill: float = 0.3) -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(via"):
        doc.line(f"(at {fmt_xy(x, y)})")
        doc.line(f"(size {size})")
        doc.line(f"(drill {drill})")
        doc.line('(layers "F.Cu" "B.Cu")')
        doc.line(f'(net "{net}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def segment(x0: float, y0: float, x1: float, y1: float, net: str, *, width: float = 0.3, layer: str = "F.Cu") -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(segment"):
        doc.line(f"(start {fmt_xy(x0, y0)})")
        doc.line(f"(end {fmt_xy(x1, y1)})")
        doc.line(f"(width {width})")
        doc.line(f'(layer "{layer}")')
        doc.line(f'(net "{net}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def gr_line(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.1, dash: bool = False) -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(gr_line"):
        doc.line(f"(start {fmt_xy(x0, y0)})")
        doc.line(f"(end {fmt_xy(x1, y1)})")
        with doc.node("(stroke"):
            doc.line(f"(width {width})")
            doc.line("(type dash)" if dash else "(type solid)")
        doc.line(f'(layer "{layer}")')
        doc.line(f"(uuid {quuid()})")
    return doc


def gr_rect(x0: float, y0: float, x1: float, y1: float, layer: str, *, width: float = 0.1) -> SexprDoc:
    doc = SexprDoc()
    with doc.node("(gr_rect"):
        doc.line(f"(start {fmt_xy(x0, y0)})")
        doc.line(f"(end {fmt_xy(x1, y1)})")
        with doc.node("(stroke"):
            doc.line(f"(width {width})")
            doc.line("(type solid)")
        doc.line("(fill no)")
        doc.line(f'(layer "{layer}")')
        doc.line(f"(uuid {quuid()})")
    return doc


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
) -> SexprDoc:
    doc = SexprDoc()
    with doc.node(f'(gr_text "{text}"'):
        doc.line(f"(at {fmt_xy(x, y, 0)})")
        doc.line(f'(layer "{layer}")')
        doc.line(f"(uuid {quuid()})")
        with doc.node("(effects"):
            with doc.node("(font"):
                doc.line(f"(size {size} {size})")
                doc.line(f"(thickness {thickness})")
                if bold:
                    doc.line("(bold yes)")
            if justify is not None:
                doc.line(f"(justify {justify})")
    return doc


def build_name_enig_sexpr(
    text: str,
    *,
    x_mm: float,
    y_mm: float,
    size_mm: float,
    thickness_mm: float,
) -> SexprDoc:
    """ENIG name via KiCad stroke text: F.Cu lettering + F.Mask opening."""
    anchor_y = y_mm + size_mm
    opts = dict(size=size_mm, thickness=thickness_mm, justify="left bottom", bold=True)
    doc = SexprDoc()
    doc.embed(gr_text(text, x_mm, anchor_y, "F.Cu", **opts))
    doc.embed(gr_text(text, x_mm, anchor_y, "F.Mask", **opts))
    return doc


def gr_poly_copper(x0: float, y0: float, x1: float, y1: float) -> SexprDoc:
    pts = (
        f"(xy {fmt_mm(x0)} {fmt_mm(y0)})",
        f"(xy {fmt_mm(x1)} {fmt_mm(y0)})",
        f"(xy {fmt_mm(x1)} {fmt_mm(y1)})",
        f"(xy {fmt_mm(x0)} {fmt_mm(y1)})",
    )
    doc = SexprDoc()
    with doc.node("(gr_poly"):
        with doc.node("(pts"):
            doc.line(" ".join(pts))
        with doc.node("(stroke"):
            doc.line("(width 0)")
            doc.line("(type solid)")
        doc.line("(fill yes)")
        doc.line('(layers "F.Cu" "F.Mask")')
        doc.line("(solder_mask_margin 0)")
        doc.line(f"(uuid {quuid()})")
    return doc
