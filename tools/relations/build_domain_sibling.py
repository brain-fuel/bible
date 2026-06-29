"""build_domain_sibling.py — Domain-sibling relation builder.

Groups lexicon entries by each domain code they carry and emits one symmetric
domain-sibling edge per pair of entries that share the same code.  ALL code
granularities are materialised: a pair sharing both "25" and "25.43" receives
a separate edge for each shared code, each ranked by that code's specificity.

Source convention (per entry lang field):
    "grc" → source = "louw-nida"   (Louw-Nida codes, dotted, e.g. "25.43")
    "hbo" → source = "sdbh"        (SDBH codes, e.g. "002004002014")
When a code group's two endpoints come from entries of different langs (this
should not occur in practice — LN codes pair grc with grc, SDBH codes pair
hbo with hbo), the source is derived from the *first* entry in the
combination; a warning comment in the code notes this assumption.

CLI usage:
    python -m tools.relations.build_domain_sibling

Writes: relations/derived/domain-sibling.jsonl
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from tools.relations.edge import Edge, canonical_orient, write_jsonl
from tools.relations.lexkeys import key_for, lexicon_keys
from tools.relations.rank import DEFAULT_RANK_THRESHOLD, specificity_rank

ROOT = Path(__file__).parent.parent.parent  # repo root


def domain_sibling_edges(entries: list[dict]) -> list[Edge]:
    """Return symmetric domain-sibling edges for all pairs sharing a domain code.

    For EACH domain code every pair of entries carrying that code gets an edge.
    ALL granularities are materialised: if a pair shares both "25" and "25.43",
    two edges are emitted — one per shared code — each ranked by that code's
    specificity_rank.

    Args:
        entries: List of lexicon entry dicts, each with at least 'strong',
                 'lemma', 'lang', and 'domains' keys.

    Returns:
        List of Edge objects.  Entries with no domains are skipped.  Self-loops
        are excluded.  Endpoints are validated against lexicon_keys() so that
        entries whose key is not in the real lexicon are filtered out.
    """
    valid_keys = lexicon_keys()

    # Build a map: code → list of (key, lang) for all entries carrying that code.
    # An entry with N domain codes is inserted into N groups.
    groups: dict[str, dict[str, str]] = defaultdict(dict)  # code → {key: lang}
    for entry in entries:
        domains = entry.get("domains") or []
        if not domains:
            continue
        key = key_for(entry)
        if key not in valid_keys:
            continue
        lang = entry.get("lang") or "grc"
        for code in domains:
            if not code:
                continue
            groups[code][key] = lang  # key dedup within a group; last lang wins

    edges: list[Edge] = []
    for code, members in groups.items():
        rank = specificity_rank(code)
        keys = list(members.keys())
        for a, b in combinations(keys, 2):
            src, dst = canonical_orient(a, b)
            if src == dst:
                continue  # no self-loops (defensive; combinations won't produce these)
            # Derive source from the lang of the canonical src endpoint.
            # In practice both endpoints share a lang because LN codes only
            # appear in grc entries and SDBH codes only appear in hbo entries.
            source = "louw-nida" if members[src] == "grc" else "sdbh"
            edges.append(
                Edge(
                    src=src,
                    dst=dst,
                    rel="domain-sibling",
                    directed=False,
                    source=source,
                    method="derived",
                    rank=rank,
                    note=None,
                )
            )
    return edges


def build_domain_sibling() -> list[Edge]:
    """Load all lexicon entries (grc + hbo) and return domain-sibling edges."""
    entries: list[dict] = []
    for lex_file in sorted((ROOT / "lexicon").glob("**/*.json")):
        try:
            entry = json.loads(lex_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: skipping {lex_file}: {e}", file=sys.stderr)
            continue
        entries.append(entry)
    return domain_sibling_edges(entries)


def main() -> None:
    """CLI entry point: build edges, write JSONL, print summary."""
    out_path = ROOT / "relations" / "derived" / "domain-sibling.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    edges = build_domain_sibling()
    write_jsonl(out_path, edges)

    total = len(edges)
    by_source: dict[str, int] = defaultdict(int)
    above = 0
    below = 0
    for e in edges:
        by_source[e.source] += 1
        if e.rank >= DEFAULT_RANK_THRESHOLD:
            above += 1
        else:
            below += 1

    print(f"domain-sibling edges written: {total}")
    print(f"output: {out_path.relative_to(ROOT)}")
    print()
    print("by source:")
    for src_name in sorted(by_source):
        print(f"  {src_name}: {by_source[src_name]}")
    print()
    print(f"rank >= {DEFAULT_RANK_THRESHOLD} (above threshold): {above}")
    print(f"rank <  {DEFAULT_RANK_THRESHOLD} (below threshold): {below}")


if __name__ == "__main__":
    main()
