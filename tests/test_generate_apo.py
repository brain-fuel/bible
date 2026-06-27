import json
from tools.generate_ot import write_book, out_path, output_editions
from tools.editions import editions_for
from tools.sources.registry import prepare_source


def _seed(tmp):
    cache = tmp / "data" / "cache"
    (cache / "scrollmapper").mkdir(parents=True)

    def sm(key, verses):
        book = {"translation": key, "books": [{"name": "Tobit", "chapters": [
            {"chapter": "1", "verses": [{"verse": str(i + 1), "text": t}
                                        for i, t in enumerate(verses)]}]}]}
        (cache / "scrollmapper" / f"{key}.json").write_text(
            json.dumps(book), encoding="utf-8")

    sm("KJVA", ["There was a man", "of the tribe"])
    # FinBiblia has verse 1 only -> verse 2 must be marked absent in Finnish.
    sm("FinBiblia", ["Oli mies"])
    return cache


TOB = {"code": "TOB", "english_name": "Tobit", "finnish_name": "Tobitin kirja",
       "kjv_name": "Tobit", "chapters": 1}


def _handles(editions, cache):
    return {e["id"]: prepare_source(e, cache) for e in editions}


def test_apo_two_columns_base_last_with_absent(tmp_path):
    cache = _seed(tmp_path)
    editions = editions_for("apo")
    n = write_book(tmp_path, TOB, editions, _handles(editions, cache),
                   {"hebrew": {}, "latin": {}}, testament="apo")
    assert n == 1
    data = json.loads(out_path(tmp_path, "apo", "TOB", 1).read_text(encoding="utf-8"))
    assert list(data) == ["book_id", "finnish_name", "english_name", "chapter", "verses"]
    v1, v2 = data["verses"]
    assert list(v1) == ["verse", "finnish_biblia", "king_james_apocrypha"]
    assert v1["king_james_apocrypha"] == "There was a man"
    assert v1["finnish_biblia"] == "Oli mies"
    assert "refs" not in v1
    # verse 2: Finnish empty -> uniform absent marker; base text present.
    assert v2["king_james_apocrypha"] == "of the tribe"
    assert v2["finnish_biblia"] == ""
    assert v2["refs"] == {"finnish_biblia": {"absent": True}}


def test_generate_apo_main_smoke(tmp_path, monkeypatch):
    # main() iterates the real registry+books; just assert it is importable and callable shape.
    import tools.generate_apo as g
    assert hasattr(g, "main")
