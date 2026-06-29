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


def bridge_rank(row: dict) -> int:
    """Rank a bridge row on 0..65535 using signal = exact_ratio × log1p(cooccur).

    exact_ratio = exact / cooccur (0 if cooccur == 0 — guard against division by zero).
    Scale pinned so cooccur=100 with exact_ratio=1.0 reaches RANK_MAX; any
    cooccur=1 row always ranks below DEFAULT_RANK_THRESHOLD regardless of exact.
    """
    cooccur = row.get("cooccur", 0)
    if cooccur == 0:
        return 0
    exact = row.get("exact", 0)
    exact_ratio = exact / cooccur
    score = exact_ratio * math.log1p(cooccur)
    return clamp_rank(int(score * _BRIDGE_SCALE))


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
