#!/usr/bin/env python3
"""Bake KiCad gr_text with TrueType render_cache via pcbnew."""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from kamae.result import Err, Ok, Result
from kamae.types import HJustify, Layer, Mm, VJustify
from kicad_paths import find_kicad_python, kicad_python_env
from name_render_cache import (
    align_gr_text_block_left,
    fit_gr_text_block_width,
    parse_render_cache_polys,
    polys_bounds,
    scale_gr_text_block,
    shift_gr_text_block,
)
from silk_layout import TEXT_LEFT_MM

_LAYER_CONST: dict[Layer, str] = {
    "F.Cu": "pcbnew.F_Cu",
    "F.Mask": "pcbnew.F_Mask",
    "F.SilkS": "pcbnew.F_SilkS",
    "B.SilkS": "pcbnew.B_SilkS",
}

_H_CONST: dict[HJustify, str] = {
    "left": "pcbnew.GR_TEXT_H_ALIGN_LEFT",
    "center": "pcbnew.GR_TEXT_H_ALIGN_CENTER",
    "right": "pcbnew.GR_TEXT_H_ALIGN_RIGHT",
}

_V_CONST: dict[VJustify, str] = {
    "top": "pcbnew.GR_TEXT_V_ALIGN_TOP",
    "center": "pcbnew.GR_TEXT_V_ALIGN_CENTER",
    "bottom": "pcbnew.GR_TEXT_V_ALIGN_BOTTOM",
}


class BakeErrorKind(Enum):
    PCBNEW_FAILED = "pcbnew_failed"
    BLOCK_COUNT_MISMATCH = "block_count_mismatch"


@dataclass(frozen=True, slots=True)
class BakeError:
    kind: BakeErrorKind
    detail: str


@dataclass(frozen=True, slots=True)
class TextSpec:
    text: str
    x_mm: Mm
    y_mm: Mm
    size_mm: Mm
    face: str
    layer: Layer
    thickness_mm: Mm = Mm(0.12)
    h_justify: HJustify = "left"
    v_justify: VJustify = "top"
    align_left_mm: Mm | None = None
    max_width_mm: Mm | None = None


def _extract_gr_text_blocks(pcb_text: str, layers: tuple[Layer, ...] | None = None) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(pcb_text):
        start = pcb_text.find("\t(gr_text ", i)
        if start < 0:
            break
        depth = 0
        j = start
        while j < len(pcb_text):
            ch = pcb_text[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    block = pcb_text[start : j + 1]
                    if layers is None:
                        out.append(block)
                    else:
                        layer_m = re.search(r'\(layer "([^"]+)"\)', block)
                        if layer_m and layer_m.group(1) in layers:
                            out.append(block)
                    i = j + 1
                    break
            j += 1
        else:
            break
    return out


def _post_process(block: str, spec: TextSpec) -> str:
    out = block
    if spec.align_left_mm is not None:
        out = align_gr_text_block_left(out, float(spec.align_left_mm))
    if spec.max_width_mm is not None:
        out = fit_gr_text_block_width(out, float(spec.max_width_mm))
    return out


def bake_specs_raw(specs: list[TextSpec]) -> Result[list[str], BakeError]:
    if not specs:
        return Ok([])

    lines = [
        "import wx",
        "import pcbnew",
        "from pcbnew import FromMM as mm",
        "app = wx.App(False)",
        "board = pcbnew.BOARD()",
    ]
    for idx, spec in enumerate(specs):
        layer = _LAYER_CONST[spec.layer]
        h = _H_CONST[spec.h_justify]
        v = _V_CONST[spec.v_justify]
        lines += [
            f"txt{idx} = pcbnew.PCB_TEXT(board)",
            f"txt{idx}.SetText({spec.text!r})",
            f"txt{idx}.SetPosition(pcbnew.VECTOR2I(int(mm({float(spec.x_mm)})), int(mm({float(spec.y_mm)}))))",
            f"txt{idx}.SetLayer({layer})",
            f"txt{idx}.SetTextSize(pcbnew.VECTOR2I(int(mm({float(spec.size_mm)})), int(mm({float(spec.size_mm)}))))",
            f"txt{idx}.SetTextThickness(int(mm({float(spec.thickness_mm)})))",
            f"txt{idx}.SetFontProp({spec.face!r})",
            f"txt{idx}.SetHorizJustify({h})",
            f"txt{idx}.SetVertJustify({v})",
            f"board.Add(txt{idx})",
        ]

    with tempfile.NamedTemporaryFile(suffix=".kicad_pcb", delete=False) as tmp:
        temp_path = tmp.name

    lines.append(f"board.Save({temp_path!r})")
    code = "\n".join(lines)

    try:
        proc = subprocess.run(
            [str(find_kicad_python()), "-c", code],
            capture_output=True,
            text=True,
            env=kicad_python_env(),
            check=False,
        )
        if proc.returncode != 0:
            return Err(
                BakeError(
                    kind=BakeErrorKind.PCBNEW_FAILED,
                    detail=proc.stderr or proc.stdout or "unknown error",
                )
            )
        pcb_text = Path(temp_path).read_text(encoding="utf-8")
        blocks = _extract_gr_text_blocks(pcb_text)
        if len(blocks) != len(specs):
            return Err(
                BakeError(
                    kind=BakeErrorKind.BLOCK_COUNT_MISMATCH,
                    detail=f"expected {len(specs)} gr_text blocks, got {len(blocks)}",
                )
            )
        return Ok(blocks)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _bake_specs_raw(specs: list[TextSpec]) -> list[str]:
    from kamae.result import unwrap

    return unwrap(bake_specs_raw(specs), context="KiCad pcbnew bake")


def _bake_specs(specs: list[TextSpec]) -> list[str]:
    blocks = _bake_specs_raw(specs)
    return [_post_process(block, spec) for block, spec in zip(blocks, specs)]


def _block_ink_width_mm(block: str) -> float:
    polys = parse_render_cache_polys(block)
    if not polys:
        return 0.0
    mnx, _, mxx, _ = polys_bounds(polys)
    return mxx - mnx


def _align_ink_bounds(
    block: str,
    *,
    left_mm: float,
    bottom_mm: float,
) -> str:
    polys = parse_render_cache_polys(block)
    mnx, _, _, mxy = polys_bounds(polys)
    return shift_gr_text_block(block, left_mm - mnx, bottom_mm - mxy)


def align_ink_bounds_top(
    block: str,
    *,
    left_mm: float,
    top_mm: float,
) -> str:
    """Align ink top edge (preview Y-down / min polygon Y)."""
    polys = parse_render_cache_polys(block)
    mnx, mny, _, _ = polys_bounds(polys)
    return shift_gr_text_block(block, left_mm - mnx, top_mm - mny)


def bake_line_block_sexpr(
    lines: tuple[str, ...],
    *,
    x_mm: float,
    y0_mm: float,
    line_step_mm: float,
    size_mm: float,
    face: str,
    layer: Layer,
    thickness_mm: float = 0.12,
    align_left_mm: float | None = TEXT_LEFT_MM,
    target_block_width_mm: float | None = None,
) -> str:
    """Bake lines; uniformly scale to match preview (Pillow) block width."""
    y0 = Mm(y0_mm)
    specs = [
        TextSpec(
            text=line,
            x_mm=Mm(x_mm),
            y_mm=Mm(y0_mm + i * line_step_mm),
            size_mm=Mm(size_mm),
            face=face,
            layer=layer,
            thickness_mm=Mm(thickness_mm),
            h_justify="left",
            v_justify="top",
        )
        for i, line in enumerate(lines)
    ]
    blocks = _bake_specs_raw(specs)
    if align_left_mm is not None:
        blocks = [align_gr_text_block_left(b, align_left_mm) for b in blocks]
    if target_block_width_mm is not None:
        kicad_w = max(_block_ink_width_mm(b) for b in blocks)
        if kicad_w > target_block_width_mm + 1e-6:
            scale = target_block_width_mm / kicad_w
            blocks = [
                scale_gr_text_block(b, scale, align_left_mm or x_mm, float(y0)) for b in blocks
            ]
    return "\n".join(blocks)


def bake_texts_sexpr(specs: list[TextSpec]) -> str:
    """Return concatenated gr_text blocks for all specs (order preserved)."""
    return "\n".join(_bake_specs(specs))
