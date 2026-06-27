"""
build_db.py -- Build the derived SQLite token DB from canonical CoNLL-U + lexicon + L0 corpus.

The DB is a pure projection: deterministic, idempotent, rebuildable.
It holds no truth the canonical files lack. Never hand-edit it.

Usage:
    python -m tools.build_db          # writes data/tokens.sqlite
    from tools.build_db import build  # build(path) for tests
"""

import json
import sqlite3
from pathlib import Path

from tools.conllu import parse_file

ROOT = Path(__file__).parent.parent  # repo root: tools/ is one level down


# ---------------------------------------------------------------------------
# MISC helpers
# ---------------------------------------------------------------------------

def misc_field(misc: str, key: str) -> "str | None":
    """Pull a single key out of a CoNLL-U MISC string.

    Args:
        misc: raw MISC column value, e.g. ``"Strong=G1722|Translit=en"`` or ``"_"``.
        key:  key name, e.g. ``"Strong"``, ``"Translit"``, ``"Align"``.

    Returns:
        The value string if found and non-empty, else ``None``.
    """
    if not misc or misc == "_":
        return None
    for part in misc.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k == key:
                return v if v else None
    return None


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verses (
    ref       TEXT PRIMARY KEY,
    testament TEXT,
    book      TEXT,
    chapter   INTEGER,
    verse     INTEGER,
    kjv       TEXT,
    vulgate   TEXT,
    greek     TEXT,
    hebrew    TEXT
);

CREATE TABLE IF NOT EXISTS lexicon (
    strong   TEXT PRIMARY KEY,
    lemma    TEXT,
    translit TEXT,
    lang     TEXT,
    pos      TEXT,
    root     TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ref        TEXT REFERENCES verses(ref),
    idx        TEXT,
    range      TEXT,
    form       TEXT,
    lemma      TEXT,
    strong     TEXT REFERENCES lexicon(strong),
    upos       TEXT,
    xpos       TEXT,
    feats      TEXT,
    translit   TEXT,
    align_note TEXT
);

CREATE TABLE IF NOT EXISTS glosses (
    strong TEXT REFERENCES lexicon(strong),
    lang   TEXT,
    text   TEXT,
    src    TEXT
);

CREATE TABLE IF NOT EXISTS senses (
    strong   TEXT REFERENCES lexicon(strong),
    sense_id INTEGER,
    gloss_en TEXT,
    domain   TEXT
);

CREATE TABLE IF NOT EXISTS domains (
    strong TEXT REFERENCES lexicon(strong),
    domain TEXT
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_tokens_strong  ON tokens(strong);
CREATE INDEX IF NOT EXISTS idx_tokens_ref     ON tokens(ref);
CREATE INDEX IF NOT EXISTS idx_domains_domain ON domains(domain);
"""


# ---------------------------------------------------------------------------
# Populate helpers
# ---------------------------------------------------------------------------

def _load_verses(con: sqlite3.Connection) -> None:
    """Insert one row per verse from bible/nt/**/*.json and bible/ot/**/*.json."""
    for testament in ("nt", "ot"):
        base = ROOT / "bible" / testament
        for chap_file in sorted(base.glob("*/*.json")):
            try:
                data = json.loads(chap_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            book = data.get("book_id", chap_file.parent.name)
            chapter = int(chap_file.stem)  # "001" -> 1
            for v in data.get("verses", []):
                verse_num = v["verse"]
                ref = f"{book}.{chapter}.{verse_num}"
                con.execute(
                    "INSERT OR IGNORE INTO verses"
                    "(ref, testament, book, chapter, verse, kjv, vulgate, greek, hebrew)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        ref,
                        testament,
                        book,
                        chapter,
                        verse_num,
                        v.get("king_james"),
                        v.get("latin_vulgate"),
                        v.get("greek_textus_receptus"),
                        v.get("hebrew_masoretic"),
                    ),
                )


def _load_lexicon(con: sqlite3.Connection) -> None:
    """Insert lexicon entries from lexicon/grc/*.json and lexicon/hbo/*.json."""
    for lex_file in sorted((ROOT / "lexicon").glob("**/*.json")):
        try:
            entry = json.loads(lex_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        strong = entry.get("strong")
        if not strong:
            continue
        con.execute(
            "INSERT OR IGNORE INTO lexicon(strong, lemma, translit, lang, pos, root)"
            " VALUES (?,?,?,?,?,?)",
            (
                strong,
                entry.get("lemma"),
                entry.get("translit"),
                entry.get("lang"),
                entry.get("pos"),
                entry.get("root"),
            ),
        )
        for gloss_lang, gl_list in entry.get("glosses", {}).items():
            for gl in gl_list:
                con.execute(
                    "INSERT INTO glosses(strong, lang, text, src) VALUES (?,?,?,?)",
                    (strong, gloss_lang, gl.get("text"), gl.get("src")),
                )
        for sense in entry.get("senses", []):
            con.execute(
                "INSERT INTO senses(strong, sense_id, gloss_en, domain) VALUES (?,?,?,?)",
                (
                    strong,
                    sense.get("id"),
                    sense.get("gloss_en"),
                    sense.get("domain"),
                ),
            )
        for domain in entry.get("domains", []):
            con.execute(
                "INSERT INTO domains(strong, domain) VALUES (?,?)",
                (strong, domain),
            )


def _load_tokens(con: sqlite3.Connection) -> None:
    """Insert tokens from morph/**/*.conllu."""
    for conllu_file in sorted((ROOT / "morph").glob("**/*.conllu")):
        try:
            sentences = parse_file(conllu_file)
        except Exception:
            continue
        for ref, toks in sentences:
            for tok in toks:
                idx = tok.idx
                # range = the "5-6" style ID for multiword tokens, else NULL
                rng = idx if ("-" in idx and all(p.isdigit() for p in idx.split("-", 1))) else None
                strong = misc_field(tok.misc, "Strong")
                translit = misc_field(tok.misc, "Translit")
                align_note = misc_field(tok.misc, "Align")
                feats = None if tok.feats == "_" else tok.feats
                upos = None if tok.upos == "_" else tok.upos
                xpos = None if tok.xpos == "_" else tok.xpos
                lemma = None if tok.lemma == "_" else tok.lemma
                con.execute(
                    "INSERT INTO tokens"
                    "(ref, idx, range, form, lemma, strong, upos, xpos, feats, translit, align_note)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (ref, idx, rng, tok.form, lemma, strong, upos, xpos, feats, translit, align_note),
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build(db_path: "str | Path") -> None:
    """Create schema and populate from canonical files in one transaction.

    Args:
        db_path: Path to write the SQLite database.  Will be created or
                 overwritten.  ``data/tokens.sqlite`` by default when run
                 as a module.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove stale DB so the build is idempotent (avoids PK conflicts on re-run)
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)
    try:
        # DDL -- executescript auto-commits; that is fine here since we haven't
        # started our data transaction yet.
        con.executescript(_SCHEMA)

        # All data inserts in a single transaction
        with con:
            _load_verses(con)
            _load_lexicon(con)
            _load_tokens(con)
            # Indexes (inside the transaction so they build under WAL if needed)
            for stmt in _INDEXES.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    con.execute(stmt)
    finally:
        con.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    out = ROOT / "data" / "tokens.sqlite"
    print(f"Building {out} ...")
    t0 = time.time()
    build(out)
    elapsed = time.time() - t0

    # Quick summary
    con = sqlite3.connect(out)
    for tbl in ("verses", "tokens", "lexicon", "glosses", "senses", "domains"):
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:10s}: {n:>8,}")
    con.close()
    print(f"Done in {elapsed:.1f}s")
