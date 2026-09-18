"""Locates the LibreOffice `soffice` executable.

It is a hard external dependency (it renders slide thumbnails and the image
fallback for export) but is usually NOT on PATH on Windows, so besides PATH we
look in the standard install locations. SLIDELIB_SOFFICE overrides everything
(portable installs, unusual layouts).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def candidate_paths(platform: str, env: dict[str, str]) -> list[str]:
    if platform.startswith("win"):
        roots = [env.get("ProgramFiles"), env.get("ProgramFiles(x86)"), env.get("ProgramW6432"),
                 str(Path(env["LOCALAPPDATA"]) / "Programs") if env.get("LOCALAPPDATA") else None]
        return [str(Path(r) / "LibreOffice" / "program" / "soffice.exe") for r in roots if r]
    if platform == "darwin":
        return ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    return ["/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice", "/opt/libreoffice/program/soffice",
            "/snap/bin/libreoffice.soffice"]


def find_soffice() -> str | None:
    """Path to soffice, or None. Not cached, so installing LibreOffice while the
    app runs is picked up on the next indexing run without a restart."""
    override = os.environ.get("SLIDELIB_SOFFICE")
    if override:
        return override if Path(override).is_file() else None
    on_path = shutil.which("soffice")
    if on_path:
        return on_path
    for candidate in candidate_paths(sys.platform, dict(os.environ)):
        if Path(candidate).is_file():
            return candidate
    return None
