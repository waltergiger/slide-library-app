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
    db.set_slide_favorite(fid, 0, True)
    old_thumbs = {p.name for p in db.THUMB_DIR.iterdir()}

    file_id, prior = db.upsert_file(sid, "/x/a.pptx", "Dom", "a", "pptx", 2, 2.0, 2)
    assert file_id == fid and prior.thumbs == old_thumbs
    from app import indexer
    fav = db.carry_favorites(prior, {0: indexer._content_hash("beta"), 1: indexer._content_hash("alpha")})
    assert fav == {1}


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
