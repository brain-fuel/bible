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

RANK_MAX: int = 65535

# Provisional: midpoint of 0..65535.
# Re-pinned in Task 10 once rank distributions from all builders are observed.
DEFAULT_RANK_THRESHOLD: int = 32768


def clamp_rank(x: int) -> int:
    """Clamp x to the valid rank range 0..65535."""
    return max(0, min(RANK_MAX, x))
