"""Walks a source directory, extracts text from every .pptx/.pdf, renders a
thumbnail for every slide, and writes it all into the SQLite index.

Slide rendering goes through LibreOffice (headless) + PyMuPDF:
  .pptx  ->  soffice converts it to a .pdf (one page per slide, laid out
             exactly as PowerPoint would render it) -> PyMuPDF rasterises
             each page to a PNG thumbnail.
  .pdf   ->  PyMuPDF rasterises each page directly.

soffice is not thread-safe against itself (concurrent instances fight over
the user profile dir), so every conversion goes through a single lock and
gets its own throwaway profile directory.
"""
from __future__ import annotations

import hashlib
import logging
import subprocess
import tempfile
import threading
from pathlib import Path

import fitz  # PyMuPDF
from pptx import Presentation

from . import db, soffice

log = logging.getLogger("slide-library.indexer")

SUPPORTED_EXTS = {".pptx", ".pptm", ".pdf"}
THUMB_MAX_WIDTH = 640
_soffice_lock = threading.Lock()


def discover_files(root: str) -> list[Path]:
    out = []
    for p in Path(root).rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("~$") or p.name.startswith("."):
            continue  # PowerPoint/Office lock files, hidden files
        if p.suffix.lower() in SUPPORTED_EXTS:
            out.append(p)
    return sorted(out)


def index_source(source_id: int) -> None:
    source = db.get_source(source_id)
    if source is None:
        return
    db.set_source_status(source_id, "indexing")
    try:
        root = source["path"]
        if not Path(root).exists():
            raise FileNotFoundError(f"Folder not found: {root}")
        files = discover_files(root)
        db.set_source_progress(source_id, len(files), 0)
        keep_paths = set()
        for i, path in enumerate(files):
            keep_paths.add(str(path))
            try:
                _index_one_file(source_id, source["domain"], path)
            except Exception:
                log.exception("Failed to index %s", path)
            db.set_source_progress(source_id, len(files), i + 1)
        db.delete_files_not_in(source_id, keep_paths)
        db.mark_source_indexed(source_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("Indexing failed for source %s", source_id)
        db.set_source_status(source_id, "error", str(exc))


def _index_one_file(source_id: int, domain: str, path: Path) -> None:
    stat = path.stat()
    if db.unchanged(str(path), stat.st_mtime, stat.st_size):
        return  # nothing changed since last index

    ext = path.suffix.lower()
    if ext == ".pdf":
        title, slides = _extract_pdf(path)
        thumb_paths = _render_pdf_thumbnails(path)
    else:
        title, slides = _extract_pptx(path)
        thumb_paths = _render_pptx_thumbnails(path)

    hashes = {slide["index"]: _content_hash(slide["text"]) for slide in slides}
    file_id, prior = db.upsert_file(
        source_id=source_id,
        path=str(path),
        domain=domain,
        title=title,
        ext="pdf" if ext == ".pdf" else "pptx",
        slide_count=len(slides),
        mtime=stat.st_mtime,
        size=stat.st_size,
    )
    favorites = db.carry_favorites(prior, hashes)
    for slide in slides:
        idx = slide["index"]
        thumb = thumb_paths.get(idx)
        db.insert_slide(
            file_id, idx, slide["title"], slide["text"], thumb,
            favorite=idx in favorites, content_hash=hashes[idx],
        )
    db.remove_thumbs(prior.thumbs - set(thumb_paths.values()))


def _content_hash(text: str) -> str | None:
    """None for image-only slides: identical empty text would make every such
    slide look interchangeable when re-matching favorites."""
    normalized = " ".join(text.split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest() if normalized else None


# ---- text extraction ------------------------------------------------------

def _extract_pptx(path: Path):
    prs = Presentation(str(path))
    title = _guess_deck_title(prs, path)
    slides = []
    for i, slide in enumerate(prs.slides):
        texts = []
        slide_title = None
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    texts.append(t)
                    if slide_title is None and shape == _title_shape(slide):
                        slide_title = t.splitlines()[0][:120]
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            texts.append(cell.text.strip())
        body = "\n".join(texts)
        if slide_title is None:
            slide_title = (texts[0].splitlines()[0][:120] if texts else f"Slide {i + 1}")
        slides.append({"index": i, "title": slide_title, "text": body})
    return title, slides


def _title_shape(slide):
    try:
        return slide.shapes.title
    except Exception:
        return None


def _guess_deck_title(prs: Presentation, path: Path) -> str:
    if len(prs.slides) > 0:
        first = prs.slides[0]
        shape = _title_shape(first)
        if shape is not None and shape.has_text_frame and shape.text_frame.text.strip():
            return shape.text_frame.text.strip().splitlines()[0][:200]
    return path.stem


def _extract_pdf(path: Path):
    doc = fitz.open(str(path))
    slides = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        title = text.splitlines()[0][:120] if text else f"Slide {i + 1}"
        slides.append({"index": i, "title": title, "text": text})
    title = path.stem
    doc.close()
    return title, slides


# ---- thumbnail rendering ---------------------------------------------------

def _render_pdf_thumbnails(path: Path) -> dict[int, str]:
    doc = fitz.open(str(path))
    out = {}
    for i, page in enumerate(doc):
        out[i] = _save_thumb(page, f"{path.stem}-{path.stat().st_mtime_ns}-{i}")
    doc.close()
    return out


def _render_pptx_thumbnails(path: Path) -> dict[int, str]:
    with tempfile.TemporaryDirectory(prefix="slidelib_") as tmp:
        pdf_path = _convert_to_pdf(path, Path(tmp))
        if pdf_path is None:
            return {}
        doc = fitz.open(str(pdf_path))
        out = {}
        for i, page in enumerate(doc):
            out[i] = _save_thumb(page, f"{path.stem}-{path.stat().st_mtime_ns}-{i}")
        doc.close()
        return out


_warned_no_soffice = False


def _convert_to_pdf(path: Path, out_dir: Path) -> Path | None:
    global _warned_no_soffice
    exe = soffice.find_soffice()
    if exe is None:
        if not _warned_no_soffice:
            log.warning("LibreOffice (soffice) not found — slides are indexed without thumbnails. "
                        "Install LibreOffice or set SLIDELIB_SOFFICE to its soffice executable.")
            _warned_no_soffice = True
        return None
    profile_dir = out_dir / "lo_profile"
    cmd = [
        exe, "--headless", "--norestore", "--nologo", "--nofirststartwizard",
        # as_uri() yields file:///C:/... on Windows; a hand-built file://C:\... is not a valid URL
        f"-env:UserInstallation={profile_dir.as_uri()}",
        "--convert-to", "pdf", "--outdir", str(out_dir), str(path),
    ]
    # No flashing console window when running as a windowed/packaged app on Windows.
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with _soffice_lock:
        result = subprocess.run(cmd, capture_output=True, timeout=120, creationflags=flags)
    if result.returncode != 0:
        log.warning("soffice failed for %s: %s", path, result.stderr.decode(errors="replace"))
        return None
    candidate = out_dir / (path.stem + ".pdf")
    return candidate if candidate.exists() else None


def _save_thumb(page, name: str) -> str:
    zoom = THUMB_MAX_WIDTH / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    filename = f"{name}.png"
    pix.save(str(db.THUMB_DIR / filename))
    return filename


class PdfRenderCache:
    """Converts each source .pptx to PDF at most once for the lifetime of the
    context. An export that falls back to images for several slides of the
    same deck would otherwise re-run a full soffice conversion per slide."""

    def __init__(self):
        self._tmp: tempfile.TemporaryDirectory | None = None
        self._pdfs: dict[str, Path] = {}

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="slidelib_export_")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def pdf_for(self, path: Path) -> Path:
        key = str(path)
        if key not in self._pdfs:
            out_dir = Path(self._tmp.name) / str(len(self._pdfs))
            out_dir.mkdir()
            pdf = _convert_to_pdf(path, out_dir)
            if pdf is None:
                hint = " LibreOffice was not found — install it (or set SLIDELIB_SOFFICE)." if soffice.find_soffice() is None else ""
                raise RuntimeError(f"Could not render {path} for export.{hint}")
            self._pdfs[key] = pdf
        return self._pdfs[key]


def _page_png(pdf_path: Path, slide_index: int, target_width_px: int) -> bytes:
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[slide_index]
        zoom = target_width_px / page.rect.width
        return page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
    finally:
        doc.close()


def render_full_size(file_path: str, ext: str, slide_index: int, target_width_px: int,
                     cache: PdfRenderCache | None = None) -> bytes:
    """Render one slide at export quality (used by the exporter for
    image-pasted slides), returning PNG bytes."""
    path = Path(file_path)
    if ext == "pdf":
        return _page_png(path, slide_index, target_width_px)
    if cache is not None:
        return _page_png(cache.pdf_for(path), slide_index, target_width_px)
    with PdfRenderCache() as tmp_cache:
        return _page_png(tmp_cache.pdf_for(path), slide_index, target_width_px)
