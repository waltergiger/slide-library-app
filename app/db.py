"""SQLite storage layer for the slide library.

Everything lives in one file, data/library.db, so the whole index can be
backed up, deleted, or rebuilt by deleting that one file.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "library.db"
THUMB_DIR = DATA_DIR / "thumbnails"
THUMB_DIR.mkdir(exist_ok=True)

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',      -- pending | indexing | indexed | error
    error_message TEXT,
    files_total INTEGER NOT NULL DEFAULT 0,
    files_done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_indexed_at TEXT
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    path TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    ext TEXT NOT NULL,                            -- pptx | pdf
    slide_count INTEGER NOT NULL DEFAULT 0,
    mtime REAL NOT NULL,
    size INTEGER NOT NULL DEFAULT 0,
    indexed_at TEXT
);

CREATE TABLE IF NOT EXISTS slides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,                 -- 0-based
    title TEXT,
    body_text TEXT,
    thumb_file TEXT,
    favorite INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT,
    UNIQUE(file_id, slide_index)
);

-- Saved Builder decks. Slides are stored as references (file_id + slide_index,
-- with a title snapshot for display if the slide later disappears), never as
-- copies, so an opened draft always reflects the current library.
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,                        -- JSON: {add_dividers, chapters:[{id,name,slides:[...]}]}
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS slides_fts USING fts5(
    title, body_text, content='slides', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS slides_ai AFTER INSERT ON slides BEGIN
    INSERT INTO slides_fts(rowid, title, body_text) VALUES (new.id, new.title, new.body_text);
END;
CREATE TRIGGER IF NOT EXISTS slides_ad AFTER DELETE ON slides BEGIN
    INSERT INTO slides_fts(slides_fts, rowid, title, body_text) VALUES ('delete', old.id, old.title, old.body_text);
END;
CREATE TRIGGER IF NOT EXISTS slides_au AFTER UPDATE ON slides BEGIN
    INSERT INTO slides_fts(slides_fts, rowid, title, body_text) VALUES ('delete', old.id, old.title, old.body_text);
    INSERT INTO slides_fts(rowid, title, body_text) VALUES (new.id, new.title, new.body_text);
END;
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    """One connection per thread (FastAPI + the background indexer thread)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a user's database already existed.
    CREATE TABLE IF NOT EXISTS leaves an existing table's columns alone, so
    new columns are added here instead."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(slides)")}
    if "favorite" not in cols:
        conn.execute("ALTER TABLE slides ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    if "content_hash" not in cols:
        conn.execute("ALTER TABLE slides ADD COLUMN content_hash TEXT")
        conn.commit()


# ---- sources -----------------------------------------------------------

def add_source(path: str, domain: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sources (path, domain, status, created_at) VALUES (?, ?, 'pending', ?)",
        (path, domain, now()),
    )
    conn.commit()
    return cur.lastrowid


def list_sources() -> list[sqlite3.Row]:
    return get_conn().execute("SELECT * FROM sources ORDER BY id").fetchall()


def get_source(source_id: int) -> sqlite3.Row | None:
    return get_conn().execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()


def delete_source(source_id: int) -> None:
    conn = get_conn()
    thumbs = [
        r["thumb_file"]
        for r in conn.execute(
            """SELECT slides.thumb_file FROM slides JOIN files ON files.id = slides.file_id
               WHERE files.source_id = ? AND slides.thumb_file IS NOT NULL""",
            (source_id,),
        )
    ]
    conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    conn.commit()
    remove_thumbs(thumbs)


def set_source_status(source_id: int, status: str, error_message: str | None = None) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE sources SET status = ?, error_message = ? WHERE id = ?",
        (status, error_message, source_id),
    )
    conn.commit()


def set_source_progress(source_id: int, files_total: int, files_done: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE sources SET files_total = ?, files_done = ? WHERE id = ?",
        (files_total, files_done, source_id),
    )
    conn.commit()


def mark_source_indexed(source_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE sources SET status = 'indexed', last_indexed_at = ? WHERE id = ?",
        (now(), source_id),
    )
    conn.commit()


# ---- files / slides ------------------------------------------------------

class PriorFile:
    """What a file looked like before re-indexing replaced its slides."""

    def __init__(self, favorites: list[tuple[int, str | None]] | None = None,
                 slide_count: int = 0, thumbs: set[str] | None = None):
        self.favorites = favorites or []
        self.slide_count = slide_count
        self.thumbs = thumbs or set()


def carry_favorites(prior: PriorFile, new_hashes: dict[int, str | None]) -> set[int]:
    """Which slide indices of the re-indexed file inherit a favorite star.

    Stars follow slide *content* (text hash) so reordering or inserting slides
    doesn't move them onto the wrong slide. A star whose content no longer
    matches anything — the slide was edited in place — stays at its position,
    but only when the slide count is unchanged; otherwise a shifted deck would
    hand the star to a neighbouring slide."""
    by_hash: dict[str, list[int]] = {}
    for idx, h in new_hashes.items():
        if h:
            by_hash.setdefault(h, []).append(idx)
    result: set[int] = set()
    unmatched: list[int] = []
    for old_idx, old_hash in prior.favorites:
        free = [i for i in by_hash.get(old_hash, []) if i not in result] if old_hash else []
        if free:
            result.add(min(free, key=lambda i: abs(i - old_idx)))
        else:
            unmatched.append(old_idx)
    if prior.slide_count == len(new_hashes):
        result.update(i for i in unmatched if i in new_hashes and i not in result)
    return result


def upsert_file(source_id, path, domain, title, ext, slide_count, mtime, size) -> tuple[int, PriorFile]:
    """Returns (file_id, PriorFile). Re-indexing an existing file replaces its
    slides wholesale, so the caller uses PriorFile to re-apply favorites
    (carry_favorites) and to delete the now-stale thumbnails."""
    conn = get_conn()
    row = conn.execute("SELECT id, slide_count FROM files WHERE path = ?", (path,)).fetchone()
    if row:
        file_id = row["id"]
        old = conn.execute(
            "SELECT slide_index, favorite, content_hash, thumb_file FROM slides WHERE file_id = ?",
            (file_id,),
        ).fetchall()
        prior = PriorFile(
            favorites=[(r["slide_index"], r["content_hash"]) for r in old if r["favorite"]],
            slide_count=row["slide_count"],
            thumbs={r["thumb_file"] for r in old if r["thumb_file"]},
        )
        conn.execute(
            """UPDATE files SET domain=?, title=?, ext=?, slide_count=?, mtime=?, size=?, indexed_at=?
               WHERE id = ?""",
            (domain, title, ext, slide_count, mtime, size, now(), file_id),
        )
        conn.execute("DELETE FROM slides WHERE file_id = ?", (file_id,))
    else:
        cur = conn.execute(
            """INSERT INTO files (source_id, path, domain, title, ext, slide_count, mtime, size, indexed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_id, path, domain, title, ext, slide_count, mtime, size, now()),
        )
        file_id = cur.lastrowid
        prior = PriorFile()
    conn.commit()
    return file_id, prior


def insert_slide(file_id, slide_index, title, body_text, thumb_file, favorite=False, content_hash=None) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO slides (file_id, slide_index, title, body_text, thumb_file, favorite, content_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (file_id, slide_index, title, body_text, thumb_file, 1 if favorite else 0, content_hash),
    )
    conn.commit()


def set_slide_favorite(file_id: int, slide_index: int, favorite: bool) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "UPDATE slides SET favorite = ? WHERE file_id = ? AND slide_index = ?",
        (1 if favorite else 0, file_id, slide_index),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_files_not_in(source_id: int, keep_paths: set[str]) -> None:
    conn = get_conn()
    rows = conn.execute("SELECT id, path FROM files WHERE source_id = ?", (source_id,)).fetchall()
    stale = [r["id"] for r in rows if r["path"] not in keep_paths]
    if stale:
        marks = ",".join("?" * len(stale))
        thumbs = [
            r["thumb_file"]
            for r in conn.execute(
                f"SELECT thumb_file FROM slides WHERE thumb_file IS NOT NULL AND file_id IN ({marks})", stale
            )
        ]
        conn.executemany("DELETE FROM files WHERE id = ?", [(i,) for i in stale])
        conn.commit()
        remove_thumbs(thumbs)


def remove_thumbs(names) -> None:
    for name in names:
        try:
            (THUMB_DIR / name).unlink(missing_ok=True)
        except OSError:
            pass  # a leftover thumbnail is harmless; never fail indexing over it


def prune_orphan_thumbnails() -> int:
    """Delete thumbnails no slide references. Only safe while no indexing
    thread is running (a freshly rendered thumbnail isn't referenced until
    its slide row is inserted), so it is called at startup only."""
    used = {r["thumb_file"] for r in get_conn().execute("SELECT thumb_file FROM slides WHERE thumb_file IS NOT NULL")}
    orphans = [p.name for p in THUMB_DIR.glob("*.png") if p.name not in used]
    remove_thumbs(orphans)
    return len(orphans)


def get_file(file_id: int) -> sqlite3.Row | None:
    return get_conn().execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()


def unchanged(path: str, mtime: float, size: int) -> bool:
    row = get_conn().execute(
        "SELECT mtime, size FROM files WHERE path = ?", (path,)
    ).fetchone()
    return bool(row and abs(row["mtime"] - mtime) < 1 and row["size"] == size)


def list_domains() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT domain, COUNT(*) AS count FROM files GROUP BY domain ORDER BY domain"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"]
    out = [{"name": "All domains", "count": total}]
    out += [{"name": r["domain"], "count": r["count"]} for r in rows]
    return out


def list_decks(domain: str | None, query: str | None, favorites_only: bool = False) -> list[sqlite3.Row]:
    conn = get_conn()
    sql = "SELECT * FROM files"
    clauses, params = [], []
    if domain and domain != "All domains":
        clauses.append("domain = ?")
        params.append(domain)
    if query:
        clauses.append(
            "id IN (SELECT file_id FROM slides WHERE id IN (SELECT rowid FROM slides_fts WHERE slides_fts MATCH ?) "
            "UNION SELECT id FROM files WHERE title LIKE ? ESCAPE '\\')"
        )
        params.append(_fts_query(query))
        params.append(_like_pattern(query))
    if favorites_only:
        clauses.append("id IN (SELECT file_id FROM slides WHERE favorite = 1)")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY indexed_at DESC"
    return conn.execute(sql, params).fetchall()


def list_slides(file_id: int) -> list[sqlite3.Row]:
    return get_conn().execute(
        "SELECT * FROM slides WHERE file_id = ? ORDER BY slide_index", (file_id,)
    ).fetchall()


def get_slide(file_id: int, slide_index: int) -> sqlite3.Row | None:
    return get_conn().execute(
        "SELECT * FROM slides WHERE file_id = ? AND slide_index = ?", (file_id, slide_index)
    ).fetchone()


def _like_pattern(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _fts_query(q: str) -> str:
    # Quote each token so punctuation in the user's query can't break FTS5 syntax.
    tokens = [t for t in q.replace('"', " ").split() if t]
    return " ".join(f'"{t}"*' for t in tokens) or '""'


def search_slides(query: str, limit: int = 40) -> list[sqlite3.Row]:
    conn = get_conn()
    sql = """
        SELECT slides.*, files.title AS deck_title, files.domain AS domain, files.path AS file_path
        FROM slides_fts
        JOIN slides ON slides.id = slides_fts.rowid
        JOIN files ON files.id = slides.file_id
        WHERE slides_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    return conn.execute(sql, (_fts_query(query), limit)).fetchall()


def list_favorites(domain: str | None = None, query: str | None = None) -> list[sqlite3.Row]:
    conn = get_conn()
    clauses, params = ["slides.favorite = 1"], []
    if domain and domain != "All domains":
        clauses.append("files.domain = ?")
        params.append(domain)
    if query and query.strip():
        clauses.append(
            "(slides.id IN (SELECT rowid FROM slides_fts WHERE slides_fts MATCH ?) "
            "OR files.title LIKE ? ESCAPE '\\')"
        )
        params.append(_fts_query(query))
        params.append(_like_pattern(query))
    sql = f"""
        SELECT slides.*, files.title AS deck_title, files.domain AS domain, files.ext AS ext, files.path AS file_path
        FROM slides
        JOIN files ON files.id = slides.file_id
        WHERE {" AND ".join(clauses)}
        ORDER BY files.domain, files.title, slides.slide_index
    """
    return conn.execute(sql, params).fetchall()


# ---- drafts (saved Builder decks) ------------------------------------------

def create_draft(name: str, content: dict) -> int:
    conn = get_conn()
    ts = now()
    cur = conn.execute(
        "INSERT INTO drafts (name, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (name, json.dumps(content), ts, ts),
    )
    conn.commit()
    return cur.lastrowid


def update_draft(draft_id: int, name: str, content: dict) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "UPDATE drafts SET name = ?, content = ?, updated_at = ? WHERE id = ?",
        (name, json.dumps(content), now(), draft_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_draft(draft_id: int) -> dict | None:
    row = get_conn().execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    return _draft_dict(row) if row else None


def list_drafts() -> list[dict]:
    rows = get_conn().execute("SELECT * FROM drafts ORDER BY updated_at DESC, id DESC").fetchall()
    return [_draft_dict(r) for r in rows]


def delete_draft(draft_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
    conn.commit()
    return cur.rowcount > 0


def _draft_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "content": json.loads(row["content"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
