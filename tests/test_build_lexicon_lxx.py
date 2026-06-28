"""
tests/test_build_lexicon_lxx.py — TDD tests for Task 6: LXX-only lemma entries.

Verifies:
  - build_lemma_entry() schema and gloss passthrough
  - lxx_only_lemmas() correctness, raw form, exclusion of Strong's-covered lemmas
  - _lemma_slug() determinism, collision-freedom, filesystem-safety
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pytest

from tools.build_lexicon import build_lemma_entry, lxx_only_lemmas, _lemma_slug


# ---------------------------------------------------------------------------
# build_lemma_entry
# ---------------------------------------------------------------------------

def test_lemma_entry_has_null_strong_and_lemma_key():
    """Canonical test from brief: strong=None, lemma passthrough, glosses, domains."""
    e = build_lemma_entry("διαθήκη", {"glosses": {"en": [{"text": "covenant", "src": "x"}]}})
    assert e["strong"] is None
    assert e["lemma"] == "διαθήκη"
    assert e["lang"] == "grc"
    assert e["glosses"]["en"][0]["text"] == "covenant"
    assert e["domains"] == []


def test_lemma_entry_minimal_schema():
    """build_lemma_entry with no extra must return a valid full schema."""
    e = build_lemma_entry("λόγος")
    assert e["strong"] is None
    assert e["lemma"] == "λόγος"
    assert e["lang"] == "grc"
    assert e["domains"] == []
    assert isinstance(e["glosses"], dict)
    assert isinstance(e["senses"], list)
    assert isinstance(e["sources"], list)
    assert "openscriptures-lxxlemmas" in e["sources"]
    # pos and translit are present (may be empty)
    assert "pos" in e
    assert "translit" in e
    assert "root" in e


def test_lemma_entry_no_fabricated_glosses():
    """Without extra, glosses must be {"en": []} (schema-uniform empty slot, no fabricated text)."""
    e = build_lemma_entry("λόγος")
    assert e["glosses"] == {"en": []}, (
        f"Expected glosses=={{'en': []}}, got {e['glosses']!r}"
    )


def test_lemma_entry_gloss_passthrough():
    """Glosses from extra must be passed through unchanged."""
    glosses = {"en": [{"text": "covenant", "src": "x"}, {"text": "will", "src": "y"}]}
    e = build_lemma_entry("διαθήκη", {"glosses": glosses})
    assert e["glosses"] == glosses


def test_lemma_entry_preserves_raw_lemma():
    """Raw lemma string (NFD or otherwise) must be stored as-is, not NFC-normalized."""
    # Use a known NFD form: add combining character manually to ensure non-NFC
    raw_nfd = unicodedata.normalize("NFD", "διαθήκη")
    e = build_lemma_entry(raw_nfd)
    assert e["lemma"] == raw_nfd
    # Confirm the NFC form is different (proving the test is meaningful)
    # Confirm the NFC form is different (proves the test is meaningful — NFD decomposes ή)
    assert unicodedata.normalize("NFC", raw_nfd) != raw_nfd


def test_lemma_entry_senses_empty():
    """LXX-only entries must have senses=[] (no fabricated senses)."""
    e = build_lemma_entry("Ααλαφ")
    assert e["senses"] == []


# ---------------------------------------------------------------------------
# lxx_only_lemmas
# ---------------------------------------------------------------------------

_TSV_HEADER = "ref\tidx\tsurface\tlemma\tstrong\txpos\tfeats\ttranslit\tedition\n"


def _write_fixture_tsv(tmp_path, rows):
    """rows = list of (ref, lemma, strong). Write a minimal normalized TSV."""
    p = tmp_path / "lxx.tsv"
    lines = [_TSV_HEADER]
    for i, (ref, lemma, strong) in enumerate(rows, start=1):
        lines.append(f"{ref}\t1\tx\t{lemma}\t{strong}\t_\t_\t_\tLXX\n")
    p.write_text("".join(lines), encoding="utf-8")
    return p


# A raw NFD (non-NFC) Greek lemma to prove no NFC-normalization happens.
_NFD_LEMMA = unicodedata.normalize("NFD", "φαῦσις")


def _fixture_rows():
    # ζευγνύω: only ever empty-strong (appears twice -> dedup) -> LXX-only
    # _NFD_LEMMA: only empty-strong, non-NFC -> LXX-only (raw preserved)
    # Ααλαφ: only empty-strong -> LXX-only
    # ἐν: has a Strong's -> excluded
    # καλος: appears with AND without a Strong's -> excluded (covered)
    return [
        ("GEN.1.1", "ἐν", "G1722"),
        ("GEN.1.2", "ζευγνύω", ""),
        ("GEN.1.3", _NFD_LEMMA, ""),
        ("GEN.1.4", "καλος", "G2570"),
        ("GEN.1.5", "ζευγνύω", ""),
        ("GEN.1.6", "Ααλαφ", ""),
        ("GEN.1.7", "καλος", ""),
    ]


def test_lxx_only_lemmas_nonempty(tmp_path):
    """Must return a non-empty list for a TSV with LXX-only lemmas."""
    tsv = _write_fixture_tsv(tmp_path, _fixture_rows())
    assert len(lxx_only_lemmas(tsv)) > 0


def test_lxx_only_lemmas_sorted(tmp_path):
    """Result must be lexicographically sorted."""
    tsv = _write_fixture_tsv(tmp_path, _fixture_rows())
    lemmas = lxx_only_lemmas(tsv)
    assert lemmas == sorted(lemmas)


def test_lxx_only_lemmas_unique(tmp_path):
    """No duplicates in result (ζευγνύω appears twice in the fixture)."""
    tsv = _write_fixture_tsv(tmp_path, _fixture_rows())
    lemmas = lxx_only_lemmas(tsv)
    assert len(lemmas) == len(set(lemmas))
    assert lemmas.count("ζευγνύω") == 1


def test_lxx_only_lemmas_excludes_strongs_covered(tmp_path):
    """A lemma that appears with a Strong's anywhere must not be in the result."""
    tsv = _write_fixture_tsv(tmp_path, _fixture_rows())
    lxx_only = set(lxx_only_lemmas(tsv))
    assert "ἐν" not in lxx_only          # always has a Strong's
    assert "καλος" not in lxx_only       # covered: appears with AND without a Strong's
    assert "ζευγνύω" in lxx_only         # never has a Strong's


def test_lxx_only_lemmas_returns_raw_strings(tmp_path):
    """Returned lemmas must be raw (non-NFC preserved, not NFC-normalized)."""
    tsv = _write_fixture_tsv(tmp_path, _fixture_rows())
    lemmas = lxx_only_lemmas(tsv)
    assert _NFD_LEMMA in lemmas, "raw NFD lemma was not preserved"
    assert unicodedata.normalize("NFC", _NFD_LEMMA) != _NFD_LEMMA  # fixture really is non-NFC
    non_nfc = [l for l in lemmas if unicodedata.normalize("NFC", l) != l]
    assert non_nfc, "lxx_only_lemmas() must not NFC-normalize"


# ---------------------------------------------------------------------------
# _lemma_slug
# ---------------------------------------------------------------------------

def test_slug_determinism():
    """Same lemma must always produce the same slug."""
    assert _lemma_slug("διαθήκη") == _lemma_slug("διαθήκη")


def test_slug_no_collision_distinct_lemmas():
    """Different lemmas must produce different slugs."""
    assert _lemma_slug("διαθήκη") != _lemma_slug("λόγος")


def test_slug_filesystem_safe():
    """Slug must consist only of characters safe in all major filesystems."""
    for lemma in ["διαθήκη", "λόγος", "Ααλαφ", "ζευγνύω", "φαῦσις"]:
        slug = _lemma_slug(lemma)
        assert re.match(r"^[a-zA-Z0-9_-]+$", slug), (
            f"slug {slug!r} for {lemma!r} is not filesystem-safe"
        )


def test_slug_all_lxx_only_unique(tmp_path):
    """Slugs for the LXX-only lemmas must be unique (no collisions)."""
    tsv = _write_fixture_tsv(tmp_path, _fixture_rows())
    lemmas = lxx_only_lemmas(tsv)
    slugs = [_lemma_slug(l) for l in lemmas]
    assert len(slugs) == len(set(slugs)), (
        "Slug collision detected among LXX-only lemmas"
    )
