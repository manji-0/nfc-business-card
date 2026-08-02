"""KiCad symbol definitions — one declarative tree, two renderings.

The canonical `Sexpr` tree feeds both the lib/symbols/NFC_BusinessCard.kicad_sym
library file (multi-line format) and the root schematic's embedded
`(lib_symbols ...)` section (compact, one node per line).  Block order follows
the schematic embed.  No hand-typed tabs: indentation comes from render_sexpr.
"""

from __future__ import annotations

from jlcpcb_limits import NC_TERM_R_KOHM
from sexpr import Sexpr, SexprDoc, render_sexpr


def _effects(*extra: Sexpr) -> Sexpr:
    return Sexpr("effects", (Sexpr("font", (Sexpr("size 1.27 1.27"),)), *extra))


def _property(name: str, value: str, *, at: str = "0 0 0", hide: bool = False) -> Sexpr:
    effects = _effects(Sexpr("hide yes")) if hide else _effects()
    return Sexpr(f'property "{name}" "{value}"', (Sexpr(f"at {at}"), effects))


def _property_justified(name: str, value: str, *, at: str, justify: str) -> Sexpr:
    return Sexpr(f'property "{name}" "{value}"', (Sexpr(f"at {at}"), _effects(Sexpr(f"justify {justify}"))))


def _pin(kind: str, at: str, length: str, name: str, number: str) -> Sexpr:
    return Sexpr(f"pin {kind} line (at {at}) (length {length})", (
        Sexpr(f'name "{name}"', (_effects(),)),
        Sexpr(f'number "{number}"', (_effects(),)),
    ))


def _stroke(width: str, style: str = "default") -> Sexpr:
    return Sexpr("stroke", (Sexpr(f"width {width}"), Sexpr(f"type {style}")))


def _fill(kind: str) -> Sexpr:
    return Sexpr("fill", (Sexpr(f"type {kind}"),))


def _rectangle(start: str, end: str) -> Sexpr:
    return Sexpr("rectangle", (
        Sexpr(f"start {start}"),
        Sexpr(f"end {end}"),
        _stroke("0.254"),
        _fill("none"),
    ))


def _arc(start: str, mid: str, end: str) -> Sexpr:
    return Sexpr("arc", (
        Sexpr(f"start {start}"),
        Sexpr(f"mid {mid}"),
        Sexpr(f"end {end}"),
        _stroke("0"),
        _fill("none"),
    ))


def _polyline(pts: tuple[str, ...], width: str) -> Sexpr:
    xy = " ".join(f"(xy {p})" for p in pts)
    # stroke + fill share one line (KiCad's GND symbol style).
    return Sexpr(f"polyline (pts {xy})", (f"{_stroke_str(width)} {_fill_str('none')}",))


def _stroke_str(width: str) -> str:
    return f"(stroke (width {width}) (type default))"


def _fill_str(kind: str) -> str:
    return f"(fill (type {kind}))"


NT3H2111 = Sexpr('symbol "NT3H2111W0FHKH"', (
    Sexpr("pin_names (offset 1.016)"),
    Sexpr("exclude_from_sim no"),
    Sexpr("in_bom yes"),
    Sexpr("on_board yes"),
    _property("Reference", "U", at="0 8.89 0"),
    _property("Value", "NT3H2111W0FHKH", at="0 -8.89 0"),
    _property("Footprint", "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111", hide=True),
    _property("Datasheet", "https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf", hide=True),
    _property("Description", "NTAG I2C plus Type 2 Tag, 1kB, 50pF", hide=True),
    _property("LCSC Part #", "C710403", hide=True),
    _property("ki_keywords", "NFC NTAG Type2", hide=True),
    Sexpr('symbol "NT3H2111W0FHKH_0_1"', (
        Sexpr("rectangle", (
            Sexpr("start -7.62 7.62"),
            Sexpr("end 7.62 -7.62"),
            _stroke("0.254"),
            _fill("background"),
        )),
    )),
    Sexpr('symbol "NT3H2111W0FHKH_1_1"', (
        _pin("passive", "-10.16 5.08 0", "2.54", "LA", "1"),
        _pin("passive", "-10.16 2.54 0", "2.54", "VSS", "2"),
        _pin("passive", "-10.16 0 0", "2.54", "SCL", "3"),
        _pin("passive", "-10.16 -2.54 0", "2.54", "FD", "4"),
        _pin("passive", "10.16 -2.54 180", "2.54", "SDA", "5"),
        _pin("passive", "10.16 0 180", "2.54", "VCC", "6"),
        _pin("passive", "10.16 2.54 180", "2.54", "VOUT", "7"),
        _pin("passive", "10.16 5.08 180", "2.54", "LB", "8"),
    )),
))

ANTENNA = Sexpr('symbol "Antenna_NFC"', (
    Sexpr("pin_names (offset 1.016)"),
    Sexpr("exclude_from_sim no"),
    Sexpr("in_bom no"),
    Sexpr("on_board yes"),
    _property("Reference", "ANT", at="0 5.08 0"),
    _property("Value", "Antenna_NFC", at="0 -5.08 0"),
    _property("Footprint", "NFC_BusinessCard:Antenna_Spiral_29x45_5T", hide=True),
    _property("Datasheet", "~", hide=True),
    _property("Description", "PCB spiral NFC antenna net-tie", hide=True),
    Sexpr('symbol "Antenna_NFC_0_1"', (
        _arc("-2.54 0", "0 2.54", "2.54 0"),
        _arc("-1.27 0", "0 1.27", "1.27 0"),
    )),
    Sexpr('symbol "Antenna_NFC_1_1"', (
        _pin("passive", "-5.08 0 0", "2.54", "1", "1"),
        _pin("passive", "5.08 0 180", "2.54", "2", "2"),
    )),
))

C0402 = Sexpr('symbol "C_0402"', (
    Sexpr("pin_numbers (hide yes)"),
    Sexpr("pin_names (offset 0.254)"),
    Sexpr("exclude_from_sim no"),
    Sexpr("in_bom yes"),
    Sexpr("on_board yes"),
    _property_justified("Reference", "C", at="0.635 2.54 0", justify="left"),
    _property_justified("Value", "C_0402", at="0.635 -2.54 0", justify="left"),
    _property("Footprint", "NFC_BusinessCard:C_0402_1005Metric", at="0.9652 -3.81 0", hide=True),
    Sexpr('symbol "C_0402_0_1"', (
        _polyline(("-2.032 -0.762", "2.032 -0.762"), "0.508"),
        _polyline(("-2.032 0.762", "2.032 0.762"), "0.508"),
    )),
    Sexpr('symbol "C_0402_1_1"', (
        _pin("passive", "0 3.81 270", "2.794", "~", "1"),
        _pin("passive", "0 -3.81 90", "2.794", "~", "2"),
    )),
))

R0402 = Sexpr('symbol "R_0402"', (
    Sexpr("pin_numbers (hide yes)"),
    Sexpr("pin_names (offset 0.254)"),
    Sexpr("exclude_from_sim no"),
    Sexpr("in_bom yes"),
    Sexpr("on_board yes"),
    _property_justified("Reference", "R", at="0.635 2.54 0", justify="left"),
    _property_justified("Value", "R_0402", at="0.635 -2.54 0", justify="left"),
    _property("Footprint", "NFC_BusinessCard:R_0402_1005Metric", at="0.9652 -3.81 0", hide=True),
    _property("Description", f"{NC_TERM_R_KOHM}k NC pull-down", hide=True),
    Sexpr('symbol "R_0402_0_1"', (
        _rectangle("-1.016 -0.508", "1.016 0.508"),
    )),
    Sexpr('symbol "R_0402_1_1"', (
        _pin("passive", "0 3.81 270", "2.794", "~", "1"),
        _pin("passive", "0 -3.81 90", "2.794", "~", "2"),
    )),
))

GND = Sexpr('symbol "GND"', (
    Sexpr("power"),
    Sexpr("pin_numbers (hide yes)"),
    Sexpr("pin_names (offset 0)"),
    Sexpr("exclude_from_sim no"),
    Sexpr("in_bom no"),
    Sexpr("on_board no"),
    _property("Reference", "#PWR", at="0 -3.81 0", hide=True),
    _property("Value", "GND", at="0 -3.81 0"),
    _property("Footprint", "", hide=True),
    Sexpr('symbol "GND_0_1"', (
        _polyline(("0 0", "0 -1.27", "1.27 -1.27", "0 -2.54", "-1.27 -1.27", "0 -1.27"), "0"),
    )),
    Sexpr('symbol "GND_1_1"', (
        _pin("power_in", "0 0 0", "0", "GND", "1"),
    )),
))

PWR_FLAG = Sexpr('symbol "PWR_FLAG"', (
    Sexpr("power"),
    Sexpr("pin_numbers (hide yes)"),
    Sexpr("pin_names (offset 0)"),
    Sexpr("exclude_from_sim no"),
    Sexpr("in_bom no"),
    Sexpr("on_board no"),
    _property("Reference", "#FLG", at="0 1.905 0", hide=True),
    _property("Value", "PWR_FLAG", at="0 1.905 0", hide=True),
    _property("Footprint", "", hide=True),
    Sexpr('symbol "PWR_FLAG_0_0"', (
        _pin("power_out", "0 0 0", "0", "pwr", "1"),
    )),
))

# Schematic embed order (R_0402 before GND / PWR_FLAG).
SYMBOLS: tuple[Sexpr, ...] = (NT3H2111, ANTENNA, C0402, R0402, GND, PWR_FLAG)

# .kicad_sym bodies mix formats: NT3H2111/Antenna keep KiCad's multi-line
# property/pin/geometry nodes; the rest are compact one-liners except GND's
# polyline (pts on the head line, stroke/fill as children).
_LIB_MULTILINE: dict[str, frozenset[str]] = {
    "NT3H2111W0FHKH": frozenset({"property", "pin", "rectangle"}),
    "Antenna_NFC": frozenset({"property", "pin", "arc"}),
    "C_0402": frozenset(),
    "R_0402": frozenset(),
    "GND": frozenset({"polyline"}),
    "PWR_FLAG": frozenset(),
}

# Schematic embed: only the `(symbol ...)` wrappers and GND's polyline stay
# multi-line; everything else is one node per line.
_EMBED_MULTILINE: dict[str, frozenset[str]] = {
    "NT3H2111W0FHKH": frozenset(),
    "Antenna_NFC": frozenset(),
    "C_0402": frozenset(),
    "R_0402": frozenset(),
    "GND": frozenset({"polyline"}),
    "PWR_FLAG": frozenset(),
}


def symbol_lib_sexpr() -> str:
    """Full .kicad_sym library file content (per-symbol formats)."""
    doc = SexprDoc()
    with doc.node("(kicad_symbol_lib"):
        doc.line("(version 20231120)")
        doc.line('(generator "nfc_business_card")')
        doc.line('(generator_version "1.0")')
        for sym in SYMBOLS:
            name = sym.head.split('"')[1]
            doc.raw(render_sexpr(sym, multiline=_LIB_MULTILINE[name], depth=1))
    return doc.render()


def embedded_lib_symbols_sexpr() -> SexprDoc:
    """`(lib_symbols ...)` node for the schematic (compact, relative depth 0)."""
    doc = SexprDoc()
    with doc.node("(lib_symbols"):
        for sym in SYMBOLS:
            name = sym.head.split('"')[1]
            doc.raw(render_sexpr(sym, multiline=_EMBED_MULTILINE[name], depth=1, lib_prefix="NFC_BusinessCard:"))
    return doc
