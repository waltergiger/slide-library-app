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
from pydantic import BaseModel, Field

from . import db, drafts, exporter, file_opener, file_picker, folder_picker, indexer, renderers, settings

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


@app.get("/api/renderers")
def api_renderers():
    """Which slide renderers (PowerPoint, LibreOffice) exist on this machine and which is in use."""
    return renderers.status()


@app.post("/api/renderers/recheck")
def api_renderers_recheck():
    """Re-detect after the user installed something or fixed a permission; also re-enables engines
    that were switched off after failing."""
    renderers.reset()
    return renderers.status()


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
    """Opens a native OS folder-picker dialog and returns the chosen path
    (null if cancelled). The dialog runs in a child process — see
    folder_picker for why it must not run inside this server process."""
    with _browse_lock:  # one native dialog at a time
        try:
            path = folder_picker.pick_folder()
        except folder_picker.PickerUnavailable as exc:
            raise HTTPException(
                400,
                f"Couldn't open a folder picker on this machine ({exc}). "
                "Type or paste the folder path directly instead.",
            ) from exc
    return {"path": path}


@app.post("/api/browse-file")
def api_browse_file():
    with _browse_lock:
        try:
            path = file_picker.pick_file()
        except file_picker.PickerUnavailable as exc:
            raise HTTPException(400, f"Couldn't open a file picker ({exc}). Type or paste the path instead.") from exc
    return {"path": path}


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


@app.post("/api/decks/{file_id}/open")
def api_open_deck_file(file_id: int):
    """Opens the deck's source file in the default desktop application.

    Security: the file is looked up by its index id — a client-supplied path is
    never accepted — and must still be a supported slide file; the Host/Origin
    middleware keeps other websites from triggering it. Only a user click in
    this app reaches here, and macro-enabled files still hit PowerPoint's own
    protected-view prompt.
    """
    row = db.get_file(file_id)
    if row is None:
        raise HTTPException(404, "deck not found")
    path = Path(row["path"])
    if not path.is_absolute() or path.suffix.lower() not in indexer.SUPPORTED_EXTS:
        raise HTTPException(400, "not an indexed slide file")
    if not path.is_file():
        raise HTTPException(404, f"File not found on disk: {path} — it was moved or deleted; re-index the source.")
    try:
        file_opener.open_file(str(path))
    except file_opener.OpenFailed as exc:
        raise HTTPException(500, f"Couldn't open {path.name}: {exc}") from exc
    return {"ok": True, "path": str(path)}


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
def api_favorites(domain: str | None = None, q: str | None = None):
    rows = db.list_favorites(domain, q)
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
            "ext": r["ext"],
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
    template_path: str | None = None


@app.post("/api/export")
def api_export(body: ExportIn):
    chapters = [
        {"name": c.name, "slides": [{"file_id": s.file_id, "slide_index": s.slide_index} for s in c.slides]}
        for c in body.chapters
    ]
    try:
        template_path = body.template_path if body.template_path is not None else settings.get()["template_path"]
        if template_path:
            template_path = settings.validate_template_path(template_path)
        data = exporter.build_deck(chapters, add_dividers=body.add_dividers, template_path=template_path or None)
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


# ------------------------------------------------------------------ drafts --
# Saved Builder decks: stored server-side (SQLite) so they survive a browser
# change or cleared site data, unlike the Builder's localStorage working copy.

class DraftSlide(BaseModel):
    file_id: int
    slide_index: int
    title: str | None = None       # snapshots, only shown if the slide later disappears
    deck_title: str | None = None


class DraftChapter(BaseModel):
    id: str
    name: str
    slides: list[DraftSlide]


class DraftIn(BaseModel):
    name: str = Field(default="Untitled deck", max_length=200)
    category: str | None = Field(default=None, max_length=60)
    add_dividers: bool = True
    chapters: list[DraftChapter]


class DraftMetaIn(BaseModel):
    """Partial update: only the fields actually sent are changed."""
    name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=60)


class SettingsIn(BaseModel):
    template_path: str | None = None
    drafts_path: str | None = None


@app.get("/api/settings")
def api_get_settings():
    return settings.get()


@app.put("/api/settings")
def api_update_settings(body: SettingsIn):
    try:
        return settings.update(body.template_path, body.drafts_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _draft_content(body: DraftIn) -> dict:
    return {"add_dividers": body.add_dividers, "chapters": [c.model_dump() for c in body.chapters]}


def _draft_name(body: DraftIn) -> str:
    return body.name.strip() or "Untitled deck"


def _category(value: str | None) -> str | None:
    return (value or "").strip() or None


@app.get("/api/drafts")
def api_list_drafts():
    return [drafts.summarize(d) for d in db.list_drafts()]


@app.post("/api/drafts")
def api_create_draft(body: DraftIn):
    draft_id = db.create_draft(_draft_name(body), _draft_content(body), _category(body.category))
    draft = db.get_draft(draft_id)
    settings.persist_draft(draft)
    return drafts.summarize(draft)


@app.get("/api/drafts/{draft_id}")
def api_get_draft(draft_id: int):
    draft = db.get_draft(draft_id)
    if draft is None:
        raise HTTPException(404, "saved deck not found")
    return drafts.hydrate(draft)


@app.put("/api/drafts/{draft_id}")
def api_update_draft(draft_id: int, body: DraftIn):
    if not db.update_draft(draft_id, _draft_name(body), _draft_content(body), _category(body.category)):
        raise HTTPException(404, "saved deck not found")
    draft = db.get_draft(draft_id)
    settings.persist_draft(draft)
    return drafts.summarize(draft)


@app.patch("/api/drafts/{draft_id}")
def api_patch_draft(draft_id: int, body: DraftMetaIn):
    name = body.name.strip() if body.name is not None else None
    if name == "":
        raise HTTPException(400, "name can't be empty")
    ok = db.update_draft_meta(
        draft_id, name,
        set_category="category" in body.model_fields_set, category=_category(body.category),
    )
    if not ok:
        raise HTTPException(404, "saved deck not found")
    draft = db.get_draft(draft_id)
    settings.persist_draft(draft)
    return drafts.summarize(draft)


@app.delete("/api/drafts/{draft_id}")
def api_delete_draft(draft_id: int):
    if not db.delete_draft(draft_id):
        raise HTTPException(404, "saved deck not found")
    return {"ok": True}


# -------------------------------------------------------------- static app --

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
