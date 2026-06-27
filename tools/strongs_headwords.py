"""Shared helper: Hebrew dictionary headwords from strongs-hebrew.xml.

Provides a single function used by BOTH build_lexicon.py and the morph
generation pipeline so the two can never drift on what constitutes the
canonical Hebrew LEMMA for a given Strong's number.

Design constraint: this module has NO import-time side effects and reads
only from the raw cache XML.  It does NOT import from tools.build_lexicon
(which would be circular, since the lexicon is built FROM the morph output)
and does NOT read from the generated lexicon/ directory.
"""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

_NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

# Default path to the raw XML file (within the repository tree).
_DEFAULT_XML = (
    Path(__file__).resolve().parents[1]
    / "data" / "cache" / "morph" / "raw" / "strongs-hebrew.xml"
)


def load_hebrew_headwords(xml_path: str | Path | None = None) -> dict[str, str]:
    """Parse strongs-hebrew.xml and return {H#### -> NFC headword} mapping.

    The headword is the ``lemma`` attribute of the first ``<w>`` element in
    each ``<div type="entry">``, NFC-normalized.  This is the same field that
    ``build_lexicon.load_hebrew_strongs()`` stores as ``entry["lemma"]``,
    so ``conllu.LEMMA`` for Hebrew tokens will equal ``lexicon.lemma`` for
    every matched Strong's number.

    Args:
        xml_path: Path to strongs-hebrew.xml.  Defaults to the repository's
                  ``data/cache/morph/raw/strongs-hebrew.xml``.

    Returns:
        Dict mapping Strong's IDs (e.g. ``"H0430"``) to clean NFC headwords.
        Entries with no ``<w>`` element or empty ``lemma`` attribute are
        omitted (none observed in the current file).
    """
    path = Path(xml_path) if xml_path is not None else _DEFAULT_XML
    tree = ET.parse(path)
    root_elem = tree.getroot()
    result: dict[str, str] = {}

    for div in root_elem.iter(_NS + "div"):
        if div.get("type") != "entry":
            continue
        n_str = div.get("n", "")
        if not n_str or not n_str.isdigit():
            continue
        strong_id = f"H{int(n_str):04d}"
        w = div.find(_NS + "w")
        if w is None:
            continue
        raw_lemma = w.get("lemma", "").strip()
        if not raw_lemma:
            continue
        result[strong_id] = unicodedata.normalize("NFC", raw_lemma)

    return result
