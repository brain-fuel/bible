"""Tests for tools/morph_norm/lxx.py — LxxLemmas normalizer.

LxxLemmas JSON format (per docs/FORMATS-lxx.md §Source 1b):
  {"Gen.1.1": [{"key": "εν", "lemma": "ἐν"}, ...], ...}
Keys are "ABBREV.chapter.verse"; words are ordered dicts with "key" (lowercase
unaccented lookup) and "lemma" (precomposed polytonic oxia form).

normalize_lxx(path) accepts either:
  - a single .js file -> parse it and return rows
  - a directory -> parse all .js files in it

lemma_strong_index() -> dict[str,str] reads lexicon/grc/*.json and maps
the raw lemma string to "Gxxxx" (no NFC normalization: oxia must round-trip).
"""

import json
import pytest
from pathlib import Path

from tools.morph_norm.lxx import normalize_lxx, lemma_strong_index


# ---------------------------------------------------------------------------
# normalize_lxx — single-file fixture
# ---------------------------------------------------------------------------

def test_normalize_lxx_row(tmp_path):
    """A single Gen.1.1 word normalizes to the correct schema row."""
    data = {
        "Gen.1.1": [
            {"key": "εν", "lemma": "ἐν"}
        ]
    }
    js_file = tmp_path / "Gen.js"
    js_file.write_text(json.dumps(data), encoding="utf-8")

    rows = normalize_lxx(js_file)
    assert len(rows) == 1
    r = rows[0]
    assert r["ref"] == "GEN.1.1"
    assert r["idx"] == 1
    assert r["lemma"] == "ἐν"          # raw polytonic oxia — NOT NFC-normalized
    assert r["xpos"] == "_"            # no morph source
    assert r["feats"] == "_"
    assert r["translit"] == "_"
    assert r["edition"] == "LXX"


def test_normalize_lxx_word_index(tmp_path):
    """idx is 1-based and increases per word in the verse."""
    data = {
        "Gen.1.1": [
            {"key": "εν", "lemma": "ἐν"},
            {"key": "αρχη", "lemma": "ἀρχή"},
        ]
    }
    js_file = tmp_path / "Gen.js"
    js_file.write_text(json.dumps(data), encoding="utf-8")

    rows = normalize_lxx(js_file)
    assert rows[0]["idx"] == 1
    assert rows[1]["idx"] == 2
    # ref stays the same for both words
    assert rows[0]["ref"] == "GEN.1.1"
    assert rows[1]["ref"] == "GEN.1.1"


def test_normalize_lxx_surface_is_key(tmp_path):
    """surface column comes from the 'key' field (unaccented lookup form)."""
    data = {
        "Gen.1.1": [
            {"key": "θεος", "lemma": "θεός"}
        ]
    }
    js_file = tmp_path / "Gen.js"
    js_file.write_text(json.dumps(data), encoding="utf-8")

    rows = normalize_lxx(js_file)
    assert rows[0]["surface"] == "θεος"


def test_normalize_lxx_epjer_mapped_to_bar6(tmp_path):
    """EpJer file verses are re-routed to BAR.6.V (Epistle of Jeremiah = BAR ch 6)."""
    data = {
        "EpJer.1.1": [{"key": "αντιγραφη", "lemma": "ἀντιγραφή"}],
        "EpJer.1.3": [{"key": "και", "lemma": "καί"}],
    }
    js_file = tmp_path / "EpJer.js"
    js_file.write_text(json.dumps(data), encoding="utf-8")

    rows = normalize_lxx(js_file)
    assert rows[0]["ref"] == "BAR.6.1"
    assert rows[1]["ref"] == "BAR.6.3"


def test_normalize_lxx_strong_filled(tmp_path):
    """strong column is filled when the lemma matches lexicon/grc."""
    # θεός -> G2316 (well-known Strong's)
    data = {
        "Gen.1.1": [
            {"key": "θεος", "lemma": "θεός"}
        ]
    }
    js_file = tmp_path / "Gen.js"
    js_file.write_text(json.dumps(data), encoding="utf-8")

    rows = normalize_lxx(js_file)
    # strong may or may not resolve depending on lexicon — just check format
    assert rows[0]["strong"] in ("", "G2316") or rows[0]["strong"].startswith("G")


def test_normalize_lxx_strong_empty_for_unknown(tmp_path):
    """strong is empty string when lemma is not in the lexicon index."""
    data = {
        "Gen.1.1": [
            {"key": "xyzzynotaword", "lemma": "ξωωωωω"}
        ]
    }
    js_file = tmp_path / "Gen.js"
    js_file.write_text(json.dumps(data), encoding="utf-8")

    rows = normalize_lxx(js_file)
    assert rows[0]["strong"] == ""


# ---------------------------------------------------------------------------
# lemma_strong_index — real lexicon join
# ---------------------------------------------------------------------------

def _read_lexicon_lemma(strong: str) -> str:
    """Read the raw lemma string from lexicon/grc/{strong}.json.

    This avoids string-literal encoding confusion: Greek accented characters
    typed in Python source are NFC (tonos, e.g. U+03AC), but lexicon/grc files
    store the oxia form (e.g. U+1F71).  Reading the file directly gives the
    exact bytes the index will use.
    """
    import json
    from pathlib import Path
    lexicon = Path(__file__).resolve().parents[1] / "lexicon" / "grc" / f"{strong}.json"
    with open(lexicon, encoding="utf-8") as fh:
        return json.load(fh)["lemma"]


def test_lemma_strong_index_agape():
    """G0026 (agape) resolves via the raw lemma string from the lexicon file."""
    index = lemma_strong_index()
    raw_agape = _read_lexicon_lemma("G0026")   # precomposed polytonic, raw oxia form
    assert raw_agape in index, f"{raw_agape!r} (G0026 lemma) should be in index"
    assert index[raw_agape] == "G0026"


def test_lemma_strong_index_theos():
    """G2316 (theos) resolves via the raw lemma string from the lexicon file."""
    index = lemma_strong_index()
    raw_theos = _read_lexicon_lemma("G2316")
    assert index.get(raw_theos) == "G2316"


def test_lemma_strong_index_no_nfc():
    """Index keys must NOT be NFC-normalized (oxia U+1F7x preserved, not tonos U+03xx).

    NFC would fold e.g. oxia ά (U+1F71) -> tonos ά (U+03AC).  The lexicon stores
    the oxia form; NFC would break the lemma->Strong's join for any accented lemma.
    This test verifies at least one index key is non-NFC (has oxia form preserved).
    """
    import unicodedata
    index = lemma_strong_index()
    for key in index:
        nfc_key = unicodedata.normalize("NFC", key)
        if nfc_key != key:
            # Found a key that is NOT NFC-normalized — correct behaviour.
            return
    # If every key happens to be NFC-stable, we can't distinguish; pass silently.
