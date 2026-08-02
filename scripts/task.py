#!/usr/bin/env python3
"""Task runner for the NFC business card generate / export pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


@dataclass(frozen=True, slots=True)
class Task:
    name: str
    description: str
    steps: tuple[str, ...]


def _python() -> str:
    venv_python = ROOT / ".venv" / "bin" / "python"
    if venv_python.is_file():
        return str(venv_python)
    return sys.executable


def _run_script(script: str) -> None:
    path = SCRIPTS / script
    if not path.is_file():
        raise FileNotFoundError(f"missing script: {path}")
    print(f"→ {script}")
    subprocess.run([_python(), str(path)], cwd=ROOT, check=True)


TASKS: dict[str, Task] = {
    "nfc-logo": Task("nfc-logo", "NFC icon silk PNG", ("make_nfc_logo.py",)),
    "back-logos": Task("back-logos", "Back 2x2 logo silk PNGs", ("make_back_logos.py",)),
    "qr-silk": Task("qr-silk", "Inverted QR silk PNG", ("make_qr_silk.py",)),
    "text-silk": Task("text-silk", "Roles + contacts silk PNGs", ("make_text_silk.py",)),
    "assets": Task(
        "assets",
        "All raster silk assets",
        ("make_nfc_logo.py", "make_back_logos.py", "make_qr_silk.py", "make_text_silk.py"),
    ),
    "project": Task("project", "KiCad project + PCB", ("generate_kicad_project.py",)),
    "preview": Task("preview", "Photoreal mockup (fab/preview.png)", ("render_preview.py",)),
    "check": Task(
        "check",
        "Component + layout + KiCad CLI checks",
        ("check_components.py", "check_layout.py", "check_kicad_cli.py"),
    ),
    "fab": Task("fab", "Gerbers, BOM, CPL, JLC zip", ("export_fab.py",)),
    "design": Task(
        "design",
        "Assets → KiCad → preview → check",
        (
            "make_nfc_logo.py",
            "make_back_logos.py",
            "make_qr_silk.py",
            "make_text_silk.py",
            "generate_kicad_project.py",
            "render_preview.py",
            "check_components.py",
            "check_layout.py",
            "check_kicad_cli.py",
        ),
    ),
    "export": Task(
        "export",
        "Full design regen then fab export",
        (
            "make_nfc_logo.py",
            "make_back_logos.py",
            "make_qr_silk.py",
            "make_text_silk.py",
            "generate_kicad_project.py",
            "render_preview.py",
            "check_components.py",
            "check_layout.py",
            "check_kicad_cli.py",
            "export_fab.py",
        ),
    ),
}


def _run_task(task: Task) -> None:
    print(f"== {task.name}: {task.description}")
    for script in task.steps:
        _run_script(script)
    print(f"== {task.name} done")


def _list_tasks() -> None:
    width = max(len(name) for name in TASKS)
    for name in sorted(TASKS):
        task = TASKS[name]
        print(f"  {name:<{width}}  {task.description}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run NFC business card pipeline tasks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  ./task export\n"
        "  ./task assets project fab\n"
        "  ./task list\n",
    )
    parser.add_argument(
        "tasks",
        nargs="*",
        metavar="TASK",
        help="task name(s) to run in order (default: export)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list available tasks and exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list:
        _list_tasks()
        return 0

    names: tuple[str, ...] = tuple(args.tasks) if args.tasks else ("export",)
    if names == ("list",):
        _list_tasks()
        return 0

    unknown = [name for name in names if name not in TASKS]
    if unknown:
        parser.error(f"unknown task(s): {', '.join(unknown)} (try --list)")

    try:
        for name in names:
            _run_task(TASKS[name])
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
