# tests/test_generate_lxx.py
from tools.generate_lxx import build_chapter


def test_build_chapter_shapes_verses():
    src = {1: "εν αρχη εποιησεν ο θεος", 2: "η δε γη ην αορατος"}
    ch = build_chapter("GEN", 1, src)
    assert ch["book_id"] == "GEN"
    assert ch["chapter"] == 1
    assert ch["verses"][0] == {"verse": 1, "greek_lxx": "εν αρχη εποιησεν ο θεος"}
    assert ch["verses"][1]["verse"] == 2
