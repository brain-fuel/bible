import json
from tools.generate_ot import write_book, out_path_ot
from tools.editions import editions_for
from tools.sources.registry import prepare_source


def _seed(tmp, he=("חֲזוֹן", "הִנֵּה")):
    cache = tmp / "data" / "cache"
    (cache / "scrollmapper").mkdir(parents=True)
    (cache / "sefaria").mkdir(parents=True)
    kjv = {"translation": "KJV", "books": [{"name": "Obadiah", "chapters": [
        {"chapter": "1", "verses": [{"verse": "1", "text": "The vision"},
                                    {"verse": "2", "text": "Behold"}]}]}]}
    (cache / "scrollmapper" / "KJV.json").write_text(json.dumps(kjv), encoding="utf-8")
    vul = {"translation": "Vul", "books": [{"name": "Obadiah", "chapters": [
        {"chapter": "1", "verses": [{"verse": "1", "text": "Visio"},
                                    {"verse": "2", "text": "Ecce"}]}]}]}
    (cache / "scrollmapper" / "VulgClementine.json").write_text(json.dumps(vul), encoding="utf-8")
    (cache / "sefaria" / "Obadiah.1.json").write_text(
        json.dumps({"he": list(he), "sections": [1]}), encoding="utf-8")
    return cache


OBA = {"code": "OBA", "latin_name": "Abdias", "hebrew_name": "עֹבַדְיָה",
       "english_name": "Obadiah", "chapters": 1, "kjv_name": "Obadiah",
       "vulgate_name": "Obadiah", "sefaria_name": "Obadiah"}


def _handles(editions, cache):
    return {e["id"]: prepare_source(e, cache) for e in editions}


def test_write_obadiah_identity(tmp_path):
    cache = _seed(tmp_path)
    editions = editions_for("ot")
    n = write_book(tmp_path, OBA, editions, _handles(editions, cache),
                   {"hebrew": {}, "latin": {}})
    assert n == 1
    data = json.loads(out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8"))
    assert data["book_id"] == "OBA" and data["chapter"] == 1
    assert list(data) == ["book_id", "latin_name", "hebrew_name", "english_name",
                          "chapter", "verses"]
    v1 = data["verses"][0]
    assert v1["king_james"] == "The vision" and v1["latin_vulgate"] == "Visio"
    assert v1["hebrew_masoretic"] == "חֲזוֹן"
    assert "refs" not in v1   # identity
    # column order: non-base editions (registry order), base last
    assert list(v1) == ["verse", "latin_vulgate", "hebrew_masoretic", "king_james"]
    assert out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8").endswith("\n")


def test_diverging_hebrew_records_normalized_src(tmp_path):
    # Hebrew verse 1 lives at masoretic 1:2 ("B"); base 1:1 must relocate there.
    cache = _seed(tmp_path, he=("A", "B"))
    editions = editions_for("ot")
    vmap = {"hebrew": {"OBA 1:1": "1:2"}, "latin": {}}
    write_book(tmp_path, OBA, editions, _handles(editions, cache), vmap)
    v1 = json.loads(out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8"))["verses"][0]
    assert v1["hebrew_masoretic"] == "B"
    assert v1["refs"] == {"hebrew_masoretic": {"src": "1:2"}}
