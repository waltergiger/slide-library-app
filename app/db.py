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
    recursive INTEGER NOT NULL DEFAULT 1,         -- 1 = include subfolders, 0 = this folder only
    added_by TEXT,                                -- self-declared name of who added the directory
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
    indexed_at TEXT,                              -- last (re-)index; changes on every re-index
    added_at TEXT,                                -- first time the deck was indexed; never changes
    added_by TEXT                                 -- who added the source it came in with
);

CREATE TABLE IF NOT EXISTS slides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,                 -- 0-based
    title TEXT,
    body_text TEXT,
    thumb_file TEXT,
    favorite INTEGER NOT NULL DEFAULT 0,          -- legacy global star, migrated into `favorites`
    content_hash TEXT,
    favorited_at TEXT,                            -- legacy, see `favorites`
    tags TEXT NOT NULL DEFAULT '[]',              -- legacy, see `favorites`
    UNIQUE(file_id, slide_index)
);

-- Per-user stars and tags. A row survives un-starring (starred = 0) so the
-- slide's tags come back if it is starred again. Rows die with their slide;
-- re-indexing re-creates them via carry_user_favorites.
CREATE TABLE IF NOT EXISTS favorites (
    slide_id INTEGER NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
    user TEXT NOT NULL,                           -- self-declared name, see app/users.py
    starred INTEGER NOT NULL DEFAULT 1,
    favorited_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',              -- JSON array of the user's labels
    PRIMARY KEY (slide_id, user)
);
CREATE INDEX IF NOT EXISTS favorites_by_user ON favorites(user, starred);

-- Saved Builder decks. Slides are stored as references (file_id + slide_index,
-- with a title snapshot for display if the slide later disappears), never as
-- copies, so an opened draft always reflects the current library.
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,                        -- JSON: {add_dividers, chapters:[{id,name,slides:[...]}]}
    category TEXT,                                -- optional single folder-style label, NULL = uncategorized
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
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
    if "favorited_at" not in cols:
        conn.execute("ALTER TABLE slides ADD COLUMN favorited_at TEXT")
        conn.commit()
    if "tags" not in cols:
        conn.execute("ALTER TABLE slides ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
        conn.commit()
    source_cols = {row["name"] for row in conn.execute("PRAGMA table_info(sources)")}
    if "recursive" not in source_cols:
        conn.execute("ALTER TABLE sources ADD COLUMN recursive INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    if "added_by" not in source_cols:
        conn.execute("ALTER TABLE sources ADD COLUMN added_by TEXT")
        conn.commit()
    file_cols = {row["name"] for row in conn.execute("PRAGMA table_info(files)")}
    if "added_at" not in file_cols:
        conn.execute("ALTER TABLE files ADD COLUMN added_at TEXT")
        conn.execute("UPDATE files SET added_at = indexed_at")  # best available guess for existing decks
        conn.commit()
    if "added_by" not in file_cols:
        conn.execute("ALTER TABLE files ADD COLUMN added_by TEXT")
        conn.commit()
    _migrate_global_favorites(conn)
    draft_cols = {row["name"] for row in conn.execute("PRAGMA table_info(drafts)")}
    if "category" not in draft_cols:
        conn.execute("ALTER TABLE drafts ADD COLUMN category TEXT")
        conn.commit()


def _migrate_global_favorites(conn: sqlite3.Connection) -> None:
    """Stars from before per-user favorites belonged to whoever used this
    machine, so they move to the OS account name — the name a browser here
    defaults to — and are cleared on the slide so this runs once."""
    if not conn.execute("SELECT 1 FROM slides WHERE favorite = 1 LIMIT 1").fetchone():
        return
    from . import users
    conn.execute(
        """INSERT OR IGNORE INTO favorites (slide_id, user, starred, favorited_at, tags)
           SELECT id, ?, 1, favorited_at, CASE WHEN json_valid(tags) THEN tags ELSE '[]' END
           FROM slides WHERE favorite = 1""",
        (users.default_name(),),
    )
    conn.execute("UPDATE slides SET favorite = 0, favorited_at = NULL, tags = '[]' WHERE favorite = 1")
    conn.commit()


# ---- storage locations -------------------------------------------------------

def storage_info() -> dict:
    """Where this instance keeps its data, so the user can verify which
    library a running server is actually using."""
    thumbs = [p for p in THUMB_DIR.iterdir() if p.is_file()] if THUMB_DIR.exists() else []
    return {
        "data_dir": str(DATA_DIR),
        "db_path": str(DB_PATH),
        "db_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "thumbnails_dir": str(THUMB_DIR),
        "thumbnail_count": len(thumbs),
        "thumbnails_bytes": sum(p.stat().st_size for p in thumbs),
    }


# ---- settings ---------------------------------------------------------------

def get_setting(key: str, default: str = "") -> str:
    row = get_conn().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


# ---- sources -----------------------------------------------------------

def add_source(path: str, domain: str, recursive: bool = True, added_by: str | None = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sources (path, domain, recursive, added_by, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (path, domain, 1 if recursive else 0, added_by, now()),
    )
    conn.commit()
    return cur.lastrowid


def set_source_recursive(source_id: int, recursive: bool) -> bool:
    conn = get_conn()
    cur = conn.execute("UPDATE sources SET recursive = ? WHERE id = ?", (1 if recursive else 0, source_id))
    conn.commit()
    return cur.rowcount > 0


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
                 slide_count: int = 0, thumbs: set[str] | None = None,
                 meta: dict[int, FavoriteMeta] | None = None,
                 by_user: dict[str, PriorFile] | None = None):
        self.favorites = favorites or []
        self.slide_count = slide_count
        self.thumbs = thumbs or set()
        self.meta = meta or {}  # old slide_index -> what travels with its star
        self.by_user = by_user or {}  # each user's stars, matched independently


class FavoriteMeta:
    def __init__(self, favorited_at: str | None = None, tags: list[str] | None = None):
        self.favorited_at = favorited_at
        self.tags = tags or []


def carry_favorites(prior: PriorFile, new_hashes: dict[int, str | None]) -> set[int]:
    """Which slide indices of the re-indexed file inherit a favorite star."""
    return set(match_favorites(prior, new_hashes))


def carry_favorite_meta(prior: PriorFile, new_hashes: dict[int, str | None]) -> dict[int, FavoriteMeta]:
    """New slide index -> the date and tags its inherited star carries."""
    return {new: prior.meta.get(old, FavoriteMeta()) for new, old in match_favorites(prior, new_hashes).items()}


def carry_user_favorites(prior: PriorFile, new_hashes: dict[int, str | None]) -> dict[str, dict[int, FavoriteMeta]]:
    """user -> {new slide index -> date and tags}, each user's stars matched on their own."""
    return {user: carry_favorite_meta(p, new_hashes) for user, p in prior.by_user.items()}


def match_favorites(prior: PriorFile, new_hashes: dict[int, str | None]) -> dict[int, int]:
    """Maps each new slide index that inherits a star to the old index it came from.

    Stars follow slide *content* (text hash) so reordering or inserting slides
    doesn't move them onto the wrong slide. A star whose content no longer
    matches anything — the slide was edited in place — stays at its position,
    but only when the slide count is unchanged; otherwise a shifted deck would
    hand the star to a neighbouring slide."""
    by_hash: dict[str, list[int]] = {}
    for idx, h in new_hashes.items():
        if h:
            by_hash.setdefault(h, []).append(idx)
    result: dict[int, int] = {}
    unmatched: list[int] = []
    for old_idx, old_hash in prior.favorites:
        free = [i for i in by_hash.get(old_hash, []) if i not in result] if old_hash else []
        if free:
            result[min(free, key=lambda i: abs(i - old_idx))] = old_idx
        else:
            unmatched.append(old_idx)
    if prior.slide_count == len(new_hashes):
        result.update({i: i for i in unmatched if i in new_hashes and i not in result})
    return result


def upsert_file(source_id, path, domain, title, ext, slide_count, mtime, size) -> tuple[int, PriorFile]:
    """Returns (file_id, PriorFile). Re-indexing an existing file replaces its
    slides wholesale, so the caller uses PriorFile to re-apply favorites
    (carry_favorites) and to delete the now-stale thumbnails."""
    conn = get_conn()
    row = conn.execute("SELECT id, slide_count FROM files WHERE path = ?", (path,)).fetchone()
    if row:
        file_id = row["id"]
        old = conn.execute("SELECT thumb_file FROM slides WHERE file_id = ?", (file_id,)).fetchall()
        stars = conn.execute(
            """SELECT f.user, s.slide_index, s.content_hash, f.favorited_at, f.tags
               FROM favorites f JOIN slides s ON s.id = f.slide_id
               WHERE s.file_id = ? AND f.starred = 1""",
            (file_id,),
        ).fetchall()
        by_user: dict[str, PriorFile] = {}
        for r in stars:
            p = by_user.setdefault(r["user"], PriorFile(slide_count=row["slide_count"]))
            p.favorites.append((r["slide_index"], r["content_hash"]))
            p.meta[r["slide_index"]] = FavoriteMeta(r["favorited_at"], parse_tags(r["tags"]))
        prior = PriorFile(
            slide_count=row["slide_count"],
            thumbs={r["thumb_file"] for r in old if r["thumb_file"]},
            by_user=by_user,
        )
        conn.execute(
            """UPDATE files SET domain=?, title=?, ext=?, slide_count=?, mtime=?, size=?, indexed_at=?
               WHERE id = ?""",
            (domain, title, ext, slide_count, mtime, size, now(), file_id),
        )
        conn.execute("DELETE FROM slides WHERE file_id = ?", (file_id,))
    else:
        cur = conn.execute(
            """INSERT INTO files (source_id, path, domain, title, ext, slide_count, mtime, size, indexed_at,
                                  added_at, added_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, (SELECT added_by FROM sources WHERE id = ?))""",
            (source_id, path, domain, title, ext, slide_count, mtime, size, now(), now(), source_id),
        )
        file_id = cur.lastrowid
        prior = PriorFile()
    conn.commit()
    return file_id, prior


def insert_slide(file_id, slide_index, title, body_text, thumb_file, content_hash=None) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO slides (file_id, slide_index, title, body_text, thumb_file, content_hash)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (file_id, slide_index, title, body_text, thumb_file, content_hash),
    )
    conn.commit()


def restore_favorites(file_id: int, carried: dict[str, dict[int, FavoriteMeta]]) -> None:
    """Re-applies stars carried through a re-index (see carry_user_favorites)."""
    conn = get_conn()
    for user, by_index in carried.items():
        for idx, meta in by_index.items():
            conn.execute(
                """INSERT OR REPLACE INTO favorites (slide_id, user, starred, favorited_at, tags)
                   SELECT id, ?, 1, ?, ? FROM slides WHERE file_id = ? AND slide_index = ?""",
                (user, meta.favorited_at, json.dumps(meta.tags), file_id, idx),
            )
    conn.commit()


def _slide_id(file_id: int, slide_index: int) -> int | None:
    row = get_conn().execute(
        "SELECT id FROM slides WHERE file_id = ? AND slide_index = ?", (file_id, slide_index)
    ).fetchone()
    return row["id"] if row else None


def set_slide_favorite(file_id: int, slide_index: int, favorite: bool, user: str = "") -> bool:
    # Re-starring an already starred slide keeps its original date; un-starring
    # keeps the row (and its tags) so an accidental un-star is undone losslessly.
    slide_id = _slide_id(file_id, slide_index)
    if slide_id is None:
        return False
    conn = get_conn()
    if favorite:
        conn.execute(
            """INSERT INTO favorites (slide_id, user, starred, favorited_at) VALUES (?, ?, 1, ?)
               ON CONFLICT (slide_id, user) DO UPDATE SET
                   favorited_at = CASE WHEN starred = 1 THEN favorited_at ELSE excluded.favorited_at END,
                   starred = 1""",
            (slide_id, user, now()),
        )
    else:
        conn.execute("UPDATE favorites SET starred = 0, favorited_at = NULL WHERE slide_id = ? AND user = ?",
                     (slide_id, user))
    conn.commit()
    return True


def favorite_indices(file_id: int, user: str = "") -> set[int]:
    return {r["slide_index"] for r in get_conn().execute(
        """SELECT s.slide_index FROM favorites f JOIN slides s ON s.id = f.slide_id
           WHERE s.file_id = ? AND f.user = ? AND f.starred = 1""", (file_id, user))}


MAX_TAGS = 20
MAX_TAG_LEN = 40


def normalize_tags(tags: list[str]) -> list[str]:
    """Trim, collapse whitespace, drop empties and case-insensitive duplicates
    (first spelling wins), cap count and length."""
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        t = " ".join(str(t).split())[:MAX_TAG_LEN]
        if t and t.casefold() not in seen:
            seen.add(t.casefold())
            out.append(t)
    return out[:MAX_TAGS]


def parse_tags(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except ValueError:
        return []
    return [t for t in value if isinstance(t, str)] if isinstance(value, list) else []


def set_slide_tags(file_id: int, slide_index: int, tags: list[str], user: str = "") -> list[str] | None:
    """Stores the user's (normalized) tags; None if the slide doesn't exist."""
    slide_id = _slide_id(file_id, slide_index)
    if slide_id is None:
        return None
    clean = normalize_tags(tags)
    conn = get_conn()
    conn.execute(
        """INSERT INTO favorites (slide_id, user, starred, tags) VALUES (?, ?, 0, ?)
           ON CONFLICT (slide_id, user) DO UPDATE SET tags = excluded.tags""",
        (slide_id, user, json.dumps(clean)),
    )
    conn.commit()
    return clean


def list_favorite_tags(user: str = "") -> list[dict]:
    rows = get_conn().execute(
        """SELECT j.value AS name, COUNT(*) AS count
           FROM favorites f, json_each(f.tags) AS j
           WHERE f.user = ? AND f.starred = 1 AND json_valid(f.tags)
           GROUP BY j.value ORDER BY j.value COLLATE NOCASE""",
        (user,),
    ).fetchall()
    return [{"name": r["name"], "count": r["count"]} for r in rows]


# Per-user star and tags as extra columns on a `slides` row; takes the user twice.
_USER_FAV_COLS = """
    EXISTS (SELECT 1 FROM favorites f WHERE f.slide_id = slides.id AND f.user = ? AND f.starred = 1) AS is_favorite,
    (SELECT f.tags FROM favorites f WHERE f.slide_id = slides.id AND f.user = ?) AS user_tags"""


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


# The first slide's thumbnail doubles as the deck's cover image.
_COVER_SQL = ("(SELECT thumb_file FROM slides WHERE slides.file_id = files.id AND thumb_file IS NOT NULL "
              "ORDER BY slide_index LIMIT 1) AS cover_thumb")


def get_file(file_id: int) -> sqlite3.Row | None:
    return get_conn().execute(f"SELECT files.*, {_COVER_SQL} FROM files WHERE id = ?", (file_id,)).fetchone()


def unchanged(path: str, mtime: float, size: int) -> bool:
    row = get_conn().execute(
        "SELECT mtime, size FROM files WHERE path = ?", (path,)
    ).fetchone()
    return bool(row and abs(row["mtime"] - mtime) < 1 and row["size"] == size)


def has_missing_thumbnails(path: str) -> bool:
    return get_conn().execute(
        """SELECT 1 FROM slides JOIN files ON files.id = slides.file_id
           WHERE files.path = ? AND slides.thumb_file IS NULL LIMIT 1""",
        (path,),
    ).fetchone() is not None


def list_domains() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT domain, COUNT(*) AS count FROM files GROUP BY domain ORDER BY domain"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"]
    out = [{"name": "All domains", "count": total}]
    out += [{"name": r["domain"], "count": r["count"]} for r in rows]
    return out


def _sep_of(path: str) -> str:
    # Paths are stored as the OS reported them; a UNC/Windows path uses "\".
    return "\\" if "\\" in path and "/" not in path else "/"


def _split(path: str) -> list[str]:
    return [p for p in path.split(_sep_of(path)) if p]


def folder_like(folder: str) -> str:
    """LIKE pattern matching every file inside `folder` or its subfolders."""
    sep = _sep_of(folder)
    return _like_pattern_prefix(folder.rstrip(sep) + sep)


def _like_pattern_prefix(prefix: str) -> str:
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def list_folder_tree() -> list[dict]:
    """One tree per source directory, built from the indexed file paths.
    Each node counts the decks in it *and* below it, matching what selecting
    the folder shows."""
    conn = get_conn()
    trees = []
    for src in conn.execute("SELECT id, path, domain FROM sources ORDER BY path COLLATE NOCASE"):
        root_path = src["path"]
        sep = _sep_of(root_path)
        root = {"name": _split(root_path)[-1] if _split(root_path) else root_path,
                "path": root_path.rstrip(sep) or root_path, "domain": src["domain"], "count": 0, "children": {}}
        root_parts = _split(root_path)
        for f in conn.execute("SELECT path FROM files WHERE source_id = ?", (src["id"],)):
            parts = _split(f["path"])
            if parts[:len(root_parts)] != root_parts:
                continue
            node = root
            node["count"] += 1
            for name in parts[len(root_parts):-1]:  # directories between the root and the file
                child = node["children"].get(name)
                if child is None:
                    child = {"name": name, "path": node["path"] + sep + name, "count": 0, "children": {}}
                    node["children"][name] = child
                node = child
                node["count"] += 1
        trees.append(_finish_node(root))
    return trees


def _finish_node(node: dict) -> dict:
    node["children"] = [_finish_node(c) for c in sorted(node["children"].values(), key=lambda c: c["name"].casefold())]
    return node


def list_decks(domain: str | None, query: str | None, favorites_only: bool = False,
               folder: str | None = None, user: str = "") -> list[sqlite3.Row]:
    conn = get_conn()
    sql = f"SELECT files.*, {_COVER_SQL} FROM files"
    clauses, params = [], []
    if domain and domain != "All domains":
        clauses.append("domain = ?")
        params.append(domain)
    if folder:
        clauses.append("path LIKE ? ESCAPE '\\'")
        params.append(folder_like(folder))
    if query:
        clauses.append(
            "id IN (SELECT file_id FROM slides WHERE id IN (SELECT rowid FROM slides_fts WHERE slides_fts MATCH ?) "
            "UNION SELECT id FROM files WHERE title LIKE ? ESCAPE '\\')"
        )
        params.append(_fts_query(query))
        params.append(_like_pattern(query))
    if favorites_only:
        clauses.append("id IN (SELECT s.file_id FROM slides s JOIN favorites f ON f.slide_id = s.id "
                       "WHERE f.user = ? AND f.starred = 1)")
        params.append(user)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY added_at DESC, title COLLATE NOCASE"
    return conn.execute(sql, params).fetchall()


def list_slides(file_id: int, user: str = "") -> list[sqlite3.Row]:
    return get_conn().execute(
        f"SELECT slides.*, {_USER_FAV_COLS} FROM slides WHERE file_id = ? ORDER BY slide_index", (user, user, file_id)
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


def search_slides(query: str, limit: int = 40, folder: str | None = None, user: str = "") -> list[sqlite3.Row]:
    # Folder is filtered in SQL, not by the caller, so the LIMIT applies to in-folder hits only.
    conn = get_conn()
    folder_sql, params = ("AND files.path LIKE ? ESCAPE '\\'", [folder_like(folder)]) if folder else ("", [])
    sql = f"""
        SELECT slides.*, files.title AS deck_title, files.domain AS domain, files.ext AS ext, files.path AS file_path,
               {_USER_FAV_COLS}
        FROM slides_fts
        JOIN slides ON slides.id = slides_fts.rowid
        JOIN files ON files.id = slides.file_id
        WHERE slides_fts MATCH ? {folder_sql}
        ORDER BY rank
        LIMIT ?
    """
    return conn.execute(sql, (user, user, _fts_query(query), *params, limit)).fetchall()


def list_favorites(domain: str | None = None, query: str | None = None, folder: str | None = None,
                   user: str = "") -> list[sqlite3.Row]:
    conn = get_conn()
    clauses, params = ["f.starred = 1"], []
    if domain and domain != "All domains":
        clauses.append("files.domain = ?")
        params.append(domain)
    if folder:
        clauses.append("files.path LIKE ? ESCAPE '\\'")
        params.append(folder_like(folder))
    if query and query.strip():
        clauses.append(
            "(slides.id IN (SELECT rowid FROM slides_fts WHERE slides_fts MATCH ?) "
            "OR files.title LIKE ? ESCAPE '\\')"
        )
        params.append(_fts_query(query))
        params.append(_like_pattern(query))
    sql = f"""
        SELECT slides.*, files.title AS deck_title, files.domain AS domain, files.ext AS ext, files.path AS file_path,
               f.favorited_at AS fav_at, f.tags AS fav_tags
        FROM slides
        JOIN files ON files.id = slides.file_id
        JOIN favorites f ON f.slide_id = slides.id AND f.user = ?
        WHERE {" AND ".join(clauses)}
        ORDER BY files.domain, files.title, slides.slide_index
    """
    return conn.execute(sql, (user, *params)).fetchall()


# ---- drafts (saved Builder decks) ------------------------------------------

def create_draft(name: str, content: dict, category: str | None = None) -> int:
    conn = get_conn()
    ts = now()
    cur = conn.execute(
        "INSERT INTO drafts (name, content, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (name, json.dumps(content), category, ts, ts),
    )
    conn.commit()
    return cur.lastrowid


def update_draft(draft_id: int, name: str, content: dict, category: str | None = None) -> bool:
    conn = get_conn()
    cur = conn.execute(
        "UPDATE drafts SET name = ?, content = ?, category = ?, updated_at = ? WHERE id = ?",
        (name, json.dumps(content), category, now(), draft_id),
    )
    conn.commit()
    return cur.rowcount > 0


def update_draft_meta(draft_id: int, name: str | None = None, *, set_category: bool = False,
                      category: str | None = None) -> bool:
    """Rename and/or recategorise without touching the deck's slides.
    `set_category` distinguishes "clear the category" (True, None) from
    "leave it alone" (False)."""
    sets, params = [], []
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if set_category:
        sets.append("category = ?")
        params.append(category)
    if not sets:
        return get_draft(draft_id) is not None
    conn = get_conn()
    cur = conn.execute(f"UPDATE drafts SET {', '.join(sets)}, updated_at = ? WHERE id = ?", (*params, now(), draft_id))
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
        "category": row["category"],
        "content": json.loads(row["content"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
