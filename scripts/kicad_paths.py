#!/usr/bin/env python3
"""Locate KiCad CLI and embedded Python for pcbnew baking."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def find_kicad_cli() -> Path:
    """Return kicad-cli executable (env KICAD_CLI, PATH, or macOS app bundle)."""
    if env := os.environ.get("KICAD_CLI"):
        path = Path(env)
        if path.is_file():
            return path
        raise FileNotFoundError(f"KICAD_CLI not found: {path}")

    if found := shutil.which("kicad-cli"):
        return Path(found)

    mac = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    if mac.is_file():
        return mac

    raise FileNotFoundError(
        "kicad-cli not found. Install KiCad 10+ or set KICAD_CLI to the binary path."
    )


def find_kicad_python() -> Path:
    """Return KiCad's Python for pcbnew (env KICAD_PYTHON or macOS app bundle)."""
    if env := os.environ.get("KICAD_PYTHON"):
        path = Path(env)
        if path.is_file():
            return path
        raise FileNotFoundError(f"KICAD_PYTHON not found: {path}")

    mac = Path(
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/"
        "Versions/Current/bin/python3"
    )
    if mac.is_file():
        return mac

    if found := shutil.which("kicad-python"):
        return Path(found)

    raise FileNotFoundError(
        "KiCad Python not found. Install KiCad 10+ or set KICAD_PYTHON."
    )


def kicad_site_packages() -> Path:
    """pcbnew site-packages directory for PYTHONPATH."""
    if env := os.environ.get("KICAD_SITE"):
        return Path(env)

    # KiCad 10+ macOS: Python.framework/.../lib/python3.X/site-packages
    fw_lib = Path(
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/"
        "Python.framework/Versions/Current/lib"
    )
    if fw_lib.is_dir():
        for candidate in sorted(fw_lib.glob("python*/site-packages")):
            if candidate.is_dir():
                return candidate

    # Older KiCad macOS layout
    mac_legacy = Path(
        "/Applications/KiCad/KiCad.app/Contents/Frameworks/python/site-packages"
    )
    if mac_legacy.is_dir():
        return mac_legacy

    cli = find_kicad_cli()
    # Nix / Linux: often ../lib/kicad/lib/python3/dist-packages relative to kicad-cli
    for candidate in (
        cli.parent.parent / "lib" / "kicad" / "lib" / "python3" / "dist-packages",
        cli.parent.parent / "lib" / "python3" / "site-packages",
    ):
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "KiCad Python site-packages not found. Set KICAD_SITE if pcbnew import fails."
    )


def kicad_python_env() -> dict[str, str]:
    """Environment for subprocess calls into KiCad's Python."""
    env = os.environ.copy()
    site = str(kicad_site_packages())
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{site}{os.pathsep}{prev}" if prev else site
    return env
