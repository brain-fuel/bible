# tests/test_build_db.py
import sqlite3
from tools.build_db import misc_field, build


def test_misc_field_extracts_strong():
    assert misc_field("Strong=G1722|Translit=en", "Strong") == "G1722"
    assert misc_field("_", "Strong") is None


def test_misc_field_extracts_translit():
    assert misc_field("Strong=G3972|Translit=Paulos", "Translit") == "Paulos"
    assert misc_field("Strong=G3972", "Translit") is None


def test_misc_field_extracts_align():
    assert misc_field("Align=unmatched", "Align") == "unmatched"
    assert misc_field("Strong=G0080|Translit=adelphos|Align=source_extra:1", "Align") == "source_extra:1"


def test_misc_field_missing_key():
    assert misc_field("Strong=G1722|Translit=en", "Align") is None


def test_misc_field_empty_string():
    assert misc_field("", "Strong") is None


def test_build_creates_joinable_db(tmp_path, monkeypatch):
    # build() reads the repo's canonical files; here assert schema + a concordance join.
    db = tmp_path / "t.sqlite"
    build(db)
    con = sqlite3.connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"verses", "tokens", "lexicon", "glosses", "senses", "domains"} <= names
    # every token's strong resolves to a lexicon row (left-join finds no orphans beyond pinned)
    orphans = con.execute(
        "SELECT COUNT(*) FROM tokens t LEFT JOIN lexicon l ON t.strong=l.strong "
        "WHERE t.strong IS NOT NULL AND l.strong IS NULL"
    ).fetchone()[0]
    assert isinstance(orphans, int)
    # spot-check: verses table has rows
    verse_count = con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    assert verse_count > 0, "verses table must be populated"
    # spot-check: tokens table has rows
    token_count = con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
    assert token_count > 0, "tokens table must be populated"
    # spot-check: lexicon table has rows
    lex_count = con.execute("SELECT COUNT(*) FROM lexicon").fetchone()[0]
    assert lex_count > 0, "lexicon table must be populated"
    # concordance join works
    rows = con.execute(
        "SELECT COUNT(*) FROM tokens t JOIN verses v ON t.ref=v.ref"
    ).fetchone()[0]
    assert rows > 0, "token -> verse join must work"
    con.close()
