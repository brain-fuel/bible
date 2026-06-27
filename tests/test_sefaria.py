import json
from pathlib import Path
from tools.sources.sefaria import chapter_url, load_chapter

ROOT = Path(__file__).resolve().parents[1]

def test_url():
    u = chapter_url("I Samuel", 3)
    assert "I%20Samuel.3" in u or "I Samuel.3" in u

def test_load_chapter_from_cache(tmp_path):
    cache = tmp_path / "cache" / "sefaria" / "Genesis.1.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"he": ["בְּרֵאשִׁית", "וְהָאָרֶץ <sup>x</sup>", 'וְהָאָרֶץ <i class="footnote">a note</i>', "טוֹב <sup class=\"footnote-marker\">b</sup>"], "sections": [1]}), encoding="utf-8")
    verses = load_chapter("Genesis", 1, tmp_path / "cache")
    assert verses[1] == "בְּרֵאשִׁית"
    assert verses[2] == "וְהָאָרֶץ"   # sup tag stripped
    assert verses[3] == "וְהָאָרֶץ"   # footnote markup and content stripped
    assert verses[4] == "טוֹב"        # footnote-marker sup stripped
