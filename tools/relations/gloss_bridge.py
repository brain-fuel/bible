"""gloss_bridge.py — Shared gloss-bridge miner engine.

Maps thesaurus headwords to lemma keys THROUGH the English gloss index, then
emits ranked relation edges.  Tasks 7, 8, and 9 each parse their own thesaurus
source into ``(headword, related, rel)`` tuples and call ``mine_relations()``
with this engine.

Design overview
---------------
A thesaurus says, for example, "joy" and "gladness" are synonyms.  The lexicon
entry for G5479 (χαρά) has gloss ``"joy, gladness"``.  ``gloss_term_index``
builds a mapping ``{"joy": {"G5479"}, "gladness": {"G5479"}, ...}``.
``mine_relations`` looks up both "joy" and "gladness", finds they both map to
G5479, and emits a synonym edge.

Public API
----------
``gloss_term_index(entries, lang="en") -> dict[str, set[str]]``
    Build a normalized-term → {lemma_key, ...} index from a list of lexicon
    entry dicts.

``mine_relations(idx, headword_links, source, method, base_rank) -> list[Edge]``
    Emit relation edges by bridging thesaurus headwords through the index.

Normalization contract
----------------------
Index build and lookup share a *single* normalizer: ``_normalize_term``.
This function is called on every token during index construction, and also on
every headword in ``mine_relations`` before the index look-up.  Any divergence
between the two call-sites would silently produce zero matches, so keeping them
in one function is a hard invariant.
"""

from __future__ import annotations

import math
import re
from typing import Iterable

from tools.relations.edge import Edge, canonical_orient
from tools.relations.lexkeys import key_for
from tools.relations.rank import clamp_rank

# ---------------------------------------------------------------------------
# Looseness-penalty constants.
#
# Two independent penalties pull a link's rank DOWN from ``base_rank``:
#
# 1. WORD_PENALTY — multi-word headwords imply a fuzzier surface match.
#    A two-word phrase costs WORD_PENALTY; a three-word phrase costs 2×, etc.
#
# 2. FANOUT_PENALTY_SCALE — *polysemy* downweight.  A link whose endpoints each
#    resolve to MANY lemma keys (large cross-product) is a vague many↔many match
#    and should rank low; a precise 1↔1 match should rank high.  The penalty
#    grows with log2 of the cross-product size, i.e. one FANOUT_PENALTY_SCALE
#    of rank is shed per *doubling* of fanout:
#        fanout=1  → 0           (precise 1↔1, no penalty)
#        fanout=2  → 1×scale
#        fanout=4  → 2×scale
#        fanout=8  → 3×scale ...
#    This makes rank strictly decreasing in fanout (monotone) while bounding the
#    cost of huge cross-products to a logarithm rather than a runaway linear hit.
# ---------------------------------------------------------------------------
WORD_PENALTY: int = 1000

# Rank points shed per doubling of the cross-product (fanout) size.  Pinned so
# that, with a per-miner base_rank chosen just above DEFAULT_RANK_THRESHOLD, a
# precise (fanout=1) single-word match lands above the threshold while a match
# with a few-dozen-way fanout falls below it.  Task 10 re-validates against
# observed rank histograms.
FANOUT_PENALTY_SCALE: int = 2500

# ---------------------------------------------------------------------------
# Stopword set — tokens removed before indexing gloss text.
# The set is intentionally small: include only words that are guaranteed to
# appear as tokens after splitting on commas/semicolons/whitespace and that
# carry no useful semantic content.
# ---------------------------------------------------------------------------
_STOPWORDS: frozenset[str] = frozenset({
    # Articles
    "a", "an", "the",
    # Common prepositions / conjunctions
    "of", "and", "or", "to", "in", "on", "at", "by", "with",
    "from", "for", "but", "nor", "yet", "so",
    # Forms of "be"
    "is", "are", "was", "were", "be", "been", "being",
    # Auxiliary verbs
    "has", "have", "had", "do", "does", "did",
    # Demonstratives / relative pronouns
    "this", "that", "these", "those", "which", "who", "whom", "whose",
    "what", "when", "where", "how",
    # Personal pronouns
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "its", "they", "their", "him", "her", "us",
    # Negation
    "not", "no",
    # Common discourse particles that appear in gloss parentheticals
    "also", "as", "so", "such", "than", "then", "there",
    # Abbreviations found in lexicon glosses
    "i.e.", "e.g.", "etc.", "etc", "cf", "cf.",
    # Connector words common in Strong's-style glosses
    "used", "one", "any",
})

# ---------------------------------------------------------------------------
# Patterns for stripping Strong's cross-references from gloss text.
# Examples of what must be stripped:
#   "from G0025"       connective lead-in + Strong's number
#   "see H1234"        connective lead-in + Strong's number
#   "of G0025"         preposition + Strong's number
#   "G0025", "H1234"   bare Strong's number
# ---------------------------------------------------------------------------

# Connective lead-in + Strong's number (strip the whole phrase)
_STRONGS_LEAD_IN: re.Pattern[str] = re.compile(
    r'\b(?:from|of|see|cf\.?|used\s+in|compare)\s+[GH]\d{1,5}\b',
    re.IGNORECASE,
)

# Bare Strong's reference remaining after lead-in removal
_STRONGS_BARE: re.Pattern[str] = re.compile(
    r'\b[GH]\d{1,5}\b',
    re.IGNORECASE,
)

# Split delimiter pattern: commas, semicolons, whitespace (one or more)
_SPLIT_RE: re.Pattern[str] = re.compile(r'[,;\s]+')


# ---------------------------------------------------------------------------
# Shared normalizer — MUST be used by both index-build and lookup paths.
# ---------------------------------------------------------------------------

def _normalize_term(t: str) -> str:
    """Normalize a single gloss token to a canonical lookup key.

    Steps:
    1. Lowercase.
    2. Strip common punctuation from both ends (covers trailing commas, periods,
       parentheses, quotes, etc. that survive splitting).

    This function is the **single source of truth** for normalization.  It is
    called per-token when building ``gloss_term_index`` and per-headword when
    resolving lookups in ``mine_relations``.  Divergence would silently break
    all mining, so no other normalization paths should exist.
    """
    return t.lower().strip(".,;:!?'\"-()[]{}/ ").strip()


def _tokenize_gloss(text: str) -> list[str]:
    """Tokenize a full gloss text string into clean, indexed terms.

    Pipeline:
    1. Strip Strong's connective lead-ins (e.g. ``"from G0025"``).
    2. Strip bare Strong's references (e.g. ``"G0025"``, ``"H1234"``).
    3. Split on commas, semicolons, and whitespace.
    4. Normalize each token via ``_normalize_term``.
    5. Drop empty strings and stopwords.

    Returns a list of normalized terms ready for index insertion.
    """
    # Step 1+2: Remove cross-reference fragments before splitting so that
    # connective words like "from" don't become stray stopword tokens.
    text = _STRONGS_LEAD_IN.sub(" ", text)
    text = _STRONGS_BARE.sub(" ", text)

    # Step 3: Split on delimiters
    raw_tokens = _SPLIT_RE.split(text)

    # Steps 4+5: Normalize and filter
    terms: list[str] = []
    for raw in raw_tokens:
        t = _normalize_term(raw)
        if t and t not in _STOPWORDS:
            terms.append(t)
    return terms


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def gloss_term_index(
    entries: list[dict],
    lang: str = "en",
) -> dict[str, set[str]]:
    """Build a normalized-term → {lemma_key, ...} index from lexicon entries.

    For each entry, iterates over every gloss in ``entry["glosses"][lang]``,
    tokenizes its ``"text"`` via ``_tokenize_gloss``, and adds the resulting
    terms to the index under ``key_for(entry)``.

    Parameters
    ----------
    entries:
        List of lexicon entry dicts.  Each entry should have:
        - ``"glosses"``: dict mapping language code → list of
          ``{"text": str, "src": str}`` dicts.
        - ``"strong"`` (preferred) or ``"lemma"`` for key derivation.
    lang:
        Language code to index (default ``"en"``).  Only glosses under this
        key are included.

    Returns
    -------
    dict[str, set[str]]
        Maps each normalized gloss term to the set of lemma keys whose
        ``glosses[lang]`` list contains that term.
    """
    idx: dict[str, set[str]] = {}
    for entry in entries:
        key = key_for(entry)
        for gloss in entry.get("glosses", {}).get(lang, []):
            text = gloss.get("text", "")
            for term in _tokenize_gloss(text):
                idx.setdefault(term, set()).add(key)
    return idx


def mine_relations(
    idx: dict[str, set[str]],
    headword_links: Iterable[tuple[str, str, str]],
    source: str,
    method: str,
    base_rank: int,
) -> list[Edge]:
    """Emit relation edges by bridging thesaurus headwords through the index.

    For each ``(headword, related, rel)`` triple in ``headword_links``:
    1. Normalise ``headword`` and ``related`` via ``_normalize_term`` (the same
       normalizer used to build the index, preventing silent mismatch).
    2. Look up matching lemma-key sets in ``idx``.
    3. Skip the triple if either side has no index entry.
    4. For each (key_a, key_b) pair in the cross-product of the two key sets,
       emit a ``rel`` edge with canonical orientation and ``directed=False``.

    Rank assignment
    ~~~~~~~~~~~~~~~
    Base rank is ``base_rank``.  Two **looseness penalties** pull it down:

    1. *Word penalty* — multi-word phrases indicate a fuzzier surface match::

           word_penalty = WORD_PENALTY × (max(wc(headword), wc(related)) − 1)

       single-word → 0; two-word phrase → WORD_PENALTY (1000).

    2. *Fanout (polysemy) penalty* — a vague many↔many bridge should rank low,
       a precise 1↔1 bridge high.  ``fanout`` is the size of the cross-product
       emitted from this link (``len(hw_keys) × len(rel_keys)``)::

           fanout_penalty = round(FANOUT_PENALTY_SCALE × log2(fanout))

       fanout=1 → 0 (precise match, no penalty); the penalty grows by one
       FANOUT_PENALTY_SCALE per *doubling* of fanout, so rank is strictly
       decreasing in fanout (monotone).  Computed ONCE per link and shared by
       every edge emitted from that link.

    Final rank: ``clamp_rank(base_rank − word_penalty − fanout_penalty)``,
    clamped to ``0..65535``.

    Self-loops (key_a == key_b)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Self-loops **are excluded**.  When a thesaurus synonymises two headwords
    that resolve to the same lemma key (e.g. "joy" and "gladness" both map to
    G5479), the resulting key_a == key_b pair is skipped after canonical
    orientation.  This honors the global "no self-loops; src != dst" invariant
    at the engine boundary, so every downstream caller (Tasks 7-9, validated by
    Task 11) is safe by construction.

    Parameters
    ----------
    idx:
        Index produced by ``gloss_term_index``.
    headword_links:
        Iterable of ``(headword, related, rel)`` tuples.
        ``rel`` ∈ ``{"synonym", "antonym"}``.
    source:
        Provenance source string (e.g. ``"roget-1911"``).
    method:
        Provenance method string (e.g. ``"mined"``).
    base_rank:
        Starting rank before the word + fanout penalties; in ``0..65535``.

    Returns
    -------
    list[Edge]
        Emitted edges.  Never contains self-loops (key_a == key_b are skipped);
        may contain duplicate edge pairs if multiple links resolve to the same
        endpoint pair.
    """
    edges: list[Edge] = []

    for headword, related, rel in headword_links:
        # Apply the shared normalizer — identical to the one used during
        # index construction so lookups are always consistent.
        hw_norm = _normalize_term(headword)
        rel_norm = _normalize_term(related)

        hw_keys = idx.get(hw_norm, set())
        rel_keys = idx.get(rel_norm, set())

        # Skip if either side has no index entry (headword not in any gloss).
        if not hw_keys or not rel_keys:
            continue

        # Looseness penalty 1: multi-word headwords imply fuzzier bridging.
        hw_wc = len(headword.split())
        rel_wc = len(related.split())
        max_wc = max(hw_wc, rel_wc)
        word_penalty = WORD_PENALTY * (max_wc - 1)

        # Looseness penalty 2: polysemy/fanout downweight.  A link whose
        # endpoints each resolve to many keys yields a large cross-product and
        # is a vague many↔many match; penalise by log2 of that cross-product so
        # precise 1↔1 matches (fanout=1 → penalty 0) keep the full base_rank.
        # Computed once per link; shared by every edge emitted below.
        fanout = len(hw_keys) * len(rel_keys)  # >= 1 (both sets are non-empty)
        fanout_penalty = (
            round(FANOUT_PENALTY_SCALE * math.log2(fanout)) if fanout > 1 else 0
        )

        rank = clamp_rank(base_rank - word_penalty - fanout_penalty)

        for key_a in hw_keys:
            for key_b in rel_keys:
                src, dst = canonical_orient(key_a, key_b)
                # Skip self-loops: honors the global "no self-loops; src != dst"
                # invariant at the engine boundary (validated by Task 11).
                if src == dst:
                    continue
                edges.append(
                    Edge(
                        src=src,
                        dst=dst,
                        rel=rel,
                        directed=False,
                        source=source,
                        method=method,
                        rank=rank,
                        note=None,
                    )
                )

    return edges
