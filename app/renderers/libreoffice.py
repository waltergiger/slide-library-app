"""LibreOffice (headless) engine — the fallback, and the only one on Linux."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .base import Engine, RenderError

# Without this LibreOffice silently drops hidden slides from the PDF, which shifts every
# later thumbnail by one. (JSON filter options need LibreOffice 7.4+; older versions
# fall back to the plain filter and the page-count check in the indexer catches the rest.)
_PDF_WITH_HIDDEN = 'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"true"}}'
_TIMEOUT_S = 120


def candidate_paths(platform: str, env: dict[str, str]) -> list[str]:
    if platform.startswith("win"):
        roots = [env.get("ProgramFiles"), env.get("ProgramFiles(x86)"), env.get("ProgramW6432"),
                 str(Path(env["LOCALAPPDATA"]) / "Programs") if env.get("LOCALAPPDATA") else None]
        return [str(Path(r) / "LibreOffice" / "program" / "soffice.exe") for r in roots if r]
    if platform == "darwin":
        return ["/Applications/LibreOffice.app/Contents/MacOS/soffice",
                str(Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice")]
    return ["/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice", "/opt/libreoffice/program/soffice",
            "/snap/bin/libreoffice.soffice"]


def find_soffice() -> str | None:
    """SLIDELIB_SOFFICE overrides everything; then PATH; then the standard install
    locations (LibreOffice is usually NOT on PATH on Windows). Not cached, so an
    install made while the app runs is noticed."""
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


class LibreOfficeEngine(Engine):
    id = "libreoffice"
    label = "LibreOffice"

    def installed(self) -> bool:
        return find_soffice() is not None

    def convert(self, path: Path, out_dir: Path) -> Path:
        exe = find_soffice()
        if exe is None:
            raise RenderError("LibreOffice was not found", systemic=True)
        expected = out_dir / (path.stem + ".pdf")
        # A fresh throwaway profile per run: soffice instances fight over a shared profile dir.
        for filter_name in (_PDF_WITH_HIDDEN, "pdf"):
            expected.unlink(missing_ok=True)
            self._run(exe, path, out_dir, filter_name)
            if expected.is_file():
                return expected
        raise RenderError("LibreOffice produced no PDF")

    @staticmethod
    def _run(exe: str, path: Path, out_dir: Path, filter_name: str) -> None:
        profile = out_dir / "lo_profile"
        cmd = [
            exe, "--headless", "--norestore", "--nologo", "--nofirststartwizard",
            f"-env:UserInstallation={profile.as_uri()}",  # valid file:///C:/... on Windows too
            "--convert-to", filter_name, "--outdir", str(out_dir), str(path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=_TIMEOUT_S,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as exc:
            raise RenderError(f"LibreOffice timed out after {_TIMEOUT_S}s") from exc
        except OSError as exc:
            raise RenderError(f"could not start LibreOffice: {exc}", systemic=True) from exc
