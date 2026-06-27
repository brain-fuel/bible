"""
tools/build_lexicon.py — L2a lexicon builder

Produces one JSON entry per Strong's number used in the corpus.
Writes lexicon/grc/G####.json (Greek) and lexicon/hbo/H####.json (Hebrew).

Sources (PD / CC-BY only):
  strongs-greek.xml  — Public Domain (Strong's 1890)
  strongs-hebrew.xml — Public Domain (Strong's 1890, OSIS XML by openscriptures)
  TBESG.txt          — CC-BY 4.0 (STEPBible / Tyndale House); gloss column only

Latin glosses are NOT generated: there is no Vulgate→Strong's alignment in this
corpus, so Latin derivation would require fabrication. Only 'en' is seeded; the
glosses dict is structured as a language-keyed map ready for future language additions.

Entry schema:
  {strong, lemma, translit, lang, pos, glosses, senses, domains, root, sources}

Usage:
  python -m tools.build_lexicon
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def seed_glosses(strong: str, sources: dict) -> dict:
    """Return {"en": [{text, src}, ...]} from all sources that have this strong.

    Each source entry must be a dict with at least a "gloss" key.
    Sources without this strong are silently skipped.
    Languages other than "en" are not generated (no Latin/Finnish/etc. available
    without fabrication; see module docstring).
    """
    en_glosses: list[dict] = []
    for src_name, src_dict in sources.items():
        entry = src_dict.get(strong)
        if entry is None:
            continue
        gloss_text = entry.get("gloss", "").strip()
        if gloss_text:
            en_glosses.append({"text": gloss_text, "src": src_name})
    return {"en": en_glosses}


def build_entry(strong: str, lang: str, sources: dict) -> dict:
    """Build one lexicon entry dict for the given Strong's number.

    Args:
        strong:  Strong's ID in 4-digit padded form, e.g. "G0026" or "H1254".
        lang:    ISO 639-3 code — "grc" for Greek, "hbo" for Hebrew.
        sources: Dict of {source_name: {strong_id: {lemma?, translit?, gloss?, root?, pos?}}}.
                 The first source whose entry contains a non-empty "lemma" is used as
                 the primary (provides lemma, translit, pos, root).

    Returns:
        Full entry dict matching the L2a schema.
    """
    glosses = seed_glosses(strong, sources)

    # Primary source: first that supplies a lemma for this strong
    lemma = ""
    translit = ""
    pos = ""
    root = None

    for _src_name, src_dict in sources.items():
        entry = src_dict.get(strong, {})
        if entry.get("lemma"):
            lemma = entry.get("lemma", "")
            translit = entry.get("translit", "")
            pos = entry.get("pos", "")
            root = entry.get("root")  # may be None — that is valid
            break

    # Sources that contributed to this entry (had a record for this strong)
    src_list = [k for k, v in sources.items() if strong in v]

    # Seed one sense from the primary English gloss
    en_glosses = glosses.get("en", [])
    primary_gloss = en_glosses[0]["text"] if en_glosses else ""
    senses = [{"id": 1, "gloss_en": primary_gloss, "domain": None}]

    return {
        "strong": strong,
        "lemma": lemma,
        "translit": translit,
        "lang": lang,
        "pos": pos,
        "glosses": glosses,
        "senses": senses,
        "domains": [],   # filled in Task 8
        "root": root,
        "sources": src_list,
    }


# ---------------------------------------------------------------------------
# Source loaders (called only by __main__)
# ---------------------------------------------------------------------------

def _itertext_clean(elem) -> str:
    """Concatenate all text within an element, stripping internal whitespace runs."""
    text = "".join(elem.itertext())
    return re.sub(r"\s+", " ", text).strip()


def load_greek_strongs(xml_path: str | Path) -> dict:
    """Parse strongs-greek.xml (Public Domain).

    Returns {G####: {lemma, translit, gloss, pos, root}} keyed by Strong's ID.
    root is "G####" derived from <strongs_derivation> → <strongsref>, else None.
    """
    tree = ET.parse(xml_path)
    root_elem = tree.getroot()
    result: dict = {}

    for entry in root_elem.iter("entry"):
        s_attr = entry.get("strongs", "")
        if not s_attr:
            continue
        try:
            snum = int(s_attr)
        except ValueError:
            continue
        strong_id = f"G{snum:04d}"

        greek = entry.find("greek")
        lemma = greek.get("unicode", "") if greek is not None else ""
        translit = greek.get("translit", "") if greek is not None else ""

        # Main gloss: strongs_def preferred, fall back to kjv_def
        sd = entry.find("strongs_def")
        gloss = _itertext_clean(sd) if sd is not None else ""
        if not gloss:
            kjv = entry.find("kjv_def")
            gloss = _itertext_clean(kjv) if kjv is not None else ""

        # Root: first GREEK strongsref in derivation
        root_val: str | None = None
        drv = entry.find("strongs_derivation")
        if drv is not None:
            for sref in drv.findall("strongsref"):
                if sref.get("language", "").upper() == "GREEK":
                    try:
                        r = int(sref.get("strongs", "0"))
                        root_val = f"G{r:04d}"
                    except ValueError:
                        pass
                    break

        result[strong_id] = {
            "lemma": lemma,
            "translit": translit,
            "gloss": gloss,
            "pos": "",   # POS derived from TBESG col 5 if available
            "root": root_val,
        }
    return result


def load_tbesg(txt_path: str | Path) -> dict:
    """Parse TBESG.txt (CC-BY 4.0 STEPBible).

    Returns {G####: {gloss, pos}} using col 6 (brief gloss) and col 5 (morph).
    Only G0001–G5624 entries (original Strong's range) are returned; extended
    STEP numbers are skipped so they don't shadow canonical Strong's entries.
    """
    result: dict = {}
    with open(txt_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            # Data rows start with G followed by 4 digits
            if not re.match(r"G\d{4}", line):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            estrong = parts[0].strip()
            # Normalise to 4-digit: eStrong is already G####
            if not re.match(r"^G\d{4}$", estrong):
                continue
            try:
                snum = int(estrong[1:])
            except ValueError:
                continue
            if snum > 5624:
                # Extended STEP numbers beyond original Strong's range
                continue
            strong_id = f"G{snum:04d}"
            gloss = parts[6].strip() if len(parts) > 6 else ""
            pos = parts[5].strip() if len(parts) > 5 else ""
            if gloss:
                result[strong_id] = {"gloss": gloss, "pos": pos}
    return result


def load_hebrew_strongs(xml_path: str | Path) -> dict:
    """Parse strongs-hebrew.xml (Public Domain; OSIS XML by openscriptures).

    Returns {H####: {lemma, translit, gloss, pos, root}} keyed by Strong's ID.
    gloss = first <item> text from the entry's <list>.
    root = H#### from <note type="exegesis"><w src="..."/> if present.
    """
    NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
    tree = ET.parse(xml_path)
    root_elem = tree.getroot()
    result: dict = {}

    for div in root_elem.iter(NS + "div"):
        if div.get("type") != "entry":
            continue
        n_str = div.get("n", "")
        if not n_str or not n_str.isdigit():
            continue
        snum = int(n_str)
        strong_id = f"H{snum:04d}"

        w = div.find(NS + "w")
        lemma = w.get("lemma", "") if w is not None else ""
        xlit = w.get("xlit", "") if w is not None else ""
        pos = w.get("morph", "") if w is not None else ""

        # Gloss: first <item> in the entry's <list>
        gloss = ""
        lst = div.find(NS + "list")
        if lst is not None:
            items = lst.findall(NS + "item")
            if items:
                raw = (items[0].text or "").strip()
                # Strip leading "1) " numbering if present
                gloss = re.sub(r"^\d+\)\s*", "", raw).strip()

        # Fallback: explanation note
        if not gloss:
            for note in div.findall(NS + "note"):
                if note.get("type") == "explanation":
                    gloss = _itertext_clean(note)
                    break

        # Root: <note type="exegesis"> containing <w src="N"/>
        root_val: str | None = None
        for note in div.findall(NS + "note"):
            if note.get("type") == "exegesis":
                src_w = note.find(NS + "w")
                if src_w is not None:
                    src_attr = src_w.get("src", "")
                    if src_attr and src_attr.isdigit():
                        try:
                            root_val = f"H{int(src_attr):04d}"
                        except ValueError:
                            pass
                break

        result[strong_id] = {
            "lemma": lemma,
            "translit": xlit,
            "gloss": gloss,
            "pos": pos,
            "root": root_val,
        }
    return result


# ---------------------------------------------------------------------------
# Strong's extraction from CoNLL-U corpus
# ---------------------------------------------------------------------------

def extract_strongs_from_corpus(morph_dir: str | Path) -> tuple[set, set]:
    """Walk morph/**/*.conllu and return (grc_strongs, hbo_strongs) sets.

    Strong's IDs are in the MISC column as Strong=G#### or Strong=H####.
    """
    morph_dir = Path(morph_dir)
    grc: set[str] = set()
    hbo: set[str] = set()
    pattern = re.compile(r"Strong=([GH]\d{4})")

    for conllu_file in morph_dir.rglob("*.conllu"):
        with open(conllu_file, encoding="utf-8") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    sid = m.group(1)
                    if sid.startswith("G"):
                        grc.add(sid)
                    else:
                        hbo.add(sid)
    return grc, hbo


# ---------------------------------------------------------------------------
# Main: build real lexicon files
# ---------------------------------------------------------------------------

def main():
    base = Path(__file__).parent.parent  # repo root
    raw = base / "data" / "cache" / "morph" / "raw"
    morph_dir = base / "morph"

    print("Loading source lexicons...")
    grc_strongs = load_greek_strongs(raw / "strongs-greek.xml")
    print(f"  strongs-greek.xml: {len(grc_strongs)} entries")

    tbesg = load_tbesg(raw / "TBESG.txt")
    print(f"  TBESG.txt: {len(tbesg)} entries")

    hbo_strongs = load_hebrew_strongs(raw / "strongs-hebrew.xml")
    print(f"  strongs-hebrew.xml: {len(hbo_strongs)} entries")

    print("Extracting Strong's numbers from corpus...")
    grc_ids, hbo_ids = extract_strongs_from_corpus(morph_dir)
    print(f"  Greek unique Strong's in corpus: {len(grc_ids)}")
    print(f"  Hebrew unique Strong's in corpus: {len(hbo_ids)}")

    # Source dicts for build_entry
    grc_sources = {
        "strongs-greek": grc_strongs,
        "tbesg": tbesg,
    }
    hbo_sources = {
        "strongs-hebrew": hbo_strongs,
    }

    # Write Greek entries
    grc_out = base / "lexicon" / "grc"
    grc_out.mkdir(parents=True, exist_ok=True)
    grc_no_gloss = 0
    for sid in sorted(grc_ids):
        entry = build_entry(sid, "grc", grc_sources)
        if not entry["glosses"]["en"]:
            grc_no_gloss += 1
        (grc_out / f"{sid}.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    grc_coverage = 100 * (len(grc_ids) - grc_no_gloss) / len(grc_ids)
    print(f"\nGreek lexicon: {len(grc_ids)} files written to lexicon/grc/")
    print(f"  en-gloss coverage: {len(grc_ids) - grc_no_gloss}/{len(grc_ids)} ({grc_coverage:.1f}%)")
    if grc_no_gloss:
        print(f"  WARNING: {grc_no_gloss} entries have no English gloss")

    # Write Hebrew entries
    hbo_out = base / "lexicon" / "hbo"
    hbo_out.mkdir(parents=True, exist_ok=True)
    hbo_no_gloss = 0
    for sid in sorted(hbo_ids):
        entry = build_entry(sid, "hbo", hbo_sources)
        if not entry["glosses"]["en"]:
            hbo_no_gloss += 1
        (hbo_out / f"{sid}.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    hbo_coverage = 100 * (len(hbo_ids) - hbo_no_gloss) / len(hbo_ids)
    print(f"\nHebrew lexicon: {len(hbo_ids)} files written to lexicon/hbo/")
    print(f"  en-gloss coverage: {len(hbo_ids) - hbo_no_gloss}/{len(hbo_ids)} ({hbo_coverage:.1f}%)")
    if hbo_no_gloss:
        print(f"  WARNING: {hbo_no_gloss} entries have no English gloss")

    # Spot-check G0026
    g0026 = json.loads((grc_out / "G0026.json").read_text(encoding="utf-8"))
    print(f"\nSpot-check G0026 (ἀγάπη):")
    print(f"  lemma: {g0026['lemma']}")
    print(f"  root:  {g0026['root']}")
    print(f"  en glosses: {g0026['glosses']['en']}")

    # Spot-check H1254
    h1254 = json.loads((hbo_out / "H1254.json").read_text(encoding="utf-8"))
    print(f"\nSpot-check H1254 (בָּרָא):")
    print(f"  lemma: {h1254['lemma']}")
    print(f"  en glosses: {h1254['glosses']['en']}")


if __name__ == "__main__":
    main()
