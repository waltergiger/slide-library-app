import fitz
import pytest
from fastapi.testclient import TestClient

from app import db, fullsize, main
from tests.conftest import add_indexed_file


def _pdf(path, pages=3):
    doc = fitz.open()
    for i in range(pages):
        doc.new_page(width=960, height=540).insert_text((72, 72), f"page {i}")
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def lib(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setattr(fullsize, "CACHE_DIR", tmp_path / "previews")
    calls = []

    def fake_convert(src, out_dir, expected_pages=None):
        calls.append(src)
        return _pdf(out_dir / "out.pdf", expected_pages or 3)

    monkeypatch.setattr(fullsize.renderers, "convert_to_pdf", fake_convert)
    sid = db.add_source(str(tmp_path), "D")
    pdf_src = _pdf(tmp_path / "deck.pdf")
    pptx_src = tmp_path / "deck.pptx"
    pptx_src.write_bytes(b"pptx")
    pdf_id = add_indexed_file(sid, str(pdf_src), [("a", "a"), ("b", "b"), ("c", "c")], ext="pdf")
    pptx_id = add_indexed_file(sid, str(pptx_src), [("a", "a"), ("b", "b"), ("c", "c")])
    return {"pdf": pdf_id, "pptx": pptx_id, "calls": calls, "tmp": tmp_path}


def _width(png: bytes) -> int:
    return fitz.Pixmap(png).width


def test_pdf_slides_render_directly_at_the_requested_width(lib):
    png = fullsize.slide_png(db.get_file(lib["pdf"]), 1, 1200)
    assert _width(png) == 1200 and lib["calls"] == []


def test_pptx_is_converted_once_and_cached(lib):
    row = db.get_file(lib["pptx"])
    fullsize.slide_png(row, 0, 800)
    fullsize.slide_png(row, 2, 800)
    assert len(lib["calls"]) == 1 and fullsize.usage()[0] == 1


def test_width_is_clamped_and_bad_index_rejected(lib):
    row = db.get_file(lib["pdf"])
    assert _width(fullsize.slide_png(row, 0, 99999)) == fullsize.MAX_WIDTH
    assert _width(fullsize.slide_png(row, 0, 1)) == fullsize.MIN_WIDTH
    with pytest.raises(IndexError):
        fullsize.slide_png(row, 3, 800)


def test_no_renderer_is_reported_not_crashing(lib, monkeypatch):
    monkeypatch.setattr(fullsize.renderers, "convert_to_pdf", lambda *a, **k: None)
    with pytest.raises(fullsize.Unavailable):
        fullsize.slide_png(db.get_file(lib["pptx"]), 0, 800)


def test_prune_drops_conversions_of_changed_or_removed_files(lib):
    fullsize.slide_png(db.get_file(lib["pptx"]), 0, 800)
    assert fullsize.prune(db.get_conn().execute("SELECT path, mtime FROM files").fetchall()) == 0
    with db.get_conn() as c:
        c.execute("UPDATE files SET mtime = mtime + 100 WHERE id = ?", (lib["pptx"],))  # edited on disk
    assert fullsize.prune(db.get_conn().execute("SELECT path, mtime FROM files").fetchall()) == 1


def test_image_endpoint(lib, monkeypatch):
    monkeypatch.setattr(main, "_start_indexing", lambda sid: None)
    with TestClient(main.app, base_url="http://127.0.0.1:8420") as client:
        r = client.get(f"/api/decks/{lib['pdf']}/slides/0/image", params={"w": 900})
        assert r.status_code == 200 and r.headers["content-type"] == "image/png" and _width(r.content) == 900
        again = client.get(f"/api/decks/{lib['pdf']}/slides/0/image", params={"w": 900},
                           headers={"If-None-Match": r.headers["etag"]})
        assert again.status_code == 304
        assert client.get(f"/api/decks/{lib['pdf']}/slides/7/image").status_code == 404
        assert client.get("/api/decks/999/slides/0/image").status_code == 404
        monkeypatch.setattr(fullsize.renderers, "convert_to_pdf", lambda *a, **k: None)
        unavailable = client.get(f"/api/decks/{lib['pptx']}/slides/0/image")
        assert unavailable.status_code == 503 and "renderer" in unavailable.json()["detail"]
