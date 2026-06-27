"""Generate the OT corpus: merge KJV, Vulgate, and Hebrew into chapter files."""
import json
import sys
from pathlib import Path

from tools.sources.scrollmapper import load_dataset
from tools.sources.sefaria import load_chapter
from tools.merge_ot import load_vmap, masoretic_ref, build_chapter

ROOT = Path(__file__).resolve().parents[1]
PAD = 3


def load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def out_path_ot(root, code, chapter):
    return Path(root) / "bible" / "ot" / code / f"{chapter:0{PAD}d}.json"


def _latin_by_kjv(code, kjv_chapter, kjv_verses, vul_index, vmap, vul_name):
    """Place Vulgate text at KJV verse positions. Invert latin vmap (KJV->Latin)."""
    latin = {}
    vbook = vul_index.get(vul_name, {})
    for v in kjv_verses:
        key = f"{code} {kjv_chapter}:{v}"
        target = vmap["latin"].get(key)  # "chap:verse" in Latin numbering, if diverging
        if target:
            lc, lv = target.split(":")
            latin[v] = vbook.get(int(lc), {}).get(int(lv), "")
        else:
            latin[v] = vbook.get(kjv_chapter, {}).get(v, "")
    return latin


def write_book(root, meta, kjv_idx, vul_idx, vmap, cache_dir):
    code = meta["code"]
    kjv_book = kjv_idx.get(meta["kjv_name"], {})
    written = 0
    hebrew_chapter_cache = {}
    for kjv_chapter in sorted(kjv_book):
        kjv_verses = kjv_book[kjv_chapter]
        latin_by_kjv = _latin_by_kjv(code, kjv_chapter, kjv_verses, vul_idx, vmap,
                                     meta["vulgate_name"])
        hebrew_ref_by_kjv = {v: masoretic_ref(code, kjv_chapter, v, vmap)
                             for v in kjv_verses}
        hebrew_by_kjv = {}
        for v, href in hebrew_ref_by_kjv.items():
            hc, hv = href.split(":")
            hc, hv = int(hc), int(hv)
            if hc not in hebrew_chapter_cache:
                hebrew_chapter_cache[hc] = load_chapter(meta["sefaria_name"], hc, cache_dir)
            hebrew_by_kjv[v] = hebrew_chapter_cache[hc].get(hv, "")
        chapter_obj = build_chapter(meta, kjv_chapter, kjv_verses, latin_by_kjv,
                                    hebrew_by_kjv, hebrew_ref_by_kjv)
        dest = out_path_ot(root, code, kjv_chapter)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(chapter_obj, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        written += 1
    return written


def main():
    cache_dir = ROOT / "data" / "cache"
    vmap = load_vmap()
    kjv_idx = load_dataset("KJV", cache_dir)
    vul_idx = load_dataset("VulgClementine", cache_dir)
    total = 0
    for meta in load_books():
        n = write_book(ROOT, meta, kjv_idx, vul_idx, vmap, cache_dir)
        total += n
        print(f"{meta['code']}: {n} chapters")
    print(f"done: {total} chapters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
