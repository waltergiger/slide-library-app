"""Native OS file picker, isolated in a child process for macOS safety."""
from __future__ import annotations

import subprocess
import sys

PROMPT = "Choose a PowerPoint template"
_OSASCRIPT_CANCELLED = "-128"

_TK_SCRIPT = """
import sys
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    sys.exit(3)
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
print(filedialog.askopenfilename(title=sys.argv[1], filetypes=[('PowerPoint', '*.pptx *.potx'), ('All files', '*')]) or '')
"""


class PickerUnavailable(Exception):
    pass


def pick_file(prompt: str = PROMPT) -> str | None:
    if sys.platform == "darwin":
        result = _run(["osascript", "-e", f'POSIX path of (choose file with prompt "{prompt}")'])
        if result.returncode != 0:
            if _OSASCRIPT_CANCELLED in result.stderr:
                return None
            raise PickerUnavailable(result.stderr.strip() or "file dialog failed")
        return _clean(result.stdout)
    result = _run([sys.executable, "-c", _TK_SCRIPT, prompt])
    if result.returncode == 3:
        raise PickerUnavailable("Python's tkinter isn't installed")
    if result.returncode != 0:
        raise PickerUnavailable(result.stderr.strip() or "file dialog failed")
    return _clean(result.stdout)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        raise PickerUnavailable(str(exc)) from exc


def _clean(stdout: str) -> str | None:
    path = stdout.strip()
    return path or None