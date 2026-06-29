"""tests/test_mine_lexica.py — TDD tests for the in-repo lexica cross-reference miner.

Covers:
  4a. Strong's gloss-text cross-refs (plan's verbatim test + gloss-regex fallback)
  4c. BDB reverse-map resolution (synthetic XML fixtures → H↔H edge)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tools.relations.mine_lexica import strongs_crossref_edges, _load_bdb_reverse_map, _mine_bdb_xrefs


# ---------------------------------------------------------------------------
# 4a — Strong's cross-ref tests (plan's verbatim test)
# ---------------------------------------------------------------------------

def test_direct_strongs_crossref_edge():
    """Plan's verbatim test: pre-extracted xref_strongs list → one synonym edge."""
    # an Abbott-Smith entry for G0026 that says "compare G5360"
    entries = [{"strong": "G0026", "lemma": "ἀγάπη", "xref_strongs": ["G5360"]}]
    edges = strongs_crossref_edges(entries, source="abbott-smith")
    assert len(edges) == 1
    e = edges[0]
    assert {e.src, e.dst} == {"G0026", "G5360"} and e.rel in ("synonym", "related")
    assert e.source == "abbott-smith" and e.method == "mined"


def test_strongs_crossref_from_gloss_text():
    """Fallback path: no xref_strongs → regex extracts from glosses.en text.

    G0032 (ἄγγελος) has gloss text containing 'compare G0034', and both keys
    exist in the committed lexicon.
    """
    entries = [
        {
            "strong": "G0032",
            "lemma": "ἄγγελος",
            "glosses": {
                "en": [
                    {
                        "text": "from a derived form of G0071 (compare G0034); a messenger",
                        "src": "strongs-greek",
                    }
                ]
            },
        }
    ]
    # G0034 exists in committed lexicon; the source key G0032 also exists.
    # 4a Strong's gloss-text cross-refs are extracted from the ALREADY-BUILT
    # committed lexicon, so they must carry method="derived" (per
    # FORMATS-relations.md §4a + edge schema), like shared-root/domain-sibling.
    edges = strongs_crossref_edges(entries, source="strongs-greek", method="derived")
    assert len(edges) == 1
    e = edges[0]
    assert {e.src, e.dst} == {"G0032", "G0034"}
    assert e.rel == "synonym"
    assert e.source == "strongs-greek"
    assert all(e.method == "derived" for e in edges)


def test_strongs_crossref_self_loop_skipped():
    """Self-loops (target == source key) must be skipped."""
    entries = [
        {
            "strong": "G0025",
            "lemma": "ἀγαπάω",
            # Artificial: entry "compares" itself — should be ignored
            "xref_strongs": ["G0025"],
        }
    ]
    edges = strongs_crossref_edges(entries, source="strongs-greek")
    assert edges == []


def test_strongs_crossref_unknown_target_skipped():
    """Target codes not in lexicon_keys() must be silently skipped."""
    entries = [
        {
            "strong": "G0025",
            "lemma": "ἀγαπάω",
            "xref_strongs": ["G9999"],  # G9999 does not exist in the lexicon
        }
    ]
    edges = strongs_crossref_edges(entries, source="strongs-greek")
    assert edges == []


def test_strongs_crossref_dedup_same_pair():
    """Duplicate (src, dst, rel, source) pairs deduplicate to max rank."""
    # Two entries both cross-referencing the same target pair
    entries = [
        {
            "strong": "G0026",
            "lemma": "ἀγάπη",
            "glosses": {
                "en": [
                    # Two gloss texts both mentioning G5360 → dedup to one edge
                    {"text": "compare G5360; also cf. G5360", "src": "strongs-greek"}
                ]
            },
        }
    ]
    edges = strongs_crossref_edges(entries, source="strongs-greek")
    # Even though G5360 appears twice, dedup yields one edge
    assert len(edges) == 1


# ---------------------------------------------------------------------------
# 4c — BDB reverse-map test (synthetic XML fixtures)
# ---------------------------------------------------------------------------

_BDB_LEXINDEX_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <index xmlns="http://openscriptures.github.com/morphhb/namespace"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://openscriptures.github.com/morphhb/namespace LiSchema.xsd">
      <part xml:lang="heb">
        <entry id="aaa">
          <w xlit="ab">אָב</w> <pos>N</pos> <def>father</def>
          <xref bdb="test.aa.aa" strong="1"/>
        </entry>
        <entry id="aab">
          <w xlit="ah">אֵם</w> <pos>N</pos> <def>mother</def>
          <xref bdb="test.aa.ab" strong="517"/>
        </entry>
      </part>
    </index>
""")

_BDB_ENTRIES_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <lexicon xmlns="http://openscriptures.github.com/morphhb/namespace"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xsi:schemaLocation="http://openscriptures.github.com/morphhb/namespace BdbSchema.xsd">
      <part id="a" title="א" xml:lang="heb">
        <section id="test.aa">
          <entry id="test.aa.aa">
            <w>אָב</w> cf. <w src="test.aa.ab">אֵם</w>
            <status p="1">done</status>
          </entry>
          <entry id="test.aa.ab">
            <w>אֵם</w> <def>mother</def>
            <status p="1">done</status>
          </entry>
        </section>
      </part>
    </lexicon>
""")


def test_bdb_reverse_map_resolution(tmp_path: Path):
    """Synthetic LexicalIndex + BDB → expected H0001 ↔ H0517 edge."""
    # Write synthetic XML files to tmp_path
    lexindex_path = tmp_path / "LexicalIndex.xml"
    bdb_path = tmp_path / "BrownDriverBriggs.xml"
    lexindex_path.write_text(_BDB_LEXINDEX_XML, encoding="utf-8")
    bdb_path.write_text(_BDB_ENTRIES_XML, encoding="utf-8")

    # Build reverse map: bdb_id → H####
    reverse_map = _load_bdb_reverse_map(lexindex_path)
    assert reverse_map == {"test.aa.aa": "H0001", "test.aa.ab": "H0517"}

    # Mine cross-refs — pass explicit valid_keys so test is hermetic
    valid_keys = {"H0001", "H0517"}
    edges = _mine_bdb_xrefs(bdb_path, reverse_map, valid_keys=valid_keys)

    assert len(edges) == 1
    e = edges[0]
    assert {e.src, e.dst} == {"H0001", "H0517"}
    assert e.rel == "synonym"
    assert e.source == "bdb"
    assert e.method == "mined"


def test_bdb_no_self_loops(tmp_path: Path):
    """BDB cross-ref from an entry to itself must be skipped."""
    lexindex_xml = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <index xmlns="http://openscriptures.github.com/morphhb/namespace">
          <part xml:lang="heb">
            <entry id="aaa">
              <xref bdb="test.xa" strong="1"/>
            </entry>
          </part>
        </index>
    """)
    bdb_xml = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <lexicon xmlns="http://openscriptures.github.com/morphhb/namespace">
          <part id="a" title="א" xml:lang="heb">
            <section id="test">
              <entry id="test.xa">
                <w>אָב</w> cf. <w src="test.xa">אָב</w>
              </entry>
            </section>
          </part>
        </lexicon>
    """)
    li = tmp_path / "LexicalIndex.xml"
    bdb = tmp_path / "BDB.xml"
    li.write_text(lexindex_xml, encoding="utf-8")
    bdb.write_text(bdb_xml, encoding="utf-8")

    reverse_map = _load_bdb_reverse_map(li)
    edges = _mine_bdb_xrefs(bdb, reverse_map, valid_keys={"H0001"})
    assert edges == []
