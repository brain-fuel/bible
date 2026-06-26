"""Structural validation and James regression oracle for the corpus."""
import json
import sys
from pathlib import Path

from tools.generate import load_books, out_path

ROOT = Path(__file__).resolve().parents[1]
BODY_KEYS = ("latin_vulgate", "greek_textus_receptus", "king_james")


def validate_chapter(obj: dict) -> list[str]:
    errs = []
    tag = f"{obj.get('book_id','?')} {obj.get('chapter','?')}"
    verses = obj.get("verses", [])
    if not verses:
        errs.append(f"{tag}: no verses")
        return errs
    numbers = [v["verse"] for v in verses]
    if numbers != list(range(1, len(numbers) + 1)):
        errs.append(f"{tag}: verse numbers not contiguous from 1: {numbers}")
    for v in verses:
        if not v.get("latin_vulgate"):
            errs.append(f"{tag}:{v.get('verse')}: empty latin_vulgate")
        if not v.get("king_james"):
            errs.append(f"{tag}:{v.get('verse')}: empty king_james")
        if not v.get("greek_textus_receptus"):
            errs.append(f"{tag}:{v.get('verse')}: empty greek_textus_receptus")
    return errs


def compare_to_james(generated: dict, reference: dict) -> list[str]:
    errs = []
    gv = {v["verse"]: v for v in generated["verses"]}
    rv = {v["verse"]: v for v in reference["verses"]}
    if set(gv) != set(rv):
        errs.append(f"verse set mismatch: {sorted(set(gv) ^ set(rv))}")
    for n in sorted(set(gv) & set(rv)):
        for key in BODY_KEYS:
            if gv[n].get(key) != rv[n].get(key):
                errs.append(f"{generated.get('book_id', reference.get('book_id', 'JAM'))} v{n} {key} differs")
    return errs


def main() -> int:
    errs = []
    books = [b for b in load_books() if b["testament"] == "nt" and b.get("dir")]
    for meta in books:
        found = 0
        for chapter in range(1, meta["chapters"] + 1):
            path = out_path(ROOT, meta, chapter)
            if not path.exists():
                errs.append(f"{meta['code']} {chapter}: missing file {path.name}")
                continue
            found += 1
            obj = json.loads(path.read_text(encoding="utf-8"))
            errs.extend(validate_chapter(obj))
        if found != meta["chapters"]:
            errs.append(f"{meta['code']}: expected {meta['chapters']} files, found {found}")

    ref_dir = ROOT / "tests" / "fixtures" / "james_ref"
    jam = next(b for b in books if b["code"] == "JAM")
    for chapter in range(1, jam["chapters"] + 1):
        gen_path = out_path(ROOT, jam, chapter)
        ref_path = ref_dir / f"jas{chapter:03d}.json"
        if gen_path.exists() and ref_path.exists():
            generated = json.loads(gen_path.read_text(encoding="utf-8"))
            reference = json.loads(ref_path.read_text(encoding="utf-8"))
            errs.extend(compare_to_james(generated, reference))

    for e in errs:
        print("ERROR:", e)
    print(f"validation: {len(errs)} error(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
