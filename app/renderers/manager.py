"""Picks and runs a rendering engine: PowerPoint first, LibreOffice as the fallback.

Availability is detected per call (cheap file/registry checks), so installing an engine while
the app runs is noticed without a restart. Failures are handled per engine:
  * a bad file just falls through to the next engine;
  * a systemic failure (permission denied, broken install) or repeated consecutive
    failures switch that engine off for the session — reset() (a re-index or “Check again”)
    switches it back on.
SLIDELIB_ENGINE=powerpoint|libreoffice forces one engine (no fallback); default "auto".
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

from .base import Engine, RenderError
from .libreoffice import LibreOfficeEngine
from .powerpoint import powerpoint_engine

log = logging.getLogger("slide-library.renderers")

MAX_CONSECUTIVE_FAILURES = 3

# PowerPoint is a single shared application and soffice instances fight over their profile, so
# only one conversion runs at a time no matter which engine handles it.
_lock = threading.Lock()
_consecutive_failures: dict[str, int] = {}
_disabled: dict[str, str] = {}
_warned_none = False


def _engines() -> list[Engine]:
    engines: list[Engine] = []
    pp = powerpoint_engine()
    if pp is not None:
        engines.append(pp)
    engines.append(LibreOfficeEngine())
    forced = os.environ.get("SLIDELIB_ENGINE", "auto").strip().lower()
    if forced in ("powerpoint", "libreoffice"):
        engines = [e for e in engines if e.id == forced]
    return engines


def usable_engines() -> list[Engine]:
    return [e for e in _engines() if e.installed() and e.id not in _disabled]


def has_usable_engine() -> bool:
    return bool(usable_engines())


def reset() -> None:
    """Forget failures so every installed engine is tried again."""
    global _warned_none
    _consecutive_failures.clear()
    _disabled.clear()
    _warned_none = False


def _page_count(pdf: Path) -> int:
    import fitz  # PyMuPDF

    doc = fitz.open(str(pdf))
    try:
        return doc.page_count
    finally:
        doc.close()


def convert_to_pdf(path: Path, out_dir: Path, expected_pages: int | None = None) -> Path | None:
    """One page per slide, or None when no engine could render the file.

    With `expected_pages` (the deck's slide count) a PDF with a different page count is treated
    as that engine failing — e.g. one that dropped hidden slides — so the next engine gets a
    chance, instead of shifting every thumbnail by one."""
    global _warned_none
    with _lock:
        engines = usable_engines()
        if not engines and not _warned_none:
            log.warning("No slide renderer available (PowerPoint or LibreOffice) — slides are indexed without thumbnails.")
            _warned_none = True
        for engine in engines:
            try:
                pdf = engine.convert(path, out_dir)
                if expected_pages is not None:
                    pages = _page_count(pdf)
                    if pages != expected_pages:
                        raise RenderError(f"produced {pages} pages for {expected_pages} slides")
            except RenderError as exc:
                _record_failure(engine, exc)
                log.warning("%s could not render %s: %s", engine.label, path.name, exc)
                continue
            _consecutive_failures[engine.id] = 0
            return pdf
    return None


def _record_failure(engine: Engine, exc: RenderError) -> None:
    n = _consecutive_failures.get(engine.id, 0) + 1
    _consecutive_failures[engine.id] = n
    if exc.systemic or n >= MAX_CONSECUTIVE_FAILURES:
        _disabled[engine.id] = str(exc)
        log.warning("%s switched off for this session: %s", engine.label, exc)


def status() -> dict:
    """What the UI needs: which engines exist, which one will be used, and why one is unusable."""
    engines, active = [], None
    for e in _engines():
        installed = e.installed()
        problem = _disabled.get(e.id)
        usable = installed and problem is None
        if usable and active is None:
            active = e.id
        engines.append({"id": e.id, "label": e.label, "installed": installed, "usable": usable, "problem": problem})
    platform = "mac" if sys.platform == "darwin" else "windows" if sys.platform.startswith("win") else "linux"
    return {"platform": platform, "active": active, "engines": engines}
