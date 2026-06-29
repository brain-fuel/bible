"""build_cross_language.py — Cross-language (MT↔LXX) relation builder.

Projects the MT-LXX co-occurrence bridge into ranked cross-language edges.
Each bridge row (one per (mt_strong, lxx_strong) pair) yields one Edge with
src=H#### (Hebrew), dst=G#### (Greek), directed=False.

Cross-language edges are NOT canonical-oriented by src<dst.  H#### and G####
prefixes never collide, so keeping src=H#### and dst=G#### makes the MT→LXX
direction readable while directed=False correctly marks the pair as a
bidirectional fact.

ALL rows are materialised, including cooccur=1 noise-floor pairs (they are
kept in the JSONL but ranked below DEFAULT_RANK_THRESHOLD so the default view
can filter them out).  No self-loops are emitted (a Hebrew and Greek Strong's
ID can never be equal, but the guard is included for correctness).

CLI usage:
    python -m tools.relations.build_cross_language

Writes: relations/derived/cross-language.jsonl
"""

from __future__ import annotations

from pathlib import Path

from tools.align_mt_lxx import build_bridge
from tools.relations.edge import Edge, write_jsonl
from tools.relations.rank import DEFAULT_RANK_THRESHOLD, bridge_rank

ROOT = Path(__file__).parent.parent.parent  # repo root


def cross_language_edges(bridge_rows: list[dict]) -> list[Edge]:
    """Return one cross-language Edge per (mt_strong, lxx_strong) bridge row.

    Args:
        bridge_rows: Aggregated bridge rows from build_bridge(), each with keys
                     mt_strong (H####), lxx_strong (G####), lxx_lemma, cooccur,
                     exact, positional.

    Returns:
        List of Edge objects.  Self-loops are excluded (defensive; H/G IDs
        cannot collide in practice).  ALL rows are materialised including
        cooccur=1 noise-floor entries.
    """
    edges: list[Edge] = []
    for row in bridge_rows:
        src = row["mt_strong"]   # H####
        dst = row["lxx_strong"]  # G####
        if src == dst:
            continue  # no self-loops (defensive)
        edges.append(
            Edge(
                src=src,
                dst=dst,
                rel="cross-language",
                directed=False,
                source="mt-lxx-bridge",
                method="projection",
                rank=bridge_rank(row),
                note=None,
            )
        )
    return edges


def build_cross_language() -> list[Edge]:
    """Call build_bridge() and project all rows into cross-language edges."""
    bridge_rows = build_bridge()
    return cross_language_edges(bridge_rows)


def main() -> None:
    """CLI entry point: build edges, write JSONL, print summary."""
    out_path = ROOT / "relations" / "derived" / "cross-language.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Building MT↔LXX cross-language edges...", flush=True)
    edges = build_cross_language()
    write_jsonl(out_path, edges)

    total = len(edges)
    above = sum(1 for e in edges if e.rank >= DEFAULT_RANK_THRESHOLD)
    below = total - above

    print(f"cross-language edges written: {total}")
    print(f"output: {out_path.relative_to(ROOT)}")
    print()
    print(f"rank >= {DEFAULT_RANK_THRESHOLD} (above threshold): {above}")
    print(f"rank <  {DEFAULT_RANK_THRESHOLD} (below threshold): {below}")

    # Spot-check: top-5 ranked Greek renderings of H7225 (רֵאשִׁית / beginning)
    # G0746 ἀρχή is the canonical translation in Gen 1:1 and should rank high.
    h7225_edges = [e for e in edges if e.src == "H7225"]
    h7225_sorted = sorted(h7225_edges, key=lambda e: -e.rank)
    print()
    print("Top-5 ranked renderings of H7225:")
    for e in h7225_sorted[:5]:
        print(f"  {e.src} -> {e.dst}  rank={e.rank}")


if __name__ == "__main__":
    main()
