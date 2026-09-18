"""Entry point of the packaged app (SlideLibrary.exe).

Differences from `python run.py` that packaging forces:
  * the index must live in a writable per-user folder, not next to the exe
    (a onefile exe unpacks into a temp dir that is deleted on exit);
  * a second double-click must not start a second server on the same port;
  * without a console, sys.stdout is None and uvicorn's logging would crash.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import sys
import threading
import urllib.request
from pathlib import Path

APP_NAME = "SlideLibrary"
HOST = "127.0.0.1"  # loopback only: the API can open files and register folders, never expose it
PORT = int(os.environ.get("SLIDELIB_PORT", "8420"))
URL = f"http://{HOST}:{PORT}"


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_NAME


def running_instance() -> str:
    """'ours' if a Slide Library already answers on the port, 'other' if something else
    holds it, '' if it is free."""
    try:
        with urllib.request.urlopen(f"{URL}/api/health", timeout=1.5) as resp:
            return "ours" if "libreoffice" in json.load(resp) else "other"
    except (OSError, ValueError):
        pass
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return "other" if s.connect_ex((HOST, PORT)) == 0 else ""


def ensure_streams(data_dir: Path) -> None:
    if sys.stdout is None or sys.stderr is None:  # windowed build: no console attached
        log = open(data_dir / "slide-library.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def main() -> int:
    multiprocessing.freeze_support()
    if not getattr(sys, "frozen", False):  # running from source: make `app` importable
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    data_dir = Path(os.environ.get("SLIDELIB_DATA_DIR") or user_data_dir() / "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SLIDELIB_DATA_DIR"] = str(data_dir)  # must be set before `app.db` is imported
    ensure_streams(data_dir)

    state = running_instance()
    if state == "ours":
        print(f"Slide Library is already running — opening {URL}")
        _open_browser()
        return 0
    if state == "other":
        print(f"Port {PORT} is used by another program. Set SLIDELIB_PORT to a free port and start again.")
        return 1

    import uvicorn
    from app import soffice
    from app.main import app

    print("=" * 62)
    print(f" Slide Library is running at {URL}")
    print(f" Index and saved decks: {data_dir}")
    lo = soffice.find_soffice()
    print(f" LibreOffice: {lo or 'NOT FOUND — thumbnails disabled (install it from libreoffice.org)'}")
    print(" Close this window (or press Ctrl+C) to quit.")
    print("=" * 62, flush=True)

    if not os.environ.get("SLIDELIB_NO_BROWSER"):
        threading.Timer(1.5, _open_browser).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    return 0


def _open_browser() -> None:
    import webbrowser
    webbrowser.open(URL)


if __name__ == "__main__":
    sys.exit(main())
