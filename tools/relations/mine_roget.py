"""mine_roget.py — Roget's Thesaurus 1911 synonym/antonym miner.

Parses the Project Gutenberg plain-text edition of Roget's Thesaurus 1911
(pg22.txt, prepared by MICRA Inc.) and emits relation edges by bridging
Roget headwords to biblical lemma keys through the gloss-bridge engine.

Source: Roget's Thesaurus 1911. Public Domain.
  Project Gutenberg #22, prepared by MICRA Inc. (no proprietary claim).
  https://www.gutenberg.org/ebooks/22

CLI usage::

    python -m tools.relations.mine_roget

Writes two source-tagged JSONL files::

    relations/derived/roget-1911.synonym.jsonl
    relations/derived/roget-1911.antonym.jsonl

Design notes
------------
**File format (pg22.txt):**

- UTF-8, CRLF line endings. Opened with ``newline=None`` so CRLF is
  transparently normalised to LF before parsing.
- Entries are numbered: ``#NNN[a|b]. CategoryName.—N. ...``
- Entry body spans multiple lines; the next ``#NNN`` marker is the delimiter.
- Bare ``#`` lines (MICRA artifact) are implicitly skipped: ``_ENTRY_START_RE``
  requires digits after ``#``.
- POS sections (N., V., Adj., Adv., Phr., Int.) appear **inline** mid-paragraph,
  NOT at line starts. Splitting uses ``_POS_SPLIT_RE`` on the flattened body.
- Only **uppercase** POS markers are used as section boundaries; lowercase
  self-refs (``&c. adj.``, ``&c. n.``) are filtered out by not matching.

**Synonym extraction:**

Parse each entry's N., V., and Adj. POS sections.  Each POS section is split
on semicolons into *sub-groups* (tighter synonym clusters); within each
sub-group all comma-separated tokens are synonyms.  All pairwise combinations
within a sub-group are emitted as synonym links.  Words in different sub-groups
within the same POS section are NOT directly linked (this is the key scale
control: a large POS section with 10 sub-groups of 5 words each yields
10 × C(5,2) = 40 pairs rather than C(50,2) = 1225).  Phr., Adv., and Int.
sections are skipped: phrases produce no single-word tokens after filtering;
adverbs/interjections rarely appear in short biblical lexicon glosses.

Multi-word phrase fragments (tokens containing whitespace after split) are
discarded. Tokens containing digits (numeric cross-references) are also
discarded. This is a deliberate choice to avoid noise from cross-reference
numbers leaking into synonym pairs.

**Antonym extraction — explicit markers only:**

Roget carries explicit ``{ant. NNN}`` annotations on 14 entries (28
unique pairs, per the format spec). These are extracted with
``_ANT_MARKER_RE`` and produce cross-product antonym links between the
words of entry X and the words of its antonym partner(s).

IMPLICIT sequential pairing is **DEFERRED**. Roget's design places opposed
concepts in consecutive even/odd entries (e.g., #897 Love / #898 Hate), but
the standard companion pair-list from Roget scholarship is not present in
this repository. Fabricating or hard-coding an unverifiable pairing table
would introduce unreliable data; explicit markers (14 entries) are reliable
and deterministic. Lower antonym coverage is acceptable; fabricated data is not.
If a verified pair-list is added to the repo later, this miner can be extended
to use it.

**base_rank rationale:**

``base_rank = 40000`` (same as the WordNet miner, ``FANOUT_PENALTY_SCALE = 2500``).

Roget 1911 is a high-quality English thesaurus. Like WordNet, it is bridged
through the gloss index, so polysemy introduces fanout for common words. The
same ceiling is appropriate: a precise 1↔1 match reaches 40000 (above
DEFAULT_RANK_THRESHOLD=32768), while high-fanout many↔many links fall below.

  fanout=1  → 40000              (ABOVE threshold — precise match)
  fanout=2  → 37500              (above)
  fanout=4  → 35000              (above)
  fanout=8  → 32500              (BELOW threshold)
  crossover at fanout ≈ 7.4

Task 10 re-validates against observed rank histograms.

**Deduplication:**

``mine_relations`` deduplicates to one edge per (src, dst, rel, source)
at MAX rank (most precise fanout wins). An additional ``set[Edge]`` collapse
is applied before writing to catch any identical tuples arising from symmetric
antonym references (entry X → Y and Y → X both produce the same
canonically-oriented edge after ``mine_relations``).
"""

from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

from tools.relations.edge import Edge, write_jsonl
from tools.relations.gloss_bridge import gloss_term_index, mine_relations

ROOT = Path(__file__).parent.parent.parent

# Cached Roget file (committed; always present after Task 8).
_ROGET_PATH = ROOT / "data" / "cache" / "relations" / "roget" / "pg22.txt"

# Source label used in all emitted edges.
_SOURCE: str = "roget-1911"

# Base rank for mined Roget edges (fanout=1 precise match).
# Matches WordNet miner base_rank=40000 — same rationale; see module docstring.
_ROGET_BASE_RANK: int = 40000

# ---------------------------------------------------------------------------
# Compiled regexes
# ---------------------------------------------------------------------------

# Entry start: a line beginning with #NNN[a|b]. (with optional letter suffix)
# The MULTILINE flag lets ^ match after each \n in the full-content string.
_ENTRY_START_RE: re.Pattern[str] = re.compile(
    r"^#(\d+[a-z]?)\.\s", re.MULTILINE
)

# POS section markers: uppercase initial, dot, whitespace.
# Matches N., V., Adj., Adv., Phr., Int. appearing inline in the body text.
# Lowercase self-refs (&c. adj., &c. n.) do NOT match because they are lower.
# Using \b (word boundary) so "N." is not matched inside a larger word.
_POS_SPLIT_RE: re.Pattern[str] = re.compile(
    r"\b(N|V|Adj|Adv|Phr|Int)\.\s"
)

# Explicit antonym markers in curly braces.
# Handles all observed variants:
#   {ant. 133}        standard
#   {ant. 162, 158}   multiple antonyms with comma
#   {ant. of 388}     with "of"
#   {ant 478}         no dot after "ant"
#   {ant. to 812b}    with "to"
#   {ant. to 812a}    with letter suffix
_ANT_MARKER_RE: re.Pattern[str] = re.compile(
    r"\{ant\.?\s*(?:of\s*|to\s*)?(\d+[a-z]?(?:\s*,\s*\d+[a-z]?)*)\}"
)

# Noise patterns removed from entry body text before word extraction.
# Order matters: remove structured patterns before simpler ones.
_NOISE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Parenthetical cross-refs like "(desire) 865" or "(event) 151"
    (re.compile(r"\([^)]*\)\s*\d+[a-z]*"), ""),
    # &c. NNN (entry-number cross-references, e.g., "&c. 682")
    (re.compile(r"&c\.?\s*\d+[a-z]*"), ""),
    # &c. with POS self-refs like "&c. adj.", "&c. n.", "&c. v."
    (re.compile(r"&c\.?\s*[a-z]+\.?", re.IGNORECASE), ""),
    # Bare &c. with or without trailing period
    (re.compile(r"&c\.?"), ""),
    # Square-bracket annotations [obs3], [Lat], [French], [Byron], etc.
    (re.compile(r"\[[^\]]*\]"), ""),
    # Italics markers: _word_ or _multi word phrase_ (greedy, same line)
    (re.compile(r"_[^_]*_"), ""),
    # Trailing pipe markers used as word-break hints in MICRA's version
    (re.compile(r"\|"), " "),
    # Embryonic reorganization markers @NNN
    (re.compile(r"@\w+"), ""),
    # Curly-brace annotations {ant. ...} and similar (strip anything remaining)
    (re.compile(r"\{[^}]*\}"), ""),
]


def _clean_text(text: str) -> str:
    """Remove Roget formatting noise from raw body text.

    Applies ``_NOISE_PATTERNS`` in order.  The result is ready for POS
    section splitting and word extraction.
    """
    for pattern, replacement in _NOISE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _extract_words(subgroup_text: str) -> list[str]:
    """Extract clean single-word tokens from one sub-group text.

    A *sub-group* is the text between two semicolons within a POS section.
    Splits on commas only (semicolons are handled at the caller level to
    delimit sub-groups; any `;` remaining here is a rare artifact).

    Filters applied per token:
    - Strip surrounding punctuation and whitespace.
    - Discard empty tokens.
    - Discard tokens that contain whitespace (multi-word phrases).
    - Discard tokens containing digits (numeric cross-reference remnants).
    - Discard tokens of 1 character or less (abbreviation artifacts).
    - Discard tokens that are purely non-word characters.

    Returns a list of clean, lowercase-ready word strings.  (Actual lowercasing
    is done by ``mine_relations`` via ``_normalize_term``.)
    """
    words: list[str] = []
    for tok in re.split(r",", subgroup_text):
        # Strip common punctuation edges and whitespace
        tok = tok.strip().strip(".,;:!?'\"-()/[] —–")
        # Skip empty
        if not tok:
            continue
        # Skip multi-word phrases (contain whitespace after stripping)
        if re.search(r"\s", tok):
            continue
        # Skip tokens containing digits (leftover cross-ref numbers)
        if re.search(r"\d", tok):
            continue
        # Skip very short tokens (1-char artifacts like "n" from "&c. n." remnants)
        if len(tok) <= 1:
            continue
        # Skip tokens that are entirely non-word characters
        if re.match(r"^[\W_]+$", tok):
            continue
        words.append(tok)
    return words


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def roget_links(roget_path: "str | Path") -> list[tuple[str, str, str]]:
    """Parse Roget's Thesaurus 1911 and return (headword, related, rel) triples.

    Synonym extraction
    ------------------
    For each numbered entry, splits the body into POS sections (N., V., Adj.).
    Each POS section is further split on semicolons into *sub-groups* (Roget's
    tighter synonym clusters).  All pairwise combinations of words within the
    same sub-group are emitted as synonym links.  Words in different sub-groups
    (even within the same POS section) are not directly linked.  Phr., Adv.,
    and Int. sections are skipped.

    Words from different entries are never linked as synonyms.

    Antonym extraction
    ------------------
    Explicit ``{ant. NNN}`` markers are extracted from each entry's raw body
    (before noise-cleaning removes curly-brace content).  For each such marker,
    all words from entry X and all words from the referenced partner entry NNN
    are cross-produced into antonym links.

    When both ``{ant. 133}`` in entry #132 and ``{ant. 132}`` in entry #133
    are present, both produce the same set of cross-product pairs (just with
    src/dst reversed), which ``mine_relations`` canonically deduplicates.

    Implicit sequential pairing is deferred — see module docstring.

    Parameters
    ----------
    roget_path:
        Path to pg22.txt (UTF-8, CRLF or LF line endings).

    Returns
    -------
    list of (headword, related, rel)
        ``rel`` ∈ ``{"synonym", "antonym"}``.  Headwords are raw text strings;
        ``mine_relations`` applies ``_normalize_term`` before index lookup.
    """
    roget_path = Path(roget_path)

    # Open with newline=None: Python normalises CRLF→LF transparently.
    with roget_path.open(encoding="utf-8", newline=None) as f:
        content = f.read()
    # Belt-and-suspenders: strip any \r that survived (e.g., bare CR on Mac)
    content = content.replace("\r", "")

    # Locate all entry start positions
    entry_starts = list(_ENTRY_START_RE.finditer(content))
    if not entry_starts:
        return []

    # ---------------------------------------------------------------------------
    # First pass: collect per-entry words and antonym references.
    # ---------------------------------------------------------------------------
    entry_words: dict[str, list[str]] = {}   # entry_num → words
    antonym_refs: dict[str, list[str]] = {}  # entry_num → [partner nums]
    synonym_raw: list[tuple[str, str]] = []  # (word_a, word_b)

    for i, m in enumerate(entry_starts):
        entry_num: str = m.group(1)
        body_start: int = m.start()
        body_end: int = (
            entry_starts[i + 1].start()
            if i + 1 < len(entry_starts)
            else len(content)
        )
        raw_body: str = content[body_start:body_end]

        # ---- Extract antonym refs BEFORE cleaning (they're in curly braces) ----
        ant_nums: list[str] = []
        for ant_m in _ANT_MARKER_RE.finditer(raw_body):
            for n in re.split(r"[\s,]+", ant_m.group(1)):
                n = n.strip()
                if n:
                    ant_nums.append(n)
        if ant_nums:
            antonym_refs[entry_num] = ant_nums

        # ---- Clean body and flatten to a single line -------------------------
        cleaned: str = _clean_text(raw_body)
        flat: str = " ".join(cleaned.split())

        # ---- Split into POS sections -----------------------------------------
        # re.split with a group returns:
        #   [prefix, marker1, section1, marker2, section2, ...]
        # prefix is the entry header (CategoryName.—); it is discarded.
        parts: list[str] = _POS_SPLIT_RE.split(flat)

        all_words: list[str] = []
        k: int = 1  # index of first (marker, section_text) pair
        while k + 1 < len(parts):
            pos_marker: str = parts[k]
            section_text: str = parts[k + 1]
            k += 2

            # Skip Phr., Adv., Int. — phrases/adverbs/interjections rarely
            # appear in short biblical lexicon glosses.
            if pos_marker in ("Phr", "Adv", "Int"):
                continue

            # Split the POS section on semicolons → sub-groups.
            # Emit all-pairs WITHIN each sub-group; sub-groups within the same
            # POS section are NOT cross-connected.  This keeps Roget's inherent
            # synonym-cluster structure and controls output scale: a section of
            # k sub-groups of n/k words each produces k×C(n/k,2) pairs rather
            # than C(n,2), a significant reduction for large sections.
            for subgroup in section_text.split(";"):
                words: list[str] = _extract_words(subgroup)
                for word_a, word_b in combinations(words, 2):
                    synonym_raw.append((word_a, word_b))
                all_words.extend(words)

        entry_words[entry_num] = all_words

    # ---------------------------------------------------------------------------
    # Second pass: emit antonym links from explicit {ant. NNN} markers.
    # ---------------------------------------------------------------------------
    antonym_raw: list[tuple[str, str]] = []
    for entry_num, partner_nums in antonym_refs.items():
        src_words = entry_words.get(entry_num, [])
        if not src_words:
            continue
        for partner_num in partner_nums:
            dst_words = entry_words.get(partner_num, [])
            if not dst_words:
                continue
            for sw in src_words:
                for dw in dst_words:
                    antonym_raw.append((sw, dw))

    # ---- Build final links list ----------------------------------------------
    links: list[tuple[str, str, str]] = []
    for a, b in synonym_raw:
        links.append((a, b, "synonym"))
    for a, b in antonym_raw:
        links.append((a, b, "antonym"))

    return links


def build_roget() -> tuple[list[Edge], list[Edge]]:
    """Load lexicon entries, build the gloss index, and mine Roget edges.

    Returns
    -------
    (synonym_edges, antonym_edges)
        Two lists of :class:`~tools.relations.edge.Edge` objects.  Edges
        within each list are deduplicated (set collapse + mine_relations
        internal dedup).
    """
    # Load all lexicon entries (grc + hbo)
    entries: list[dict] = []
    for lex_file in sorted((ROOT / "lexicon").glob("**/*.json")):
        try:
            entry = json.loads(lex_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries.append(entry)

    idx = gloss_term_index(entries, lang="en")

    print(f"Parsing {_ROGET_PATH.relative_to(ROOT)} …", flush=True)
    links = roget_links(_ROGET_PATH)
    print(
        f"  Roget raw links: {len(links):,} "
        f"({sum(1 for _,_,r in links if r=='synonym'):,} syn, "
        f"{sum(1 for _,_,r in links if r=='antonym'):,} ant)",
        flush=True,
    )

    # Mine edges through the gloss bridge
    all_edges = mine_relations(
        idx=idx,
        headword_links=links,
        source=_SOURCE,
        method="mined",
        base_rank=_ROGET_BASE_RANK,
    )

    # Dedup: Edge is a frozen dataclass; set() collapses exact duplicates from
    # symmetric antonym references (X→Y and Y→X both produce the same
    # canonically-oriented edge after mine_relations).
    deduped: set[Edge] = set(all_edges)

    synonym_edges = [e for e in deduped if e.rel == "synonym"]
    antonym_edges = [e for e in deduped if e.rel == "antonym"]

    return synonym_edges, antonym_edges


def main() -> None:
    """CLI entry point: build edges, write source-tagged JSONL, print summary."""
    from tools.relations.rank import DEFAULT_RANK_THRESHOLD

    derived_dir = ROOT / "relations" / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)

    syn_path = derived_dir / f"{_SOURCE}.synonym.jsonl"
    ant_path = derived_dir / f"{_SOURCE}.antonym.jsonl"

    synonym_edges, antonym_edges = build_roget()

    write_jsonl(syn_path, synonym_edges)
    write_jsonl(ant_path, antonym_edges)

    # Summary with above/below threshold split
    threshold = DEFAULT_RANK_THRESHOLD
    syn_above = sum(1 for e in synonym_edges if e.rank >= threshold)
    syn_below = sum(1 for e in synonym_edges if e.rank < threshold)
    ant_above = sum(1 for e in antonym_edges if e.rank >= threshold)
    ant_below = sum(1 for e in antonym_edges if e.rank < threshold)

    print(f"\nsynonym edges written : {len(synonym_edges):,}  →  {syn_path.relative_to(ROOT)}")
    print(f"  above threshold ({threshold}): {syn_above:,}")
    print(f"  below threshold          : {syn_below:,}")
    print(f"antonym edges written : {len(antonym_edges):,}  →  {ant_path.relative_to(ROOT)}")
    print(f"  above threshold ({threshold}): {ant_above:,}")
    print(f"  below threshold          : {ant_below:,}")

    # Spot-check: look for known synonym pairs (love/affection → G0026/G5368)
    # and antonym pairs (love/hate → G0026/G3404)
    print("\nSpot-check (synonym edges for known Biblical lemma pairs):")
    syn_set = {(e.src, e.dst) for e in synonym_edges}
    syn_known = [
        ("G0026", "G5368"),  # ἀγάπη / φιλέω   (both gloss as "love")
        ("G5479", "G2167"),  # χαρά / εὐφροσύνη (both gloss as "joy"/"gladness")
        ("G3056", "G4487"),  # λόγος / ῥῆμα      (word/saying)
    ]
    for pair in syn_known:
        pair_sorted = tuple(sorted(pair))
        if pair_sorted in syn_set:
            a, b = pair_sorted
            print(f"  FOUND: {a} -- {b}  (synonym)")
        else:
            print(f"  not found: {pair_sorted[0]} -- {pair_sorted[1]}")

    print("\nSpot-check (antonym edges for known Biblical lemma pairs):")
    ant_set = {(e.src, e.dst) for e in antonym_edges}
    ant_known = [
        ("G0026", "G3404"),  # ἀγάπη / μισέω  (love / hate)
        ("G5368", "G3404"),  # φιλέω / μισέω   (love / hate)
    ]
    found_any = False
    for pair in ant_known:
        pair_sorted = tuple(sorted(pair))
        if pair_sorted in ant_set:
            a, b = pair_sorted
            print(f"  FOUND: {a} -- {b}  (antonym)")
            found_any = True
    if not found_any:
        print(
            "  (none found — antonym coverage is limited to 14 explicit {ant.} entries;\n"
            "   'love'/'hate' are #897/#898 which use implicit pairing, deferred)"
        )


if __name__ == "__main__":
    main()
