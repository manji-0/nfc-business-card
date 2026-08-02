#!/usr/bin/env python3
"""KiCad CLI validation (ERC, DRC, schematic parity, unconnected items).

Recommended checks (fail on any error-level result):
  1. kicad-cli available (KiCad 10+)
  2. sch erc  — electrical rule check, errors only
  3. pcb drc  — design rule check, errors only
  4. pcb drc  — schematic parity (no PCB↔schematic mismatches)
  5. pcb drc  — zero unconnected items

DRC rules in nfc-business-card.kicad_pro are generated with JLC minimum
clearance (see jlcpcb_limits.KICAD_DRC_MIN_CLEARANCE_MM). Tighter design
targets are still checked by check_layout.py.
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


@dataclass(frozen=True, slots=True)
class CliCheck:
    name: str
    description: str


CHECKS: tuple[CliCheck, ...] = (
    CliCheck("version", "KiCad CLI is installed and reports a version"),
    CliCheck("erc", "Schematic ERC — zero errors"),
    CliCheck("drc", "PCB DRC — zero errors"),
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


def _erc_errors(report: dict) -> list[dict]:
    out: list[dict] = []
    for sheet in report.get("sheets", []):
        for v in sheet.get("violations", []):
            if v.get("severity") == "error":
                out.append(v)
    return out


def _drc_errors(report: dict) -> list[dict]:
    return [v for v in report.get("violations", []) if v.get("severity") == "error"]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

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

    erc_path = REPORT_DIR / "kicad-erc.json"
    erc = _run_kicad_json(
        [
            str(kicad_cli),
            "sch",
            "erc",
            "--format",
            "json",
            "--severity-error",
            "--exit-code-violations",
            "-o",
            str(erc_path),
            str(SCH),
        ],
        erc_path,
    )
    erc_errs = _erc_errors(erc)
    if erc_errs:
        for v in erc_errs[:8]:
            errors.append(f"ERC: {v.get('type', '?')} — {v.get('description', '')}")
        if len(erc_errs) > 8:
            errors.append(f"ERC: …and {len(erc_errs) - 8} more (see {erc_path})")
    else:
        print("OK: ERC zero errors")

    drc_path = REPORT_DIR / "kicad-drc.json"
    drc = _run_kicad_json(
        [
            str(kicad_cli),
            "pcb",
            "drc",
            "--format",
            "json",
            "--severity-error",
            "--schematic-parity",
            "--exit-code-violations",
            "-o",
            str(drc_path),
            str(PCB),
        ],
        drc_path,
    )
    drc_errs = _drc_errors(drc)
    if drc_errs:
        for v in drc_errs[:8]:
            errors.append(f"DRC: {v.get('type', '?')} — {v.get('description', '')}")
        if len(drc_errs) > 8:
            errors.append(f"DRC: …and {len(drc_errs) - 8} more (see {drc_path})")
    else:
        print("OK: DRC zero errors")

    parity = drc.get("schematic_parity") or []
    if parity:
        for issue in parity[:5]:
            errors.append(f"parity: {issue.get('description', issue)}")
        if len(parity) > 5:
            errors.append(f"parity: …and {len(parity) - 5} more")
    else:
        print("OK: schematic parity")

    unconnected = drc.get("unconnected_items") or []
    if unconnected:
        errors.append(f"unconnected items: {len(unconnected)} (see {drc_path})")
    else:
        print("OK: zero unconnected items")

    for w in warnings:
        print(f"Warning: {w}")

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
