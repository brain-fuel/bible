# tests/test_generate_lxx.py
from tools.generate_lxx import build_chapter


def test_build_chapter_shapes_verses():
    src = {1: "εν αρχη εποιησεν ο θεος", 2: "η δε γη ην αορατος"}
    ch = build_chapter("GEN", 1, src)
    assert ch["book_id"] == "GEN"
    assert ch["chapter"] == 1
    assert ch["verses"][0] == {"verse": 1, "greek_lxx": "εν αρχη εποιησεν ο θεος"}
    assert ch["verses"][1]["verse"] == 2


def test_refs_absent_for_deuterocanon():
    """Deuterocanon book (1MA) produces verse dicts with no 'refs' key."""
    ch = build_chapter("1MA", 1, {1: "Ἐγένετο"})
    verse = ch["verses"][0]
    assert "refs" not in verse, f"Expected no 'refs' key for deuterocanon 1MA; got {verse}"


def test_refs_mt_absent_for_lxx_only_verse():
    """PSA 151 has no MT counterpart; verse refs.mt must be {'absent': True}."""
    # PSA 151 is LXX-only; mt_ref returns None for all its verses.
    ch = build_chapter("PSA", 151, {1: "Μικρὸς ἤμην"})
    verse = ch["verses"][0]
    assert "refs" in verse, "Expected 'refs' key for protocanon PSA"
    assert verse["refs"] == {"mt": {"absent": True}}, (
        f"Expected refs.mt == {{absent: true}}; got {verse['refs']}"
    )


def test_refs_mt_src_for_divergent_verse():
    """PSA 9:22 (LXX) maps to MT 10:1; verse refs.mt must carry {'src': '10:1'}."""
    # mt_ref("PSA", 9, 22) == "10:1" (diverges from identity "9:22")
    ch = build_chapter("PSA", 9, {22: "ὅτι ἐπελάθετο ὁ θεός"})
    verse = ch["verses"][0]
    assert "refs" in verse, "Expected 'refs' key for protocanon PSA"
    assert verse["refs"] == {"mt": {"src": "10:1"}}, (
        f"Expected refs.mt == {{src: '10:1'}}; got {verse['refs']}"
    )
