import json
from pathlib import Path
from tools.generate import out_path, write_chapter

ROOT = Path(__file__).resolve().parents[1]
META = {"code":"JAM","dir":"james","prefix":"jam","latin_name":"Epistula Jacobi",
        "greek_name":"Ἰάκωβος","english_name":"The General Epistle of James"}

def test_out_path_uses_three_digit_padding(tmp_path):
    p = out_path(tmp_path, META, 5)
    assert p == tmp_path / "bible" / "nt" / "JAM" / "005.json"

def test_write_chapter_emits_valid_json(tmp_path):
    # seed the cache with the committed fixture so no network is used
    cache = tmp_path / "cache" / "james" / "jam01.htm"
    cache.parent.mkdir(parents=True)
    cache.write_text((ROOT / "tests" / "fixtures" / "jam01.htm").read_text(encoding="utf-8"),
                     encoding="utf-8")
    p = write_chapter(tmp_path, META, 1, tmp_path / "cache")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["book_id"] == "JAM"
    assert data["chapter"] == 1
    assert len(data["verses"]) == 27
    assert p.read_text(encoding="utf-8").endswith("\n")
