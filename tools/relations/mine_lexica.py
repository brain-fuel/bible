"""mine_lexica.py — In-repo lexica cross-reference miner (Task 9).

Sources mined
-------------
4a. Strong's gloss-text compare/cf cross-refs (Greek + Hebrew)
    - Zero download — uses committed lexicon/grc/*.json and lexicon/hbo/*.json.
    - Extracts "compare G####" / "cf. H####" patterns from glosses.en[*].text,
      OR uses a pre-parsed ``xref_strongs`` list if present in the entry.
    - Coverage: ~89 Greek entries, ~167 Hebrew entries.

4b. Abbott-Smith via TBESG col 7 (Meaning)
    - Downloads TBESG.txt if not cached (CC-BY 4.0, STEPBible).
    - Parses Greek-script words after "see:" markers in col 7; resolves to G####
      via a lemma → Strong's map built from col 3 + col 0.
    - Direct key↔key edges (Greek-word resolved to G####, not gloss-bridged).
    - Source tag: "abbott-smith".

4c. BDB (Brown-Driver-Briggs Hebrew Lexicon)
    - Downloads BrownDriverBriggs.xml + LexicalIndex.xml from openscriptures if
      not cached (Public Domain).
    - Builds {bdb_entry_id → H####} reverse map from LexicalIndex.xml.
    - Mines <w src="bdb_id"> cross-references in BrownDriverBriggs.xml entries.
    - Direct key↔key H####↔H#### edges.
    - Source tag: "bdb".

Latin (Lewis & Short): DEFERRED.
    Two blockers: CC-BY-SA 4.0 license incompatibility, and zero Latin glosses
    in the committed lexicon (no GRC→Latin bridge). Skip with logged note.

rel value: "synonym" (NOT "related")
-------------------------------------
All cross-reference edges use rel="synonym". This satisfies the plan's test
assertion ``e.rel in ("synonym","related")`` AND stays inside the canonical
relation set {domain-sibling, shared-root, cross-language, synonym, antonym}.
"related" is NOT a valid rel per Task 11's validator. Do NOT change this.

Rank choice: XREF_RANK = 50000
---------------------------------
Direct key↔key cross-reference edges use rank=50000. This is:
  - ABOVE DEFAULT_RANK_THRESHOLD (32768): so these edges appear in the default
    view and aren't treated as weak noise-floor links.
  - WELL BELOW RANK_MAX (65535): "compare/see" is a weaker semantic signal than
    etymological identity (shared-root edges use 65535), so they deserve a lower
    rank. 50000 ≈ 76% of the scale is a reasonable "moderate strong" assignment.

CLI usage::

    python -m tools.relations.mine_lexica

Writes source-tagged JSONL files::

    relations/derived/strongs-greek.synonym.jsonl
    relations/derived/strongs-hebrew.synonym.jsonl
    relations/derived/bdb.synonym.jsonl
    relations/derived/abbott-smith.synonym.jsonl   (if 4b yields edges)
"""

from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

from tools.relations.edge import Edge, canonical_orient, write_jsonl
from tools.relations.lexkeys import key_for, lexicon_keys
from tools.relations.rank import DEFAULT_RANK_THRESHOLD, RANK_MAX, clamp_rank

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent.parent  # repo root

# Rank for all direct key↔key cross-reference edges.
# Above DEFAULT_RANK_THRESHOLD (32768) so these edges appear by default;
# below RANK_MAX (65535) since "compare/see" is weaker than etymological identity.
# See module docstring for full rationale.
XREF_RANK: int = 50000

# Regex to extract Strong's cross-refs from gloss text.
# Matches patterns like "compare G0025", "cf. H1234", "cf G5689"
_COMPARE_RE = re.compile(r"(?:compare|cf\.?)\s+([GH]\d{4})", re.IGNORECASE)

# Namespace for openscriptures HebrewLexicon XML files
_OBS_NS = "http://openscriptures.github.com/morphhb/namespace"
_OBS_TAG = f"{{{_OBS_NS}}}"

# Greek Unicode ranges: Basic Greek (U+0370–U+03FF) and Extended (U+1F00–U+1FFF)
_GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]{2,}")

# Cache paths
_CACHE_BDB = ROOT / "data" / "cache" / "relations" / "bdb"
_BDB_PATH = _CACHE_BDB / "BrownDriverBriggs.xml"
_LEXINDEX_PATH = _CACHE_BDB / "LexicalIndex.xml"
_TBESG_PATH = ROOT / "data" / "cache" / "morph" / "raw" / "TBESG.txt"

# Download URLs
_URL_BDB = "https://raw.githubusercontent.com/openscriptures/HebrewLexicon/master/BrownDriverBriggs.xml"
_URL_LEXINDEX = "https://raw.githubusercontent.com/openscriptures/HebrewLexicon/master/LexicalIndex.xml"
_URL_TBESG = (
    "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
    "Lexicons/TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20"
    "for%20Greek%20-%20STEPBible.org%20CC%20BY.txt"
)


# ---------------------------------------------------------------------------
# 4a — Strong's cross-refs
# ---------------------------------------------------------------------------

def strongs_crossref_edges(
    entries: list[dict],
    source: str,
    method: str = "mined",
) -> list[Edge]:
    """Emit direct synonym edges from Strong's-code cross-references.

    For each entry:
    - If ``entry["xref_strongs"]`` is a non-empty list, use it directly.
    - Otherwise, regex-scan ``glosses.en[*].text`` for
      ``compare G####`` / ``cf. H####`` patterns.

    Both the entry's own key and each target code are validated against
    ``lexicon_keys()``; any target not present in the lexicon is skipped.
    Self-loops (target == source key) are skipped.

    Edges are deduped to one per (src, dst, rel, source), keeping max rank.

    Parameters
    ----------
    entries:
        List of lexicon entry dicts.
    source:
        Provenance source string (e.g. ``"strongs-greek"`` or
        ``"abbott-smith"``).
    method:
        Provenance method string.  Defaults to ``"mined"`` (so callers that
        feed externally-derived xref lists, e.g. the 4b Abbott-Smith path, get
        the correct tag without extra args).  The 4a Strong's gloss-text path
        passes ``method="derived"`` because those cross-refs are extracted from
        the ALREADY-BUILT committed lexicon (consistent with shared-root /
        domain-sibling, per FORMATS-relations.md §4a + the edge schema).

    Returns
    -------
    list[Edge]
        Direct synonym edges, deduplicated.
    """
    valid = lexicon_keys()
    raw_edges: list[Edge] = []

    for entry in entries:
        src_key = key_for(entry)
        if src_key not in valid:
            continue

        # Collect target codes: prefer pre-parsed xref_strongs
        xref_list: list[str] = entry.get("xref_strongs") or []
        if not xref_list:
            # Fallback: extract from gloss text
            for gloss in entry.get("glosses", {}).get("en", []):
                for m in _COMPARE_RE.finditer(gloss.get("text", "")):
                    code = m.group(1).upper()
                    # Normalise: ensure 4-digit zero-padding
                    letter = code[0]
                    digits = code[1:]
                    code_norm = f"{letter}{int(digits):04d}"
                    xref_list.append(code_norm)

        for tgt_code in xref_list:
            # Normalise code (e.g. "G25" → "G0025")
            m_norm = re.match(r"^([GH])(\d+)$", tgt_code.strip())
            if not m_norm:
                continue
            tgt_key = f"{m_norm.group(1)}{int(m_norm.group(2)):04d}"

            if tgt_key == src_key:
                continue  # skip self-loops
            if tgt_key not in valid:
                continue  # skip unknown targets

            src, dst = canonical_orient(src_key, tgt_key)
            raw_edges.append(
                Edge(
                    src=src,
                    dst=dst,
                    rel="synonym",
                    directed=False,
                    source=source,
                    method=method,
                    rank=XREF_RANK,
                    note=None,
                )
            )

    # Dedup (src, dst, rel, source) → keep max rank
    best: dict[tuple[str, str, str, str], Edge] = {}
    for e in raw_edges:
        k = (e.src, e.dst, e.rel, e.source)
        if k not in best or e.rank > best[k].rank:
            best[k] = e
    return list(best.values())


def _load_all_entries(lang: str) -> list[dict]:
    """Load all lexicon entries for a language directory (grc or hbo)."""
    entries = []
    lex_dir = ROOT / "lexicon" / lang
    for f in sorted(lex_dir.glob("*.json")):
        try:
            entries.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return entries


# ---------------------------------------------------------------------------
# 4c — BDB (Brown-Driver-Briggs)
# ---------------------------------------------------------------------------

def _load_bdb_reverse_map(lexindex_path: "str | Path") -> dict[str, str]:
    """Build {bdb_entry_id → H####} from LexicalIndex.xml.

    Parses ``<xref bdb="..." strong="NNN"/>`` elements.  Only entries whose
    ``strong`` attribute is a positive integer are included (skips those with
    no Strong number).

    Parameters
    ----------
    lexindex_path:
        Path to LexicalIndex.xml (namespace-aware XML).

    Returns
    -------
    dict[str, str]
        Maps BDB entry ID strings (e.g. ``"a.ae.ab"``) to Strong's key
        strings (e.g. ``"H0001"``).
    """
    lexindex_path = Path(lexindex_path)
    reverse: dict[str, str] = {}
    tree = ET.parse(lexindex_path)
    root = tree.getroot()

    for entry in root.iter(f"{_OBS_TAG}entry"):
        for xref in entry.findall(f"{_OBS_TAG}xref"):
            bdb_id = xref.get("bdb", "").strip()
            strong_str = xref.get("strong", "").strip()
            if not bdb_id or not strong_str:
                continue
            try:
                snum = int(strong_str)
                if snum <= 0:
                    continue
                reverse[bdb_id] = f"H{snum:04d}"
            except ValueError:
                pass

    return reverse


def _mine_bdb_xrefs(
    bdb_path: "str | Path",
    reverse_map: dict[str, str],
    valid_keys: "set[str] | None" = None,
) -> list[Edge]:
    """Mine H↔H synonym edges from BrownDriverBriggs.xml.

    For each ``<entry id="source_bdb_id">`` in the BDB XML:
    - Finds all child ``<w src="target_bdb_id">`` elements.
    - Resolves both IDs to H#### via ``reverse_map``.
    - Emits a direct synonym edge if both endpoints are in ``valid_keys``
      (or in ``lexicon_keys()`` if ``valid_keys`` is None) and are not equal.

    Edges are deduped to one per (src, dst, rel, source), keeping max rank.

    Parameters
    ----------
    bdb_path:
        Path to BrownDriverBriggs.xml.
    reverse_map:
        {bdb_id → H####} built by ``_load_bdb_reverse_map``.
    valid_keys:
        Explicit set of valid endpoint keys.  If None, calls
        ``lexicon_keys()`` (reads the committed lexicon directory).

    Returns
    -------
    list[Edge]
        H↔H synonym edges.
    """
    bdb_path = Path(bdb_path)
    if valid_keys is None:
        valid_keys = lexicon_keys()

    raw_edges: list[Edge] = []
    tree = ET.parse(bdb_path)
    root = tree.getroot()

    for entry in root.iter(f"{_OBS_TAG}entry"):
        entry_id = entry.get("id", "").strip()
        if not entry_id or entry_id not in reverse_map:
            continue
        src_key = reverse_map[entry_id]
        if src_key not in valid_keys:
            continue

        for w in entry.findall(f".//{_OBS_TAG}w"):
            tgt_bdb = w.get("src", "").strip()
            if not tgt_bdb:
                continue
            tgt_key = reverse_map.get(tgt_bdb)
            if not tgt_key:
                continue
            if tgt_key == src_key:
                continue  # skip self-loops
            if tgt_key not in valid_keys:
                continue

            src, dst = canonical_orient(src_key, tgt_key)
            raw_edges.append(
                Edge(
                    src=src,
                    dst=dst,
                    rel="synonym",
                    directed=False,
                    source="bdb",
                    method="mined",
                    rank=XREF_RANK,
                    note=None,
                )
            )

    # Dedup (src, dst, rel, source) → keep max rank
    best: dict[tuple[str, str, str, str], Edge] = {}
    for e in raw_edges:
        k = (e.src, e.dst, e.rel, e.source)
        if k not in best or e.rank > best[k].rank:
            best[k] = e
    return list(best.values())


def bdb_edges() -> list[Edge]:
    """Download BDB files if needed and mine H↔H synonym edges.

    Returns
    -------
    list[Edge]
        BDB synonym edges (empty list if download fails).
    """
    _cache_download(_BDB_PATH, _URL_BDB, "BrownDriverBriggs.xml")
    _cache_download(_LEXINDEX_PATH, _URL_LEXINDEX, "LexicalIndex.xml")

    if not _BDB_PATH.exists() or not _LEXINDEX_PATH.exists():
        print("  [bdb] WARNING: BDB files not available — skipping BDB mining.")
        return []

    print(f"  [bdb] Building reverse map from {_LEXINDEX_PATH.name} …", flush=True)
    reverse = _load_bdb_reverse_map(_LEXINDEX_PATH)
    print(f"  [bdb] Reverse map: {len(reverse):,} bdb_id → H#### entries", flush=True)

    print(f"  [bdb] Mining cross-refs from {_BDB_PATH.name} …", flush=True)
    edges = _mine_bdb_xrefs(_BDB_PATH, reverse)
    print(f"  [bdb] Resolved edges: {len(edges):,}", flush=True)
    return edges


# ---------------------------------------------------------------------------
# 4b — Abbott-Smith via TBESG col 7 (Meaning)
# ---------------------------------------------------------------------------

def _build_tbesg_lemma_map(tbesg_path: "str | Path") -> dict[str, str]:
    """Build {greek_lemma → G####} from TBESG.txt col 3 (lemma) + col 0 (eStrong).

    Only original Strong's range (G0001–G5624) is included.

    Parameters
    ----------
    tbesg_path:
        Path to TBESG.txt (UTF-8-BOM encoded, tab-separated).

    Returns
    -------
    dict[str, str]
        Maps Greek lemma strings to their G#### Strong's ID.
    """
    lemma_map: dict[str, str] = {}
    with open(tbesg_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or not re.match(r"G\d{4}", line):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            estrong = parts[0].strip()
            if not re.match(r"^G\d{4}$", estrong):
                continue
            try:
                snum = int(estrong[1:])
            except ValueError:
                continue
            if snum > 5624:
                continue
            strong_id = f"G{snum:04d}"
            lemma = parts[3].strip()
            if lemma:
                lemma_map[lemma] = strong_id
    return lemma_map


def abbott_smith_edges() -> list[Edge]:
    """Download TBESG if needed and mine Abbott-Smith cross-ref edges.

    Mines "see:" references from TBESG col 7 (Meaning / Abbott-Smith text).
    Greek-script words after "see:" markers are resolved via a lemma→G#### map.
    Edges are direct key↔key (not gloss-bridged) using rel="synonym".

    Returns
    -------
    list[Edge]
        Abbott-Smith synonym edges (empty list if TBESG unavailable or yield=0).
    """
    _cache_download(_TBESG_PATH, _URL_TBESG, "TBESG.txt")

    if not _TBESG_PATH.exists():
        print("  [abbott-smith] WARNING: TBESG.txt not available — skipping.")
        return []

    print(f"  [abbott-smith] Building lemma map from {_TBESG_PATH.name} …", flush=True)
    lemma_map = _build_tbesg_lemma_map(_TBESG_PATH)
    print(f"  [abbott-smith] Lemma map: {len(lemma_map):,} entries", flush=True)

    valid = lexicon_keys()

    # Parse col 7 for "see:" + Greek words, resolve to G####
    # Pattern: "see:" followed by optional whitespace, then Greek text up to
    # the first HTML tag, space, or punctuation.  Resolves via lemma_map.
    # This is BEST EFFORT; unresolvable references are silently skipped.
    _SEE_RE = re.compile(r"see[:\s]+", re.IGNORECASE)

    as_entries: list[dict] = []
    with open(_TBESG_PATH, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or not re.match(r"G\d{4}", line):
                continue
            parts = line.split("\t")
            if len(parts) < 8:
                continue
            estrong = parts[0].strip()
            if not re.match(r"^G\d{4}$", estrong):
                continue
            try:
                snum = int(estrong[1:])
            except ValueError:
                continue
            if snum > 5624:
                continue
            strong_id = f"G{snum:04d}"

            meaning = parts[7]
            xrefs: list[str] = []

            # Find "see:" references followed by Greek text
            for m in _SEE_RE.finditer(meaning):
                tail = meaning[m.end():]
                # Extract the first Greek-script word in the tail
                gm = _GREEK_RE.match(tail.lstrip())
                if gm:
                    candidate = gm.group(0)
                    tgt = lemma_map.get(candidate)
                    if tgt and tgt != strong_id:
                        xrefs.append(tgt)

            if xrefs:
                as_entries.append({"strong": strong_id, "xref_strongs": xrefs})

    print(
        f"  [abbott-smith] Entries with resolved see-refs: {len(as_entries):,}",
        flush=True,
    )

    if not as_entries:
        return []

    edges = strongs_crossref_edges(as_entries, source="abbott-smith")
    print(f"  [abbott-smith] Synonym edges: {len(edges):,}", flush=True)
    return edges


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _cache_download(dest: Path, url: str, label: str) -> None:
    """Download ``url`` to ``dest`` if ``dest`` does not already exist."""
    if dest.exists():
        print(f"  [cache] {label} already cached at {dest.relative_to(ROOT)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [cache] Downloading {label} from {url} …", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  [cache] Saved {dest.stat().st_size:,} bytes → {dest.relative_to(ROOT)}")
    except Exception as exc:
        print(f"  [cache] ERROR downloading {label}: {exc}")


# ---------------------------------------------------------------------------
# Top-level combiner
# ---------------------------------------------------------------------------

def build_lexica() -> list[Edge]:
    """Run all sub-sources and return combined synonym edges.

    Sub-sources (in order):
    1. 4a Greek: Strong's compare/cf cross-refs from lexicon/grc/*.json
    2. 4a Hebrew: Strong's compare/cf cross-refs from lexicon/hbo/*.json
    3. 4c BDB: H↔H cross-refs from BrownDriverBriggs.xml
    4. 4b Abbott-Smith: G↔G see-refs from TBESG col 7

    Latin (Lewis & Short) is DEFERRED: CC-BY-SA 4.0 incompatibility +
    zero glosses.la bridge. No action taken here.

    Returns
    -------
    list[Edge]
        All synonym edges from all sub-sources combined.
    """
    print("=" * 60)
    print("build_lexica() — in-repo lexica cross-reference miner")
    print("=" * 60)

    # 4a Greek
    print("\n[4a] Mining Strong's Greek compare-refs …", flush=True)
    grc_entries = _load_all_entries("grc")
    print(f"  Loaded {len(grc_entries):,} Greek lexicon entries", flush=True)
    # method="derived": extracted from the committed lexicon (built artifact),
    # like shared-root / domain-sibling — NOT mined from an external download.
    grc_edges = strongs_crossref_edges(
        grc_entries, source="strongs-greek", method="derived"
    )
    print(f"  → {len(grc_edges):,} synonym edges (strongs-greek)", flush=True)

    # 4a Hebrew
    print("\n[4a] Mining Strong's Hebrew compare-refs …", flush=True)
    hbo_entries = _load_all_entries("hbo")
    print(f"  Loaded {len(hbo_entries):,} Hebrew lexicon entries", flush=True)
    # method="derived": extracted from the committed lexicon (built artifact).
    hbo_edges = strongs_crossref_edges(
        hbo_entries, source="strongs-hebrew", method="derived"
    )
    print(f"  → {len(hbo_edges):,} synonym edges (strongs-hebrew)", flush=True)

    # 4c BDB
    print("\n[4c] Mining BDB Hebrew cross-refs …", flush=True)
    bdb_edge_list = bdb_edges()
    print(f"  → {len(bdb_edge_list):,} synonym edges (bdb)", flush=True)

    # 4b Abbott-Smith
    print("\n[4b] Mining Abbott-Smith cross-refs from TBESG col 7 …", flush=True)
    as_edges = abbott_smith_edges()
    print(f"  → {len(as_edges):,} synonym edges (abbott-smith)", flush=True)

    # Latin: DEFERRED
    print(
        "\n[Latin] Lewis & Short DEFERRED:"
        " CC-BY-SA 4.0 license incompatibility + no glosses.la bridge.",
        flush=True,
    )

    all_edges = grc_edges + hbo_edges + bdb_edge_list + as_edges
    print(f"\nTotal synonym edges across all sub-sources: {len(all_edges):,}", flush=True)
    return all_edges


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI: build all edges, write source-tagged JSONL, print summary."""
    derived_dir = ROOT / "relations" / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)

    all_edges = build_lexica()

    # Group by source for source-tagged output
    by_source: dict[str, list[Edge]] = {}
    for e in all_edges:
        by_source.setdefault(e.source, []).append(e)

    threshold = DEFAULT_RANK_THRESHOLD
    print("\n" + "=" * 60)
    print("Output summary")
    print("=" * 60)

    written_paths: list[Path] = []
    for src_name, edges in sorted(by_source.items()):
        out_path = derived_dir / f"{src_name}.synonym.jsonl"
        write_jsonl(out_path, edges)
        written_paths.append(out_path)

        above = sum(1 for e in edges if e.rank >= threshold)
        below = len(edges) - above
        print(f"\n{src_name}:")
        print(f"  synonym edges : {len(edges):,}  →  {out_path.relative_to(ROOT)}")
        print(f"  above threshold ({threshold}): {above:,}")
        print(f"  below threshold          : {below:,}")

    # Spot-check: known cross-ref pairs
    print("\nSpot-check (expected cross-ref pairs):")
    all_set = {(e.src, e.dst) for e in all_edges}
    known_pairs = [
        # 4a Greek: G0009 compares H0058
        ("G0009", "H0058"),
        # 4a Greek: G0025 compares G5689
        ("G0025", "G5689"),
        # 4a Greek: G0032 compares G0034 (from "compare G0034")
        ("G0032", "G0034"),
    ]
    for a, b in known_pairs:
        pair = tuple(sorted((a, b)))
        status = "FOUND" if pair in all_set else "not found"
        print(f"  {status}: {pair[0]} -- {pair[1]}")


if __name__ == "__main__":
    main()
