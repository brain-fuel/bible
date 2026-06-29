"""build_shared_root.py — Shared-root (cognate) relation builder.

Groups lexicon entries by their `root` field and emits one symmetric
shared-root edge per pair of entries that share the same root.

CLI usage:
    python -m tools.relations.build_shared_root

Writes: relations/derived/shared-root.jsonl
"""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from tools.relations.edge import Edge, canonical_orient, write_jsonl
from tools.relations.lexkeys import key_for, lexicon_keys
from tools.relations.rank import RANK_MAX

ROOT = Path(__file__).parent.parent.parent  # repo root


def shared_root_edges(entries: list[dict]) -> list[Edge]:
    """Return symmetric shared-root edges for all pairs sharing the same root.

    Args:
        entries: List of lexicon entry dicts, each with at least 'strong',
                 'lemma', and 'root' keys.

    Returns:
        List of Edge objects — one per unique pair within each root group.
        Entries with root=None/falsy are skipped. Self-loops are excluded.
        Endpoints are validated against lexicon_keys() (entries that don't
        produce a valid key are filtered out).
    """
    valid_keys = lexicon_keys()

    # Group entry keys by root value (skip entries with no root)
    groups: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        root = entry.get("root")
        if not root:
            continue
        key = key_for(entry)
        if key not in valid_keys:
            continue
        groups[root].append(key)

    edges: list[Edge] = []
    for root, keys in groups.items():
        for a, b in combinations(keys, 2):
            src, dst = canonical_orient(a, b)
            if src == dst:
                continue  # no self-loops (defensive; combinations won't produce these)
            edges.append(
                Edge(
                    src=src,
                    dst=dst,
                    rel="shared-root",
                    directed=False,
                    source="strongs-root",
                    method="derived",
                    rank=RANK_MAX,
                    note=None,
                )
            )
    return edges


def build_shared_root() -> list[Edge]:
    """Load all lexicon entries (grc + hbo) and return shared-root edges."""
    entries: list[dict] = []
    for lex_file in sorted((ROOT / "lexicon").glob("**/*.json")):
        try:
            entry = json.loads(lex_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries.append(entry)
    return shared_root_edges(entries)


def main() -> None:
    """CLI entry point: build edges, write JSONL, print summary."""
    out_path = ROOT / "relations" / "derived" / "shared-root.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    edges = build_shared_root()
    write_jsonl(out_path, edges)

    print(f"shared-root edges written: {len(edges)}")
    print(f"output: {out_path.relative_to(ROOT)}")

    # Spot-check: G0025 root group
    # Entries with root="G0025" in the real lexicon are G0026, G0027.
    # The edge between them uses those keys as endpoints (not G0025 itself).
    g0025_members = {"G0026", "G0027"}
    g0025_edges = [
        e for e in edges
        if e.src in g0025_members and e.dst in g0025_members
    ]
    print(f"\nG0025 root group spot-check (root='G0025' → members {sorted(g0025_members)}):")
    print(f"  {len(g0025_edges)} edge(s) found:")
    for e in sorted(g0025_edges, key=lambda x: (x.src, x.dst)):
        print(f"  {e.src} -- {e.dst}  rel={e.rel}  rank={e.rank}")


if __name__ == "__main__":
    main()
