"""build_relations.py — Canonical relation-graph builder (Task 10).

Calls each in-memory builder/miner function, groups edges by rel, and writes
exactly FIVE canonical per-rel JSONL files:

    relations/derived/shared-root.jsonl
    relations/derived/domain-sibling.jsonl
    relations/derived/cross-language.jsonl
    relations/derived/synonym.jsonl
    relations/derived/antonym.jsonl

Each file is sorted by (src, rel, dst, source) and UTF-8 / LF encoded.
Provenance (source, method) is embedded per-edge so merging many sources into
one per-rel file loses nothing.  Edges from different sources for the same
(src, dst) pair are kept as distinct rows (many-valued provenance).

After this module runs the 8 legacy source-tagged files
(open-english-wordnet.{synonym,antonym}.jsonl, roget-1911.{synonym,antonym}.jsonl,
strongs-{greek,hebrew}.synonym.jsonl, bdb.synonym.jsonl, abbott-smith.synonym.jsonl)
are no longer tracked — they have been git-rm'd.  Running:

    rm -rf relations/derived && python -m tools.build_relations

must reproduce exactly the same 5 files (byte-identical), verified by git status
showing no diff.

Usage:
    python -m tools.build_relations
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from tools.relations.build_cross_language import build_cross_language
from tools.relations.build_domain_sibling import build_domain_sibling
from tools.relations.build_shared_root import build_shared_root
from tools.relations.edge import Edge, write_jsonl
from tools.relations.mine_lexica import build_lexica
from tools.relations.mine_roget import build_roget
from tools.relations.mine_wordnet import build_wordnet
from tools.relations.rank import DEFAULT_RANK_THRESHOLD

ROOT = Path(__file__).parent.parent  # repo root
DERIVED_DIR = ROOT / "relations" / "derived"

# Canonical per-rel output files (exactly 5)
CANONICAL_RELS = ("shared-root", "domain-sibling", "cross-language", "synonym", "antonym")


def _empty_histogram() -> dict[str, int]:
    """Return a zeroed coarse rank histogram with a few buckets."""
    return {
        "0..9999": 0,
        "10000..32767": 0,
        "32768..49999": 0,
        "50000..65535": 0,
    }


def _accumulate_histogram(buckets: dict[str, int], edges: list[Edge]) -> None:
    """Tally edges into the rank buckets in place (no second flat copy)."""
    for e in edges:
        r = e.rank
        if r < 10000:
            buckets["0..9999"] += 1
        elif r < 32768:
            buckets["10000..32767"] += 1
        elif r < 50000:
            buckets["32768..49999"] += 1
        else:
            buckets["50000..65535"] += 1


def build_relations() -> dict[str, list[Edge]]:
    """Run all builders/miners, return edges grouped by rel.

    Returns:
        Dict mapping rel name to list of Edge objects.
    """
    # Accumulate per-rel to keep memory bounded (process one source at a time)
    rel_edges: dict[str, list[Edge]] = defaultdict(list)

    # --- shared-root ---
    print("\n[1/6] build_shared_root() …", flush=True)
    t0 = time.time()
    sr_edges = build_shared_root()
    print(f"  → {len(sr_edges):,} edges in {time.time()-t0:.1f}s", flush=True)
    rel_edges["shared-root"].extend(sr_edges)
    del sr_edges

    # --- domain-sibling ---
    print("\n[2/6] build_domain_sibling() …", flush=True)
    t0 = time.time()
    ds_edges = build_domain_sibling()
    print(f"  → {len(ds_edges):,} edges in {time.time()-t0:.1f}s", flush=True)
    rel_edges["domain-sibling"].extend(ds_edges)
    del ds_edges

    # --- cross-language ---
    print("\n[3/6] build_cross_language() …", flush=True)
    t0 = time.time()
    cl_edges = build_cross_language()
    print(f"  → {len(cl_edges):,} edges in {time.time()-t0:.1f}s", flush=True)
    rel_edges["cross-language"].extend(cl_edges)
    del cl_edges

    # --- WordNet: synonym + antonym ---
    print("\n[4/6] build_wordnet() …", flush=True)
    t0 = time.time()
    wn_syn, wn_ant = build_wordnet()
    print(f"  → {len(wn_syn):,} synonym + {len(wn_ant):,} antonym in {time.time()-t0:.1f}s", flush=True)
    rel_edges["synonym"].extend(wn_syn)
    rel_edges["antonym"].extend(wn_ant)
    del wn_syn, wn_ant

    # --- Roget: synonym + antonym ---
    print("\n[5/6] build_roget() …", flush=True)
    t0 = time.time()
    rg_syn, rg_ant = build_roget()
    print(f"  → {len(rg_syn):,} synonym + {len(rg_ant):,} antonym in {time.time()-t0:.1f}s", flush=True)
    rel_edges["synonym"].extend(rg_syn)
    rel_edges["antonym"].extend(rg_ant)
    del rg_syn, rg_ant

    # --- Lexica (Strong's + BDB + Abbott-Smith): synonym only ---
    print("\n[6/6] build_lexica() …", flush=True)
    t0 = time.time()
    lex_edges = build_lexica()
    print(f"  → {len(lex_edges):,} synonym edges in {time.time()-t0:.1f}s", flush=True)
    rel_edges["synonym"].extend(lex_edges)
    del lex_edges

    return dict(rel_edges)


def write_canonical_files(rel_edges: dict[str, list[Edge]]) -> None:
    """Write exactly 5 canonical per-rel JSONL files to relations/derived/.

    Before writing, prune any *.jsonl in relations/derived/ that is NOT one of
    the 5 canonical files.  Standalone miner CLIs (e.g. `python -m
    tools.relations.mine_wordnet`) drop source-tagged files like
    open-english-wordnet.synonym.jsonl into this dir; left in place they would be
    double-loaded by build_db / validate_relations.  This makes regen robust even
    without `rm -rf relations/derived`.  relations/authored/ is never touched.
    """
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    canonical_names = {f"{rel}.jsonl" for rel in CANONICAL_RELS}
    for stray in sorted(DERIVED_DIR.glob("*.jsonl")):
        if stray.name not in canonical_names:
            print(f"\nPruning non-canonical derived file: {stray.name}", flush=True)
            stray.unlink()
    for rel in CANONICAL_RELS:
        edges = rel_edges.get(rel, [])
        out = DERIVED_DIR / f"{rel}.jsonl"
        print(f"\nWriting {out.name}: {len(edges):,} edges …", flush=True)
        write_jsonl(out, edges)
        print(f"  → wrote {out}", flush=True)


def print_report(rel_edges: dict[str, list[Edge]]) -> None:
    """Print per-rel counts, per-source counts, rank histogram, and threshold split."""
    total = sum(len(v) for v in rel_edges.values())
    print("\n" + "=" * 60)
    print("CANONICAL RELATION GRAPH — REPORT")
    print("=" * 60)

    print(f"\nTotal edges: {total:>12,}")
    print(f"\nPer-rel counts:")
    for rel in CANONICAL_RELS:
        edges = rel_edges.get(rel, [])
        print(f"  {rel:20s}: {len(edges):>10,}")

    print(f"\nPer-source counts (across all rels):")
    source_counts: dict[str, int] = defaultdict(int)
    for edges in rel_edges.values():
        for e in edges:
            source_counts[e.source] += 1
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {src:30s}: {cnt:>10,}")

    print(f"\nRank histogram (all rels combined):")
    hist = _empty_histogram()
    for edges in rel_edges.values():
        _accumulate_histogram(hist, edges)
    for bucket, cnt in sorted(hist.items()):
        print(f"  [{bucket}]: {cnt:>10,}")

    above = sum(
        sum(1 for e in edges if e.rank >= DEFAULT_RANK_THRESHOLD)
        for edges in rel_edges.values()
    )
    below = total - above
    print(f"\nDEFAULT_RANK_THRESHOLD = {DEFAULT_RANK_THRESHOLD}")
    print(f"  rank >= threshold (in default view): {above:>10,}")
    print(f"  rank <  threshold (filtered out):    {below:>10,}")
    print(f"\nThreshold rationale (32768):")
    print(f"  • depth-1 domain codes   → rank 16384 (below threshold, excluded)")
    print(f"  • depth>=2 domain codes  → rank 40960+ (above threshold, included)")
    print(f"  • cooccur=1 cross-lang   → rank ~9836 (below threshold, excluded)")
    print(f"  • shared-root edges      → rank 65535 (always included)")
    print(f"  • lexica cross-ref edges → rank 50000 (included)")


def main() -> None:
    """CLI entry point."""
    print("=" * 60)
    print("build_relations — canonical relation-graph driver")
    print(f"Output dir: {DERIVED_DIR}")
    print("=" * 60)

    t_start = time.time()
    rel_edges = build_relations()
    print_report(rel_edges)
    write_canonical_files(rel_edges)

    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
