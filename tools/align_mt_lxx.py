"""MT<->LXX aggregated co-occurrence bridge.

Derived projection (recomputable from morph/ot + morph/lxx + mt_ref).
NOT committed canonical data.  Output: data/cache/mt-lxx-bridge.jsonl (gitignored).

Provenance: bridge rows are DERIVED from CC-BY morpho-lexical data
(STEPBible TAGNT/TAHOT via morph/lxx and morph/ot); inherited licence is CC-BY.
The src field on each per-verse edge is "derived:verse-cooccurrence".

Public interfaces
-----------------
align_verse_pair(lxx_ref, mt_ref, mt_tokens, lxx_tokens) -> list[dict]
    Per-verse building block kept for testing.  Content-word cross-product
    (skip tokens with empty strong).  Each edge carries:
        lxx_ref, mt_ref, mt_strong, lxx_strong, lxx_lemma,
        confidence="verse-cooccurrence", lxx_align, src="derived:verse-cooccurrence"

aggregate_verse_pairs(verse_pairs) -> list[dict]
    Aggregate an iterable of (lxx_ref, mt_ref_str, mt_tokens, lxx_tokens)
    into one row per (mt_strong, lxx_strong).  Row keys:
        mt_strong, lxx_strong, lxx_lemma, cooccur, exact, positional

    Counting unit: cooccur is incremented ONCE per verse-pair where both
    strongs appear, regardless of how many cross-product cells exist in that
    verse.  exact/positional are also per-verse-pair; tie rule: if both
    exact and positional instances of a lxx_strong appear in one verse,
    the verse-pair counts toward "exact" (exact-wins).

build_bridge() -> list[dict]
    Walk all protocanon LXX verses (lxx_books(), skip deuterocanon),
    pair each to its MT counterpart via mt_ref (skip None), extract
    tokens from morph/lxx and morph/ot CoNLL-U files, and return
    sorted aggregate rows.

CLI
---
python -m tools.align_mt_lxx
    Writes data/cache/mt-lxx-bridge.jsonl and prints a build report.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tools.conllu import parse_file
from tools.lxx_versification import lxx_books
from tools.lxx_versification import mt_ref as _mt_ref

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_misc(misc: str) -> dict:
    """Parse a CoNLL-U misc field into a key->value dict.

    Splits on ``|``, then on ``=``.  Keys with no value are ignored.
    """
    result: dict = {}
    if not misc or misc == "_":
        return result
    for part in misc.split("|"):
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
    return result


def _extract_mt_strongs(strong_val: str) -> list[str]:
    """Return a list of canonical H#### codes from a Strong= field value.

    Handles compound codes like H9001/H7225 by splitting on ``/``.
    Drops H9000-H9999 prefix/grammatical codes.

    Returns an empty list if nothing remains after filtering.
    """
    if not strong_val:
        return []
    parts = strong_val.split("/")
    result = []
    for part in parts:
        if part.startswith("H") and part[1:].isdigit():
            num = int(part[1:])
            if 9000 <= num <= 9999:
                continue  # grammatical-prefix code: not a content strong
        if part:
            result.append(part)
    return result


def _token_to_mt_dict(tok) -> dict | None:
    """Convert a conllu.Token to a mt_tokens dict, or None if no content strong."""
    m = _parse_misc(tok.misc)
    raw_strong = m.get("Strong", "")
    strongs = _extract_mt_strongs(raw_strong)
    if not strongs:
        return None
    # If a compound resolves to multiple content strongs, use the last one
    # (the root/content word, as prefix codes were dropped first).
    return {"strong": strongs[-1], "lemma": tok.lemma}


def _token_to_lxx_dict(tok) -> dict | None:
    """Convert a conllu.Token to a lxx_tokens dict, or None if no content strong."""
    m = _parse_misc(tok.misc)
    strong = m.get("Strong", "")
    if not strong:
        return None  # Align=unmatched or Align=exact-with-no-Strong
    align_raw = m.get("Align", "")
    # Normalize: take first segment before comma (e.g. "exact,source_extra:5" -> "exact")
    align = align_raw.split(",")[0] if align_raw else "positional"
    return {"strong": strong, "lemma": tok.lemma, "align": align}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def align_verse_pair(
    lxx_ref: str,
    mt_ref: str,
    mt_tokens: list[dict],
    lxx_tokens: list[dict],
) -> list[dict]:
    """Return the content-word cross-product edge list for one verse pair.

    Parameters
    ----------
    lxx_ref    : LXX reference string, e.g. "GEN.1.1"
    mt_ref     : MT reference string, e.g. "GEN.1.1"
    mt_tokens  : list of dicts with at least ``{"strong": str, ...}``
    lxx_tokens : list of dicts with at least
                 ``{"strong": str, "lemma": str, "align": str}``

    Returns
    -------
    list of edge dicts with keys:
        lxx_ref, mt_ref, mt_strong, lxx_strong, lxx_lemma,
        confidence, lxx_align, src
    """
    edges = []
    for mt_tok in mt_tokens:
        ms = mt_tok.get("strong", "")
        if not ms:
            continue
        for lxx_tok in lxx_tokens:
            ls = lxx_tok.get("strong", "")
            if not ls:
                continue
            edges.append(
                {
                    "lxx_ref": lxx_ref,
                    "mt_ref": mt_ref,
                    "mt_strong": ms,
                    "lxx_strong": ls,
                    "lxx_lemma": lxx_tok.get("lemma", ""),
                    "confidence": "verse-cooccurrence",
                    "lxx_align": lxx_tok.get("align", ""),
                    "src": "derived:verse-cooccurrence",
                }
            )
    return edges


def aggregate_verse_pairs(verse_pairs) -> list[dict]:
    """Aggregate an iterable of verse-pair tuples into one row per (mt_strong, lxx_strong).

    Parameters
    ----------
    verse_pairs : iterable of (lxx_ref, mt_ref_str, mt_tokens, lxx_tokens)
        mt_tokens  : list of dicts with ``{"strong": str, ...}``
        lxx_tokens : list of dicts with ``{"strong": str, "lemma": str, "align": str}``

    Returns
    -------
    Sorted list of dicts with keys:
        mt_strong, lxx_strong, lxx_lemma, cooccur, exact, positional

    Counting unit
    -------------
    cooccur is incremented ONCE per verse-pair where both strongs co-occur,
    regardless of token-cross-product size.  exact/positional are also
    per-verse-pair; tie rule: if both exact and positional instances of the
    same lxx_strong appear in one verse, the verse-pair counts as "exact"
    (exact-wins).
    """
    agg: dict = defaultdict(
        lambda: {"cooccur": 0, "exact": 0, "positional": 0, "lemma_counts": Counter()}
    )

    for _lxx_ref, _mt_ref_str, mt_toks, lxx_toks in verse_pairs:
        # Unique MT strongs in this verse
        mt_strongs = {t["strong"] for t in mt_toks if t.get("strong")}
        if not mt_strongs:
            continue

        # Per distinct LXX strong: best align (exact-wins) and representative lemma
        lxx_best_align: dict[str, str] = {}
        lxx_best_lemma: dict[str, str] = {}
        for t in lxx_toks:
            ls = t.get("strong", "")
            if not ls:
                continue
            a = t.get("align", "positional")
            lemma = t.get("lemma", "")
            if ls not in lxx_best_align:
                lxx_best_align[ls] = a
                lxx_best_lemma[ls] = lemma
            elif lxx_best_align[ls] != "exact" and a == "exact":
                # exact-wins tie rule
                lxx_best_align[ls] = "exact"

        if not lxx_best_align:
            continue

        # Cross-product of unique strongs: count once per verse-pair per pair
        for ms in mt_strongs:
            for ls, la in lxx_best_align.items():
                key = (ms, ls)
                agg[key]["cooccur"] += 1
                if la == "exact":
                    agg[key]["exact"] += 1
                else:
                    agg[key]["positional"] += 1
                agg[key]["lemma_counts"][lxx_best_lemma[ls]] += 1

    rows = []
    for (mt_strong, lxx_strong), data in sorted(agg.items()):
        best_lemma = (
            data["lemma_counts"].most_common(1)[0][0] if data["lemma_counts"] else ""
        )
        rows.append(
            {
                "mt_strong": mt_strong,
                "lxx_strong": lxx_strong,
                "lxx_lemma": best_lemma,
                "cooccur": data["cooccur"],
                "exact": data["exact"],
                "positional": data["positional"],
            }
        )
    return rows


# ---------------------------------------------------------------------------
# File-based bridge builder
# ---------------------------------------------------------------------------


def _iter_verse_pairs():
    """Generator: yield (lxx_ref, mt_ref_str, mt_token_dicts, lxx_token_dicts)
    for every protocanon LXX verse that has an MT counterpart.

    Also yields a stats sentinel at the end as a special tuple
    ``("__stats__", stats_dict, None, None)``.
    """
    stats = {
        "total_lxx_verses": 0,
        "verses_skipped_no_mt": 0,
        "verses_with_edges": 0,
    }

    mt_chapter_cache: dict[tuple, dict] = {}

    for book in lxx_books():
        code = book["code"]
        lxx_dir = ROOT / "morph" / "lxx" / code
        if not lxx_dir.exists():
            continue

        for ch_file in sorted(lxx_dir.glob("*.conllu")):
            try:
                sentences = parse_file(ch_file)
            except Exception:
                continue

            for ref, raw_toks in sentences:
                if not ref:
                    continue

                parts = ref.split(".")
                if len(parts) != 3:
                    continue
                _, lxx_ch_str, lxx_v_str = parts
                try:
                    lxx_ch = int(lxx_ch_str)
                    lxx_v = int(lxx_v_str)
                except ValueError:
                    continue

                stats["total_lxx_verses"] += 1

                mt_ref_val = _mt_ref(code, lxx_ch, lxx_v)
                if mt_ref_val is None:
                    stats["verses_skipped_no_mt"] += 1
                    continue

                # Parse "chapter:verse"
                try:
                    mt_ch_str, mt_v_str = mt_ref_val.split(":", 1)
                    mt_ch = int(mt_ch_str)
                    mt_v = int(mt_v_str)
                except (ValueError, AttributeError):
                    stats["verses_skipped_no_mt"] += 1
                    continue

                # Load MT chapter (cached)
                cache_key = (code, mt_ch)
                if cache_key not in mt_chapter_cache:
                    mt_ch_file = ROOT / "morph" / "ot" / code / f"{mt_ch:03d}.conllu"
                    if not mt_ch_file.exists():
                        mt_chapter_cache[cache_key] = {}
                    else:
                        try:
                            ch_sents = parse_file(mt_ch_file)
                            mt_chapter_cache[cache_key] = {
                                r: toks for r, toks in ch_sents if r
                            }
                        except Exception:
                            mt_chapter_cache[cache_key] = {}

                mt_sent_ref = f"{code}.{mt_ch}.{mt_v}"
                mt_raw_toks = mt_chapter_cache[cache_key].get(mt_sent_ref, [])

                # Convert to dicts
                mt_dicts = [d for tok in mt_raw_toks for d in [_token_to_mt_dict(tok)] if d]
                lxx_dicts = [d for tok in raw_toks for d in [_token_to_lxx_dict(tok)] if d]

                if mt_dicts and lxx_dicts:
                    stats["verses_with_edges"] += 1

                mt_ref_label = f"{code}.{mt_ch}.{mt_v}"
                yield ref, mt_ref_label, mt_dicts, lxx_dicts

    # Sentinel at end (consumed by _build_bridge_impl)
    yield "__stats__", stats, None, None


def _build_bridge_impl():
    """Internal: build the bridge and return (rows, stats)."""
    verse_pairs = []
    stats = {}
    for item in _iter_verse_pairs():
        if item[0] == "__stats__":
            stats = item[1]
        else:
            verse_pairs.append(item)

    rows = aggregate_verse_pairs(verse_pairs)
    return rows, stats


def build_bridge() -> list[dict]:
    """Build and return the aggregated MT<->LXX co-occurrence bridge rows.

    Walks all protocanon LXX verses, pairs them to their MT counterparts via
    mt_ref, and aggregates into one row per (mt_strong, lxx_strong).

    Returns
    -------
    list of dicts sorted by (mt_strong, lxx_strong), each with keys:
        mt_strong, lxx_strong, lxx_lemma, cooccur, exact, positional
    """
    rows, _ = _build_bridge_impl()
    return rows


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    out_path = ROOT / "data" / "cache" / "mt-lxx-bridge.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Building MT<->LXX aggregated co-occurrence bridge...", flush=True)
    rows, stats = _build_bridge_impl()

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    total_lxx = stats.get("total_lxx_verses", 0)
    skipped = stats.get("verses_skipped_no_mt", 0)
    with_edges = stats.get("verses_with_edges", 0)
    protocanon_verses = total_lxx - skipped

    total_cooccur = sum(r["cooccur"] for r in rows)
    total_exact = sum(r["exact"] for r in rows)
    total_positional = sum(r["positional"] for r in rows)
    file_size = out_path.stat().st_size

    coverage_pct = (with_edges / protocanon_verses * 100) if protocanon_verses else 0.0
    exact_pct = (total_exact / total_cooccur * 100) if total_cooccur else 0.0

    print(f"Output:          {out_path}")
    print(f"File size:       {file_size / 1024:.1f} KB  ({file_size:,} bytes)")
    print(f"Aggregate rows:  {len(rows):,}")
    print(f"Total cooccur:   {total_cooccur:,}")
    print(f"  exact:         {total_exact:,}  ({exact_pct:.1f}%)")
    print(f"  positional:    {total_positional:,}  ({100 - exact_pct:.1f}%)")
    print(f"LXX verses seen: {total_lxx:,}")
    print(f"  protocanon:    {protocanon_verses:,}")
    print(f"  skipped(no MT):{skipped:,}")
    print(f"  with >=1 edge: {with_edges:,}  ({coverage_pct:.1f}% of protocanon)")

    # Spot-check: top renderings of H7225 (רֵאשִׁית)
    h7225 = [r for r in rows if r["mt_strong"] == "H7225"]
    h7225.sort(key=lambda r: r["cooccur"], reverse=True)
    print("\nH7225 (רֵאשִׁית) top LXX renderings by cooccur:")
    for r in h7225[:5]:
        print(
            f"  {r['lxx_strong']} {r['lxx_lemma']:<25} "
            f"cooccur={r['cooccur']}  exact={r['exact']}  positional={r['positional']}"
        )


if __name__ == "__main__":
    main()
