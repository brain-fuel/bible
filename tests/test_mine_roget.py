"""tests/test_mine_roget.py — TDD tests for the Roget 1911 thesaurus miner.

Fixture: a realistic minimal Roget-format plain-text document:
  - Two entries with N./V. sections → synonym links emitted
  - Two entries with explicit {ant. NNN} markers → antonym links emitted
  - Roget noise tokens (&c., underscores, |, cross-refs) that should be stripped

The fixture uses the CRLF-stripped format (the implementation handles CRLF via
newline=None; this test writes plain LF which is equally valid and simpler).
"""

from pathlib import Path

import pytest

from tools.relations.mine_roget import roget_links

# ---------------------------------------------------------------------------
# Minimal but realistic Roget-format fixture
#
# Entry #1 Existence:
#   N. section → existence, being, entity → synonym pairs
#   V. section → exist, subsist → synonym pair
#
# Entry #2 Inexistence:
#   N. section → inexistence, nonexistence, nothingness → synonym pairs
#   (tests that multiple entries don't bleed into each other)
#
# Entry #132 Earliness  (with {ant. 133}):
#   N. section → earliness, promptitude, punctuality → synonym pairs
#   Antonym link to #133 words
#
# Entry #133 Lateness  (with {ant. 132}):
#   N. section → lateness, tardiness, delay → synonym pairs
#   Antonym link to #132 words
#
# Noise tokens embedded to verify stripping:
#   &c. adj.  (POS self-ref)
#   &c. 682   (cross-ref with entry number)
#   _ens_     (italics marker)
#   dilection| (trailing pipe)
#   (desire) 865  (parenthetical cross-ref)
# ---------------------------------------------------------------------------

_FIXTURE = (
    "#1. Existence.—N. existence, being, entity, _ens_; positiveness &c. adj.;\n"
    "     fact, matter.\n"
    "     V. exist, subsist; have being &c. n.\n"
    "     Adj. existing, real.\n"
    "\n"
    "#2. Inexistence.—N. inexistence, nonexistence, nothingness.\n"
    "     V. perish, vanish.\n"
    "\n"
    "#132. Earliness.—N. {ant. 133} earliness, promptitude &c. adj.;\n"
    "     punctuality &c. (activity) 682.\n"
    "     V. anticipate, hasten.\n"
    "\n"
    "#133. Lateness.—N. {ant. 132} lateness, tardiness &c. adj.;\n"
    "     delay|, procrastination.\n"
    "     V. delay, postpone.\n"
)


def _write_fixture(tmp_path: Path) -> Path:
    """Write the fixture as a plain-text .txt file and return its path."""
    p = tmp_path / "roget_test.txt"
    p.write_text(_FIXTURE, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRogetLinksReturnTypes:
    """roget_links returns only valid (headword, related, rel) triples."""

    def test_returns_list_of_three_tuples(self, tmp_path):
        """Every element of the result must be a 3-tuple."""
        links = roget_links(_write_fixture(tmp_path))
        assert isinstance(links, list), "Expected a list"
        for item in links:
            assert len(item) == 3, f"Expected 3-tuple, got {item!r}"

    def test_relation_types_are_synonym_or_antonym(self, tmp_path):
        """The third element of every triple must be 'synonym' or 'antonym'."""
        links = roget_links(_write_fixture(tmp_path))
        rels = {r for _, _, r in links}
        assert rels <= {"synonym", "antonym"}, (
            f"Unexpected relation types: {rels - {'synonym', 'antonym'}}"
        )


class TestRogetSynonymExtraction:
    """Comma-separated words within a POS section become synonym pairs."""

    def test_synonym_links_are_produced(self, tmp_path):
        """At least one synonym link must be produced from the fixture."""
        links = roget_links(_write_fixture(tmp_path))
        assert any(r == "synonym" for _, _, r in links), (
            "Expected at least one synonym link; got none"
        )

    def test_n_section_pair_present(self, tmp_path):
        """'existence' and 'being' share the N. section of #1 → synonym."""
        links = roget_links(_write_fixture(tmp_path))
        syn_pairs = {
            frozenset([hw, rel]) for hw, rel, r in links if r == "synonym"
        }
        assert frozenset(["existence", "being"]) in syn_pairs, (
            f"Expected synonym pair {{existence, being}} in {syn_pairs}"
        )

    def test_v_section_pair_present(self, tmp_path):
        """'exist' and 'subsist' share the V. section of #1 → synonym."""
        links = roget_links(_write_fixture(tmp_path))
        syn_pairs = {
            frozenset([hw, rel]) for hw, rel, r in links if r == "synonym"
        }
        assert frozenset(["exist", "subsist"]) in syn_pairs, (
            f"Expected synonym pair {{exist, subsist}} in {syn_pairs}"
        )

    def test_cross_entry_words_are_not_synonyms(self, tmp_path):
        """'existence' (#1) and 'inexistence' (#2) are in different entries, not synonyms."""
        links = roget_links(_write_fixture(tmp_path))
        syn_pairs = {
            frozenset([hw, rel]) for hw, rel, r in links if r == "synonym"
        }
        assert frozenset(["existence", "inexistence"]) not in syn_pairs, (
            "Words from different entries must not become synonyms"
        )

    def test_noise_tokens_are_stripped(self, tmp_path):
        """Noise tokens (&c., _ens_, |, cross-refs) must not appear as headwords."""
        links = roget_links(_write_fixture(tmp_path))
        all_words = {w for pair in links for w in pair[:2]}
        # None of these noise artefacts should appear as headwords
        noise_tokens = {"&c", "ens", "adj", "682", "n"}
        # _ens_ is italics-wrapped → should be stripped entirely
        # &c. → stripped
        # 682 → numeric cross-ref, dropped
        assert "682" not in all_words, f"Numeric cross-ref '682' leaked into links"
        assert "&c" not in all_words, f"'&c' leaked into links"


class TestRogetAntonymExtraction:
    """Explicit {{ant. NNN}} markers produce antonym links between the two entries."""

    def test_antonym_links_are_produced(self, tmp_path):
        """At least one antonym link must be produced from the {ant.} markers."""
        links = roget_links(_write_fixture(tmp_path))
        assert any(r == "antonym" for _, _, r in links), (
            "Expected antonym links from {ant. 133}/{ant. 132} markers"
        )

    def test_explicit_antonym_pair_present(self, tmp_path):
        """'earliness' (#132) and 'lateness' (#133) should be antonyms via {ant.}."""
        links = roget_links(_write_fixture(tmp_path))
        ant_pairs = {
            frozenset([hw, rel]) for hw, rel, r in links if r == "antonym"
        }
        assert frozenset(["earliness", "lateness"]) in ant_pairs, (
            f"Expected antonym pair {{earliness, lateness}} in {ant_pairs}"
        )

    def test_antonym_cross_product_is_symmetric(self, tmp_path):
        """Both directions of the antonym pair should appear (cross-product).

        Entry #132 words × #133 words and #133 words × #132 words both contribute;
        the resulting set of pairs should be symmetric (same pairs either way).
        """
        links = roget_links(_write_fixture(tmp_path))
        ant_pairs = {
            frozenset([hw, rel]) for hw, rel, r in links if r == "antonym"
        }
        # promptitude (#132) × tardiness (#133) must also appear
        assert frozenset(["promptitude", "tardiness"]) in ant_pairs, (
            f"Expected antonym pair {{promptitude, tardiness}} in {ant_pairs}"
        )

    def test_synonym_words_not_linked_as_antonyms(self, tmp_path):
        """Words within the same entry (#1) must not appear as antonyms."""
        links = roget_links(_write_fixture(tmp_path))
        ant_pairs = {
            frozenset([hw, rel]) for hw, rel, r in links if r == "antonym"
        }
        assert frozenset(["existence", "being"]) not in ant_pairs, (
            "Words from the same entry must not be antonyms of each other"
        )
