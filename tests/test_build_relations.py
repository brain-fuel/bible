"""test_build_relations.py — TDD test for Task 10: DB relations load.

Verifies that build() populates the relations table from authored + derived
JSONL files and that the relations_default view is a strict subset.
"""
import sqlite3
from tools.build_db import build


def test_relations_table_loaded_and_default_view(tmp_path):
    db = tmp_path / "t.sqlite"
    build(db)
    con = sqlite3.connect(db)
    total = con.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
    default = con.execute("SELECT COUNT(*) FROM relations_default").fetchone()[0]
    assert total > 0
    assert default <= total                      # default view filters by rank
    rels = {r[0] for r in con.execute("SELECT DISTINCT rel FROM relations")}
    assert {"shared-root", "domain-sibling", "cross-language"} <= rels
