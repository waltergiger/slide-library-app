import pytest
from fastapi.testclient import TestClient

from app import db, main
from tests.conftest import add_indexed_file


@pytest.fixture()
def client(tmp_db, monkeypatch):
    monkeypatch.setattr(main, "_start_indexing", lambda source_id: None)
    with TestClient(main.app, base_url="http://127.0.0.1:8420") as c:
        yield c


def test_host_header_must_be_local(client):
    assert client.get("/api/domains").status_code == 200
    assert client.get("/api/domains", headers={"host": "evil.example.com"}).status_code == 403
    assert client.get("/api/domains", headers={"host": "localhost:8420"}).status_code == 200
    assert client.get("/api/domains", headers={"host": "[::1]:8420"}).status_code == 200


def test_cross_origin_state_changing_requests_are_blocked(client):
    body = {"path": "/tmp", "domain": "D"}
    r = client.post("/api/sources", json=body, headers={"origin": "https://evil.example.com"})
    assert r.status_code == 403
    assert client.post("/api/browse-folder", headers={"origin": "null"}).status_code == 403
    assert client.get("/api/sources").json() == []  # nothing was registered

    ok = client.post("/api/sources", json=body, headers={"origin": "http://127.0.0.1:8420"})
    assert ok.status_code == 200 and ok.json()["domain"] == "D"


def test_search_and_favorite_roundtrip(client):
    sid = db.add_source("/x", "Strategy")
    fid = add_indexed_file(sid, "/x/a.pptx", [("Wealth", "digital wealth plan")])
    hits = client.get("/api/search", params={"q": "wealth"}).json()
    assert hits[0]["file_id"] == fid and hits[0]["favorite"] is False and hits[0]["ext"] == "pptx"

    assert client.post(f"/api/decks/{fid}/slides/0/favorite", json={"favorite": True}).status_code == 200
    assert client.get("/api/favorites").json()[0]["title"] == "Wealth"
    assert client.get("/api/decks", params={"favorites_only": True}).json()[0]["id"] == fid
    assert client.post(f"/api/decks/{fid}/slides/7/favorite", json={"favorite": True}).status_code == 404


def test_thumbnail_serving_and_traversal(client):
    sid = db.add_source("/x", "S")
    add_indexed_file(sid, "/x/a.pptx", [("t", "b")])
    assert client.get("/api/thumb/a-0.png").status_code == 200
    assert client.get("/api/thumb/nope.png").status_code == 404
    assert client.get("/api/thumb/..%2Flibrary.db").status_code == 404


def test_export_with_empty_chapter_returns_valid_pptx(client):
    r = client.post("/api/export", json={"filename": "Out", "chapters": [{"name": "C", "slides": []}]})
    assert r.status_code == 200
    assert 'filename="Out.pptx"' in r.headers["content-disposition"]
    assert r.content[:2] == b"PK"


def test_browse_folder_returns_path_or_null_on_cancel(client, monkeypatch):
    from app import folder_picker

    monkeypatch.setattr(folder_picker, "pick_folder", lambda: "/Users/x/Slides")
    assert client.post("/api/browse-folder").json() == {"path": "/Users/x/Slides"}
    monkeypatch.setattr(folder_picker, "pick_folder", lambda: None)
    assert client.post("/api/browse-folder").json() == {"path": None}


def test_browse_folder_reports_unavailable_picker_as_400(client, monkeypatch):
    from app import folder_picker

    def boom():
        raise folder_picker.PickerUnavailable("no display")

    monkeypatch.setattr(folder_picker, "pick_folder", boom)
    r = client.post("/api/browse-folder")
    assert r.status_code == 400 and "type or paste" in r.json()["detail"].lower()
