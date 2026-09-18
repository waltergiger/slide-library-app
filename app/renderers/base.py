"""Common shape of a slide rendering engine.

An engine does exactly one thing: turn a .pptx/.pptm into a PDF with ONE PAGE
PER SLIDE, hidden slides included (the app maps slide N to page N). Everything
downstream — thumbnails, the image fallback used by export — is rasterised from
that PDF with PyMuPDF, so engines stay interchangeable.
"""
from __future__ import annotations

from pathlib import Path


class RenderError(Exception):
    """A conversion failed. `systemic` means the engine itself can't work on this
    machine right now (permission denied, broken install) rather than this one
    file being bad, so it is skipped for the rest of the session instead of
    being retried — and waited on — for every remaining file."""

    def __init__(self, message: str, systemic: bool = False):
        super().__init__(message)
        self.systemic = systemic


class Engine:
    id = ""
    label = ""

    def installed(self) -> bool:
        raise NotImplementedError

    def convert(self, path: Path, out_dir: Path) -> Path:
        """Write `<out_dir>/<stem>.pdf` and return it; raise RenderError on failure."""
        raise NotImplementedError
