from __future__ import annotations

import io
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, indexer, exporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

APP_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_DIR / "static"

log = logging.getLogger("slide-library")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    pruned = db.prune_orphan_thumbnails()  # safe here: no indexing thread exists yet
    if pruned:
        log.info("Removed %d orphaned thumbnails", pruned)
    yield


app = FastAPI(title="Slide Library", lifespan=lifespan)

# Security: the API can register arbitrary filesystem paths and open native
# dialogs, and it listens on localhost where any web page open in the same
# browser can reach it. Validating Host stops DNS-rebinding (attacker domain
# resolving to 127.0.0.1); validating Origin on state-changing requests stops
# cross-site request forgery from other tabs.
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"} | {
    h.strip().lower() for h in os.environ.get("SLIDELIB_ALLOWED_HOSTS", "").split(",") if h.strip()
}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _hostname(value: str) -> str:
    return (urlsplit("//" + value).hostname or "").lower() if value else ""


@app.middleware("http")
async def _validate_host_and_origin(request: Request, call_next):
    host = _hostname(request.headers.get("host", ""))
    if host not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Host not allowed"}, status_code=403)
    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        if origin and _hostname(urlsplit(origin).netloc) not in ALLOWED_HOSTS:
            return JSONResponse({"detail": "Cross-origin request blocked"}, status_code=403)
    return await call_next(request)


# ---------------------------------------------------------------- sources --

class SourceIn(BaseModel):
    path: str
    domain: str


def _source_dict(row) -> dict:
    return {
        "id": row["id"],
        "path": row["path"],
        "domain": row["domain"],
        "status": row["status"],
        "error_message": row["error_message"],
        "files_total": row["files_total"],
        "files_done": row["files_done"],
        "last_indexed_at": row["last_indexed_at"],
    }


@app.get("/api/sources")
def api_list_sources():
    return [_source_dict(r) for r in db.list_sources()]


@app.post("/api/sources")
def api_add_source(body: SourceIn):
    path = body.path.strip()
    domain = body.domain.strip() or "Uncategorized"
    if not path:
        raise HTTPException(400, "path is required")
    source_id = db.add_source(path, domain)
    _start_indexing(source_id)
    return _source_dict(db.get_source(source_id))


@app.post("/api/sources/{source_id}/reindex")
def api_reindex_source(source_id: int):
    if db.get_source(source_id) is None:
        raise HTTPException(404, "source not found")
    _start_indexing(source_id)
    return {"ok": True}


@app.delete("/api/sources/{source_id}")
def api_delete_source(source_id: int):
    db.delete_source(source_id)
    return {"ok": True}


def _start_indexing(source_id: int) -> None:
    t = threading.Thread(target=indexer.index_source, args=(source_id,), daemon=True)
    t.start()


# -------------------------------------------------------- native folder picker --

_browse_lock = threading.Lock()


@app.post("/api/browse-folder")
def api_browse_folder():
    """Opens a native OS folder-picker dialog and returns the chosen path.

    This app and its browser tab run on the same machine, so this is safe
    and normal for a local, single-user tool — it's the same trick behind
    every desktop app's "Choose Folder..." button, just triggered from the
    browser instead of a native window. Defined as a plain `def` (not
    `async def`) so FastAPI runs it in a worker thread and the dialog
    doesn't block the rest of the app while it's open.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            400,
            "Folder browsing needs Python's tkinter, which isn't installed here "
            "(common on Linux: `sudo apt install python3-tk`, then restart the app). "
            "You can still type or paste the folder path directly.",
        ) from exc

    with _browse_lock:  # one native dialog at a time
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                path = filedialog.askdirectory(title="Choose a slide library folder", mustexist=True)
            finally:
                root.destroy()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                400,
                f"Couldn't open a folder picker on this machine ({exc}). "
                "Type or paste the folder path directly instead.",
            ) from exc

    return {"path": path or None}


# ----------------------------------------------------------------- domains --

@app.get("/api/domains")
def api_domains():
    return db.list_domains()


# ------------------------------------------------------------------- decks --

def _deck_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "domain": row["domain"],
        "ext": row["ext"],
        "slide_count": row["slide_count"],
        "indexed_at": row["indexed_at"],
        "path": row["path"],
    }


@app.get("/api/decks")
def api_list_decks(domain: str | None = None, q: str | None = None, favorites_only: bool = False):
    return [_deck_dict(r) for r in db.list_decks(domain, q, favorites_only=favorites_only)]


@app.get("/api/decks/{file_id}")
def api_get_deck(file_id: int):
    row = db.get_file(file_id)
    if row is None:
        raise HTTPException(404, "deck not found")
    slides = db.list_slides(file_id)
    return {
        **_deck_dict(row),
        "slides": [
            {
                "index": s["slide_index"],
                "title": s["title"],
                "thumb_url": f"/api/thumb/{s['thumb_file']}" if s["thumb_file"] else None,
                "favorite": bool(s["favorite"]),
            }
            for s in slides
        ],
    }


# --------------------------------------------------------------- favorites --

class FavoriteIn(BaseModel):
    favorite: bool


@app.post("/api/decks/{file_id}/slides/{slide_index}/favorite")
def api_set_favorite(file_id: int, slide_index: int, body: FavoriteIn):
    ok = db.set_slide_favorite(file_id, slide_index, body.favorite)
    if not ok:
        raise HTTPException(404, "slide not found")
    return {"ok": True, "favorite": body.favorite}


@app.get("/api/favorites")
def api_favorites():
    rows = db.list_favorites()
    return [
        {
            "file_id": r["file_id"],
            "slide_index": r["slide_index"],
            "title": r["title"],
            "deck_title": r["deck_title"],
            "domain": r["domain"],
            "ext": r["ext"],
            "thumb_url": f"/api/thumb/{r['thumb_file']}" if r["thumb_file"] else None,
            "favorite": True,
        }
        for r in rows
    ]


# ----------------------------------------------------------------- search --

@app.get("/api/search")
def api_search(q: str):
    if not q.strip():
        return []
    rows = db.search_slides(q)
    return [
        {
            "file_id": r["file_id"],
            "slide_index": r["slide_index"],
            "title": r["title"],
            "deck_title": r["deck_title"],
            "domain": r["domain"],
            "thumb_url": f"/api/thumb/{r['thumb_file']}" if r["thumb_file"] else None,
            "favorite": bool(r["favorite"]),
        }
        for r in rows
    ]


# --------------------------------------------------------------- thumbnails --

@app.get("/api/thumb/{filename}")
def api_thumb(filename: str):
    path = db.THUMB_DIR / filename
    if ".." in filename or not path.exists():
        raise HTTPException(404, "thumbnail not found")
    return FileResponse(path, media_type="image/png")


# ------------------------------------------------------------------ export --

class SlideRef(BaseModel):
    file_id: int
    slide_index: int


class Chapter(BaseModel):
    name: str
    slides: list[SlideRef]


class ExportIn(BaseModel):
    filename: str = "New Deck.pptx"
    add_dividers: bool = True
    chapters: list[Chapter]


@app.post("/api/export")
def api_export(body: ExportIn):
    chapters = [
        {"name": c.name, "slides": [{"file_id": s.file_id, "slide_index": s.slide_index} for s in c.slides]}
        for c in body.chapters
    ]
    try:
        data = exporter.build_deck(chapters, add_dividers=body.add_dividers)
    except Exception as exc:  # noqa: BLE001
        log.getChild("export").exception("export failed")
        raise HTTPException(500, f"Export failed: {exc}") from exc

    filename = body.filename.strip() or "New Deck.pptx"
    if not filename.lower().endswith(".pptx"):
        filename += ".pptx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# -------------------------------------------------------------- static app --

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
