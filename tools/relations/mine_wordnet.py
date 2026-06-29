"""mine_wordnet.py — Open English WordNet synonym/antonym miner.

Parses the WN-LMF-1.3 XML (Open English WordNet 2024 edition) and emits
relation edges by bridging WordNet writtenForms to biblical lemma keys through
the gloss-bridge engine (``gloss_bridge.mine_relations``).

Source: Open English WordNet 2024, CC-BY 4.0
  https://github.com/globalwordnet/english-wordnet

CLI usage::

    python -m tools.relations.mine_wordnet

Writes two source-tagged JSONL files::

    relations/derived/open-english-wordnet.synonym.jsonl
    relations/derived/open-english-wordnet.antonym.jsonl

Design notes
------------
**XML structure (WN-LMF-1.3):**

- ``<LexicalEntry id="oewn-love-n">`` contains ``<Lemma writtenForm="love"/>``
  and one or more ``<Sense id="oewn-love__1.12.00.." synset="oewn-07558676-n">``
  elements.  Sense elements may carry ``<SenseRelation relType="antonym"
  target="oewn-hate__1.12.00.."/>`` children.

- ``<Synset members="oewn-love-n oewn-affection-n ...">`` lists
  **LexicalEntry IDs** (not Sense IDs) as space-separated values.

**Synonym extraction:**
  Each Synset ``members`` attribute lists LexicalEntry IDs.  Look up the
  writtenForm for each member from a ``entry_id → writtenForm`` map built
  during the LexicalEntry pass.  Emit pairwise synonym links for all pairs
  within each Synset (all 2-combinations).

**Antonym extraction:**
  Antonyms are Sense-level (inside ``<Sense>/<SenseRelation relType="antonym">``).
  The ``target`` attribute is a Sense ID (e.g. ``oewn-hate__1.12.00..``).
  Build a ``sense_id → writtenForm`` map during the LexicalEntry pass; resolve
  targets after the full parse.

**Memory:**
  Uses ``xml.etree.ElementTree.iterparse`` (streaming) and clears processed
  elements to keep memory bounded.  The ``sense_id → writtenForm`` and
  ``entry_id → writtenForm`` maps are the only in-memory structures that grow
  with the file size.  At 161,705 LexicalEntry elements with ~2 senses each,
  these maps hold ~484,000 string pairs — acceptable on any modern system.

**base_rank rationale:**
  ``base_rank = 40000``  (with engine ``FANOUT_PENALTY_SCALE = 2500``)

  WordNet is a high-quality curated lexicon, but the gloss bridge introduces
  *polysemy*: a writtenForm like "love" maps to many biblical lemma keys, so a
  single WordNet link can fan out into a large cross-product of vague edges.
  The engine's fanout penalty (``round(2500 × log2(fanout))``) downweights
  these; base_rank is the ceiling reached only by a precise 1↔1 (fanout=1)
  match.

  Math (threshold = DEFAULT_RANK_THRESHOLD = 32768):
    - fanout=1  → rank 40000                       (ABOVE — precise match)
    - fanout=2  → 40000 − 2500          = 37500    (above)
    - fanout=4  → 40000 − 5000          = 35000    (above)
    - crossover: 40000 − 2500·log2(f) = 32768  ⇒  f ≈ 7.4
    - fanout≥8  → rank ≤ 32500                     (BELOW)
    - fanout=32 (a few dozen) → 40000 − 12500 = 27500  (well below)

  So precise matches land above the threshold (default-view visible) while
  high-fanout, many↔many matches fall below it — a meaningful gradation rather
  than the previous flat "everything above".  40000 sits below domain-sibling
  depth-2 (40960) and shared-root (65535): root > domain-sibling > precise
  WordNet > fuzzy WordNet.  Task 10 re-validates against observed histograms.

**Deduplication:**
  ``mine_relations`` may emit identical edges when multiple synonym/antonym
  links from the cross-product of two overlapping gloss-index entries resolve
  to the same (src, dst, rel, source) tuple (e.g. "hate → love" and
  "love → hate" both produce the same canonically-oriented edge).  Edges are
  deduped as a ``set[Edge]`` before writing (Edge is a frozen dataclass, so
  hashing is exact-match on all fields).
"""

from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from itertools import combinations
from pathlib import Path
from typing import IO
from xml.etree.ElementTree import iterparse

from tools.relations.edge import Edge, write_jsonl
from tools.relations.gloss_bridge import gloss_term_index, mine_relations
from tools.relations.lexkeys import key_for

ROOT = Path(__file__).parent.parent.parent  # repo root

# Cached WordNet file (gitignored; auto-downloaded on first use)
_WN_PATH = (
    ROOT / "data" / "cache" / "relations" / "wordnet" / "english-wordnet-2024.xml.gz"
)

# Download URL for the cached file
_WN_URL = (
    "https://github.com/globalwordnet/english-wordnet/releases/download/"
    "2024-edition/english-wordnet-2024.xml.gz"
)


# ---------------------------------------------------------------------------
# Cache download helper
# ---------------------------------------------------------------------------

def _cache_download(dest: Path, url: str, label: str) -> None:
    """Download ``url`` to ``dest`` if ``dest`` does not already exist.

    Creates parent directories as needed.  Skips the download if ``dest``
    already exists (idempotent).  Raises :exc:`RuntimeError` on any network
    or I/O failure so that callers never silently produce empty output.
    """
    if dest.exists():
        print(f"  [cache] {label} already cached at {dest.relative_to(ROOT)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [cache] Downloading {label} from {url} …", flush=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  [cache] Saved {dest.stat().st_size:,} bytes → {dest.relative_to(ROOT)}")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download {label}.\n"
            f"  URL:    {url}\n"
            f"  Target: {dest}\n"
            f"  Error:  {exc}\n"
            "Download the file manually and place it at the target path."
        ) from exc

# ---------------------------------------------------------------------------
# Rank constant
# ---------------------------------------------------------------------------

# Mined synonym/antonym rank ceiling (fanout=1 precise match).
# See module docstring for the full rationale + threshold math.
_WN_BASE_RANK: int = 40000

# Source label for all edges produced by this module.
_SOURCE: str = "open-english-wordnet"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wordnet_links(wn_path: "str | Path") -> list[tuple[str, str, str]]:
    """Parse the WordNet LMF XML and return (headword, related, rel) triples.

    Handles both plain ``.xml`` and gzip-compressed ``.xml.gz`` files by
    sniffing the file extension.

    Returns
    -------
    list of (headword, related, rel)
        ``rel`` is either ``"synonym"`` or ``"antonym"``.
        headwords are writtenForm strings as they appear in the XML (may be
        mixed-case; ``mine_relations`` normalises via ``_normalize_term``).
    """
    wn_path = Path(wn_path)

    # Choose open function based on extension
    def _open() -> IO[str]:
        suffix = wn_path.suffix.lower()
        if suffix == ".gz":
            return gzip.open(wn_path, "rt", encoding="utf-8")
        return wn_path.open("rt", encoding="utf-8")

    # Maps built during the LexicalEntry pass
    sense_to_form: dict[str, str] = {}   # sense_id   → writtenForm
    entry_to_form: dict[str, str] = {}   # entry_id   → writtenForm

    # Pending antonym resolutions: (source_writtenForm, target_sense_id)
    pending_antonyms: list[tuple[str, str]] = []

    # Synset member groups: list of [entry_id, ...]
    synset_member_groups: list[list[str]] = []

    with _open() as fh:
        context = iterparse(fh, events=("end",))
        for _event, elem in context:
            tag = elem.tag

            if tag == "LexicalEntry":
                entry_id = elem.get("id", "")
                lemma_elem = elem.find("Lemma")
                if lemma_elem is None:
                    elem.clear()
                    continue
                wf = lemma_elem.get("writtenForm", "")
                if not wf:
                    elem.clear()
                    continue

                entry_to_form[entry_id] = wf

                for sense in elem.findall("Sense"):
                    sid = sense.get("id", "")
                    if sid:
                        sense_to_form[sid] = wf
                    for sense_rel in sense.findall("SenseRelation"):
                        if sense_rel.get("relType") == "antonym":
                            target = sense_rel.get("target", "")
                            if target:
                                pending_antonyms.append((wf, target))

                elem.clear()

            elif tag == "Synset":
                members_str = elem.get("members", "")
                if members_str:
                    synset_member_groups.append(members_str.split())
                elem.clear()

    # -----------------------------------------------------------------------
    # Resolve and emit links
    # -----------------------------------------------------------------------
    links: list[tuple[str, str, str]] = []

    # Synonyms: all pairs of writtenForms within each Synset
    for members in synset_member_groups:
        forms = [entry_to_form[m] for m in members if m in entry_to_form]
        for form_a, form_b in combinations(forms, 2):
            links.append((form_a, form_b, "synonym"))

    # Antonyms: resolve target sense ID → writtenForm
    for source_form, target_sense_id in pending_antonyms:
        target_form = sense_to_form.get(target_sense_id)
        if target_form:
            links.append((source_form, target_form, "antonym"))

    return links


def build_wordnet() -> tuple[list[Edge], list[Edge]]:
    """Load lexicon entries, build the gloss index, and mine WordNet edges.

    Returns
    -------
    (synonym_edges, antonym_edges)
        Two lists of :class:`~tools.relations.edge.Edge` objects, one per
        relation type.  Edges within each list are deduplicated (set collapse).
    """
    # Load all lexicon entries (grc + hbo)
    entries: list[dict] = []
    for lex_file in sorted((ROOT / "lexicon").glob("**/*.json")):
        try:
            entry = json.loads(lex_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries.append(entry)

    idx = gloss_term_index(entries, lang="en")

    # Ensure cached source file is present (auto-download if missing)
    _cache_download(_WN_PATH, _WN_URL, "english-wordnet-2024.xml.gz")

    # Parse WordNet links
    links = wordnet_links(_WN_PATH)

    # Mine edges through the gloss bridge
    all_edges = mine_relations(
        idx=idx,
        headword_links=links,
        source=_SOURCE,
        method="mined",
        base_rank=_WN_BASE_RANK,
    )

    # Dedup: Edge is a frozen dataclass; set() collapses exact duplicates.
    # Duplicates arise because:
    #   a) both "love → hate" and "hate → love" antonym links appear in WordNet
    #      (both resolve to the same canonically-oriented edge after mine_relations)
    #   b) cross-products of overlapping index entries can yield identical Edge tuples
    deduped: set[Edge] = set(all_edges)

    synonym_edges = [e for e in deduped if e.rel == "synonym"]
    antonym_edges = [e for e in deduped if e.rel == "antonym"]

    return synonym_edges, antonym_edges


def main() -> None:
    """CLI entry point: build edges, write source-tagged JSONL, print summary."""
    derived_dir = ROOT / "relations" / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)

    syn_path = derived_dir / f"{_SOURCE}.synonym.jsonl"
    ant_path = derived_dir / f"{_SOURCE}.antonym.jsonl"

    print(f"Parsing {_WN_PATH.relative_to(ROOT)} …", flush=True)

    synonym_edges, antonym_edges = build_wordnet()

    write_jsonl(syn_path, synonym_edges)
    write_jsonl(ant_path, antonym_edges)

    print(f"synonym edges written : {len(synonym_edges):,}  →  {syn_path.relative_to(ROOT)}")
    print(f"antonym edges written : {len(antonym_edges):,}  →  {ant_path.relative_to(ROOT)}")

    # Spot-check: look for a known antonym pair (love/hate → G0026/G3404)
    # These are well-known Biblical Greek words whose TBESG glosses include
    # "love" (G0026 ἀγάπη, G5368 φιλέω) and "hate" (G3404 μισέω).
    known_pairs = [
        {"G0026", "G3404"},  # ἀγάπη / μισέω  (love / hate)
        {"G5368", "G3404"},  # φιλέω / μισέω   (love / hate)
        {"G5479", "G3077"},  # χαρά / λύπη      (joy / grief — if present)
    ]
    print("\nSpot-check (antonym edges for known Biblical lemma pairs):")
    ant_set = {(e.src, e.dst) for e in antonym_edges}
    found_any = False
    for pair in known_pairs:
        pair_sorted = tuple(sorted(pair))
        if pair_sorted in ant_set:
            a, b = pair_sorted
            print(f"  FOUND: {a} -- {b}  (antonym)")
            found_any = True
    if not found_any:
        print("  (none of the expected pairs found — check gloss coverage)")

    print("\nSpot-check (synonym edges):")
    syn_set = {(e.src, e.dst) for e in synonym_edges}
    syn_known = [
        {"G0026", "G5368"},  # ἀγάπη / φιλέω (both gloss as "love")
        {"G5479", "G2167"},  # χαρά / εὐφροσύνη (both gloss as "joy"/"gladness")
    ]
    for pair in syn_known:
        pair_sorted = tuple(sorted(pair))
        if pair_sorted in syn_set:
            a, b = pair_sorted
            print(f"  FOUND: {a} -- {b}  (synonym)")


if __name__ == "__main__":
    main()
