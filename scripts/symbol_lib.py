"""KiCad symbol definitions — single source of truth.

One canonical copy of every `(symbol ...)` block, shared by the
lib/symbols/NFC_BusinessCard.kicad_sym library file (multi-line format)
and the root schematic's embedded `(lib_symbols ...)` section (compacted
to one node per line).  Block order follows the schematic embed.
"""

from __future__ import annotations

import re

from jlcpcb_limits import NC_TERM_R_KOHM

# {NC_TERM_R_KOHM} is a .format() placeholder resolved at write time.
_SYMBOL_BODIES = (
'\t(symbol "NT3H2111W0FHKH"\n\t\t(pin_names (offset 1.016))\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(property "Reference" "U"\n\t\t\t(at 0 8.89 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n\t\t(property "Value" "NT3H2111W0FHKH"\n\t\t\t(at 0 -8.89 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n\t\t(property "Footprint" "NFC_BusinessCard:XQFN-8_1.6x1.6mm_P0.4mm_NT3H2111"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(property "Datasheet" "https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(property "Description" "NTAG I2C plus Type 2 Tag, 1kB, 50pF"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(property "LCSC Part #" "C710403"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(property "ki_keywords" "NFC NTAG Type2"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(symbol "NT3H2111W0FHKH_0_1"\n\t\t\t(rectangle\n\t\t\t\t(start -7.62 7.62)\n\t\t\t\t(end 7.62 -7.62)\n\t\t\t\t(stroke (width 0.254) (type default))\n\t\t\t\t(fill (type background))\n\t\t\t)\n\t\t)\n\t\t(symbol "NT3H2111W0FHKH_1_1"\n\t\t\t(pin passive line (at -10.16 5.08 0) (length 2.54)\n\t\t\t\t(name "LA" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at -10.16 2.54 0) (length 2.54)\n\t\t\t\t(name "VSS" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at -10.16 0 0) (length 2.54)\n\t\t\t\t(name "SCL" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "3" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at -10.16 -2.54 0) (length 2.54)\n\t\t\t\t(name "FD" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "4" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at 10.16 -2.54 180) (length 2.54)\n\t\t\t\t(name "SDA" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "5" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at 10.16 0 180) (length 2.54)\n\t\t\t\t(name "VCC" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "6" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at 10.16 2.54 180) (length 2.54)\n\t\t\t\t(name "VOUT" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "7" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at 10.16 5.08 180) (length 2.54)\n\t\t\t\t(name "LB" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "8" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t)\n\t)\n\t(symbol "Antenna_NFC"\n\t\t(pin_names (offset 1.016))\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n\t\t(on_board yes)\n\t\t(property "Reference" "ANT"\n\t\t\t(at 0 5.08 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n\t\t(property "Value" "Antenna_NFC"\n\t\t\t(at 0 -5.08 0)\n\t\t\t(effects (font (size 1.27 1.27)))\n\t\t)\n\t\t(property "Footprint" "NFC_BusinessCard:Antenna_Spiral_29x45_5T"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(property "Datasheet" "~"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(property "Description" "PCB spiral NFC antenna net-tie"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)\n\t\t(symbol "Antenna_NFC_0_1"\n\t\t\t(arc\n\t\t\t\t(start -2.54 0)\n\t\t\t\t(mid 0 2.54)\n\t\t\t\t(end 2.54 0)\n\t\t\t\t(stroke (width 0) (type default))\n\t\t\t\t(fill (type none))\n\t\t\t)\n\t\t\t(arc\n\t\t\t\t(start -1.27 0)\n\t\t\t\t(mid 0 1.27)\n\t\t\t\t(end 1.27 0)\n\t\t\t\t(stroke (width 0) (type default))\n\t\t\t\t(fill (type none))\n\t\t\t)\n\t\t)\n\t\t(symbol "Antenna_NFC_1_1"\n\t\t\t(pin passive line (at -5.08 0 0) (length 2.54)\n\t\t\t\t(name "1" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t\t(pin passive line (at 5.08 0 180) (length 2.54)\n\t\t\t\t(name "2" (effects (font (size 1.27 1.27))))\n\t\t\t\t(number "2" (effects (font (size 1.27 1.27))))\n\t\t\t)\n\t\t)\n\t)\n\t(symbol "C_0402"\n\t\t(pin_numbers (hide yes))\n\t\t(pin_names (offset 0.254))\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(property "Reference" "C" (at 0.635 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))\n\t\t(property "Value" "C_0402" (at 0.635 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))\n\t\t(property "Footprint" "NFC_BusinessCard:C_0402_1005Metric" (at 0.9652 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(symbol "C_0402_0_1"\n\t\t\t(polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n\t\t\t(polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))\n\t\t)\n\t\t(symbol "C_0402_1_1"\n\t\t\t(pin passive line (at 0 3.81 270) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))\n\t\t\t(pin passive line (at 0 -3.81 90) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))\n\t\t)\n\t)\n\t(symbol "R_0402"\n\t\t(pin_numbers (hide yes))\n\t\t(pin_names (offset 0.254))\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(property "Reference" "R" (at 0.635 2.54 0) (effects (font (size 1.27 1.27)) (justify left)))\n\t\t(property "Value" "R_0402" (at 0.635 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))\n\t\t(property "Footprint" "NFC_BusinessCard:R_0402_1005Metric" (at 0.9652 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(property "Description" "{NC_TERM_R_KOHM}k NC pull-down" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(symbol "R_0402_0_1"\n\t\t\t(rectangle (start -1.016 -0.508) (end 1.016 0.508) (stroke (width 0.254) (type default)) (fill (type none)))\n\t\t)\n\t\t(symbol "R_0402_1_1"\n\t\t\t(pin passive line (at 0 3.81 270) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))\n\t\t\t(pin passive line (at 0 -3.81 90) (length 2.794) (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))\n\t\t)\n\t)\n\t(symbol "GND"\n\t\t(power)\n\t\t(pin_numbers (hide yes))\n\t\t(pin_names (offset 0))\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n\t\t(on_board no)\n\t\t(property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(property "Value" "GND" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))\n\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(symbol "GND_0_1"\n\t\t\t(polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27))\n\t\t\t\t(stroke (width 0) (type default)) (fill (type none)))\n\t\t)\n\t\t(symbol "GND_1_1"\n\t\t\t(pin power_in line (at 0 0 0) (length 0) (name "GND" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))\n\t\t)\n\t)\n\t(symbol "PWR_FLAG"\n\t\t(power)\n\t\t(pin_numbers (hide yes))\n\t\t(pin_names (offset 0))\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n\t\t(on_board no)\n\t\t(property "Reference" "#FLG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(property "Value" "PWR_FLAG" (at 0 1.905 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))\n\t\t(symbol "PWR_FLAG_0_0"\n\t\t\t(pin power_out line (at 0 0 0) (length 0) (name "pwr" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))\n\t\t)\n\t)')


def symbol_bodies() -> str:
    """Canonical `(symbol ...)` blocks in .kicad_sym (multi-line) format."""
    return _SYMBOL_BODIES.format(NC_TERM_R_KOHM=NC_TERM_R_KOHM)


_COMPACT_NODE = (
    (re.compile(r"(?P<ind>\t+)\(property \"([^\"]*)\" \"([^\"]*)\"\n(?P=ind)\t\(at ([^\n]*)\)\n(?P=ind)\t\(effects ([^\n]*)\)\n(?P=ind)\)"),
     lambda mm: f'{mm.group("ind")}(property "{mm.group(2)}" "{mm.group(3)}" (at {mm.group(4)}) (effects {mm.group(5)}))'),
    (re.compile(r"(?P<ind>\t+)\(pin (\w+) (\w+) \(at ([^\n]*)\) \(length ([^\n]*)\)\n(?P=ind)\t\(name ([^\n]*)\)\n(?P=ind)\t\(number ([^\n]*)\)\n(?P=ind)\)"),
     lambda mm: f'{mm.group("ind")}(pin {mm.group(2)} {mm.group(3)} (at {mm.group(4)}) (length {mm.group(5)}) (name {mm.group(6)}) (number {mm.group(7)}))'),
    (re.compile(r"(?P<ind>\t+)\((rectangle|arc)\n(?P=ind)\t\(start ([^\n]*)\)\n(?P=ind)\t(?:\(mid ([^\n]*)\)\n(?P=ind)\t)?\(end ([^\n]*)\)\n(?P=ind)\t\(stroke ([^\n]*)\)\n(?P=ind)\t\(fill ([^\n]*)\)\n(?P=ind)\)"),
     lambda mm: f'{mm.group("ind")}({mm.group(2)} (start {mm.group(3)})' + (f' (mid {mm.group(4)})' if mm.group(4) else '') + f' (end {mm.group(5)}) (stroke {mm.group(6)}) (fill {mm.group(7)}))'),
    (re.compile(r"(?P<ind>\t+)\(polyline\n(?P=ind)\t\(pts ([^\n]*)\)\n(?P=ind)\t\(stroke ([^\n]*)\)\n(?P=ind)\t\(fill ([^\n]*)\)\n(?P=ind)\)"),
     lambda mm: f'{mm.group("ind")}(polyline (pts {mm.group(2)}) (stroke {mm.group(3)}) (fill {mm.group(4)}))'),
)


def _compactify(text: str) -> str:
    """Collapse multi-line nodes to one line each (schematic embed style)."""
    for pattern, replace in _COMPACT_NODE:
        text = pattern.sub(replace, text)
    return text


def symbol_bodies_embedded() -> str:
    """Same blocks re-indented for the schematic's `(lib_symbols ...)` section."""
    lines = []
    for line in _compactify(symbol_bodies()).splitlines():
        if line.startswith("\t(symbol \""):
            name = line[len("\t(symbol \""):].split('"')[0]
            line = '\t(symbol "NFC_BusinessCard:' + name + '"'
        lines.append("\t" + line)
    return "\n".join(lines)
