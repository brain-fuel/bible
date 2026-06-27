import json
import pytest
from tools.sources.registry import (prepare_source, ScrollmapperSource,
                                     SefariaSource)


def _seed(tmp):
    cache = tmp / "data" / "cache"
    (cache / "scrollmapper").mkdir(parents=True)
    (cache / "sefaria").mkdir(parents=True)
    kjv = {"translation": "KJV", "books": [{"name": "Obadiah", "chapters": [
        {"chapter": "1", "verses": [{"verse": "1", "text": "The vision"},
                                    {"verse": "2", "text": "Behold"}]}]}]}
    (cache / "scrollmapper" / "KJV.json").write_text(json.dumps(kjv), encoding="utf-8")
    (cache / "sefaria" / "Obadiah.1.json").write_text(
        json.dumps({"he": ["חֲזוֹן", "הִנֵּה"], "sections": [1]}), encoding="utf-8")
    return cache


KJV_ED = {"id": "king_james", "source": {"type": "scrollmapper", "key": "KJV"},
          "book_name_field": "kjv_name"}
HEB_ED = {"id": "hebrew_masoretic", "source": {"type": "sefaria"},
          "book_name_field": "sefaria_name"}
META = {"kjv_name": "Obadiah", "sefaria_name": "Obadiah"}


def test_prepare_dispatches_scrollmapper(tmp_path):
    cache = _seed(tmp_path)
    h = prepare_source(KJV_ED, cache)
    assert isinstance(h, ScrollmapperSource)
    assert h.chapters(META) == [1]
    assert h.chapter(META, 1) == {1: "The vision", 2: "Behold"}


def test_prepare_dispatches_sefaria(tmp_path):
    cache = _seed(tmp_path)
    h = prepare_source(HEB_ED, cache)
    assert isinstance(h, SefariaSource)
    assert h.chapter(META, 1) == {1: "חֲזוֹן", 2: "הִנֵּה"}


def test_sefaria_chapter_is_cached(tmp_path):
    cache = _seed(tmp_path)
    h = prepare_source(HEB_ED, cache)
    first = h.chapter(META, 1)
    # Delete the cache file; a second call must hit the in-run cache, not disk.
    (cache / "sefaria" / "Obadiah.1.json").unlink()
    assert h.chapter(META, 1) == first


def test_unwired_source_type_raises(tmp_path):
    cache = _seed(tmp_path)
    scrape = {"id": "greek_textus_receptus",
              "source": {"type": "scrape", "site": "x"},
              "book_name_field": "greek_name"}
    with pytest.raises(NotImplementedError):
        prepare_source(scrape, cache)
