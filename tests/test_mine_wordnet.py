"""tests/test_mine_wordnet.py — TDD tests for the Open English WordNet miner.

Fixture: a realistic minimal LMF XML document matching the WN-LMF-1.3 layout:
  - Two LexicalEntry elements sharing a Synset → yields a synonym link
  - One Sense-level SenseRelation relType="antonym" → yields an antonym link

Both plain .xml and gzip-compressed .xml.gz paths are tested.
"""

import gzip
import textwrap
from pathlib import Path

import pytest

from tools.relations.mine_wordnet import wordnet_links

# ---------------------------------------------------------------------------
# Minimal but realistic WN-LMF-1.3 XML fixture
#
# Structure mirrors the real OEWN file:
#   - LexicalEntry  elements carry a Lemma + one or more Sense elements
#   - Synset        elements list member LexicalEntry IDs in the "members" attr
#   - Antonyms are Sense-level <SenseRelation relType="antonym" target="..."/>
#
# Synonym pair: "love" and "affection" are both members of oewn-07558000-n
# Antonym link: "love" Sense oewn-love__1.12.00.. → antonym target oewn-hate__1.12.00..
# ---------------------------------------------------------------------------

_FIXTURE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE LexicalResource SYSTEM "http://globalwordnet.github.io/schemas/WN-LMF-1.3.dtd">
    <LexicalResource xmlns:dc="https://globalwordnet.github.io/schemas/dc/">
      <Lexicon id="oewn" label="Open English Wordnet" language="en"
               email="test@example.com"
               license="https://creativecommons.org/licenses/by/4.0"
               version="2024"
               url="https://github.com/globalwordnet/english-wordnet">

        <!-- Entry 1: love (noun) — member of oewn-07558000-n; antonym of hate -->
        <LexicalEntry id="oewn-love-n">
          <Lemma writtenForm="love" partOfSpeech="n"/>
          <Sense id="oewn-love__1.12.00.." synset="oewn-07558000-n">
            <SenseRelation relType="antonym" target="oewn-hate__1.12.00.."/>
            <SenseRelation relType="derivation" target="oewn-love__2.37.00.."/>
          </Sense>
        </LexicalEntry>

        <!-- Entry 2: affection (noun) — member of oewn-07558000-n (synonym of love) -->
        <LexicalEntry id="oewn-affection-n">
          <Lemma writtenForm="affection" partOfSpeech="n"/>
          <Sense id="oewn-affection__1.12.00.." synset="oewn-07558000-n"/>
        </LexicalEntry>

        <!-- Entry 3: hate (noun) — antonym target; NOT in the same synset -->
        <LexicalEntry id="oewn-hate-n">
          <Lemma writtenForm="hate" partOfSpeech="n"/>
          <Sense id="oewn-hate__1.12.00.." synset="oewn-07561000-n">
            <SenseRelation relType="antonym" target="oewn-love__1.12.00.."/>
          </Sense>
        </LexicalEntry>

        <!-- Synset: love + affection are mutual synonyms -->
        <Synset id="oewn-07558000-n" ili="i99991"
                members="oewn-love-n oewn-affection-n"
                partOfSpeech="n" lexfile="noun.feeling">
          <Definition>a strong positive emotion of regard and affection</Definition>
        </Synset>

        <!-- Synset for hate (single member, no synonym links emitted) -->
        <Synset id="oewn-07561000-n" ili="i99992"
                members="oewn-hate-n"
                partOfSpeech="n" lexfile="noun.feeling">
          <Definition>the emotion of intense dislike</Definition>
        </Synset>

      </Lexicon>
    </LexicalResource>
""")


def _write_xml(tmp_path: Path) -> Path:
    """Write the fixture as a plain .xml file and return its path."""
    p = tmp_path / "wn_test.xml"
    p.write_text(_FIXTURE_XML, encoding="utf-8")
    return p


def _write_gz(tmp_path: Path) -> Path:
    """Write the fixture as a gzip-compressed .xml.gz file and return its path."""
    p = tmp_path / "wn_test.xml.gz"
    with gzip.open(str(p), "wt", encoding="utf-8") as f:
        f.write(_FIXTURE_XML)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWordnetLinksParsesXml:
    """wordnet_links correctly extracts synonym and antonym pairs from plain XML."""

    def test_returns_only_synonym_and_antonym_relations(self, tmp_path):
        """All returned relation types must be exactly 'synonym' or 'antonym'."""
        links = wordnet_links(_write_xml(tmp_path))
        rels = {r for _, _, r in links}
        assert rels <= {"synonym", "antonym"}, f"Unexpected relation types: rels - {{'synonym','antonym'}} = {rels - {'synonym','antonym'}}"

    def test_synonym_pair_present(self, tmp_path):
        """love + affection share a Synset → exactly one synonym link emitted."""
        links = wordnet_links(_write_xml(tmp_path))
        syn_pairs = {frozenset([hw, rel]) for hw, rel, r in links if r == "synonym"}
        assert frozenset(["love", "affection"]) in syn_pairs, (
            f"Expected synonym pair {{love, affection}} in {syn_pairs}"
        )

    def test_antonym_pair_present(self, tmp_path):
        """love Sense has SenseRelation antonym → hate; link must appear."""
        links = wordnet_links(_write_xml(tmp_path))
        ant_pairs = {frozenset([hw, rel]) for hw, rel, r in links if r == "antonym"}
        assert frozenset(["love", "hate"]) in ant_pairs, (
            f"Expected antonym pair {{love, hate}} in {ant_pairs}"
        )

    def test_no_extra_synonym_pairs(self, tmp_path):
        """Only one synonym pair should come from the two-member synset."""
        links = wordnet_links(_write_xml(tmp_path))
        syn_pairs = [frozenset([hw, rel]) for hw, rel, r in links if r == "synonym"]
        assert len(syn_pairs) == 1, f"Expected exactly 1 synonym pair, got {syn_pairs}"

    def test_single_member_synset_produces_no_synonyms(self, tmp_path):
        """The hate synset has only one member — no synonym link should be emitted for it."""
        links = wordnet_links(_write_xml(tmp_path))
        syn_pairs = {frozenset([hw, rel]) for hw, rel, r in links if r == "synonym"}
        assert frozenset(["hate"]) not in syn_pairs


class TestWordnetLinksGzip:
    """wordnet_links correctly handles gzip-compressed .xml.gz input."""

    def test_gz_returns_same_links_as_plain_xml(self, tmp_path):
        """Parsing the .gz and plain .xml versions of the fixture yields identical results."""
        links_xml = wordnet_links(_write_xml(tmp_path))
        links_gz = wordnet_links(_write_gz(tmp_path))
        assert sorted(links_xml) == sorted(links_gz), (
            "Gzip and plain XML parsing produced different results"
        )
