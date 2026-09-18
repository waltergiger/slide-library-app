"""Microsoft PowerPoint engines — the first choice: slides come out exactly as
PowerPoint draws them (fonts, SmartArt, charts, effects), where LibreOffice approximates.

PowerPoint is automated through the OS scripting layer — AppleScript on macOS, COM (via a
short PowerShell script, so no extra Python dependency) on Windows. Two rules apply to both:
  * never touch the user's own session: if PowerPoint was already running, only our
    presentation is closed and the app is left alone;
  * never modify or lock the original file.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .base import Engine, RenderError

_TIMEOUT_S = 180  # large decks are slow; a blocking dialog (password, macros, permission) would otherwise hang forever

# ---------------------------------------------------------------- macOS ------

_MAC_APP_DIRS = (Path("/Applications"), Path.home() / "Applications")
_MAC_APP_NAME = "Microsoft PowerPoint.app"
_MAC_CONTAINER = Path.home() / "Library" / "Containers" / "com.microsoft.Powerpoint" / "Data"

# PowerPoint on macOS is sandboxed: it can only read/write inside its own container unless the
# user grants access file by file. So the deck is COPIED into the container, converted there, and
# the PDF moved out — which also keeps the original untouched (no lock/owner files next to it).
_APPLESCRIPT = [
    "on run argv",
    "set inPath to item 1 of argv",
    "set outPath to item 2 of argv",
    'set wasRunning to (application "Microsoft PowerPoint" is running)',
    'tell application "Microsoft PowerPoint"',
    "open POSIX file inPath",
    "set pres to active presentation",
    "try",
    # PowerPoint leaves hidden slides out of the PDF, which would shift page N away from slide N.
    # This is our private copy, so un-hiding them there is safe.
    # (Index-based on purpose: looping over `slides of pres` by reference hangs PowerPoint.)
    "repeat with i from 1 to (count of slides of pres)",
    "set hidden of slide show transition of slide i of pres to false",
    "end repeat",
    "save pres in POSIX file outPath as save as PDF",
    "on error errMsg number errNum",
    "close pres saving no",
    "error errMsg number errNum",
    "end try",
    "close pres saving no",
    "if (not wasRunning) and ((count of presentations) = 0) then quit",
    "end tell",
    "end run",
]

_mdfind_cache: tuple[float, str | None] = (0.0, None)


def mac_powerpoint_path() -> str | None:
    for base in _MAC_APP_DIRS:
        if (base / _MAC_APP_NAME).is_dir():
            return str(base / _MAC_APP_NAME)
    # Installed somewhere unusual: ask Spotlight (cached — this runs on every status check).
    global _mdfind_cache
    now = time.monotonic()
    if now - _mdfind_cache[0] > 60:
        found = None
        try:
            out = subprocess.run(["mdfind", "kMDItemCFBundleIdentifier == 'com.microsoft.Powerpoint'"],
                                 capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
            found = out[0] if out else None
        except (OSError, subprocess.TimeoutExpired):
            pass
        _mdfind_cache = (now, found)
    return _mdfind_cache[1]


class PowerPointMacEngine(Engine):
    id = "powerpoint"
    label = "Microsoft PowerPoint"

    def installed(self) -> bool:
        return mac_powerpoint_path() is not None

    def convert(self, path: Path, out_dir: Path) -> Path:
        work = _MAC_CONTAINER / "SlideLibrary" / uuid.uuid4().hex
        try:
            work.mkdir(parents=True)
            src = work / ("deck" + path.suffix.lower())  # plain ASCII name: nothing to escape in AppleScript
            out = work / "deck.pdf"
            shutil.copy2(path, src)
            self._run(src, out)
            if not out.is_file():
                raise RenderError("PowerPoint produced no PDF")
            dest = out_dir / (path.stem + ".pdf")
            shutil.move(str(out), dest)
            return dest
        except OSError as exc:
            raise RenderError(f"could not prepare {path.name} for PowerPoint: {exc}") from exc
        finally:
            shutil.rmtree(work, ignore_errors=True)

    @staticmethod
    def _run(src: Path, out: Path) -> None:
        cmd = ["osascript"] + [a for line in _APPLESCRIPT for a in ("-e", line)] + [str(src), str(out)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_S)
        except subprocess.TimeoutExpired as exc:
            raise RenderError(
                f"PowerPoint didn't finish within {_TIMEOUT_S}s — a dialog may be waiting "
                "(password, macros or a macOS permission prompt)") from exc
        except OSError as exc:
            raise RenderError(f"could not run osascript: {exc}", systemic=True) from exc
        if result.returncode == 0:
            return
        err = result.stderr.strip()
        if "-1743" in err or "not authorized" in err.lower():
            raise RenderError(
                "macOS blocked Slide Library from controlling PowerPoint. Allow it under System Settings → "
                "Privacy & Security → Automation (enable Microsoft PowerPoint for the app that runs Slide "
                "Library, e.g. Terminal), then click “Check again”.", systemic=True)
        raise RenderError(err or f"osascript exited with {result.returncode}")


# -------------------------------------------------------------- Windows ------

# Open(FileName, ReadOnly=true, Untitled=true, WithWindow=false): read-only, windowless, no lock file.
# ExportAsFixedFormat(Path, PDF, Intent=print, FrameSlides, HandoutOrder, OutputType=slides,
#                     PrintHiddenSlides=true) — hidden slides must be included to keep page N == slide N.
# Quit only if we started PowerPoint and nothing else is open in it; the user's session is never closed.
_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
$wasRunning = [bool](Get-Process POWERPNT -ErrorAction SilentlyContinue)
$app = New-Object -ComObject PowerPoint.Application
$pres = $null
try {
    $pres = $app.Presentations.Open($env:SLIDELIB_IN, -1, -1, 0)
    $pres.ExportAsFixedFormat($env:SLIDELIB_OUT, 2, 2, 0, 1, 1, -1)
} finally {
    if ($pres) { $pres.Close() }
    if (-not $wasRunning -and $app.Presentations.Count -eq 0) { $app.Quit() }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
"""
_COM_NOT_REGISTERED = "80040154"


def windows_powerpoint_installed() -> bool:
    try:
        import winreg  # Windows only
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID"):
            return True
    except (ImportError, OSError):
        return False


class PowerPointWindowsEngine(Engine):
    id = "powerpoint"
    label = "Microsoft PowerPoint"

    def installed(self) -> bool:
        return windows_powerpoint_installed()

    def convert(self, path: Path, out_dir: Path) -> Path:
        out = out_dir / (path.stem + ".pdf")
        env = {**os.environ, "SLIDELIB_IN": str(path), "SLIDELIB_OUT": str(out)}  # env vars: no quoting issues
        cmd = ["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", _POWERSHELL]
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=_TIMEOUT_S,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as exc:
            raise RenderError(
                f"PowerPoint didn't finish within {_TIMEOUT_S}s — a dialog may be waiting (password or macros)") from exc
        except OSError as exc:
            raise RenderError(f"could not run PowerShell: {exc}", systemic=True) from exc
        if result.returncode != 0:
            err = result.stderr.strip()
            if _COM_NOT_REGISTERED in err:
                raise RenderError("PowerPoint is installed but not available for automation (COM class not "
                                  "registered — the Microsoft Store edition doesn't support it).", systemic=True)
            raise RenderError(err or f"PowerShell exited with {result.returncode}")
        if not out.is_file():
            raise RenderError("PowerPoint produced no PDF")
        return out


def powerpoint_engine() -> Engine | None:
    """The PowerPoint engine for this OS, or None where PowerPoint can't run (Linux)."""
    if sys.platform == "darwin":
        return PowerPointMacEngine()
    if sys.platform.startswith("win"):
        return PowerPointWindowsEngine()
    return None
