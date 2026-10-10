from app import db
from tests.conftest import add_indexed_file


def test_fts_query_quotes_tokens_and_survives_punctuation():
    assert db._fts_query('foo "bar" AND') == '"foo"* "bar"* "AND"*'
    assert db._fts_query("   ") == '""'


def test_search_prefix_and_special_chars(tmp_db):
    sid = db.add_source("/x", "Dom")
    add_indexed_file(sid, "/x/a.pptx", [("Digital Wealth", "Wealth strategy 2027 (draft)")])
    assert len(db.search_slides("wealt")) == 1
    assert db.search_slides('") OR ("') == []  # no FTS syntax error


def test_like_wildcards_in_query_are_literal(tmp_db):
    sid = db.add_source("/x", "Dom")
    add_indexed_file(sid, "/x/a.pptx", [("t", "body")])
    add_indexed_file(sid, "/x/b_c.pptx", [("t", "body")])
    assert [r["title"] for r in db.list_decks(None, "%")] == []
    assert [r["title"] for r in db.list_decks(None, "b_c")] == ["b_c"]
    assert db.list_decks(None, "_") != []  # '_' matches only the literal underscore
    assert [r["title"] for r in db.list_decks(None, "_")] == ["b_c"]


class TestCarryFavorites:
    def carry(self, favs, old_count, hashes):
        return db.carry_favorites(db.PriorFile(favs, old_count), hashes)

    def test_follows_content_when_slides_reordered(self):
        assert self.carry([(0, "A")], 3, {0: "B", 1: "C", 2: "A"}) == {2}

    def test_follows_content_when_slide_inserted(self):
        assert self.carry([(1, "B")], 2, {0: "X", 1: "A", 2: "B"}) == {2}

    def test_edited_in_place_keeps_position_when_count_unchanged(self):
        assert self.carry([(1, "B")], 3, {0: "A", 1: "B2", 2: "C"}) == {1}

    def test_edited_slide_with_shifted_count_is_dropped(self):
        assert self.carry([(1, "B")], 3, {0: "A", 1: "C"}) == set()

    def test_deleted_favorite_does_not_star_neighbour(self):
        assert self.carry([(0, "A")], 3, {0: "B", 1: "C"}) == set()

    def test_legacy_rows_without_hash_fall_back_to_position(self):
        assert self.carry([(1, None)], 3, {0: "A", 1: "B", 2: "C"}) == {1}

    def test_duplicate_content_maps_each_favorite_to_distinct_slide(self):
        assert self.carry([(0, "A"), (1, "A")], 2, {0: "A", 1: "A"}) == {0, 1}

    def test_image_only_slides_never_match_by_hash(self):
        assert self.carry([(0, None)], 2, {0: None, 1: None}) == {0}


def test_reindex_preserves_favorite_through_reorder_and_removes_stale_thumbs(tmp_db):
    sid = db.add_source("/x", "Dom")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t0", "alpha"), ("t1", "beta")])
    db.set_slide_favorite(fid, 0, True, "Ann")
    old_thumbs = {p.name for p in db.THUMB_DIR.iterdir()}

    file_id, prior = db.upsert_file(sid, "/x/a.pptx", "Dom", "a", "pptx", 2, 2.0, 2)
    assert file_id == fid and prior.thumbs == old_thumbs
    from app import indexer
    carried = db.carry_user_favorites(prior, {0: indexer._content_hash("beta"), 1: indexer._content_hash("alpha")})
    assert set(carried) == {"Ann"} and set(carried["Ann"]) == {1}


def test_delete_source_removes_its_thumbnails(tmp_db):
    s1, s2 = db.add_source("/x", "D"), db.add_source("/y", "D")
    add_indexed_file(s1, "/x/a.pptx", [("t", "a")])
    add_indexed_file(s2, "/y/b.pptx", [("t", "b")])
    db.delete_source(s1)
    assert [p.name for p in db.THUMB_DIR.iterdir()] == ["b-0.png"]


def test_delete_files_not_in_removes_thumbnails(tmp_db):
    sid = db.add_source("/x", "D")
    add_indexed_file(sid, "/x/a.pptx", [("t", "a")])
    add_indexed_file(sid, "/x/b.pptx", [("t", "b")])
    db.delete_files_not_in(sid, {"/x/b.pptx"})
    assert [p.name for p in db.THUMB_DIR.iterdir()] == ["b-0.png"]


def test_prune_orphan_thumbnails(tmp_db):
    sid = db.add_source("/x", "D")
    add_indexed_file(sid, "/x/a.pptx", [("t", "a")])
    (db.THUMB_DIR / "orphan.png").write_bytes(b"x")
    assert db.prune_orphan_thumbnails() == 1
    assert [p.name for p in db.THUMB_DIR.iterdir()] == ["a-0.png"]


def test_migration_adds_content_hash_to_old_database(tmp_db):
    conn = db.get_conn()
    conn.executescript("DROP TABLE slides_fts; DROP TABLE slides; CREATE TABLE slides ("
                       "id INTEGER PRIMARY KEY, file_id INTEGER, slide_index INTEGER, title TEXT, body_text TEXT, thumb_file TEXT)")
    db._migrate(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(slides)")}
    assert {"favorite", "content_hash"} <= cols


def test_list_favorites_filters_by_domain_and_query(tmp_db):
    s1, s2 = db.add_source("/x", "Strategy"), db.add_source("/y", "Architecture")
    a = add_indexed_file(s1, "/x/a.pptx", [("Wealth", "digital wealth plan"), ("Other", "misc")])
    b = add_indexed_file(s2, "/y/b.pptx", [("Target", "target architecture")])
    with db.get_conn() as c:
        c.execute("UPDATE files SET domain='Strategy' WHERE id=?", (a,))
        c.execute("UPDATE files SET domain='Architecture' WHERE id=?", (b,))
    for fid, idx in [(a, 0), (a, 1), (b, 0)]:
        db.set_slide_favorite(fid, idx, True)

    assert [r["domain"] for r in db.list_favorites()] == ["Architecture", "Strategy", "Strategy"]
    assert len(db.list_favorites("Strategy")) == 2
    assert len(db.list_favorites("All domains")) == 3
    assert [r["title"] for r in db.list_favorites(None, "wealth")] == ["Wealth"]
    assert [r["title"] for r in db.list_favorites("Architecture", "wealth")] == []


def test_favorited_at_is_set_on_star_kept_on_restar_and_cleared_on_unstar(tmp_db):
    sid = db.add_source("/x", "Dom")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t", "a")])
    db.set_slide_favorite(fid, 0, True, "Ann")
    assert _fav(fid, 0, "Ann")["favorited_at"]
    with db.get_conn() as c:
        c.execute("UPDATE favorites SET favorited_at = '2020-01-01T00:00:00+00:00'")
    db.set_slide_favorite(fid, 0, True, "Ann")
    assert _fav(fid, 0, "Ann")["favorited_at"] == "2020-01-01T00:00:00+00:00"
    db.set_slide_tags(fid, 0, ["Keep"], "Ann")
    db.set_slide_favorite(fid, 0, False, "Ann")
    row = _fav(fid, 0, "Ann")
    assert row["starred"] == 0 and row["favorited_at"] is None and db.parse_tags(row["tags"]) == ["Keep"]  # undo keeps tags
    assert db.set_slide_favorite(fid, 9, True, "Ann") is False


def _fav(file_id, slide_index, user):
    return db.get_conn().execute(
        "SELECT f.* FROM favorites f JOIN slides s ON s.id = f.slide_id WHERE s.file_id = ? AND s.slide_index = ? AND f.user = ?",
        (file_id, slide_index, user)).fetchone()


def test_normalize_tags_trims_dedupes_and_caps():
    assert db.normalize_tags(["  Q3 ", "board   pack", "q3", "", "Board Pack"]) == ["Q3", "board pack"]
    assert db.normalize_tags(["x" * 100]) == ["x" * db.MAX_TAG_LEN]
    assert len(db.normalize_tags([f"t{i}" for i in range(50)])) == db.MAX_TAGS


def test_parse_tags_tolerates_garbage():
    assert db.parse_tags(None) == []
    assert db.parse_tags("not json") == []
    assert db.parse_tags('{"a": 1}') == []
    assert db.parse_tags('["a", 3, "b"]') == ["a", "b"]


def test_set_slide_tags_and_list_counts_only_favorites(tmp_db):
    sid = db.add_source("/x", "Dom")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t0", "a"), ("t1", "b"), ("t2", "c")])
    db.set_slide_favorite(fid, 0, True)
    db.set_slide_favorite(fid, 1, True)
    assert db.set_slide_tags(fid, 0, ["Board", "Q3"]) == ["Board", "Q3"]
    db.set_slide_tags(fid, 1, ["q3"])
    db.set_slide_tags(fid, 2, ["Hidden"])  # not a favorite: must not be offered
    assert db.set_slide_tags(fid, 9, ["x"]) is None
    assert db.list_favorite_tags() == [{"name": "Board", "count": 1}, {"name": "Q3", "count": 1}, {"name": "q3", "count": 1}]


def test_reindex_carries_tags_and_date_with_the_star(tmp_db):
    sid = db.add_source("/x", "Dom")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t0", "alpha"), ("t1", "beta")])
    db.set_slide_favorite(fid, 0, True, "Ann")
    db.set_slide_tags(fid, 0, ["Keep"], "Ann")
    db.set_slide_favorite(fid, 1, True, "Bob")
    starred_at = _fav(fid, 0, "Ann")["favorited_at"]

    add_indexed_file(sid, "/x/a.pptx", [("new", "gamma"), ("t1", "beta"), ("t0", "alpha")])  # alpha moved to 2, beta stays 1
    assert db.favorite_indices(fid, "Ann") == {2} and db.favorite_indices(fid, "Bob") == {1}
    assert db.parse_tags(_fav(fid, 2, "Ann")["tags"]) == ["Keep"] and _fav(fid, 2, "Ann")["favorited_at"] == starred_at
    assert _fav(fid, 0, "Ann") is None


def test_migration_adds_tag_and_date_columns(tmp_db):
    conn = db.get_conn()
    conn.executescript("DROP TABLE slides_fts; DROP TABLE slides; CREATE TABLE slides ("
                       "id INTEGER PRIMARY KEY, file_id INTEGER, slide_index INTEGER, title TEXT, body_text TEXT, thumb_file TEXT)")
    db._migrate(conn)
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(slides)")}
    assert {"favorited_at", "tags"} <= cols


def test_discover_files_can_skip_subfolders(tmp_path):
    from app import indexer
    (tmp_path / "sub").mkdir()
    for p in ["top.pptx", "top.pdf", "notes.txt", "sub/deep.pptx", "~$top.pptx"]:
        (tmp_path / p).write_bytes(b"x")
    assert [p.name for p in indexer.discover_files(str(tmp_path))] == ["deep.pptx", "top.pdf", "top.pptx"]
    assert [p.name for p in indexer.discover_files(str(tmp_path), recursive=False)] == ["top.pdf", "top.pptx"]


def test_source_recursive_flag_defaults_on_and_can_change(tmp_db):
    a = db.add_source("/a", "D")
    b = db.add_source("/b", "D", recursive=False)
    assert db.get_source(a)["recursive"] == 1 and db.get_source(b)["recursive"] == 0
    assert db.set_source_recursive(b, True) and db.get_source(b)["recursive"] == 1
    assert not db.set_source_recursive(999, True)


def test_migration_adds_recursive_to_old_sources_table(tmp_db):
    conn = db.get_conn()
    conn.executescript("PRAGMA foreign_keys=OFF; DROP TABLE sources; CREATE TABLE sources (id INTEGER PRIMARY KEY, path TEXT, domain TEXT, "
                       "status TEXT, error_message TEXT, files_total INTEGER, files_done INTEGER, created_at TEXT, last_indexed_at TEXT);"
                       "INSERT INTO sources (path, domain) VALUES ('/old', 'D');")
    db._migrate(conn)
    assert conn.execute("SELECT recursive FROM sources").fetchone()[0] == 1  # existing sources keep indexing subfolders


def test_storage_info_reports_paths_and_thumbnail_usage(tmp_db):
    (db.THUMB_DIR / "a.png").write_bytes(b"12345")
    info = db.storage_info()
    assert info["db_path"] == str(db.DB_PATH) and info["thumbnails_dir"] == str(db.THUMB_DIR)
    assert info["thumbnail_count"] == 1 and info["thumbnails_bytes"] == 5 and info["db_bytes"] > 0


def _folder_lib():
    sid = db.add_source("/lib/Strategy", "Strategy")
    a = add_indexed_file(sid, "/lib/Strategy/top.pptx", [("Top", "alpha")])
    b = add_indexed_file(sid, "/lib/Strategy/2024/q1.pptx", [("Q1", "alpha beta")])
    c = add_indexed_file(sid, "/lib/Strategy/2024/Board/b.pptx", [("Board", "alpha")])
    d = add_indexed_file(sid, "/lib/Strategy/2024_old/x.pptx", [("Old", "alpha")])  # prefix lookalike of "2024"
    return a, b, c, d


def test_folder_tree_counts_decks_including_subfolders(tmp_db):
    _folder_lib()
    [root] = db.list_folder_tree()
    assert (root["name"], root["path"], root["domain"], root["count"]) == ("Strategy", "/lib/Strategy", "Strategy", 4)
    assert [(c["name"], c["count"]) for c in root["children"]] == [("2024", 2), ("2024_old", 1)]
    board = root["children"][0]["children"][0]
    assert (board["name"], board["path"], board["count"], board["children"]) == ("Board", "/lib/Strategy/2024/Board", 1, [])


def test_folder_filter_includes_subfolders_but_not_lookalike_siblings(tmp_db):
    a, b, c, d = _folder_lib()
    assert {r["id"] for r in db.list_decks(None, None, folder="/lib/Strategy/2024")} == {b, c}
    assert {r["id"] for r in db.list_decks(None, None, folder="/lib/Strategy/2024/")} == {b, c}
    assert {r["id"] for r in db.list_decks(None, None, folder="/lib/Strategy")} == {a, b, c, d}
    assert {r["file_id"] for r in db.search_slides("alpha", folder="/lib/Strategy/2024")} == {b, c}
    db.set_slide_favorite(b, 0, True)
    db.set_slide_favorite(d, 0, True)
    assert [r["file_id"] for r in db.list_favorites(folder="/lib/Strategy/2024")] == [b]


def test_folder_filter_treats_like_wildcards_literally(tmp_db):
    sid = db.add_source("/x", "D")
    add_indexed_file(sid, "/x/a_b/one.pptx", [("t", "a")])
    add_indexed_file(sid, "/x/axb/two.pptx", [("t", "b")])
    assert [r["title"] for r in db.list_decks(None, None, folder="/x/a_b")] == ["one"]


def test_folder_tree_handles_windows_paths(tmp_db):
    sid = db.add_source("\\\\share\\Decks", "D")
    add_indexed_file(sid, "\\\\share\\Decks\\Sub\\a.pptx", [("t", "a")])
    [root] = db.list_folder_tree()
    assert root["count"] == 1 and root["children"][0]["path"] == "\\\\share\\Decks\\Sub"
    assert len(db.list_decks(None, None, folder="\\\\share\\Decks\\Sub")) == 1


def test_decks_record_who_added_them_and_keep_the_first_added_date(tmp_db):
    sid = db.add_source("/x", "D", added_by="Walter Giger")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t", "a")])
    first = db.get_file(fid)
    assert first["added_by"] == "Walter Giger" and first["added_at"]
    with db.get_conn() as c:
        c.execute("UPDATE files SET added_at = '2020-01-01T00:00:00+00:00' WHERE id = ?", (fid,))
    add_indexed_file(sid, "/x/a.pptx", [("t", "changed")])            # re-index
    again = db.get_file(fid)
    assert again["added_at"] == "2020-01-01T00:00:00+00:00" and again["added_by"] == "Walter Giger"


def test_cover_is_first_slide_with_a_thumbnail(tmp_db):
    sid = db.add_source("/x", "D")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t0", "a"), ("t1", "b")])
    assert db.get_file(fid)["cover_thumb"] == "a-0.png"
    assert db.list_decks(None, None)[0]["cover_thumb"] == "a-0.png"
    nothumb = add_indexed_file(sid, "/x/b.pptx", [("t", "c")], thumbs=False)
    assert db.get_file(nothumb)["cover_thumb"] is None


def test_migration_backfills_added_at_and_adds_added_by(tmp_db):
    conn = db.get_conn()
    conn.executescript("PRAGMA foreign_keys=OFF; DROP TABLE files; CREATE TABLE files (id INTEGER PRIMARY KEY, source_id INTEGER, "
                       "path TEXT, domain TEXT, title TEXT, ext TEXT, slide_count INTEGER, mtime REAL, size INTEGER, indexed_at TEXT);"
                       "INSERT INTO files (path, indexed_at) VALUES ('/a.pptx', '2026-01-02T03:04:05+00:00');")
    db._migrate(conn)
    row = conn.execute("SELECT added_at, added_by FROM files").fetchone()
    assert row["added_at"] == "2026-01-02T03:04:05+00:00" and row["added_by"] is None
    assert "added_by" in {r["name"] for r in conn.execute("PRAGMA table_info(sources)")}


def test_each_user_has_their_own_stars_and_tags(tmp_db):
    sid = db.add_source("/x", "D")
    fid = add_indexed_file(sid, "/x/a.pptx", [("Wealth", "a"), ("Other", "b")])
    db.set_slide_favorite(fid, 0, True, "Ann")
    db.set_slide_tags(fid, 0, ["Board"], "Ann")
    db.set_slide_favorite(fid, 1, True, "Bob")
    db.set_slide_tags(fid, 1, ["Q3"], "Bob")

    assert [r["title"] for r in db.list_favorites(user="Ann")] == ["Wealth"]
    assert [r["title"] for r in db.list_favorites(user="Bob")] == ["Other"]
    assert db.list_favorites(user="Cleo") == []
    assert [t["name"] for t in db.list_favorite_tags("Ann")] == ["Board"]
    assert [t["name"] for t in db.list_favorite_tags("Bob")] == ["Q3"]
    assert [bool(r["is_favorite"]) for r in db.list_slides(fid, "Ann")] == [True, False]
    assert [bool(r["is_favorite"]) for r in db.list_slides(fid, "Bob")] == [False, True]
    assert len(db.list_decks(None, None, favorites_only=True, user="Ann")) == 1
    assert db.list_decks(None, None, favorites_only=True, user="Cleo") == []

    db.set_slide_favorite(fid, 0, False, "Bob")            # Bob un-starring never touches Ann's star
    assert db.favorite_indices(fid, "Ann") == {0}


def test_global_stars_migrate_once_to_the_os_account_name(tmp_db, monkeypatch):
    from app import users
    monkeypatch.setattr(users, "default_name", lambda: "Walter Giger")
    sid = db.add_source("/x", "D")
    fid = add_indexed_file(sid, "/x/a.pptx", [("t0", "a"), ("t1", "b")])
    with db.get_conn() as c:                                # a pre-0.5 database: star + tags on the slide row
        c.execute("UPDATE slides SET favorite = 1, favorited_at = '2026-01-01T00:00:00+00:00', tags = '[\"Keep\"]' "
                  "WHERE slide_index = 1")
    db._migrate(db.get_conn())
    db._migrate(db.get_conn())                              # idempotent
    assert db.favorite_indices(fid, "Walter Giger") == {1}
    row = _fav(fid, 1, "Walter Giger")
    assert row["favorited_at"] == "2026-01-01T00:00:00+00:00" and db.parse_tags(row["tags"]) == ["Keep"]
    assert db.get_conn().execute("SELECT COUNT(*) FROM slides WHERE favorite = 1").fetchone()[0] == 0
