"""lexkeys.py — Lexical key helpers for relation endpoints.

A "lexkey" is the canonical identifier for a lexical entry used as a node in
the relation graph:
  - Entries with a Strong number use the Strong string (e.g. "G0026").
  - LXX-only entries with no Strong number use "lemma-<sha1[:12]>".

The slug algorithm MUST match tools/build_lexicon.py:_lemma_slug exactly
(sha1 of raw UTF-8 bytes, no NFC normalisation, hex[:12], prefixed "lemma-").
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # repo root (tools/relations/ -> tools/ -> root)


def slug(lemma: str) -> str:
    """Return "lemma-" + sha1(lemma.encode("utf-8")).hexdigest()[:12].

    Replicates tools/build_lexicon.py:_lemma_slug.  The raw (non-NFC) lemma
    bytes are hashed so the slug is stable across Unicode-normalisation choices.
    """
    return "lemma-" + hashlib.sha1(lemma.encode("utf-8")).hexdigest()[:12]


def key_for(entry: dict) -> str:
    """Return the lexkey for a lexicon entry dict.

    Returns entry['strong'] if non-null/non-empty, else the lemma slug.
    """
    strong = entry.get("strong") or None
    if strong:
        return strong
    return slug(entry.get("lemma", ""))


def lexicon_keys() -> "set[str]":
    """Return the set of all valid endpoint keys from lexicon/grc/*.json + lexicon/hbo/*.json.

    For each entry: its Strong number (e.g. "G0026") if present, else its
    "lemma-<slug>" slug.  Scanning both lang directories under lexicon/.
    """
    keys: set[str] = set()
    for lex_file in sorted((ROOT / "lexicon").glob("**/*.json")):
        try:
            entry = json.loads(lex_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        keys.add(key_for(entry))
    return keys
