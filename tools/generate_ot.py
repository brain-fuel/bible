"""Generate the OT corpus, driven entirely by the edition registry.

Every column, its source backend, versification namespace, output ordering and
header name comes from a row in ``data/editions.json``. Adding a new parallel
OT text needs only a registry row (plus its per-book source name in
``books.json``); this driver does not name any edition.
"""
import json
import sys
from pathlib import Path

from tools.editions import editions_for
from tools.sources.registry import prepare_source
from tools.merge_ot import load_vmap, source_ref, build_chapter

ROOT = Path(__file__).resolve().parents[1]
PAD = 3


def load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def out_path_ot(root, code, chapter):
    return Path(root) / "bible" / "ot" / code / f"{chapter:0{PAD}d}.json"


def output_editions(editions):
    """Column order: non-base editions in registry order, then the base last."""
    base = next(e for e in editions if e.get("base"))
    return [e for e in editions if not e.get("base")] + [base], base


def build_columns(meta, editions, base, handles, vmap, chapter, base_verses):
    """For one chapter, resolve every edition's text + divergence ref per verse."""
    code = meta["code"]
    columns = {}
    for e in editions:
        eid = e["id"]
        if eid == base["id"]:
            columns[eid] = {v: {"text": base_verses[v], "src": None}
                            for v in base_verses}
            continue
        vmap_key = e.get("vmap_key")
        col = {}
        for v in base_verses:
            sref = source_ref(code, chapter, v, vmap, vmap_key)
            sc, sv = sref.split(":")
            text = handles[eid].chapter(meta, int(sc)).get(int(sv), "")
            src = sref if sref != f"{chapter}:{v}" else None
            col[v] = {"text": text, "src": src}
        columns[eid] = col
    return columns


def write_book(root, meta, editions, handles, vmap):
    out_eds, base = output_editions(editions)
    base_handle = handles[base["id"]]
    written = 0
    for chapter in base_handle.chapters(meta):
        base_verses = base_handle.chapter(meta, chapter)
        columns = build_columns(meta, editions, base, handles, vmap, chapter,
                                base_verses)
        obj = build_chapter(meta, out_eds, base["id"], chapter, columns)
        dest = out_path_ot(root, meta["code"], chapter)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        written += 1
    return written


def main():
    cache_dir = ROOT / "data" / "cache"
    editions = editions_for("ot")
    vmap = load_vmap()
    handles = {e["id"]: prepare_source(e, cache_dir) for e in editions}
    total = 0
    for meta in load_books():
        n = write_book(ROOT, meta, editions, handles, vmap)
        total += n
        print(f"{meta['code']}: {n} chapters")
    print(f"done: {total} chapters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
