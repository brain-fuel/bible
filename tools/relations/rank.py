"""rank.py — Rank constants and helpers for relation edges.

Rank is an integer in 0..65535 (unsigned 16-bit range).
Higher rank = higher confidence / relevance.

DEFAULT_RANK_THRESHOLD is a provisional midpoint (Task 10 re-pins it from
observed rank histograms).  The intent (Global Constraints in the L2b spec):
  - a cooccur=1 cross-language pair  → rank BELOW threshold
  - an exact derivation / finest subdomain → rank ABOVE threshold
A provisional midpoint of 32768 sits equidistant on the 0..65535 scale and
satisfies both constraints given typical assignment ranges chosen by builders.
"""

import math

RANK_MAX: int = 65535

# Provisional: midpoint of 0..65535.
# Re-pinned in Task 10 once rank distributions from all builders are observed.
DEFAULT_RANK_THRESHOLD: int = 32768


def clamp_rank(x: int) -> int:
    """Clamp x to the valid rank range 0..65535."""
    return max(0, min(RANK_MAX, x))


# Domain-code specificity -> rank band.
# Two code formats: Louw-Nida (grc) is dotted ("25.43" -> depth 2);
# SDBH (hbo) is fixed-width hierarchical, 3-digit chunks ("002001002010" -> depth 4).
# depth-1 (broadest) ranks BELOW DEFAULT_RANK_THRESHOLD; depth>=2 ranks above,
# strictly increasing through depth 5 (no clamp collision).
#
# WHY the threshold split: a top-level domain code loosely groups many words and
# is a weak semantic signal; a subdomain code identifies a genuinely specific
# semantic cluster and is a strong signal.  DEFAULT_RANK_THRESHOLD (32768) is the
# intended cut-off between "weak" and "meaningful" connections, so coarse
# (depth-1) codes fall below it and fine-grained (depth>=2) codes fall above it.
# Distinct per-depth bands keep "more-specific ranks higher" monotone for BOTH
# code formats, including SDBH depths 2..5, without colliding at RANK_MAX.
_SPECIFICITY_BANDS = {1: 16384, 2: 40960, 3: 49152, 4: 57344, 5: 65535}


# Bridge-rank scale: a pair with exact_ratio=1.0 and cooccur=100 maps to RANK_MAX.
#
# WHY cooccur=100 as the saturation ceiling:
#   Most Hebrew-Greek co-occurrence pairs in the protocanon alignment cluster far
#   below 100 verse-pairs; the few very common pairs (e.g. H0430/G2316) saturate
#   well within this range.  Pinning the ceiling at log1p(100) ≈ 4.615 gives:
#
#     cooccur=1, exact=1  → score = 1.0 × log1p(1) ≈ 0.693
#                           rank  = int(0.693 / 4.615 × 65535) ≈ 9836
#                           9836 < 32768 = DEFAULT_RANK_THRESHOLD  ✓  (noise floor)
#
#     cooccur=1, exact=0  → score = 0  → rank = 0  (hardest noise floor)
#
#   So ANY cooccur=1 pair, even with a perfect exact ratio, lands comfortably
#   below DEFAULT_RANK_THRESHOLD, keeping them out of the default view while
#   still materialising them in the JSONL for completeness.
#
#     cooccur=50, exact=45 → score ≈ 0.9 × 3.932 ≈ 3.539
#                            rank  = int(3.539 / 4.615 × 65535) ≈ 50,253  ✓
#
# Use clamp_rank to guarantee 0..65535 for pairs with cooccur > 100.
_BRIDGE_SCALE: float = 65535.0 / math.log1p(100)

# LINEAR ubiquity downweight.  A Greek lemma (lxx_strong) that translates many
# DISTINCT Hebrew lemmas (high "fan"/ubiquity) is a weak, generic signal — most
# often a function word (καί, εἰς, ἐν) that co-occurs with nearly anything — so we
# subtract a penalty LINEAR in the fan count: round(UBIQUITY_PENALTY_PER_PARTNER
# * ubiquity).  ubiquity<=1 → no penalty (preserves the original signal-only rank
# for single-partner pairs and keeps the no-ubiquity callers byte-identical).
#
# WHY linear and not classic log-IDF: on the real MT↔LXX bridge the ubiquity here
# counts *verse-level co-occurrence* partners (every Hebrew word sharing a verse
# with the Greek word), not true translation links — so even genuine cognates are
# fairly "ubiquitous".  The ubiquity RATIO between a function word and a cognate
# is small (e.g. καί 7701 vs ἀρχή 663 ≈ 11.6×), which a log penalty compresses to
# a ~3.5 gap in log2 space — far too little to overcome the function word's higher
# base score before the cognate itself clamps to 0.  A LINEAR term has the dynamic
# range to demote high-fan function words below distinctive cognates.  (See the
# proof in .superpowers/sdd/task-4-report.md.)
#
# K=3 is tuned so ἀρχή/G0746 becomes H7225's #1 cross-language partner, ahead of
# καί/G2532.  Provisional: re-pinned in Task 10 from observed rank histograms.
UBIQUITY_PENALTY_PER_PARTNER: float = 3.0


def bridge_rank(row: dict, ubiquity: int = 1) -> int:
    """Rank a bridge row on 0..65535 with an optional linear ubiquity downweight.

    The base signal is exact_ratio × log1p(cooccur), where
    exact_ratio = exact / cooccur (0 if cooccur == 0 — guard against div-by-zero).
    Scale pinned so cooccur=100 with exact_ratio=1.0 reaches RANK_MAX; any
    cooccur=1 row always ranks below DEFAULT_RANK_THRESHOLD regardless of exact.

    Args:
        row: bridge row dict with at least 'cooccur' and 'exact'.
        ubiquity: number of DISTINCT mt_strong partners the row's lxx_strong
            appears with (its "fan").  Default 1 → no penalty, so existing
            callers that pass no ubiquity get the pure signal rank.

    A penalty LINEAR in ubiquity is subtracted: a higher fan yields a strictly
    lower rank.  Result is clamped to 0..65535.
    """
    cooccur = row.get("cooccur", 0)
    if cooccur == 0:
        return 0
    exact = row.get("exact", 0)
    exact_ratio = exact / cooccur
    score = exact_ratio * math.log1p(cooccur)
    score_rank = int(score * _BRIDGE_SCALE)
    penalty = round(UBIQUITY_PENALTY_PER_PARTNER * ubiquity) if ubiquity > 1 else 0
    return clamp_rank(score_rank - penalty)


def specificity_rank(code: str) -> int:
    """Map a domain code's hierarchical depth to a rank band.

    Detects the code format:
        SDBH (hbo): all-digit, length a multiple of 3 -> depth = len(code)//3
        Louw-Nida (grc): dotted -> depth = number of dot-separated parts

    depth-1 ranks below DEFAULT_RANK_THRESHOLD; depths 2..5 are distinct and
    strictly increasing above it.  Examples:
        specificity_rank("25.43") = 40960 > specificity_rank("25") = 16384
        specificity_rank("004003002") = 49152 > specificity_rank("004003") = 40960
    """
    if code.isdigit() and len(code) % 3 == 0:
        depth = len(code) // 3            # SDBH fixed-width
    else:
        depth = code.count(".") + 1       # Louw-Nida dotted
    depth = max(1, min(depth, 5))
    return _SPECIFICITY_BANDS[depth]
