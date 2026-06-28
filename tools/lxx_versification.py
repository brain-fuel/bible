"""LXX book registry and LXX<->MT versification map.

Interfaces:
  lxx_books()    -- list of LXX book dicts, each with testament='lxx'
  load_lxx_vmap() -- dict loading data/versification/lxx-versification.json
  mt_ref(code, chapter, verse) -> str|None
                 -- MT 'chapter:verse' for a protocanon LXX position,
                    or None if no MT counterpart (deuterocanon / absent).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_VMAP_PATH = ROOT / "data" / "versification" / "lxx-versification.json"
_SUPP_PATH = ROOT / "data" / "versification" / "lxx-versification-supplement.json"
_BOOKS_PATH = ROOT / "data" / "books.json"

_vmap_cache = None
_books_cache = None
_protocanon_cache = None


def load_lxx_vmap():
    """Load the LXX<->MT versification map (TVTMS-derived + CC0 supplement).

    Returns a dict with key 'greek' mapping LXX 'CODE C:V' to MT 'c:v'
    (only for verses where LXX numbering diverges from MT), plus 'greek'
    entries with null values for LXX-only positions (e.g. Psalm 151).
    """
    global _vmap_cache
    if _vmap_cache is not None:
        return _vmap_cache

    data = json.loads(_VMAP_PATH.read_text(encoding="utf-8"))
    greek = dict(data.get("greek", {}))

    # Merge CC0 supplement (supplement entries override TVTMS).
    if _SUPP_PATH.exists():
        supp = json.loads(_SUPP_PATH.read_text(encoding="utf-8"))
        for k, v in supp.get("greek", {}).items():
            greek[k] = v  # null values are preserved as Python None

    _vmap_cache = {"greek": greek}
    return _vmap_cache


def _load_books():
    global _books_cache
    if _books_cache is not None:
        return _books_cache
    data = json.loads(_BOOKS_PATH.read_text(encoding="utf-8"))
    _books_cache = data["books"]
    return _books_cache


def _lxx_protocanon_codes():
    """Return the frozenset of LXX codes that have MT (Hebrew) counterparts.

    A code qualifies if its books.json row has testament='ot' AND an
    lxx_order field (i.e. it participates in the LXX canon AND is an OT
    protocanon book with a Hebrew text).  Deuterocanon codes (testament='apo')
    and LXX-only codes (testament='lxx') are excluded, as are codes such as
    2ES that have no lxx_order at all (4 Ezra is not a Greek LXX book).
    """
    global _protocanon_cache
    if _protocanon_cache is not None:
        return _protocanon_cache
    books = _load_books()
    _protocanon_cache = frozenset(
        b["code"]
        for b in books
        if b.get("testament") == "ot" and b.get("lxx_order") is not None
    )
    return _protocanon_cache


def lxx_books():
    """Return a list of LXX book dicts, each with testament='lxx'.

    Builds the list from data/books.json:
    - OT rows that carry an 'lxx_order' field: copied with testament='lxx'.
    - Apo rows that carry an 'lxx_order' field: copied with testament='lxx'.
    - Rows already bearing testament='lxx' (3MA, 4MA, ODE, PSS): returned as-is.
    The list is sorted by lxx_order.
    """
    books = _load_books()
    result = []
    for b in books:
        if b.get("testament") == "lxx":
            # New LXX-only codes already have the right testament.
            result.append(b)
        elif b.get("lxx_order") is not None:
            # OT or apo row that participates in the LXX canon:
            # synthesize a view with testament='lxx'.
            row = dict(b)
            row["testament"] = "lxx"
            result.append(row)
    result.sort(key=lambda b: b.get("lxx_order", 9999))
    return result


def mt_ref(lxx_code, lxx_chapter, lxx_verse):
    """Return the MT (Hebrew) 'chapter:verse' for a LXX verse position.

    Parameters
    ----------
    lxx_code    : str  -- uppercase 3-char book code (e.g. 'PSA', 'GEN')
    lxx_chapter : int  -- LXX chapter number
    lxx_verse   : int  -- LXX verse number

    Returns
    -------
    str   -- MT 'chapter:verse' string for protocanon positions.
             For verses with no divergence, returns 'chapter:verse'
             (identity mapping).
    None  -- for deuterocanon books, LXX-only books, codes not in the LXX
             canon at all (e.g. 2ES), or genuinely absent verses (e.g.
             Psalm 151).
    """
    # Only OT protocanon books (testament='ot' with lxx_order in books.json)
    # have MT counterparts.  Deuterocanon (testament='apo'), LXX-only codes
    # (testament='lxx'), and codes absent from the LXX entirely (e.g. 2ES)
    # all return None.
    if lxx_code not in _lxx_protocanon_codes():
        return None

    vmap = load_lxx_vmap()
    greek = vmap["greek"]
    key = f"{lxx_code} {lxx_chapter}:{lxx_verse}"

    if key in greek:
        val = greek[key]
        if val is None:
            # Explicitly marked as absent (e.g. Psalm 151).
            return None
        return val

    # No divergence recorded: identity mapping.
    return f"{lxx_chapter}:{lxx_verse}"
