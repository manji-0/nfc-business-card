#!/usr/bin/env python3
"""Exhaustive same-layer copper checks (crossings, clearances, zones).

Operates on pure segment/via/pad geometry and on KiCad 10 PCB S-expressions.
Net-tie LA/LB pad overlap is the only intentional cross-net copper contact.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from kamae.result import Err, Ok, Result

Seg = tuple[float, float, float, float, str, float, str]  # x0,y0,x1,y1,net,w,layer
Via = tuple[float, float, str, float, float]  # x,y,net,size,drill
Pad = tuple[float, float, float, float, str, str]  # x0,y0,x1,y1,net,layer


@dataclass(frozen=True, slots=True)
class CopperIssue:
    kind: str  # "crossing" | "clearance" | "hole_clearance" | "zone" | "no_net" | "via"
    message: str


def _orient(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> int:
    v = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
    if abs(v) < 1e-9:
        return 0
    return 1 if v > 0 else 2


def _on_seg(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    return (
        min(ax, bx) - 1e-9 <= cx <= max(ax, bx) + 1e-9
        and min(ay, by) - 1e-9 <= cy <= max(ay, by) + 1e-9
    )


def segments_intersect(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    *,
    endpoint_touch_ok: bool = True,
) -> bool:
    """Proper intersection of two open/closed axis segments (including diagonals)."""
    x0, y0, x1, y1 = a
    x2, y2, x3, y3 = b
    if (x0, y0) == (x1, y1) or (x2, y2) == (x3, y3):
        return False
    o1 = _orient(x0, y0, x1, y1, x2, y2)
    o2 = _orient(x0, y0, x1, y1, x3, y3)
    o3 = _orient(x2, y2, x3, y3, x0, y0)
    o4 = _orient(x2, y2, x3, y3, x1, y1)
    if o1 != o2 and o3 != o4:
        if endpoint_touch_ok:
            # Ignore pure endpoint sharing (T-junctions / colinear joins).
            shared = {
                (round(x0, 6), round(y0, 6)),
                (round(x1, 6), round(y1, 6)),
            } & {
                (round(x2, 6), round(y2, 6)),
                (round(x3, 6), round(y3, 6)),
            }
            if shared and o1 != 0 and o2 != 0 and o3 != 0 and o4 != 0:
                # Crossing at a shared vertex still counts if directions cross;
                # only skip when the intersection is exactly an endpoint and
                # the other segment does not continue through.
                ix, iy = next(iter(shared))
                a_end = (ix, iy) in {(round(x0, 6), round(y0, 6)), (round(x1, 6), round(y1, 6))}
                b_end = (ix, iy) in {(round(x2, 6), round(y2, 6)), (round(x3, 6), round(y3, 6))}
                if a_end and b_end:
                    return False
        return True
    if o1 == 0 and _on_seg(x0, y0, x1, y1, x2, y2):
        return True
    if o2 == 0 and _on_seg(x0, y0, x1, y1, x3, y3):
        return True
    if o3 == 0 and _on_seg(x2, y2, x3, y3, x0, y0):
        return True
    if o4 == 0 and _on_seg(x2, y2, x3, y3, x1, y1):
        return True
    return False


def _seg_point_dist(x0: float, y0: float, x1: float, y1: float, px: float, py: float) -> float:
    dx, dy = x1 - x0, y1 - y0
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))


def segment_edge_clearance(a: Seg, b: Seg) -> float:
    """Approximate edge-to-edge clearance between two track segments."""
    x0, y0, x1, y1, _na, wa, _la = a
    x2, y2, x3, y3, _nb, wb, _lb = b
    # Sample distance between centerlines, then subtract half-widths.
    samples = [
        _seg_point_dist(x0, y0, x1, y1, x2, y2),
        _seg_point_dist(x0, y0, x1, y1, x3, y3),
        _seg_point_dist(x2, y2, x3, y3, x0, y0),
        _seg_point_dist(x2, y2, x3, y3, x1, y1),
    ]
    # Midpoint samples for parallel runs.
    mx0, my0 = (x0 + x1) / 2, (y0 + y1) / 2
    mx1, my1 = (x2 + x3) / 2, (y2 + y3) / 2
    samples.append(_seg_point_dist(x2, y2, x3, y3, mx0, my0))
    samples.append(_seg_point_dist(x0, y0, x1, y1, mx1, my1))
    return min(samples) - wa / 2 - wb / 2


def parse_pcb_segments(text: str) -> list[Seg]:
    pat = re.compile(
        r"\(segment\s+"
        r"\(start ([-\d.]+) ([-\d.]+)\)\s+"
        r"\(end ([-\d.]+) ([-\d.]+)\)\s+"
        r"\(width ([-\d.]+)\)\s+"
        r'\(layer "([^"]+)"\)\s+'
        r'\(net "([^"]*)"\)',
        re.S,
    )
    out: list[Seg] = []
    for m in pat.finditer(text):
        x0, y0, x1, y1, w, layer, net = m.groups()
        out.append((float(x0), float(y0), float(x1), float(y1), net, float(w), layer))
    return out


def parse_pcb_vias(text: str) -> list[Via]:
    pat = re.compile(
        r"\(via\s+"
        r"\(at ([-\d.]+) ([-\d.]+)\)\s+"
        r"\(size ([-\d.]+)\)\s+"
        r"\(drill ([-\d.]+)\)\s+"
        r'\(layers "([^"]+)" "([^"]+)"\)\s+'
        r'\(net "([^"]*)"\)',
        re.S,
    )
    return [
        (float(x), float(y), net, float(size), float(drill))
        for x, y, size, drill, _lf, _lb, net in (m.groups() for m in pat.finditer(text))
    ]


def find_crossings(
    segs: Sequence[Seg],
    *,
    allow_net_pairs: set[tuple[str, str]] | None = None,
) -> list[CopperIssue]:
    """Report same-layer different-net centerline crossings."""
    allow = allow_net_pairs or set()
    issues: list[CopperIssue] = []
    for i, a in enumerate(segs):
        for b in segs[i + 1 :]:
            if a[4] == b[4] or a[6] != b[6]:
                continue
            pair = tuple(sorted((a[4], b[4])))
            if pair in allow:
                continue
            if segments_intersect((a[0], a[1], a[2], a[3]), (b[0], b[1], b[2], b[3])):
                issues.append(
                    CopperIssue(
                        "crossing",
                        f"{a[4]}/{b[4]} cross on {a[6]} near "
                        f"({a[0]:.3f},{a[1]:.3f})–({a[2]:.3f},{a[3]:.3f}) × "
                        f"({b[0]:.3f},{b[1]:.3f})–({b[2]:.3f},{b[3]:.3f})",
                    )
                )
    return issues


def find_clearance_violations(
    segs: Sequence[Seg],
    *,
    min_clearance: float,
    allow_net_pairs: set[tuple[str, str]] | None = None,
    jlc_min: float | None = None,
) -> list[CopperIssue]:
    """Edge clearance between different-net same-layer tracks."""
    allow = allow_net_pairs or set()
    issues: list[CopperIssue] = []
    for i, a in enumerate(segs):
        for b in segs[i + 1 :]:
            if a[4] == b[4] or a[6] != b[6]:
                continue
            pair = tuple(sorted((a[4], b[4])))
            if pair in allow:
                continue
            if segments_intersect((a[0], a[1], a[2], a[3]), (b[0], b[1], b[2], b[3])):
                continue  # reported as crossing
            gap = segment_edge_clearance(a, b)
            if gap < min_clearance - 1e-9:
                tag = "clearance"
                extra = ""
                if jlc_min is not None and gap < jlc_min - 1e-9:
                    extra = f" (also < JLC min {jlc_min:.3f})"
                issues.append(
                    CopperIssue(
                        tag,
                        f"{a[4]}/{b[4]} on {a[6]} edge gap {gap:.3f} mm "
                        f"< design {min_clearance:.2f} mm{extra}",
                    )
                )
    return issues


def find_via_hole_clearances(
    vias: Sequence[Via],
    pads: Sequence[Pad],
    *,
    min_hole_clearance: float,
) -> list[CopperIssue]:
    """Via drill edge vs pad copper of a different net."""
    issues: list[CopperIssue] = []
    for vx, vy, vnet, _size, drill in vias:
        hr = drill / 2
        for x0, y0, x1, y1, pnet, _layer in pads:
            if pnet == vnet:
                continue
            # Distance from via center to pad rect, then subtract hole radius.
            cx = min(max(vx, x0), x1)
            cy = min(max(vy, y0), y1)
            dist = math.hypot(vx - cx, vy - cy) - hr
            # For point inside pad, dist is negative before hole — treat as overlap.
            if vx < x0 or vx > x1 or vy < y0 or vy > y1:
                # outside: dist to edge already computed; subtract nothing more for pad edge
                gap = dist
            else:
                gap = -hr  # hole center inside foreign pad
            # Pad edge clearance from hole wall:
            if vx < x0 or vx > x1 or vy < y0 or vy > y1:
                gap = math.hypot(vx - cx, vy - cy) - hr
            else:
                # inside bbox: distance to nearest edge minus hole radius (negative = violation)
                gap = min(vx - x0, x1 - vx, vy - y0, y1 - vy) - hr
            if gap < min_hole_clearance - 1e-9:
                issues.append(
                    CopperIssue(
                        "hole_clearance",
                        f"via {vnet} hole vs pad {pnet} clearance {gap:.4f} mm "
                        f"< {min_hole_clearance:.2f} mm at ({vx:.3f},{vy:.3f})",
                    )
                )
    return issues


def find_no_net_copper(segs: Sequence[Seg], vias: Sequence[Via]) -> list[CopperIssue]:
    issues: list[CopperIssue] = []
    for s in segs:
        if not s[4]:
            issues.append(
                CopperIssue(
                    "no_net",
                    f"no-net track on {s[6]} ({s[0]:.2f},{s[1]:.2f})–({s[2]:.2f},{s[3]:.2f})",
                )
            )
    for v in vias:
        if not v[2]:
            issues.append(CopperIssue("no_net", f"no-net via at ({v[0]:.2f},{v[1]:.2f})"))
    return issues


def find_via_track_clearances(
    vias: Sequence[Via],
    segs: Sequence[Seg],
    *,
    min_clearance: float,
    jlc_min: float | None = None,
) -> list[CopperIssue]:
    """Via copper annulus vs different-net tracks on either layer."""
    issues: list[CopperIssue] = []
    for vx, vy, vnet, size, _drill in vias:
        vr = size / 2
        for x0, y0, x1, y1, snet, w, layer in segs:
            if snet == vnet:
                continue
            if layer not in ("F.Cu", "B.Cu"):
                continue
            center = _seg_point_dist(x0, y0, x1, y1, vx, vy)
            gap = center - vr - w / 2
            if gap < min_clearance - 1e-9:
                extra = ""
                if jlc_min is not None and gap < jlc_min - 1e-9:
                    extra = f" (also < JLC min {jlc_min:.3f})"
                issues.append(
                    CopperIssue(
                        "clearance",
                        f"via {vnet}/track {snet} on {layer} gap {gap:.3f} mm "
                        f"< design {min_clearance:.2f} mm{extra} at ({vx:.3f},{vy:.3f})",
                    )
                )
    return issues


def find_via_via_clearances(
    vias: Sequence[Via],
    *,
    min_clearance: float,
    min_hole_clearance: float,
) -> list[CopperIssue]:
    issues: list[CopperIssue] = []
    for i, a in enumerate(vias):
        ax, ay, anet, asize, adrill = a
        for b in vias[i + 1 :]:
            bx, by, bnet, bsize, bdrill = b
            if anet == bnet:
                continue
            d = math.hypot(ax - bx, ay - by)
            copper_gap = d - asize / 2 - bsize / 2
            hole_gap = d - adrill / 2 - bdrill / 2
            if copper_gap < min_clearance - 1e-9:
                issues.append(
                    CopperIssue(
                        "clearance",
                        f"vias {anet}/{bnet} copper gap {copper_gap:.3f} mm "
                        f"< design {min_clearance:.2f} mm",
                    )
                )
            if hole_gap < min_hole_clearance - 1e-9:
                issues.append(
                    CopperIssue(
                        "hole_clearance",
                        f"vias {anet}/{bnet} hole gap {hole_gap:.3f} mm "
                        f"< {min_hole_clearance:.2f} mm",
                    )
                )
    return issues


def check_zone_bounds(
    segs: Sequence[Seg],
    vias: Sequence[Via],
    *,
    board_w: float,
    board_h: float,
    text_zone_w: float,
    ant_left: float,
    ant_nets: set[str],
    min_clearance: float,
    feed_half_w: float,
) -> list[CopperIssue]:
    issues: list[CopperIssue] = []
    keepout = ant_left - min_clearance - feed_half_w
    for x0, y0, x1, y1, net, w, layer in segs:
        for x, y in ((x0, y0), (x1, y1)):
            if x < -1e-9 or x > board_w + 1e-9 or y < -1e-9 or y > board_h + 1e-9:
                issues.append(CopperIssue("zone", f"{net} {layer} off-board at ({x:.2f},{y:.2f})"))
        if net not in ant_nets and min(x0, x1) - w / 2 < text_zone_w - 1e-9:
            issues.append(
                CopperIssue(
                    "zone",
                    f"{net} {layer} enters text zone (x={min(x0, x1):.2f})",
                )
            )
        if net not in ant_nets and max(x0, x1) + w / 2 > keepout + 1e-9:
            issues.append(
                CopperIssue(
                    "zone",
                    f"{net} {layer} enters antenna keep-out "
                    f"(edge={max(x0, x1) + w / 2:.2f}, keep-out < {keepout:.2f})",
                )
            )
    for x, y, net, size, _drill in vias:
        if net in ant_nets:
            continue
        if x + size / 2 > keepout + 1e-9:
            issues.append(
                CopperIssue(
                    "zone",
                    f"via {net} enters antenna keep-out (x={x:.2f}, r={size / 2:.2f})",
                )
            )
        if x < text_zone_w:
            issues.append(CopperIssue("zone", f"via {net} in text zone at x={x:.2f}"))
    return issues


def check_gnd_via_connectivity(
    vias: Sequence[Via],
    segs: Sequence[Seg],
    *,
    attach_tol: float = 0.05,
) -> list[CopperIssue]:
    """Each GND via must sit on a GND track endpoint (both layers ideally)."""
    issues: list[CopperIssue] = []
    gnd_vias = [v for v in vias if v[2] == "GND"]
    gnd_segs = [s for s in segs if s[4] == "GND"]
    for vx, vy, _net, size, _drill in gnd_vias:
        layers_hit: set[str] = set()
        for x0, y0, x1, y1, _n, w, layer in gnd_segs:
            for ex, ey in ((x0, y0), (x1, y1)):
                if math.hypot(vx - ex, vy - ey) <= attach_tol + size / 2:
                    layers_hit.add(layer)
            # Also accept via center on the track body.
            if _seg_point_dist(x0, y0, x1, y1, vx, vy) <= w / 2 + attach_tol:
                layers_hit.add(layer)
        if not layers_hit:
            issues.append(
                CopperIssue(
                    "via",
                    f"GND via at ({vx:.3f},{vy:.3f}) not attached to any GND track",
                )
            )
        elif layers_hit != {"F.Cu", "B.Cu"} and len(layers_hit) == 1:
            # Through-via should stitch both layers when both have GND copper nearby.
            # Soft: only error if neither layer has copper (handled above).
            pass
    return issues


def check_geometry(
    segs: Sequence[Seg],
    vias: Sequence[Via],
    pads: Sequence[Pad],
    *,
    design_clearance: float,
    hole_clearance: float,
    jlc_min: float,
    board_w: float,
    board_h: float,
    text_zone_w: float,
    ant_left: float,
    feed_half_w: float,
    allow_net_pairs: set[tuple[str, str]] | None = None,
) -> Result[None, list[CopperIssue]]:
    allow = allow_net_pairs if allow_net_pairs is not None else {("LA", "LB")}
    issues: list[CopperIssue] = []
    issues.extend(find_no_net_copper(segs, vias))
    issues.extend(find_crossings(segs, allow_net_pairs=allow))
    issues.extend(
        find_clearance_violations(
            segs,
            min_clearance=design_clearance,
            allow_net_pairs=allow,
            jlc_min=jlc_min,
        )
    )
    issues.extend(
        find_via_track_clearances(
            vias,
            segs,
            min_clearance=design_clearance,
            jlc_min=jlc_min,
        )
    )
    issues.extend(
        find_via_via_clearances(
            vias,
            min_clearance=design_clearance,
            min_hole_clearance=hole_clearance,
        )
    )
    issues.extend(find_via_hole_clearances(vias, pads, min_hole_clearance=hole_clearance))
    issues.extend(
        check_zone_bounds(
            segs,
            vias,
            board_w=board_w,
            board_h=board_h,
            text_zone_w=text_zone_w,
            ant_left=ant_left,
            ant_nets={"LA", "LB"},
            min_clearance=design_clearance,
            feed_half_w=feed_half_w,
        )
    )
    issues.extend(check_gnd_via_connectivity(vias, segs))
    if issues:
        return Err(issues)
    return Ok(None)


def check_pcb_file(
    pcb_path: Path,
    *,
    design_clearance: float,
    hole_clearance: float,
    jlc_min: float,
    board_w: float,
    board_h: float,
    text_zone_w: float,
    ant_left: float,
    feed_half_w: float,
    pads: Sequence[Pad] = (),
) -> Result[None, list[CopperIssue]]:
    text = pcb_path.read_text(encoding="utf-8")
    segs = parse_pcb_segments(text)
    vias = parse_pcb_vias(text)
    return check_geometry(
        segs,
        vias,
        pads,
        design_clearance=design_clearance,
        hole_clearance=hole_clearance,
        jlc_min=jlc_min,
        board_w=board_w,
        board_h=board_h,
        text_zone_w=text_zone_w,
        ant_left=ant_left,
        feed_half_w=feed_half_w,
    )


def known_crossing_pairs(issues: Iterable[CopperIssue]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for issue in issues:
        if issue.kind != "crossing":
            continue
        # message starts with "LA/VOUT cross ..."
        head = issue.message.split(" ", 1)[0]
        if "/" in head:
            a, b = head.split("/", 1)
            pairs.add(tuple(sorted((a, b))))  # type: ignore[arg-type]
    return pairs
