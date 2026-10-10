"""Readable full-resolution slide images for the large (lightbox) view.

Thumbnails are 640 px wide — too small to read a dense slide. PDF sources are
rasterised on demand straight from the file. PowerPoint sources need a full
deck conversion (seconds, via PowerPoint/LibreOffice), so the converted PDF is
kept in data/previews/, keyed by path and modification time: the first large
view of a deck pays the conversion, every later slide of it is instant, and an
edited file gets a fresh conversion.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
from pathlib import Path

import fitz  # PyMuPDF

from . import db, renderers

CACHE_DIR = db.DATA_DIR / "previews"
MIN_WIDTH, MAX_WIDTH = 320, 2400

_guard = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}


class Unavailable(Exception):
    """The slide can't be rendered (source missing, or no renderer produced it)."""


def clamp_width(width: int) -> int:
    return max(MIN_WIDTH, min(MAX_WIDTH, int(width)))


def _prefix(path: str) -> str:
    return hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]


def _key(row) -> str:
    return f"{_prefix(row['path'])}-{int(row['mtime'])}"


def _lock_for(key: str) -> threading.Lock:
    # Two viewers opening the same deck at once must not convert it twice.
    with _guard:
        return _key_locks.setdefault(key, threading.Lock())


def cached_pdf(row) -> Path:
    target = CACHE_DIR / f"{_key(row)}.pdf"
    if target.exists():
        return target
    with _lock_for(_key(row)):
        if target.exists():
            return target
        src = Path(row["path"])
        if not src.is_file():
            raise Unavailable(f"Source file not found: {src}")
        with tempfile.TemporaryDirectory(prefix="slidelib_preview_") as tmp:
            pdf = renderers.convert_to_pdf(src, Path(tmp), row["slide_count"])
            if pdf is None:
                raise Unavailable("No slide renderer (PowerPoint or LibreOffice) could render this deck.")
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            for old in CACHE_DIR.glob(f"{_prefix(row['path'])}-*.pdf"):
                old.unlink(missing_ok=True)  # an older version of the same file
            partial = target.with_suffix(".part")
            shutil.copyfile(pdf, partial)
            os.replace(partial, target)
    return target


def slide_png(row, slide_index: int, width: int) -> bytes:
    """PNG of one slide, `width` px wide. Raises IndexError for a slide the deck doesn't have."""
    if not 0 <= slide_index < row["slide_count"]:
        raise IndexError(slide_index)
    if row["ext"] == "pdf":
        pdf = Path(row["path"])
        if not pdf.is_file():
            raise Unavailable(f"Source file not found: {pdf}")
    else:
        pdf = cached_pdf(row)
    doc = fitz.open(str(pdf))
    try:
        if slide_index >= doc.page_count:
            raise IndexError(slide_index)  # file changed on disk since it was indexed
        page = doc[slide_index]
        zoom = clamp_width(width) / page.rect.width
        return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
    finally:
        doc.close()


def prune(valid_rows) -> int:
    """Removes cached conversions of files that were removed or changed since."""
    if not CACHE_DIR.exists():
        return 0
    keep = {f"{_key(r)}.pdf" for r in valid_rows}
    removed = 0
    for p in CACHE_DIR.iterdir():
        if p.is_file() and p.name not in keep:
            p.unlink(missing_ok=True)
            removed += 1
    return removed


def usage() -> tuple[int, int]:
    files = [p for p in CACHE_DIR.iterdir() if p.is_file()] if CACHE_DIR.exists() else []
    return len(files), sum(p.stat().st_size for p in files)
