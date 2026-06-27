import json
from tools.generate_ot import write_book, out_path_ot
from tools.editions import editions_for
from tools.sources.registry import prepare_source


def _seed(tmp, he=("חֲזוֹן", "הִנֵּה")):
    cache = tmp / "data" / "cache"
    (cache / "scrollmapper").mkdir(parents=True)
    (cache / "sefaria").mkdir(parents=True)

    def sm(name, key, verses):
        book = {"translation": name, "books": [{"name": "Obadiah", "chapters": [
            {"chapter": "1", "verses": [{"verse": str(i + 1), "text": t}
                                        for i, t in enumerate(verses)]}]}]}
        (cache / "scrollmapper" / f"{key}.json").write_text(
            json.dumps(book), encoding="utf-8")

    sm("KJV", "KJV", ["The vision", "Behold"])
    sm("Vul", "VulgClementine", ["Visio", "Ecce"])
    sm("DRC", "DRC", ["The vision of Abdias", "Thus saith"])
    sm("Fin", "FinBiblia", ["Obadjan näky", "Näin sanoo"])
    (cache / "sefaria" / "Obadiah.1.json").write_text(
        json.dumps({"he": list(he), "sections": [1]}), encoding="utf-8")
    return cache


OBA = {"code": "OBA", "english_name": "Obadiah", "hebrew_name": "עֹבַדְיָה",
       "latin_name": "Abdias", "douay_name": "Abdias",
       "finnish_name": "Obadja", "chapters": 1, "kjv_name": "Obadiah",
       "vulgate_name": "Obadiah", "sefaria_name": "Obadiah"}


def _handles(editions, cache):
    return {e["id"]: prepare_source(e, cache) for e in editions}


def test_write_obadiah_five_columns_identity(tmp_path):
    cache = _seed(tmp_path)
    editions = editions_for("ot")
    n = write_book(tmp_path, OBA, editions, _handles(editions, cache),
                   {"hebrew": {}, "latin": {}})
    assert n == 1
    data = json.loads(out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8"))
    assert list(data) == ["book_id", "latin_name", "hebrew_name", "douay_name",
                          "finnish_name", "english_name", "chapter", "verses"]
    v1 = data["verses"][0]
    assert list(v1) == ["verse", "latin_vulgate", "hebrew_masoretic",
                        "douay_rheims", "finnish_biblia", "king_james"]
    assert v1["douay_rheims"] == "The vision of Abdias"
    assert v1["finnish_biblia"] == "Obadjan näky"
    assert "refs" not in v1   # identity (no latin vmap entries for OBA)
    assert out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8").endswith("\n")


def test_douay_relocates_with_latin_vmap(tmp_path):
    # A latin-vmap entry relocates BOTH latin and douay to source 1:2.
    cache = _seed(tmp_path)
    # DRC source verse 2 holds the relocated text.
    editions = editions_for("ot")
    vmap = {"hebrew": {}, "latin": {"OBA 1:1": "1:2"}}
    write_book(tmp_path, OBA, editions, _handles(editions, cache), vmap)
    v1 = json.loads(out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8"))["verses"][0]
    assert v1["douay_rheims"] == "Thus saith"          # fetched from DRC 1:2
    assert v1["refs"]["douay_rheims"] == {"src": "1:2"}
    assert v1["refs"]["latin_vulgate"] == {"src": "1:2"}
    assert "finnish_biblia" not in v1.get("refs", {})   # identity, no vmap_key
