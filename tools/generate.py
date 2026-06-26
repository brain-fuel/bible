"""Generate the bible/nt corpus from the source site."""
import json
import sys
from pathlib import Path

from tools.fetch import chapter_url, fetch_cached
from tools.parse import parse_chapter

ROOT = Path(__file__).resolve().parents[1]
PAD = 3  # fixed chapter-filename width across the whole corpus


def load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return data["books"]


def out_path(root: Path, meta: dict, chapter: int) -> Path:
    testament = meta.get("testament", "nt")
    return Path(root) / "bible" / testament / meta["code"] / f"{chapter:0{PAD}d}.json"


def write_chapter(root: Path, meta: dict, chapter: int, cache_dir: Path) -> Path:
    url = chapter_url(meta, chapter)
    cache_path = Path(cache_dir) / meta["dir"] / f"{meta['prefix']}{chapter:02d}.htm"
    page = fetch_cached(url, cache_path)
    chapter_obj = parse_chapter(page, meta, chapter)
    dest = out_path(root, meta, chapter)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(chapter_obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return dest


def main() -> int:
    root = ROOT
    cache_dir = root / "data" / "cache"
    for sub in ("ot", "apo"):
        keep = root / "bible" / sub / ".gitkeep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch()
    count = 0
    for meta in load_books():
        if meta["testament"] != "nt" or not meta.get("dir"):
            continue
        for chapter in range(1, meta["chapters"] + 1):
            dest = write_chapter(root, meta, chapter, cache_dir)
            count += 1
            print(f"wrote {dest.relative_to(root)}")
    print(f"done: {count} chapters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
