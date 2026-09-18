import os
import subprocess

import pytest
from fastapi.testclient import TestClient

from app import db, file_opener, main
from tests.conftest import add_indexed_file


def _proc(code=0, err=""):
    return subprocess.CompletedProcess([], code, "", err)


def test_macos_uses_open_and_reports_failure(monkeypatch):
    calls = []
    monkeypatch.setattr(file_opener.sys, "platform", "darwin")
    monkeypatch.setattr(file_opener.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or _proc())
    file_opener.open_file("/Users/x/My Deck.pptx")
    assert calls == [["open", "/Users/x/My Deck.pptx"]]  # argv list: spaces/quotes can't be reinterpreted

    monkeypatch.setattr(file_opener.subprocess, "run", lambda cmd, **kw: _proc(1, "No application knows how to open"))
    with pytest.raises(file_opener.OpenFailed, match="No application"):
        file_opener.open_file("/x.pdf")


def test_windows_uses_startfile(monkeypatch):
    opened = []
    monkeypatch.setattr(file_opener.sys, "platform", "win32")
    monkeypatch.setattr(os, "startfile", lambda p: opened.append(p), raising=False)
    file_opener.open_file(r"C:\Decks\a.pptx")
    assert opened == [r"C:\Decks\a.pptx"]

    def boom(p):
        raise OSError("no association")
    monkeypatch.setattr(os, "startfile", boom, raising=False)
    with pytest.raises(file_opener.OpenFailed):
        file_opener.open_file(r"C:\Decks\a.pptx")


def test_linux_uses_detached_xdg_open_and_missing_binary_is_a_clean_error(monkeypatch):
    seen = {}
    monkeypatch.setattr(file_opener.sys, "platform", "linux")
    monkeypatch.setattr(file_opener.subprocess, "Popen", lambda cmd, **kw: seen.update(cmd=cmd, kw=kw))
    file_opener.open_file("/srv/a.pdf")
    assert seen["cmd"] == ["xdg-open", "/srv/a.pdf"] and seen["kw"]["start_new_session"] is True

    def missing(cmd, **kw):
        raise FileNotFoundError("xdg-open")
    monkeypatch.setattr(file_opener.subprocess, "Popen", missing)
    with pytest.raises(file_opener.OpenFailed):
        file_opener.open_file("/srv/a.pdf")


@pytest.fixture()
def client(tmp_db, monkeypatch):
    monkeypatch.setattr(main, "_start_indexing", lambda source_id: None)
    with TestClient(main.app, base_url="http://127.0.0.1:8420") as c:
        yield c


@pytest.fixture()
def opened(monkeypatch):
    calls = []
    monkeypatch.setattr(file_opener, "open_file", calls.append)
    return calls


def test_open_endpoint_opens_the_indexed_file_by_id(client, opened, tmp_path):
    real = tmp_path / "Board deck.pptx"
    real.write_bytes(b"x")
    fid = add_indexed_file(db.add_source(str(tmp_path), "D"), real, [("s", "t")])
    r = client.post(f"/api/decks/{fid}/open")
    assert r.status_code == 200 and r.json()["path"] == str(real)
    assert opened == [str(real)]


def test_open_endpoint_errors(client, opened, tmp_path):
    sid = db.add_source(str(tmp_path), "D")
    assert client.post("/api/decks/999/open").status_code == 404

    ghost = add_indexed_file(sid, tmp_path / "moved.pptx", [("s", "t")])
    r = client.post(f"/api/decks/{ghost}/open")
    assert r.status_code == 404 and "moved.pptx" in r.json()["detail"]

    script = tmp_path / "evil.sh"
    script.write_text("echo hi")
    bad = add_indexed_file(sid, script, [("s", "t")])
    assert client.post(f"/api/decks/{bad}/open").status_code == 400  # only slide file types can be launched
    assert opened == []


def test_open_endpoint_surfaces_launcher_failure_and_blocks_cross_origin(client, tmp_path, monkeypatch):
    real = tmp_path / "a.pdf"
    real.write_bytes(b"%PDF")
    fid = add_indexed_file(db.add_source(str(tmp_path), "D"), real, [("s", "t")], ext="pdf")

    def fail(path):
        raise file_opener.OpenFailed("no viewer installed")
    monkeypatch.setattr(file_opener, "open_file", fail)
    r = client.post(f"/api/decks/{fid}/open")
    assert r.status_code == 500 and "no viewer installed" in r.json()["detail"]

    launched = []
    monkeypatch.setattr(file_opener, "open_file", launched.append)
    r = client.post(f"/api/decks/{fid}/open", headers={"origin": "https://evil.example.com"})
    assert r.status_code == 403 and launched == []


def test_deck_api_exposes_full_path_for_display(client, tmp_path):
    p = tmp_path / "Strategy" / "2027 Plan.pptx"
    fid = add_indexed_file(db.add_source(str(tmp_path), "D"), p, [("s", "t")])
    assert client.get("/api/decks").json()[0]["path"] == str(p)
    assert client.get(f"/api/decks/{fid}").json()["path"] == str(p)
