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


def test_settings_validate_and_roundtrip(client, tmp_path):
    template = tmp_path / "brand.pptx"
    from pptx import Presentation
    Presentation().save(template)
    r = client.put("/api/settings", json={"template_path": str(template), "drafts_path": str(tmp_path / "drafts")})
    assert r.status_code == 200
    assert r.json()["template_path"] == str(template)
    assert client.get("/api/settings").json()["drafts_path"] == str(tmp_path / "drafts")
    assert client.put("/api/settings", json={"template_path": str(tmp_path / "missing.pptx")}).status_code == 400


def test_browse_file_returns_path_or_null_on_cancel(client, monkeypatch):
    from app import file_picker

    monkeypatch.setattr(file_picker, "pick_file", lambda: "/Users/x/brand.potx")
    assert client.post("/api/browse-file").json() == {"path": "/Users/x/brand.potx"}
    monkeypatch.setattr(file_picker, "pick_file", lambda: None)
    assert client.post("/api/browse-file").json() == {"path": None}


def test_tags_roundtrip(client):
    sid = db.add_source("/x", "Strategy")
    fid = add_indexed_file(sid, "/x/a.pptx", [("Wealth", "digital wealth plan")])
    client.post(f"/api/decks/{fid}/slides/0/favorite", json={"favorite": True})

    r = client.put(f"/api/decks/{fid}/slides/0/tags", json={"tags": [" Board ", "board", "Q3"]})
    assert r.status_code == 200 and r.json()["tags"] == ["Board", "Q3"]
    fav = client.get("/api/favorites").json()[0]
    assert fav["tags"] == ["Board", "Q3"] and fav["favorited_at"]
    assert client.get("/api/search", params={"q": "wealth"}).json()[0]["tags"] == ["Board", "Q3"]
    assert [t["name"] for t in client.get("/api/favorites/tags").json()] == ["Board", "Q3"]

    assert client.put(f"/api/decks/{fid}/slides/5/tags", json={"tags": ["x"]}).status_code == 404
    assert client.put(f"/api/decks/{fid}/slides/0/tags", json={"tags": ["x"] * 101}).status_code == 422
    assert client.put(f"/api/decks/{fid}/slides/0/tags", json={"tags": ["x"]},
                      headers={"origin": "https://evil.example.com"}).status_code == 403


def test_add_source_with_subfolder_choice_and_change_it(client, monkeypatch):
    started = []
    monkeypatch.setattr(main, "_start_indexing", started.append)
    flat = client.post("/api/sources", json={"path": "/tmp/flat", "domain": "D", "recursive": False}).json()
    deep = client.post("/api/sources", json={"path": "/tmp/deep", "domain": "D"}).json()
    assert flat["recursive"] is False and deep["recursive"] is True

    r = client.patch(f"/api/sources/{flat['id']}", json={"recursive": True})
    assert r.status_code == 200 and r.json()["recursive"] is True
    assert started == [flat["id"], deep["id"], flat["id"]]  # scope change re-indexes
    assert client.patch("/api/sources/999", json={"recursive": True}).status_code == 404


def test_storage_endpoint_and_reveal_allow_list(client, monkeypatch):
    info = client.get("/api/storage").json()
    assert info["db_path"] == str(db.DB_PATH) and info["thumbnails_dir"] == str(db.THUMB_DIR)
    assert "drafts_dir" in info

    opened = []
    monkeypatch.setattr(main.file_opener, "open_file", opened.append)
    assert client.post("/api/storage/thumbnails/reveal").status_code == 200
    assert opened == [str(db.THUMB_DIR)]
    assert client.post("/api/storage/..%2Fetc/reveal").status_code in (404, 405)
    assert client.post("/api/storage/passwd/reveal").status_code == 404
    assert opened == [str(db.THUMB_DIR)]


def test_ui_assets_are_revalidated_so_updates_show_up(client):
    assert client.get("/app.js").headers["cache-control"] == "no-cache"
    assert client.get("/").headers["cache-control"] == "no-cache"


def test_folders_endpoint_and_folder_filters(client):
    sid = db.add_source("/lib/S", "S")
    a = add_indexed_file(sid, "/lib/S/a.pptx", [("A", "wealth")])
    b = add_indexed_file(sid, "/lib/S/sub/b.pptx", [("B", "wealth")])
    tree = client.get("/api/folders").json()
    assert tree[0]["count"] == 2 and tree[0]["children"][0]["path"] == "/lib/S/sub"
    assert [d["id"] for d in client.get("/api/decks", params={"folder": "/lib/S/sub"}).json()] == [b]
    assert [h["file_id"] for h in client.get("/api/search", params={"q": "wealth", "folder": "/lib/S/sub"}).json()] == [b]
    client.post(f"/api/decks/{a}/slides/0/favorite", json={"favorite": True})
    assert client.get("/api/favorites", params={"folder": "/lib/S/sub"}).json() == []


def test_index_page_carries_the_release_version(client, monkeypatch):
    info = main.version.build_info("v9.8.7-2-gabc1234", "0.0.0")
    monkeypatch.setattr(main.version, "get", lambda: info)
    page = client.get("/").text
    assert '<meta name="app-version" content="9.8.7+2">' in page
    assert '/app.js?v=9.8.7+2"' in page and "{{" not in page
    assert client.get("/index.html").text == page
    assert client.get("/api/version").json()["label"] == "9.8.7+2"


def test_added_by_comes_from_the_browser_name_header_sanitised(client, monkeypatch):
    monkeypatch.setattr(main, "_start_indexing", lambda sid: None)
    from urllib.parse import quote
    r = client.post("/api/sources", json={"path": "/tmp/a", "domain": "D"},
                    headers={"X-Slidelib-User": quote("  Jürg\u0007  Müller  ")})
    assert r.json()["added_by"] == "Jürg Müller"                      # decoded, control chars and extra spaces gone
    long = client.post("/api/sources", json={"path": "/tmp/b", "domain": "D"}, headers={"X-Slidelib-User": "x" * 500})
    assert len(long.json()["added_by"]) == 80
    anon = client.post("/api/sources", json={"path": "/tmp/c", "domain": "D"})
    assert anon.json()["added_by"] is None

    sid = r.json()["id"]
    fid = add_indexed_file(sid, "/tmp/a/deck.pptx", [("t", "x")])
    deck = next(d for d in client.get("/api/decks").json() if d["id"] == fid)
    assert deck["added_by"] == "Jürg Müller" and deck["added_at"] and deck["cover_url"] == "/api/thumb/deck-0.png"


def test_me_reports_header_name_and_a_default(client):
    me = client.get("/api/me", headers={"X-Slidelib-User": "Ann"}).json()
    assert me["name"] == "Ann" and me["default_name"]
