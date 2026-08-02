#!/usr/bin/env python3
"""Component + antenna invariant checks (BOM identity, not copper routing).

Fails fast on LCSC/value mismatches so routing fixes cannot hide part errors.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_kicad_project import (  # noqa: E402
    C1_LCSC,
    GAP,
    NC_TERMINATORS,
    TEXT_ZONE_W,
    TRACE_W,
    TURNS,
    nfc_layout,
)
from jlcpcb_limits import (  # noqa: E402
    ANT_INSET_MM,
    ANTENNA_GAP_MM,
    ANTENNA_TRACE_W_MM,
    NC_TERM_R_KOHM,
    NC_TERM_R_LCSC,
)
from kamae.result import Err, Ok, Result  # noqa: E402

# Locked identities — verified against LCSC / JLCPCB parts library.
U1_MPN = "NT3H2111W0FHKH"
U1_LCSC = "C710403"
C1_VALUE = "10pF NP0"
C1_LCSC_EXPECTED = "C301961"
NC_TERM_OHMS_EXPECTED = 100_000
NC_TERM_PACKAGE = "0402"

# LCSC ID → resistance in ohms for parts we have locked or rejected.
# C25744 is Uni-Royal 0402WGF1002TCE = 10 kΩ (not 100 kΩ).
KNOWN_LCSC_RESISTOR_OHMS: dict[str, int] = {
    "C25744": 10_000,
    "C60491": 100_000,  # YAGEO RC0402FR-07100KL 100 kΩ 0402 ±1%
}


@dataclass(frozen=True, slots=True)
class AntennaSpec:
    turns: int
    trace_mm: float
    gap_mm: float
    inset_mm: float


@dataclass(frozen=True, slots=True)
class ComponentIssue:
    kind: str  # "component" | "antenna" | "bom"
    message: str


def _check_u1() -> list[ComponentIssue]:
    issues: list[ComponentIssue] = []
    pcb = (ROOT / "nfc-business-card.kicad_pcb").read_text(encoding="utf-8")
    if U1_LCSC not in pcb:
        issues.append(ComponentIssue("component", f"U1 LCSC {U1_LCSC} missing from PCB"))
    if U1_MPN not in pcb:
        issues.append(ComponentIssue("component", f"U1 MPN {U1_MPN} missing from PCB"))
    return issues


def _check_c1() -> list[ComponentIssue]:
    issues: list[ComponentIssue] = []
    if C1_LCSC != C1_LCSC_EXPECTED:
        issues.append(
            ComponentIssue(
                "component",
                f"C1 LCSC {C1_LCSC!r} != expected {C1_LCSC_EXPECTED!r}",
            )
        )
    pcb = (ROOT / "nfc-business-card.kicad_pcb").read_text(encoding="utf-8")
    if C1_LCSC not in pcb:
        issues.append(ComponentIssue("component", f"C1 LCSC {C1_LCSC} missing from PCB"))
    if '(property "Reference" "C1"' not in pcb and "(reference C1)" not in pcb:
        # KiCad 10 footprint property form
        if 'fp_text reference "C1"' not in pcb and 'property "Reference" "C1"' not in pcb:
            issues.append(ComponentIssue("component", "C1 reference missing from PCB"))
    return issues


def _check_nc_terminators() -> list[ComponentIssue]:
    issues: list[ComponentIssue] = []
    if NC_TERM_R_KOHM * 1000 != NC_TERM_OHMS_EXPECTED:
        issues.append(
            ComponentIssue(
                "component",
                f"NC_TERM_R_KOHM={NC_TERM_R_KOHM} does not equal {NC_TERM_OHMS_EXPECTED // 1000} kΩ design value",
            )
        )
    known = KNOWN_LCSC_RESISTOR_OHMS.get(NC_TERM_R_LCSC)
    if known is None:
        issues.append(
            ComponentIssue(
                "component",
                f"NC terminator LCSC {NC_TERM_R_LCSC!r} is not in the verified resistor table "
                f"(need {NC_TERM_OHMS_EXPECTED} Ω {NC_TERM_PACKAGE} ±1%)",
            )
        )
    elif known != NC_TERM_OHMS_EXPECTED:
        issues.append(
            ComponentIssue(
                "component",
                f"NC terminator LCSC {NC_TERM_R_LCSC} is {known} Ω on LCSC, "
                f"but design requires {NC_TERM_OHMS_EXPECTED} Ω "
                f"(NC_TERM_R_KOHM={NC_TERM_R_KOHM})",
            )
        )
    refs = [ref for ref, _net, _dx, _dy in NC_TERMINATORS]
    if refs != ["R2", "R4", "R3", "R5", "R6"]:
        issues.append(ComponentIssue("component", f"Unexpected NC terminator refs: {refs}"))
    pcb = (ROOT / "nfc-business-card.kicad_pcb").read_text(encoding="utf-8")
    for ref in refs:
        if f'"{ref}"' not in pcb and f" {ref} " not in pcb:
            issues.append(ComponentIssue("component", f"{ref} missing from PCB"))
    if NC_TERM_R_LCSC in pcb and known != NC_TERM_OHMS_EXPECTED:
        # Surface the identity bug even when PCB already embeds the bad LCSC.
        pass
    return issues


def _check_antenna() -> list[ComponentIssue]:
    issues: list[ComponentIssue] = []
    spec = AntennaSpec(TURNS, TRACE_W, GAP, ANT_INSET_MM)
    if spec.turns != 5:
        issues.append(ComponentIssue("antenna", f"TURNS={spec.turns} (require 5)"))
    if abs(spec.trace_mm - ANTENNA_TRACE_W_MM) > 1e-9 or abs(spec.trace_mm - 0.25) > 1e-9:
        issues.append(ComponentIssue("antenna", f"trace={spec.trace_mm} mm (require 0.25)"))
    if abs(spec.gap_mm - ANTENNA_GAP_MM) > 1e-9 or abs(spec.gap_mm - 0.30) > 1e-9:
        issues.append(ComponentIssue("antenna", f"gap={spec.gap_mm} mm (require 0.30)"))
    if spec.inset_mm < 3.0 - 1e-9:
        issues.append(ComponentIssue("antenna", f"ANT_INSET={spec.inset_mm} mm (require ≥ 3)"))
    lay = nfc_layout()
    if abs(lay["ant_w"] - 29.0) > 0.2 or abs(lay["ant_h"] - 45.0) > 0.2:
        issues.append(
            ComponentIssue(
                "antenna",
                f"spiral outer {lay['ant_w']:.1f}×{lay['ant_h']:.1f} mm (expect ~29×45)",
            )
        )
    if lay["ant_x0"] < TEXT_ZONE_W + 6.5:
        issues.append(
            ComponentIssue(
                "antenna",
                f"antenna left edge x={lay['ant_x0']:.2f} invades component strip/text zone",
            )
        )
    return issues


def _check_bom_files() -> list[ComponentIssue]:
    issues: list[ComponentIssue] = []
    bom = ROOT / "fab" / "bom.csv"
    bom_c1 = ROOT / "fab" / "bom-c1.csv"
    pos = ROOT / "fab" / "positions.csv"
    pos_c1 = ROOT / "fab" / "positions-c1.csv"

    def _rows(path: Path) -> list[dict[str, str]]:
        if not path.is_file():
            return []
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    if not bom.is_file():
        issues.append(ComponentIssue("bom", "missing fab/bom.csv"))
    else:
        rows = _rows(bom)
        refs = {r.get("Designator") for r in rows}
        if refs != {"U1"}:
            issues.append(ComponentIssue("bom", f"fab/bom.csv (C1 DNP) refs={sorted(refs)} (expect only U1)"))
        for r in rows:
            if r.get("Designator") == "U1" and r.get("LCSC Part #") != U1_LCSC:
                issues.append(ComponentIssue("bom", f"fab/bom.csv U1 LCSC {r.get('LCSC Part #')!r}"))

    if not bom_c1.is_file():
        issues.append(ComponentIssue("bom", "missing fab/bom-c1.csv"))
    else:
        rows = _rows(bom_c1)
        by_ref = {r.get("Designator"): r for r in rows}
        if set(by_ref) != {"U1", "C1"}:
            issues.append(ComponentIssue("bom", f"fab/bom-c1.csv refs={sorted(by_ref)} (expect U1+C1)"))
        c1 = by_ref.get("C1")
        if c1 is not None:
            if c1.get("LCSC Part #") != C1_LCSC_EXPECTED:
                issues.append(ComponentIssue("bom", f"fab/bom-c1.csv C1 LCSC {c1.get('LCSC Part #')!r}"))
            if "10" not in (c1.get("Value") or "") and "10pF" not in (c1.get("Value") or ""):
                issues.append(ComponentIssue("bom", f"fab/bom-c1.csv C1 value {c1.get('Value')!r}"))

    for path, allow in ((pos, {"U1"}), (pos_c1, {"U1", "C1"})):
        if not path.is_file():
            issues.append(ComponentIssue("bom", f"missing {path.relative_to(ROOT)}"))
            continue
        rows = _rows(path)
        refs = {r.get("Designator") for r in rows}
        # DNP parts must not appear in CPL.
        bad = refs - allow
        if bad:
            issues.append(
                ComponentIssue(
                    "bom",
                    f"{path.name} contains unexpected designators {sorted(bad)} (DNP leak?)",
                )
            )
        if "R2" in refs or "R3" in refs or "R4" in refs or "R5" in refs or "R6" in refs:
            issues.append(ComponentIssue("bom", f"{path.name} lists NC terminators (must stay DNP)"))
    return issues


def run_checks() -> Result[None, list[ComponentIssue]]:
    issues = (
        _check_u1()
        + _check_c1()
        + _check_nc_terminators()
        + _check_antenna()
        + _check_bom_files()
    )
    if issues:
        return Err(issues)
    return Ok(None)


def main() -> int:
    match run_checks():
        case Ok(_):
            print("OK: U1 = NT3H2111W0FHKH / C710403")
            print(f"OK: C1 candidate = {C1_VALUE} / {C1_LCSC_EXPECTED} (DNP default)")
            print(
                f"OK: R2–R6 NC terminators = {NC_TERM_OHMS_EXPECTED // 1000} kΩ "
                f"/ {NC_TERM_R_LCSC} ({NC_TERM_PACKAGE})"
            )
            print(f"OK: antenna {TURNS}T {TRACE_W}/{GAP} mm, inset ≥ {ANT_INSET_MM} mm")
            print("OK: BOM/CPL variants (C1 DNP vs C1 populated)")
            print("Component invariant checks passed.")
            return 0
        case Err(error=issues):
            print("Component / antenna invariant checks failed:", file=sys.stderr)
            for issue in issues:
                print(f"  [{issue.kind}] {issue.message}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
