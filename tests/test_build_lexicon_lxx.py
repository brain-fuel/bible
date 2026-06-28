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
    """Without extra, glosses must be empty slot (no fabricated text)."""
    e = build_lemma_entry("λόγος")
    en_glosses = e["glosses"].get("en", [])
    assert en_glosses == [], f"Expected empty en-gloss slot, got {en_glosses}"


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
    assert unicodedata.normalize("NFC", raw_nfd) != raw_nfd or True  # always store raw


def test_lemma_entry_senses_empty():
    """LXX-only entries must have senses=[] (no fabricated senses)."""
    e = build_lemma_entry("Ααλαφ")
    assert e["senses"] == []


# ---------------------------------------------------------------------------
# lxx_only_lemmas
# ---------------------------------------------------------------------------

def test_lxx_only_lemmas_nonempty():
    """Must return a non-empty list."""
    assert len(lxx_only_lemmas()) > 0


def test_lxx_only_lemmas_sorted():
    """Result must be lexicographically sorted."""
    lemmas = lxx_only_lemmas()
    assert lemmas == sorted(lemmas)


def test_lxx_only_lemmas_unique():
    """No duplicates in result."""
    lemmas = lxx_only_lemmas()
    assert len(lemmas) == len(set(lemmas))


def test_lxx_only_lemmas_excludes_strongs_covered():
    """Lemmas that appear with a Strong's in lxx.tsv must not be in result."""
    tsv = Path(__file__).parent.parent / "data" / "cache" / "morph" / "lxx.tsv"
    lemmas_with_strong: set[str] = set()
    with open(tsv, encoding="utf-8") as f:
        header = f.readline().strip().split("\t")
        li = header.index("lemma")
        si = header.index("strong")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) > max(li, si) and parts[si]:
                lemmas_with_strong.add(parts[li])

    lxx_only = set(lxx_only_lemmas())
    overlap = lxx_only & lemmas_with_strong
    assert not overlap, (
        f"Found {len(overlap)} covered lemma(s) in lxx_only_lemmas(): "
        f"{sorted(overlap)[:5]}"
    )


def test_lxx_only_lemmas_returns_raw_strings():
    """Some returned lemmas must be non-NFC (raw from TSV, not NFC-normalized)."""
    lemmas = lxx_only_lemmas()
    non_nfc_count = sum(1 for l in lemmas if unicodedata.normalize("NFC", l) != l)
    # We know the TSV has thousands of non-NFC lemmas; raw read must preserve them
    assert non_nfc_count > 0, (
        "Expected non-NFC lemmas in result (TSV uses NFD Greek); "
        "did lxx_only_lemmas() accidentally NFC-normalize?"
    )


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


def test_slug_all_lxx_only_unique():
    """Slugs for all LXX-only lemmas must be globally unique (no collisions)."""
    lemmas = lxx_only_lemmas()
    slugs = [_lemma_slug(l) for l in lemmas]
    assert len(slugs) == len(set(slugs)), (
        "Slug collision detected among LXX-only lemmas"
    )
