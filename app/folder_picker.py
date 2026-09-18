"""Native OS folder-picker dialog, always run in a separate process.

Why a subprocess: Tk (and Cocoa) must create windows on a process's main
thread. FastAPI runs sync endpoints in worker threads, and on macOS calling
tkinter there aborts the whole server with an uncaught NSException (SIGABRT).
A child process has its own main thread, so a dialog problem can never take
the API down with it.

This app and the browser run on the same machine, so opening a dialog from
the server is safe for a local single-user tool.
"""
from __future__ import annotations

import subprocess
import sys

PROMPT = "Choose a slide library folder"

_TK_SCRIPT = """
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    sys.exit(3)
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
print(filedialog.askdirectory(title=sys.argv[1], mustexist=True) or "")
"""

_TK_MISSING = 3
_OSASCRIPT_CANCELLED = "-128"


class PickerUnavailable(Exception):
    """No folder dialog could be shown; the user should type the path."""


def pick_folder(prompt: str = PROMPT) -> str | None:
    """Returns the chosen folder, or None if the user cancelled."""
    if sys.platform == "darwin":
        return _pick_macos(prompt)
    return _pick_tk(prompt)


def _pick_macos(prompt: str) -> str | None:
    script = f'POSIX path of (choose folder with prompt "{prompt}")'
    result = _run(["osascript", "-e", script])
    if result.returncode != 0:
        if _OSASCRIPT_CANCELLED in result.stderr:
            return None
        raise PickerUnavailable(result.stderr.strip() or "osascript failed")
    return _clean(result.stdout)


def _pick_tk(prompt: str) -> str | None:
    result = _run([sys.executable, "-c", _TK_SCRIPT, prompt])
    if result.returncode == _TK_MISSING:
        raise PickerUnavailable(
            "Python's tkinter isn't installed "
            "(Linux: `sudo apt install python3-tk`, then restart the app)"
        )
    if result.returncode != 0:
        raise PickerUnavailable(result.stderr.strip() or "folder dialog failed")
    return _clean(result.stdout)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        raise PickerUnavailable(str(exc)) from exc


def _clean(stdout: str) -> str | None:
    path = stdout.strip()
    if len(path) > 1:
        path = path.rstrip("/")  # osascript appends a trailing slash
    return path or None
