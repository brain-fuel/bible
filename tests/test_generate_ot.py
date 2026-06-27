import json
from pathlib import Path
from tools.generate_ot import write_book, out_path_ot

ROOT = Path(__file__).resolve().parents[1]


def _seed(tmp):
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
        json.dumps({"he": ["חֲזוֹן", "הִנֵּה"], "sections": [1]}), encoding="utf-8")
    return cache


def test_write_obadiah(tmp_path):
    cache = _seed(tmp_path)
    from tools.sources.scrollmapper import load_dataset
    kjv_idx = load_dataset("KJV", cache)
    vul_idx = load_dataset("VulgClementine", cache)
    meta = {"code": "OBA", "latin_name": "Abdias", "hebrew_name": "עֹבַדְיָה",
            "english_name": "Obadiah", "chapters": 1, "kjv_name": "Obadiah",
            "vulgate_name": "Obadiah", "sefaria_name": "Obadiah"}
    vmap = {"hebrew": {}, "latin": {}}
    n = write_book(tmp_path, meta, kjv_idx, vul_idx, vmap, cache)
    assert n == 1
    p = out_path_ot(tmp_path, "OBA", 1)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["book_id"] == "OBA" and data["chapter"] == 1
    assert len(data["verses"]) == 2
    v1 = data["verses"][0]
    assert v1["king_james"] == "The vision" and v1["latin_vulgate"] == "Visio"
    assert v1["hebrew_masoretic"] == "חֲזוֹן"
    assert "refs" not in v1   # identity
    assert p.read_text(encoding="utf-8").endswith("\n")
