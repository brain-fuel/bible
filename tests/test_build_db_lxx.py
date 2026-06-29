"""Tests for LXX extension of build_db: verses, tokens, mt_lxx table, nullable-strong lexicon."""
import sqlite3
from tools.build_db import build


def test_mt_lxx_table_and_lxx_tokens(tmp_path):
    db = tmp_path / "t.sqlite"
    build(db, load_relations=False)
    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "mt_lxx" in names
    lxx_tokens = con.execute("SELECT COUNT(*) FROM tokens WHERE testament='lxx'").fetchone()[0]
    assert lxx_tokens > 0


def test_h7225_maps_to_g0746(tmp_path):
    """H7225 (Hebrew 'beginning') should render as G0746 (ἀρχή) in the LXX bridge."""
    db = tmp_path / "t.sqlite"
    build(db, load_relations=False)
    con = sqlite3.connect(db)
    lxx_strongs = {
        r[0] for r in con.execute(
            "SELECT lxx_strong FROM mt_lxx WHERE mt_strong='H7225'"
        ).fetchall()
    }
    assert "G0746" in lxx_strongs, (
        f"Expected G0746 (ἀρχή) among H7225's LXX renderings, got: {lxx_strongs}"
    )


def test_null_strong_lexicon_queryable_by_lemma(tmp_path):
    """LXX-only lemma entries (strong=null) must be loadable and queryable by lemma."""
    db = tmp_path / "t.sqlite"
    build(db, load_relations=False)
    con = sqlite3.connect(db)
    null_count = con.execute(
        "SELECT COUNT(*) FROM lexicon WHERE strong IS NULL"
    ).fetchone()[0]
    assert null_count > 0, "Expected null-strong lexicon entries for LXX-only lemmas"
    # Query by lemma: εὔρωστος is a known LXX-only lemma entry (lemma-000be90419d6.json)
    row = con.execute(
        "SELECT lemma, lang FROM lexicon WHERE lemma = 'εὔρωστος'"
    ).fetchone()
    assert row is not None, "εὔρωστος lemma not found in lexicon"
    assert row[1] == "grc"
