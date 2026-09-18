"""Opens a file in the user's default application (PowerPoint for .pptx,
the default PDF viewer for .pdf).

A page served from http://127.0.0.1 can't follow file:// links (browsers
block that), so "open this file" has to be done by the local server — the
same reasoning as folder_picker: the app and the browser run on the same
machine, so launching a desktop application from here is what the user
means by clicking the link.
"""
from __future__ import annotations

import os
import subprocess
import sys


class OpenFailed(Exception):
    """The OS couldn't launch a handler for the file."""


def open_file(path: str) -> None:
    if sys.platform == "darwin":
        _run(["open", path])
    elif sys.platform.startswith("win"):
        try:
            os.startfile(path)  # type: ignore[attr-defined]  # Windows-only
        except OSError as exc:
            raise OpenFailed(str(exc)) from exc
    else:
        _launch_detached(["xdg-open", path])


def _run(cmd: list[str]) -> None:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OpenFailed(str(exc)) from exc
    if result.returncode != 0:
        raise OpenFailed(result.stderr.strip() or f"{cmd[0]} exited with {result.returncode}")


def _launch_detached(cmd: list[str]) -> None:
    # xdg-open can stay alive as long as the viewer does, so don't wait for it.
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as exc:
        raise OpenFailed(str(exc)) from exc
