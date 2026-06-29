"""validate_relations.py — Relation-graph validator with pinned counts.

Loads the full relations/ tree (authored + derived) and asserts:
  - every edge endpoint is a valid lexicon key
  - no self-loops (src != dst)
  - every edge has provenance.source, provenance.method, and rank ∈ 0..65535
  - symmetric relations are canonically oriented (src <= dst) for the 4
    symmetric rels — cross-language is EXEMPTED (H####→G#### by design)
  - per-rel edge counts match pinned EXPECTED_<REL>_EDGES constants
  - per-source edge counts match pinned EXPECTED_<SOURCE>_EDGES constants
  - default-view count (rank >= DEFAULT_RANK_THRESHOLD) matches pinned constant

Exits nonzero on any drift.

Usage:
    python -m tools.validate_relations
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from tools.relations.edge import Edge, read_jsonl
from tools.relations.lexkeys import lexicon_keys
from tools.relations.rank import DEFAULT_RANK_THRESHOLD, RANK_MAX

ROOT = Path(__file__).parent.parent  # repo root
RELATIONS_DIR = ROOT / "relations"

# ---------------------------------------------------------------------------
# Pinned expected counts (observed from a clean build; update only after a
# deliberate, justified change to the relation builders).
# ---------------------------------------------------------------------------

# Per-rel counts (authored + derived combined)
EXPECTED_SHARED_ROOT_EDGES: int = 80904
EXPECTED_DOMAIN_SIBLING_EDGES: int = 1959593
EXPECTED_CROSS_LANGUAGE_EDGES: int = 691240
EXPECTED_SYNONYM_EDGES: int = 6909342  # 6909340 derived + 2 authored
EXPECTED_ANTONYM_EDGES: int = 1955929  # 1955927 derived + 2 authored

# Default-view count (rank >= DEFAULT_RANK_THRESHOLD = 32768)
EXPECTED_DEFAULT_VIEW: int = 2091882

# Per-source counts (across all rels)
EXPECTED_OPEN_ENGLISH_WORDNET: int = 5199108
EXPECTED_ROGET_1911: int = 3665461
EXPECTED_SDBH: int = 1956567
EXPECTED_MT_LXX_BRIDGE: int = 691240
EXPECTED_STRONGS_ROOT: int = 80904
EXPECTED_LOUW_NIDA: int = 3026
EXPECTED_ABBOTT_SMITH: int = 243
EXPECTED_BDB: int = 218
EXPECTED_STRONGS_HEBREW: int = 153
EXPECTED_STRONGS_GREEK: int = 84
EXPECTED_HAND: int = 4

# cross-language is the ONLY rel whose edges are NOT src<dst oriented.
# It stores src=H#### (Hebrew), dst=G#### (Greek) to preserve MT→LXX direction.
# "G" < "H" lexicographically, so cross-language edges are H>G by design.
SYMMETRIC_CANONICAL_RELS = {"shared-root", "domain-sibling", "synonym", "antonym"}


# ---------------------------------------------------------------------------
# Helper functions (unit-tested via tests/test_validate_relations.py)
# ---------------------------------------------------------------------------


def endpoints_resolve(edge: Edge, valid_keys: "set[str]") -> bool:
    """Return True if both edge.src and edge.dst are in valid_keys."""
    return edge.src in valid_keys and edge.dst in valid_keys


def no_self_loops(edge: Edge) -> bool:
    """Return True if edge.src != edge.dst (i.e. no self-loop)."""
    return edge.src != edge.dst


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_all_edges() -> list[Edge]:
    """Load all edges from relations/authored/**/*.jsonl + relations/derived/**/*.jsonl."""
    edges: list[Edge] = []
    for jsonl_file in sorted(RELATIONS_DIR.rglob("*.jsonl")):
        edges.extend(read_jsonl(jsonl_file))
    return edges


# ---------------------------------------------------------------------------
# Core validator
# ---------------------------------------------------------------------------


def validate() -> dict:
    """Validate the full relation graph and return a summary dict.

    Asserts all pinned invariants.  Returns a dict with counts and per-check
    pass/fail entries.  Raises AssertionError on any violation (so the caller
    can catch it, or let it propagate to exit nonzero).
    """
    summary: dict = {}

    # --- Load valid lexicon keys ---
    keys = lexicon_keys()
    summary["lexicon_key_count"] = len(keys)

    # --- Load all edges ---
    edges = load_all_edges()
    total = len(edges)
    summary["total_edges"] = total

    # --- Per-rel and per-source counts ---
    rel_counts: dict[str, int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)

    # --- Run checks ---
    bad_endpoints: list[str] = []
    self_loops: list[str] = []
    bad_provenance: list[str] = []
    bad_rank: list[str] = []
    bad_orient: list[str] = []
    default_view_count = 0

    for e in edges:
        rel_counts[e.rel] += 1
        source_counts[e.source] += 1

        if not endpoints_resolve(e, keys):
            bad_endpoints.append(f"{e.src}→{e.dst} ({e.rel})")

        if not no_self_loops(e):
            self_loops.append(f"{e.src} ({e.rel})")

        if not e.source or not e.method:
            bad_provenance.append(f"{e.src}→{e.dst} ({e.rel}): source={e.source!r} method={e.method!r}")

        if not (0 <= e.rank <= RANK_MAX):
            bad_rank.append(f"{e.src}→{e.dst} ({e.rel}): rank={e.rank}")

        if e.rel in SYMMETRIC_CANONICAL_RELS and e.src > e.dst:
            bad_orient.append(f"{e.src}→{e.dst} ({e.rel})")

        if e.rank >= DEFAULT_RANK_THRESHOLD:
            default_view_count += 1

    summary["rel_counts"] = dict(rel_counts)
    summary["source_counts"] = dict(source_counts)
    summary["default_view_count"] = default_view_count

    # --- Assert: no bad endpoints ---
    assert not bad_endpoints, (
        f"FAIL endpoints_resolve: {len(bad_endpoints)} edges have unknown endpoints "
        f"(first: {bad_endpoints[0]})"
    )
    summary["check_endpoints"] = "PASS"

    # --- Assert: no self-loops ---
    assert not self_loops, (
        f"FAIL no_self_loops: {len(self_loops)} self-loop edges "
        f"(first: {self_loops[0]})"
    )
    summary["check_self_loops"] = "PASS"

    # --- Assert: provenance complete ---
    assert not bad_provenance, (
        f"FAIL provenance: {len(bad_provenance)} edges missing source/method "
        f"(first: {bad_provenance[0]})"
    )
    summary["check_provenance"] = "PASS"

    # --- Assert: rank in range ---
    assert not bad_rank, (
        f"FAIL rank_range: {len(bad_rank)} edges outside 0..65535 "
        f"(first: {bad_rank[0]})"
    )
    summary["check_rank_range"] = "PASS"

    # --- Assert: canonical orientation (4 symmetric rels, NOT cross-language) ---
    assert not bad_orient, (
        f"FAIL canonical_orient: {len(bad_orient)} edges not in src<=dst order "
        f"(first: {bad_orient[0]})"
    )
    summary["check_canonical_orient"] = "PASS"

    # --- Assert: per-rel counts ---
    assert rel_counts.get("shared-root", 0) == EXPECTED_SHARED_ROOT_EDGES, (
        f"FAIL shared-root count: got {rel_counts.get('shared-root', 0):,}, "
        f"expected {EXPECTED_SHARED_ROOT_EDGES:,}"
    )
    assert rel_counts.get("domain-sibling", 0) == EXPECTED_DOMAIN_SIBLING_EDGES, (
        f"FAIL domain-sibling count: got {rel_counts.get('domain-sibling', 0):,}, "
        f"expected {EXPECTED_DOMAIN_SIBLING_EDGES:,}"
    )
    assert rel_counts.get("cross-language", 0) == EXPECTED_CROSS_LANGUAGE_EDGES, (
        f"FAIL cross-language count: got {rel_counts.get('cross-language', 0):,}, "
        f"expected {EXPECTED_CROSS_LANGUAGE_EDGES:,}"
    )
    assert rel_counts.get("synonym", 0) == EXPECTED_SYNONYM_EDGES, (
        f"FAIL synonym count: got {rel_counts.get('synonym', 0):,}, "
        f"expected {EXPECTED_SYNONYM_EDGES:,}"
    )
    assert rel_counts.get("antonym", 0) == EXPECTED_ANTONYM_EDGES, (
        f"FAIL antonym count: got {rel_counts.get('antonym', 0):,}, "
        f"expected {EXPECTED_ANTONYM_EDGES:,}"
    )
    summary["check_rel_counts"] = "PASS"

    # --- Assert: default-view count ---
    assert default_view_count == EXPECTED_DEFAULT_VIEW, (
        f"FAIL default_view count: got {default_view_count:,}, "
        f"expected {EXPECTED_DEFAULT_VIEW:,}"
    )
    summary["check_default_view"] = "PASS"

    # --- Assert: per-source counts ---
    _assert_source("open-english-wordnet", source_counts, EXPECTED_OPEN_ENGLISH_WORDNET)
    _assert_source("roget-1911", source_counts, EXPECTED_ROGET_1911)
    _assert_source("sdbh", source_counts, EXPECTED_SDBH)
    _assert_source("mt-lxx-bridge", source_counts, EXPECTED_MT_LXX_BRIDGE)
    _assert_source("strongs-root", source_counts, EXPECTED_STRONGS_ROOT)
    _assert_source("louw-nida", source_counts, EXPECTED_LOUW_NIDA)
    _assert_source("abbott-smith", source_counts, EXPECTED_ABBOTT_SMITH)
    _assert_source("bdb", source_counts, EXPECTED_BDB)
    _assert_source("strongs-hebrew", source_counts, EXPECTED_STRONGS_HEBREW)
    _assert_source("strongs-greek", source_counts, EXPECTED_STRONGS_GREEK)
    _assert_source("hand", source_counts, EXPECTED_HAND)
    summary["check_source_counts"] = "PASS"

    summary["overall"] = "PASS"
    return summary


def _assert_source(source: str, source_counts: dict, expected: int) -> None:
    """Assert that source_counts[source] == expected."""
    got = source_counts.get(source, 0)
    assert got == expected, (
        f"FAIL source '{source}' count: got {got:,}, expected {expected:,}"
    )


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point: validate and print summary. Exits nonzero on drift."""
    print("=" * 60)
    print("validate_relations — relation-graph integrity check")
    print(f"Relations dir: {RELATIONS_DIR}")
    print(f"DEFAULT_RANK_THRESHOLD: {DEFAULT_RANK_THRESHOLD}")
    print("=" * 60)

    try:
        summary = validate()
    except AssertionError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nTotal edges loaded: {summary['total_edges']:,}")
    print(f"Lexicon keys:       {summary['lexicon_key_count']:,}")
    print(f"\nPer-rel counts:")
    for rel in ("shared-root", "domain-sibling", "cross-language", "synonym", "antonym"):
        print(f"  {rel:20s}: {summary['rel_counts'].get(rel, 0):>10,}")
    print(f"\nDefault-view count (rank >= {DEFAULT_RANK_THRESHOLD}): {summary['default_view_count']:,}")
    print(f"\nPer-source counts:")
    for src, cnt in sorted(summary["source_counts"].items(), key=lambda x: -x[1]):
        print(f"  {src:30s}: {cnt:>10,}")
    print(f"\nChecks:")
    for key, val in summary.items():
        if key.startswith("check_"):
            label = key[len("check_"):]
            print(f"  {label:30s}: {val}")
    print(f"\nOverall: {summary['overall']}")


if __name__ == "__main__":
    main()
