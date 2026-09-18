import io

import pytest
from fastapi.testclient import TestClient
from pptx import Presentation

from app import db, exporter, main
from tests.conftest import add_indexed_file


@pytest.fixture()
def client(tmp_db, monkeypatch):
    monkeypatch.setattr(main, "_start_indexing", lambda source_id: None)
    with TestClient(main.app, base_url="http://127.0.0.1:8420") as c:
        yield c


def _payload(file_id, name="Board deck"):
    return {
        "name": name,
        "add_dividers": False,
        "chapters": [
            {"id": "c1", "name": "Intro", "slides": [{"file_id": file_id, "slide_index": 1, "title": "old", "deck_title": "old"}]},
            {"id": "c2", "name": "Empty", "slides": []},
        ],
    }


def test_draft_crud_roundtrip_preserves_order_and_ids(client):
    fid = add_indexed_file(db.add_source("/x", "D"), "/x/a.pptx", [("s0", "a"), ("s1", "b")])
    created = client.post("/api/drafts", json=_payload(fid)).json()
    assert created["slide_count"] == 1 and created["chapter_count"] == 2

    got = client.get(f"/api/drafts/{created['id']}").json()
    assert [c["id"] for c in got["chapters"]] == ["c1", "c2"]
    slide = got["chapters"][0]["slides"][0]
    assert slide["title"] == "s1" and slide["deck_title"] == "a"  # live values, not the snapshot
    assert slide["thumb_url"] == "/api/thumb/a-1.png" and slide["missing"] is False

    changed = _payload(fid, "Renamed")
    changed["chapters"].reverse()
    assert client.put(f"/api/drafts/{created['id']}", json=changed).status_code == 200
    assert [c["id"] for c in client.get(f"/api/drafts/{created['id']}").json()["chapters"]] == ["c2", "c1"]
    assert client.get("/api/drafts").json()[0]["name"] == "Renamed"

    assert client.delete(f"/api/drafts/{created['id']}").status_code == 200
    assert client.get(f"/api/drafts/{created['id']}").status_code == 404
    assert client.delete(f"/api/drafts/{created['id']}").status_code == 404
    assert client.put(f"/api/drafts/{created['id']}", json=changed).status_code == 404


def test_blank_name_falls_back_and_list_is_newest_first(client):
    a = client.post("/api/drafts", json={"name": "  ", "chapters": []}).json()
    b = client.post("/api/drafts", json={"name": "Second", "chapters": []}).json()
    assert a["name"] == "Untitled deck"
    assert [d["id"] for d in client.get("/api/drafts").json()] == [b["id"], a["id"]]


def test_missing_slides_are_flagged_and_keep_their_snapshot(client):
    sid = db.add_source("/x", "D")
    fid = add_indexed_file(sid, "/x/a.pptx", [("s0", "a"), ("s1", "b")])
    created = client.post("/api/drafts", json=_payload(fid)).json()

    db.delete_files_not_in(sid, set())  # source file vanished
    slide = client.get(f"/api/drafts/{created['id']}").json()["chapters"][0]["slides"][0]
    assert slide["missing"] is True and slide["title"] == "old" and slide["thumb_url"] is None

    fid2 = add_indexed_file(sid, "/x/b.pptx", [("only", "x")])
    payload = _payload(fid2)  # slide_index 1 but the deck now has a single slide
    shrunk = client.post("/api/drafts", json=payload).json()
    assert client.get(f"/api/drafts/{shrunk['id']}").json()["chapters"][0]["slides"][0]["missing"] is True


def test_export_skips_missing_slides_instead_of_failing(tmp_db):
    fid = add_indexed_file(db.add_source("/x", "D"), "/x/gone.pptx", [("s", "t")], thumbs=False)
    chapters = [{"name": "C", "slides": [{"file_id": fid, "slide_index": 5}, {"file_id": 999, "slide_index": 0}]}]
    data = exporter.build_deck(chapters, add_dividers=False)
    assert len(Presentation(io.BytesIO(data)).slides) == 0


def test_draft_writes_reject_cross_origin(client):
    r = client.post("/api/drafts", json={"name": "x", "chapters": []}, headers={"origin": "https://evil.example.com"})
    assert r.status_code == 403


def test_category_is_saved_normalised_listed_and_clearable(client):
    a = client.post("/api/drafts", json={"name": "A", "category": "  Board  ", "chapters": []}).json()
    b = client.post("/api/drafts", json={"name": "B", "category": "   ", "chapters": []}).json()
    assert a["category"] == "Board" and b["category"] is None
    assert client.get(f"/api/drafts/{a['id']}").json()["category"] == "Board"

    client.put(f"/api/drafts/{a['id']}", json={"name": "A", "category": None, "chapters": []})
    assert client.get(f"/api/drafts/{a['id']}").json()["category"] is None


def test_patch_renames_and_recategorises_without_touching_slides(client):
    fid = add_indexed_file(db.add_source("/x", "D"), "/x/a.pptx", [("s0", "a"), ("s1", "b")])
    d = client.post("/api/drafts", json=_payload(fid)).json()

    r = client.patch(f"/api/drafts/{d['id']}", json={"name": "  Renamed  "})
    assert r.status_code == 200 and r.json()["name"] == "Renamed" and r.json()["slide_count"] == 1
    assert r.json()["category"] is None

    assert client.patch(f"/api/drafts/{d['id']}", json={"category": "Clients"}).json()["category"] == "Clients"
    kept = client.patch(f"/api/drafts/{d['id']}", json={"name": "Again"}).json()
    assert kept["category"] == "Clients"  # omitted field is left alone
    cleared = client.patch(f"/api/drafts/{d['id']}", json={"category": None}).json()
    assert cleared["category"] is None and cleared["name"] == "Again"

    full = client.get(f"/api/drafts/{d['id']}").json()
    assert [c["id"] for c in full["chapters"]] == ["c1", "c2"] and len(full["chapters"][0]["slides"]) == 1


def test_patch_validation_and_errors(client):
    d = client.post("/api/drafts", json={"name": "A", "chapters": []}).json()
    assert client.patch(f"/api/drafts/{d['id']}", json={"name": "   "}).status_code == 400
    assert client.patch(f"/api/drafts/{d['id']}", json={"category": "x" * 61}).status_code == 422
    assert client.patch("/api/drafts/999", json={"name": "x"}).status_code == 404
    assert client.patch("/api/drafts/999", json={}).status_code == 404
    assert client.patch(f"/api/drafts/{d['id']}", json={}).status_code == 200  # no-op
    assert client.patch(f"/api/drafts/{d['id']}", json={"name": "x"},
                        headers={"origin": "https://evil.example.com"}).status_code == 403


def test_migration_adds_category_to_existing_drafts_table(tmp_db):
    conn = db.get_conn()
    conn.executescript("DROP TABLE drafts; CREATE TABLE drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,"
                       " content TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);"
                       " INSERT INTO drafts (name, content, created_at, updated_at) VALUES ('old', '{\"chapters\": []}', 't', 't')")
    db._migrate(conn)
    assert db.get_draft(1)["category"] is None
    assert db.update_draft_meta(1, set_category=True, category="Legacy")
    assert db.get_draft(1)["category"] == "Legacy"
