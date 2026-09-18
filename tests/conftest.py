import io
import sys
import threading
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Isolated SQLite file + thumbnail dir; never touches the real data/."""
    thumbs = tmp_path / "thumbnails"
    thumbs.mkdir()
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "library.db")
    monkeypatch.setattr(db, "THUMB_DIR", thumbs)
    monkeypatch.setattr(db, "_local", threading.local())
    db.init_db()
    return tmp_path


def png_bytes(color="red", size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def add_indexed_file(source_id, path, slides, ext="pptx", thumbs=True):
    """Insert a file with (title, text) slides straight into the DB."""
    from app import indexer

    file_id, prior = db.upsert_file(source_id, str(path), "Dom", Path(path).stem, ext, len(slides), 1.0, 1)
    hashes = {i: indexer._content_hash(t) for i, (_, t) in enumerate(slides)}
    fav = db.carry_favorites(prior, hashes)
    for i, (title, text) in enumerate(slides):
        thumb = None
        if thumbs:
            thumb = f"{Path(path).stem}-{i}.png"
            (db.THUMB_DIR / thumb).write_bytes(png_bytes())
        db.insert_slide(file_id, i, title, text, thumb, favorite=i in fav, content_hash=hashes[i])
    return file_id
