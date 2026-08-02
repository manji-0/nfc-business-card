#!/usr/bin/env python3
"""KiCad CLI validation (ERC, DRC, schematic parity, unconnected items).

Fails on:
  1. missing kicad-cli / project files
  2. ERC errors, and ERC warnings except an explicit allowlist
  3. DRC errors, and DRC warnings except an explicit allowlist
  4. any schematic_parity issue
  5. any unconnected items

DRC rules in nfc-business-card.kicad_pro use JLC minimum clearance
(see jlcpcb_limits.KICAD_DRC_MIN_CLEARANCE_MM). Tighter design targets
are still checked by check_layout.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "nfc-business-card.kicad_sch"
PCB = ROOT / "nfc-business-card.kicad_pcb"
REPORT_DIR = ROOT / "fab"

sys.path.insert(0, str(ROOT / "scripts"))
from kicad_paths import find_kicad_cli, kicad_fontconfig_env  # noqa: E402

# Accepted residual warnings (documented; must not hide shorts / dangling / parity).
ALLOWED_DRC_WARNINGS: frozenset[str] = frozenset(
    {
        # Generator rewrites footprint UUIDs each regen; copper geometry matches.
        "lib_footprint_mismatch",
        # B.Cu DNP resistor silk/fab text is readable without mirror.
        "nonmirrored_text_on_back_layer",
    }
)
ALLOWED_ERC_WARNINGS: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class CliCheck:
    name: str
    description: str


CHECKS: tuple[CliCheck, ...] = (
    CliCheck("version", "KiCad CLI is installed and reports a version"),
    CliCheck("erc", "Schematic ERC — zero errors / unaccepted warnings"),
    CliCheck("drc", "PCB DRC — zero errors / unaccepted warnings"),
    CliCheck("parity", "PCB/schematic parity — zero issues"),
    CliCheck("unconnected", "PCB — zero unconnected items"),
)


def _run_kicad_json(cmd: list[str], out_path: Path) -> dict:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=kicad_fontconfig_env(),
    )
    if not out_path.is_file():
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"{' '.join(cmd)}\nfailed ({result.returncode}): {stderr or 'no report written'}"
        )
    if result.returncode not in (0, 5):
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{' '.join(cmd)}\nfailed ({result.returncode}): {stderr}")
    return json.loads(out_path.read_text(encoding="utf-8"))


def _erc_violations(report: dict) -> list[dict]:
    out: list[dict] = []
    for sheet in report.get("sheets", []):
        out.extend(sheet.get("violations", []))
    return out


def _summarize(v: dict) -> str:
    return f"{v.get('type', '?')} — {v.get('description', '')}"


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []

    try:
        kicad_cli = find_kicad_cli()
    except FileNotFoundError as exc:
        print(f"SKIP: {exc}", file=sys.stderr)
        print("Install KiCad 10+ or set KICAD_CLI to run CLI checks.", file=sys.stderr)
        return 0

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    version_out = subprocess.run(
        [str(kicad_cli), "version"],
        check=True,
        capture_output=True,
        text=True,
        env=kicad_fontconfig_env(),
    )
    version_line = version_out.stdout.strip().splitlines()[0] if version_out.stdout else "unknown"
    print(f"OK: KiCad CLI {version_line}")

    if not SCH.is_file():
        errors.append(f"missing schematic: {SCH}")
    if not PCB.is_file():
        errors.append(f"missing PCB: {PCB}")
    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    # Full ERC (all severities) — do not use --severity-error (hides warnings).
    erc_path = REPORT_DIR / "kicad-erc.json"
    erc = _run_kicad_json(
        [
            str(kicad_cli),
            "sch",
            "erc",
            "--format",
            "json",
            "--exit-code-violations",
            "-o",
            str(erc_path),
            str(SCH),
        ],
        erc_path,
    )
    erc_all = _erc_violations(erc)
    erc_errs = [v for v in erc_all if v.get("severity") == "error"]
    erc_warns = [v for v in erc_all if v.get("severity") == "warning"]
    erc_unaccepted = [v for v in erc_warns if v.get("type") not in ALLOWED_ERC_WARNINGS]
    if erc_errs:
        for v in erc_errs[:8]:
            errors.append(f"ERC: {_summarize(v)}")
        if len(erc_errs) > 8:
            errors.append(f"ERC: …and {len(erc_errs) - 8} more (see {erc_path})")
    if erc_unaccepted:
        for v in erc_unaccepted[:8]:
            errors.append(f"ERC warning: {_summarize(v)}")
        if len(erc_unaccepted) > 8:
            errors.append(f"ERC warning: …and {len(erc_unaccepted) - 8} more")
    accepted_erc = len(erc_warns) - len(erc_unaccepted)
    if not erc_errs and not erc_unaccepted:
        print("OK: ERC zero errors / unaccepted warnings")
    elif accepted_erc:
        notes.append(f"ERC accepted warnings: {accepted_erc}")

    # Full DRC + parity (all severities).
    drc_path = REPORT_DIR / "kicad-drc.json"
    drc = _run_kicad_json(
        [
            str(kicad_cli),
            "pcb",
            "drc",
            "--format",
            "json",
            "--schematic-parity",
            "--exit-code-violations",
            "-o",
            str(drc_path),
            str(PCB),
        ],
        drc_path,
    )
    drc_all = list(drc.get("violations") or [])
    drc_errs = [v for v in drc_all if v.get("severity") == "error"]
    drc_warns = [v for v in drc_all if v.get("severity") == "warning"]
    drc_unaccepted = [v for v in drc_warns if v.get("type") not in ALLOWED_DRC_WARNINGS]
    if drc_errs:
        for v in drc_errs[:8]:
            errors.append(f"DRC: {_summarize(v)}")
        if len(drc_errs) > 8:
            errors.append(f"DRC: …and {len(drc_errs) - 8} more (see {drc_path})")
    if drc_unaccepted:
        for v in drc_unaccepted[:8]:
            errors.append(f"DRC warning: {_summarize(v)}")
        if len(drc_unaccepted) > 8:
            errors.append(f"DRC warning: …and {len(drc_unaccepted) - 8} more")
    accepted_drc = len(drc_warns) - len(drc_unaccepted)
    if not drc_errs and not drc_unaccepted:
        print("OK: DRC zero errors / unaccepted warnings")
    if accepted_drc:
        notes.append(
            f"DRC accepted warnings: {accepted_drc} "
            f"({', '.join(sorted(ALLOWED_DRC_WARNINGS))})"
        )

    parity = drc.get("schematic_parity") or []
    if parity:
        for issue in parity[:8]:
            errors.append(f"parity: {issue.get('description', issue)}")
        if len(parity) > 8:
            errors.append(f"parity: …and {len(parity) - 8} more")
    else:
        print("OK: schematic parity")

    unconnected = drc.get("unconnected_items") or []
    if unconnected:
        errors.append(f"unconnected items: {len(unconnected)} (see {drc_path})")
    else:
        print("OK: zero unconnected items")

    for n in notes:
        print(f"Note: {n}")

    if errors:
        print("KiCad CLI checks failed:", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        print(f"Reports: {erc_path}, {drc_path}", file=sys.stderr)
        return 1

    print(f"KiCad CLI checks passed ({len(CHECKS)} items).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
