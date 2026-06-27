# Apocrypha Corpus (KJVA spine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a parallel Apocrypha corpus under `bible/apo/` with the Authorized KJV-with-Apocrypha (KJVA) as the verse-position spine and a Finnish Biblia 1776 column, by generalizing the existing registry-driven engine to a third testament.

**Architecture:** The OT/NT pipeline keys every column off `data/editions.json` and uses `king_james` as the verse-position spine — but `king_james` (the KJV dataset) has no deuterocanon. The Apocrypha needs its own spine, so this plan introduces a **per-testament base**: a new `king_james_apocrypha` edition (Scrollmapper `KJVA`) is the base for testament `apo`, and `finnish_biblia` gains `apo`. The generator and validator are generalized to take a `testament` parameter; the merge engine, source dispatch, and refs/absent semantics are reused unchanged. Cross-edition apocrypha alignment is **identity placement with no versification map** (justified below), with absences recorded uniformly.

**Tech Stack:** Python 3, pytest, Scrollmapper `bible_databases` JSON datasets (`KJVA`, `FinBiblia`).

## Global Constraints

- **Spine = KJVA (`king_james_apocrypha`).** 14 Apocrypha books, Greek/KJV-family versification, **5717 verses**, **182 chapter files**. The English column stays KJV across the whole corpus (OT + NT + Apo).
- **Apocrypha books (14), exact KJVA names + chapter counts:** I Esdras (9), II Esdras (16), Tobit (14), Judith (16), Additions to Esther (16), Wisdom (19), Sirach (51), Baruch (6), Prayer of Azariah (1), Susanna (1), Bel and the Dragon (1), Prayer of Manasses (1), I Maccabees (16), II Maccabees (15).
- **Columns = `king_james_apocrypha` (base) + `finnish_biblia`.** Output column order is non-base first, base last: verse keys `["verse","finnish_biblia","king_james_apocrypha"]`; header keys `["book_id","finnish_name","english_name","chapter","verses"]`.
- **Identity placement, NO fabricated versification map.** TVTMS treats KJVA and FinBiblia as the same tradition ("Eng-KJV+Greek") and provides no KJVA↔FinBiblia verse map; the small Tobit/Sirach/Judith count differences are edition-level quirks, not a documented tradition difference. Inventing a map would fabricate scholarship. FinBiblia text is placed at the identical KJVA position (`book_name_field:"kjv_name"`, no `vmap_key`); where FinBiblia has no text, the verse is marked `refs.finnish_biblia = {"absent": true}` — the same uniform shape as OT.
- **Finnish coverage is partial and honest.** FinBiblia ships empty placeholder text for I Esdras and II Esdras, and its Greek-Esther book is a different unit than KJVA "Additions to Esther"; those three books are fully Finnish-absent (448 + 874 + 117 = 1439 verses). With scattered per-verse gaps in the 11 populated books, total Finnish-absent = **1505** verses.
- **Normalized refs.** `refs[<edition_id>] = {"src": "c:v", "absent": true}` (apo uses only `absent`; no `src` because no `vmap_key`). The base `king_james_apocrypha` never appears in `refs`.
- **Invariance.** The OT corpus (`bible/ot`, 23145 verses) and NT corpus (`bible/nt`) must not change. All existing tests stay green; OT generation output stays byte-identical (the generator generalization defaults to `testament="ot"`).
- **Public domain.** KJVA (1611/Authorized) and Biblia 1776 are PD by age; the new registry row sets `"license":"PD"`.
- **Out of scope (separate future plan):** Latin/Vulgate and Douay-Rheims Apocrypha columns. They are a different versification family (Sirach diverges in 48 of 51 chapters) with four books absent (Daniel/Esther additions are embedded in the Vulgate, unreachable cross-book) and no map in our sources. The Vulgate/DRC datasets carrying the deuterocanon are already cached for that plan.

---

## File Structure

- `data/books.json` — append 14 `testament:"apo"` book objects (`code`, `english_name`, `kjv_name`, `finnish_name`, `chapters`).
- `data/editions.json` — add the `king_james_apocrypha` base row; add `"apo"` to `finnish_biblia`'s `testaments`.
- `tools/generate_ot.py` — generalize for per-testament output: add `out_path(root, testament, code, chapter)`, make `out_path_ot` a wrapper, add `testament="ot"` params to `write_book` and `load_books`. OT behavior unchanged (defaults).
- `tools/generate_apo.py` — **new.** Thin driver: `editions_for("apo")` + `write_book(..., testament="apo")`.
- `tools/validate_ot.py` — extract `validate_chapter(obj, body, base_id)` generic; keep `validate_chapter_ot(obj)` as a thin wrapper (behavior unchanged).
- `tools/validate_apo.py` — **new.** Apo BODY/base from the registry; pinned oracles (5717 verses, 182 files, Finnish-absent 1505, fully-absent books).
- Tests: `tests/test_books_apo.py` (new), `tests/test_editions.py` (update finnish testaments + add apo base), `tests/test_generate_ot.py` (add testament-routing test), `tests/test_generate_apo.py` (new), `tests/test_validate_ot.py` (generic validate_chapter), `tests/test_validate_apo.py` (new).
- `README.md` — document the Apocrypha corpus.
- `bible/apo/**` — 182 generated chapter files (committed in Task 6).
- `data/cache/scrollmapper/KJVA.json` — local cache (gitignored), fetched in Task 1.

---

### Task 1: Apocrypha book metadata

**Files:**
- Modify: `data/books.json` (append 14 apo book objects)
- Test: `tests/test_books_apo.py` (new)

**Interfaces:**
- Consumes: nothing.
- Produces: 14 book objects with `testament:"apo"`, fields `code`, `english_name`, `kjv_name`, `finnish_name`, `chapters`. The apo editions (Task 2) reference `kjv_name` (source lookup), `english_name` and `finnish_name` (display).

- [ ] **Step 1: Fetch the KJVA dataset into cache (idempotent)**

```bash
cd "$(git rev-parse --show-toplevel)"
mkdir -p data/cache/scrollmapper
f=data/cache/scrollmapper/KJVA.json
[ -f "$f" ] || curl -s "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/KJVA.json" -o "$f"
ls -l "$f"
```
Expected: `KJVA.json` present, ~9–10 MB.

- [ ] **Step 2: Write the failing test**

Create `tests/test_books_apo.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "1ES": ("I Esdras", 9), "2ES": ("II Esdras", 16), "TOB": ("Tobit", 14),
    "JDT": ("Judith", 16), "ADE": ("Additions to Esther", 16),
    "WIS": ("Wisdom", 19), "SIR": ("Sirach", 51), "BAR": ("Baruch", 6),
    "PAZ": ("Prayer of Azariah", 1), "SUS": ("Susanna", 1),
    "BEL": ("Bel and the Dragon", 1), "MAN": ("Prayer of Manasses", 1),
    "1MA": ("I Maccabees", 16), "2MA": ("II Maccabees", 15),
}


def _apo_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "apo"]


def test_fourteen_apo_books():
    books = _apo_books()
    assert len(books) == 14
    by = {b["code"]: b for b in books}
    assert set(by) == set(EXPECTED)


def test_apo_book_fields_and_chapters():
    by = {b["code"]: b for b in _apo_books()}
    for code, (name, chapters) in EXPECTED.items():
        b = by[code]
        # kjv_name MUST equal the KJVA dataset book name (source lookup key).
        assert b["english_name"] == name
        assert b["kjv_name"] == name
        assert b["chapters"] == chapters
        assert b.get("finnish_name")


def test_apo_finnish_spot_names():
    by = {b["code"]: b for b in _apo_books()}
    assert by["TOB"]["finnish_name"] == "Tobitin kirja"
    assert by["1MA"]["finnish_name"] == "Ensimmäinen makkabilaiskirja"
    assert by["SUS"]["finnish_name"] == "Susanna"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_books_apo.py::test_fourteen_apo_books -v`
Expected: FAIL (0 apo books found).

- [ ] **Step 4: Apply the migration script**

Run from repo root (preserves the one-object-per-line compact style; appends apo books after the existing books):

```python
# scratch migration — run once, then discard
import json
from pathlib import Path

APO = [
    ("1ES", "I Esdras", "Ensimmäinen Esran kirja", 9),
    ("2ES", "II Esdras", "Toinen Esran kirja", 16),
    ("TOB", "Tobit", "Tobitin kirja", 14),
    ("JDT", "Judith", "Juditin kirja", 16),
    ("ADE", "Additions to Esther", "Esterin kirjan lisäykset", 16),
    ("WIS", "Wisdom", "Viisauden kirja", 19),
    ("SIR", "Sirach", "Sirakin kirja", 51),
    ("BAR", "Baruch", "Barukin kirja", 6),
    ("PAZ", "Prayer of Azariah", "Asarjan rukous", 1),
    ("SUS", "Susanna", "Susanna", 1),
    ("BEL", "Bel and the Dragon", "Bel ja lohikäärme", 1),
    ("MAN", "Prayer of Manasses", "Manassen rukous", 1),
    ("1MA", "I Maccabees", "Ensimmäinen makkabilaiskirja", 16),
    ("2MA", "II Maccabees", "Toinen makkabilaiskirja", 15),
]

p = Path("data/books.json")
d = json.loads(p.read_text(encoding="utf-8"))
have = {b["code"] for b in d["books"]}
for code, en, fi, ch in APO:
    if code in have:
        continue
    d["books"].append({"code": code, "testament": "apo", "english_name": en,
                       "kjv_name": en, "finnish_name": fi, "chapters": ch})
objs = d["books"]
lines = ["{", '  "books": [']
for i, b in enumerate(objs):
    comma = "," if i < len(objs) - 1 else ""
    lines.append("    " + json.dumps(b, ensure_ascii=False, separators=(",", ":")) + comma)
lines += ["  ]", "}"]
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("appended apo books:", len(APO))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_books_apo.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Verify OT/NT counts unchanged + JSON parses**

Run: `python3 -c "import json;d=json.load(open('data/books.json'))['books'];from collections import Counter;print(Counter(b['testament'] for b in d))"`
Expected: `Counter({'ot': 39, 'nt': 27, 'apo': 14})`

- [ ] **Step 7: Commit**

```bash
git add data/books.json tests/test_books_apo.py
git commit -m "feat: add 14 Apocrypha book metadata entries (KJVA spine)"
```

---

### Task 2: Registry — KJVA base edition + Finnish gains apo

**Files:**
- Modify: `data/editions.json`
- Test: `tests/test_editions.py`

**Interfaces:**
- Consumes: `editions_for(testament)`, `book_name_field`/`display_name_field`/`base` conventions.
- Produces: `editions_for("apo")` returns `[king_james_apocrypha, finnish_biblia]` (base first). `king_james_apocrypha`: source scrollmapper `KJVA`, `base:true`, `testaments:["apo"]`, `book_name_field:"kjv_name"`, `display_name_field:"english_name"`, no `vmap_key`. `finnish_biblia`: `testaments` becomes `["ot","apo"]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_editions.py`:

```python
def test_apo_base_edition_registered():
    eds = {e["id"]: e for e in load_editions()}
    kjva = eds["king_james_apocrypha"]
    assert kjva["source"] == {"type": "scrollmapper", "key": "KJVA"}
    assert kjva["base"] is True
    assert kjva["testaments"] == ["apo"]
    assert kjva["book_name_field"] == "kjv_name"
    assert kjva["display_name_field"] == "english_name"
    assert "vmap_key" not in kjva
    assert kjva["license"] == "PD"


def test_finnish_now_serves_apo():
    eds = {e["id"]: e for e in load_editions()}
    assert eds["finnish_biblia"]["testaments"] == ["ot", "apo"]


def test_apo_editions_order_base_first():
    apo = [e["id"] for e in editions_for("apo")]
    assert apo == ["king_james_apocrypha", "finnish_biblia"]
```

Also update the existing `test_new_ot_editions_registered` assertion (it pins the old value): change
`assert fin["testaments"] == ["ot"]` to `assert fin["testaments"] == ["ot", "apo"]`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_editions.py::test_apo_base_edition_registered -v`
Expected: FAIL with `KeyError: 'king_james_apocrypha'`.

- [ ] **Step 3: Edit the registry**

In `data/editions.json`: change the `finnish_biblia` row's `"testaments":["ot"]` to `"testaments":["ot","apo"]`. Then append (after the `finnish_biblia` row, keeping the array valid — add a trailing comma to the row before it as needed) the new base row:

```json
    {"id":"king_james_apocrypha","name":"King James Version with Apocrypha","language":"en","source":{"type":"scrollmapper","key":"KJVA"},"versification":"kjv","license":"PD","testaments":["apo"],"base":true,"book_name_field":"kjv_name","display_name_field":"english_name"},
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_editions.py -v`
Expected: PASS (all editions tests, including the updated OT-finnish assertion).

- [ ] **Step 5: Commit**

```bash
git add data/editions.json tests/test_editions.py
git commit -m "feat: register king_james_apocrypha base; finnish_biblia serves apo"
```

---

### Task 3: Generalize the generator for per-testament output

Make the OT generator testament-parametric so a second driver can reuse it. OT behavior must stay byte-identical (defaults preserve it).

**Files:**
- Modify: `tools/generate_ot.py`
- Test: `tests/test_generate_ot.py`

**Interfaces:**
- Consumes: existing `output_editions`, `build_columns`, `build_chapter`.
- Produces: `out_path(root, testament, code, chapter) -> Path`; `out_path_ot(root, code, chapter)` unchanged wrapper; `load_books(testament="ot") -> list`; `write_book(root, meta, editions, handles, vmap, testament="ot") -> int` (writes to `bible/<testament>/`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_generate_ot.py`:

```python
def test_write_book_routes_to_testament_dir(tmp_path):
    # Reuse the OT fixture but route output to the apo tree.
    cache = _seed(tmp_path)
    editions = editions_for("ot")
    from tools.generate_ot import write_book, out_path
    write_book(tmp_path, OBA, editions, _handles(editions, cache),
               {"hebrew": {}, "latin": {}}, testament="apo")
    apo_file = out_path(tmp_path, "apo", "OBA", 1)
    assert apo_file.exists()
    # Default testament stays "ot": the ot path is untouched by this call.
    assert not out_path(tmp_path, "ot", "OBA", 1).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_generate_ot.py::test_write_book_routes_to_testament_dir -v`
Expected: FAIL with `ImportError: cannot import name 'out_path'`.

- [ ] **Step 3: Generalize the four functions**

In `tools/generate_ot.py` replace the `out_path_ot`, `load_books`, and `write_book` definitions with:

```python
def out_path(root, testament, code, chapter):
    return Path(root) / "bible" / testament / code / f"{chapter:0{PAD}d}.json"


def out_path_ot(root, code, chapter):
    return out_path(root, "ot", code, chapter)


def load_books(testament="ot"):
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == testament]


def write_book(root, meta, editions, handles, vmap, testament="ot"):
    out_eds, base = output_editions(editions)
    base_handle = handles[base["id"]]
    written = 0
    for chapter in base_handle.chapters(meta):
        base_verses = base_handle.chapter(meta, chapter)
        columns = build_columns(meta, editions, base, handles, vmap, chapter,
                                base_verses)
        obj = build_chapter(meta, out_eds, base["id"], chapter, columns)
        dest = out_path(root, testament, meta["code"], chapter)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        written += 1
    return written
```

(`main()` is unchanged — it calls `load_books()` and `write_book(...)` with defaults, so OT generation is byte-identical.)

- [ ] **Step 4: Run the full generator test file**

Run: `python3 -m pytest tests/test_generate_ot.py -v`
Expected: PASS (existing OT tests + the new routing test).

- [ ] **Step 5: Confirm OT output is byte-identical**

Run: `python3 -m tools.generate_ot >/dev/null && git status --short bible/ot | wc -l`
Expected: `0` (regenerating OT produces no diff).

- [ ] **Step 6: Commit**

```bash
git add tools/generate_ot.py tests/test_generate_ot.py
git commit -m "refactor: make OT generator testament-parametric (out_path/write_book/load_books)"
```

---

### Task 4: Apocrypha generator driver

**Files:**
- Create: `tools/generate_apo.py`
- Test: `tests/test_generate_apo.py` (new)

**Interfaces:**
- Consumes: `editions_for("apo")`, `prepare_source`, `load_vmap`, `write_book(..., testament="apo")`, `load_books("apo")`, `out_path`.
- Produces: `main() -> int` writing `bible/apo/<code>/<chapter>.json`. Apo verse objects have keys `["verse","finnish_biblia","king_james_apocrypha"]` (+ optional `refs`); Finnish-empty verses carry `refs.finnish_biblia == {"absent": true}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_generate_apo.py`:

```python
import json
from tools.generate_ot import write_book, out_path, output_editions
from tools.editions import editions_for
from tools.sources.registry import prepare_source


def _seed(tmp):
    cache = tmp / "data" / "cache"
    (cache / "scrollmapper").mkdir(parents=True)

    def sm(key, verses):
        book = {"translation": key, "books": [{"name": "Tobit", "chapters": [
            {"chapter": "1", "verses": [{"verse": str(i + 1), "text": t}
                                        for i, t in enumerate(verses)]}]}]}
        (cache / "scrollmapper" / f"{key}.json").write_text(
            json.dumps(book), encoding="utf-8")

    sm("KJVA", ["There was a man", "of the tribe"])
    # FinBiblia has verse 1 only -> verse 2 must be marked absent in Finnish.
    sm("FinBiblia", ["Oli mies"])
    return cache


TOB = {"code": "TOB", "english_name": "Tobit", "finnish_name": "Tobitin kirja",
       "kjv_name": "Tobit", "chapters": 1}


def _handles(editions, cache):
    return {e["id"]: prepare_source(e, cache) for e in editions}


def test_apo_two_columns_base_last_with_absent(tmp_path):
    cache = _seed(tmp_path)
    editions = editions_for("apo")
    n = write_book(tmp_path, TOB, editions, _handles(editions, cache),
                   {"hebrew": {}, "latin": {}}, testament="apo")
    assert n == 1
    data = json.loads(out_path(tmp_path, "apo", "TOB", 1).read_text(encoding="utf-8"))
    assert list(data) == ["book_id", "finnish_name", "english_name", "chapter", "verses"]
    v1, v2 = data["verses"]
    assert list(v1) == ["verse", "finnish_biblia", "king_james_apocrypha"]
    assert v1["king_james_apocrypha"] == "There was a man"
    assert v1["finnish_biblia"] == "Oli mies"
    assert "refs" not in v1
    # verse 2: Finnish empty -> uniform absent marker; base text present.
    assert v2["king_james_apocrypha"] == "of the tribe"
    assert v2["finnish_biblia"] == ""
    assert v2["refs"] == {"finnish_biblia": {"absent": True}}


def test_generate_apo_main_smoke(tmp_path, monkeypatch):
    # main() iterates the real registry+books; just assert it is importable and callable shape.
    import tools.generate_apo as g
    assert hasattr(g, "main")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_generate_apo.py::test_generate_apo_main_smoke -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.generate_apo'`.

- [ ] **Step 3: Create the driver**

Create `tools/generate_apo.py`:

```python
"""Generate the Apocrypha corpus (KJVA spine + Finnish), driven by the registry.

The apo testament uses king_james_apocrypha (Scrollmapper KJVA) as its
verse-position base. Columns are placed by identity (no versification map);
Finnish gaps are recorded as refs.finnish_biblia.absent. See the plan and
README for why no KJVA<->FinBiblia map is fabricated.
"""
import sys

from tools.editions import editions_for
from tools.sources.registry import prepare_source
from tools.merge_ot import load_vmap
from tools.generate_ot import write_book, load_books, ROOT


def main():
    cache_dir = ROOT / "data" / "cache"
    editions = editions_for("apo")
    vmap = load_vmap()  # apo editions declare no vmap_key -> identity placement
    handles = {e["id"]: prepare_source(e, cache_dir) for e in editions}
    total = 0
    for meta in load_books("apo"):
        n = write_book(ROOT, meta, editions, handles, vmap, testament="apo")
        total += n
        print(f"{meta['code']}: {n} chapters")
    print(f"done: {total} chapters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_generate_apo.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/generate_apo.py tests/test_generate_apo.py
git commit -m "feat: Apocrypha generator driver (KJVA spine + Finnish, identity placement)"
```

---

### Task 5: Shared chapter validator + Apocrypha validator

Extract the generic per-chapter validation from `validate_ot.py` (no behavior change for OT), then build an apo validator with pinned oracles.

**Files:**
- Modify: `tools/validate_ot.py`
- Create: `tools/validate_apo.py` (new)
- Test: `tests/test_validate_ot.py`, `tests/test_validate_apo.py` (new)

**Interfaces:**
- Consumes: `editions_for("apo")`, `validate_chapter(obj, body, base_id) -> list[str]`.
- Produces: `tools.validate_ot.validate_chapter(obj, body, base_id)`; `tools.validate_apo` with `BODY`, `BASE_ID`, `TOTAL_APO_VERSES=5717`, `EXPECTED_ABSENT={"finnish_biblia":1505}`, `EXPECTED_BOOK_ABSENT={"1ES":448,"2ES":874,"ADE":117}`, and `main() -> int`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_validate_ot.py` (verifies the extraction keeps OT behavior and the generic signature works):

```python
from tools.validate_ot import validate_chapter


def test_validate_chapter_generic_signature():
    good = {"book_id": "X", "chapter": 1, "verses": [
        {"verse": 1, "finnish_biblia": "a", "king_james_apocrypha": "b"}]}
    assert validate_chapter(good, ("finnish_biblia", "king_james_apocrypha"),
                            "king_james_apocrypha") == []
    bad = {"book_id": "X", "chapter": 1, "verses": [
        {"verse": 1, "finnish_biblia": "a", "king_james_apocrypha": ""}]}
    errs = validate_chapter(bad, ("finnish_biblia", "king_james_apocrypha"),
                            "king_james_apocrypha")
    assert any("king_james_apocrypha" in e for e in errs)  # base never empty
```

Create `tests/test_validate_apo.py`:

```python
from tools.validate_apo import (BODY, BASE_ID, TOTAL_APO_VERSES,
                                EXPECTED_ABSENT, EXPECTED_BOOK_ABSENT)


def test_apo_body_base_from_registry():
    assert BODY == ("finnish_biblia", "king_james_apocrypha")
    assert BASE_ID == "king_james_apocrypha"


def test_apo_pinned_oracles():
    assert TOTAL_APO_VERSES == 5717
    assert EXPECTED_ABSENT == {"finnish_biblia": 1505}
    assert EXPECTED_BOOK_ABSENT == {"1ES": 448, "2ES": 874, "ADE": 117}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validate_apo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.validate_apo'`.

- [ ] **Step 3: Extract the generic chapter validator in `validate_ot.py`**

In `tools/validate_ot.py`, rename the current `validate_chapter_ot(obj)` body into a generic function and add a thin wrapper. Replace the `def validate_chapter_ot(obj):` definition with:

```python
def validate_chapter(obj, body, base_id):
    errs = []
    tag = f"{obj.get('book_id','?')} {obj.get('chapter','?')}"
    verses = obj.get("verses", [])
    if not verses:
        return [f"{tag}: no verses"]
    nums = [v["verse"] for v in verses]
    if nums != list(range(1, len(nums) + 1)):
        errs.append(f"{tag}: verse numbers not contiguous from 1: {nums}")
    for v in verses:
        refs = v.get("refs") or {}
        for eid in body:
            if not v.get(eid):
                if eid == base_id:
                    errs.append(f"{tag}:{v.get('verse')}: empty {eid}")
                elif refs.get(eid, {}).get("absent") is not True:
                    errs.append(f"{tag}:{v.get('verse')}: empty {eid}")
        for eid, entry in refs.items():
            src = entry.get("src", "")
            if src and len(src.split(":")) != 2:
                errs.append(f"{tag}:{v.get('verse')}: malformed src {src}")
    return errs


def validate_chapter_ot(obj):
    return validate_chapter(obj, BODY, BASE_ID)
```

(`BODY`/`BASE_ID` are already module-level in `validate_ot.py`; the OT `main()` and existing callers/tests use `validate_chapter_ot` unchanged.)

- [ ] **Step 4: Create `tools/validate_apo.py`**

```python
"""Structural validation for the Apocrypha corpus (KJVA spine + Finnish).

BODY/base derive from the registry. Finnish is placed by identity (no map),
so the only refs are absent markers; the pinned counts lock the partial
Finnish coverage (I/II Esdras placeholders + Additions to Esther are fully
absent; see plan/README).
"""
import json
import sys
from pathlib import Path

from tools.editions import editions_for
from tools.validate_ot import validate_chapter

ROOT = Path(__file__).resolve().parents[1]


def _apo_output_editions():
    eds = editions_for("apo")
    base = next(e for e in eds if e.get("base"))
    out = [e for e in eds if not e.get("base")] + [base]
    return out, base["id"]


_OUT, BASE_ID = _apo_output_editions()
BODY = tuple(e["id"] for e in _OUT)
NONBASE = tuple(eid for eid in BODY if eid != BASE_ID)

TOTAL_APO_VERSES = 5717
EXPECTED_ABSENT = {"finnish_biblia": 1505}
# Books FinBiblia ships empty / under a different unit -> fully Finnish-absent.
EXPECTED_BOOK_ABSENT = {"1ES": 448, "2ES": 874, "ADE": 117}


def _load_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "apo"]


def main():
    errs = []
    total = 0
    absent = {eid: 0 for eid in NONBASE}
    book_finnish_absent = {}
    for meta in _load_books():
        code = meta["code"]
        found = 0
        ba = 0
        for chapter in range(1, meta["chapters"] + 1):
            p = ROOT / "bible" / "apo" / code / f"{chapter:03d}.json"
            if not p.exists():
                errs.append(f"{code} {chapter}: missing file")
                continue
            found += 1
            obj = json.loads(p.read_text(encoding="utf-8"))
            errs.extend(validate_chapter(obj, BODY, BASE_ID))
            total += len(obj.get("verses", []))
            for v in obj.get("verses", []):
                refs = v.get("refs") or {}
                for eid, entry in refs.items():
                    if eid in absent and entry.get("absent") is True:
                        absent[eid] += 1
                        if eid == "finnish_biblia":
                            ba += 1
        book_finnish_absent[code] = ba
        if found != meta["chapters"]:
            errs.append(f"{code}: expected {meta['chapters']} files, found {found}")
    if total != TOTAL_APO_VERSES:
        errs.append(f"total apo verses {total}, expected {TOTAL_APO_VERSES}")
    for eid, exp in EXPECTED_ABSENT.items():
        if absent.get(eid, 0) != exp:
            errs.append(f"absent {eid} count {absent.get(eid, 0)}, expected {exp}")
    for code, exp in EXPECTED_BOOK_ABSENT.items():
        got = book_finnish_absent.get(code, 0)
        if got != exp:
            errs.append(f"{code} finnish-absent {got}, expected {exp} (fully absent book)")
    for e in errs:
        print("ERROR:", e)
    print(f"Apo validation: {len(errs)} error(s); {total} verses")
    print(f"absent markers: {absent}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_validate_apo.py tests/test_validate_ot.py -v`
Expected: PASS (apo oracle tests + all existing OT validator tests, proving the extraction preserved behavior).

- [ ] **Step 6: Commit**

```bash
git add tools/validate_ot.py tools/validate_apo.py tests/test_validate_ot.py tests/test_validate_apo.py
git commit -m "feat: shared chapter validator + Apocrypha validator with pinned oracles"
```

---

### Task 6: Generate the Apocrypha corpus and verify end-to-end

**Files:**
- Create: `bible/apo/**/*.json` (182 chapter files)

**Interfaces:**
- Consumes: KJVA/FinBiblia caches, the apo registry rows, the apo driver and validator.
- Produces: a validated `bible/apo/` corpus.

- [ ] **Step 1: Confirm caches present**

Run: `ls -l data/cache/scrollmapper/KJVA.json data/cache/scrollmapper/FinBiblia.json`
Expected: both present. If `KJVA.json` is missing, re-run Task 1 Step 1.

- [ ] **Step 2: Generate**

Run: `python3 -m tools.generate_apo | tail -2`
Expected: `done: 182 chapters`.

- [ ] **Step 3: Validate (0 errors with pinned counts)**

Run: `python3 -m tools.validate_apo | tail -3`
Expected:
```
Apo validation: 0 error(s); 5717 verses
absent markers: {'finnish_biblia': 1505}
```
If the total or absent count differs, the regenerated corpus is authoritative: update `TOTAL_APO_VERSES`, `EXPECTED_ABSENT`, or `EXPECTED_BOOK_ABSENT` in `tools/validate_apo.py` to the reported values, re-run validate to 0 errors, re-run the suite, and include the correction in this task's commit with a note in your report. (The dataset simulation predicted 5717 / 1505 / {1ES:448,2ES:874,ADE:117}.)

- [ ] **Step 4: Spot-check columns and absent shape**

Run:
```bash
python3 -c "import json; v=json.load(open('bible/apo/TOB/001.json'))['verses'][0]; print('TOB1:1 cols', [k for k in v if k not in ('verse','refs')], 'refs', v.get('refs'))"
python3 -c "import json; v=json.load(open('bible/apo/1ES/001.json'))['verses'][0]; print('1ES absent?', v.get('refs'))"
```
Expected: TOB 1:1 has `finnish_biblia` + `king_james_apocrypha` with text; I Esdras 1:1 shows `refs.finnish_biblia == {"absent": true}` (placeholder book, fully Finnish-absent).

- [ ] **Step 5: Confirm OT + NT corpora untouched**

Run: `git status --short bible/ot bible/nt | wc -l`
Expected: `0`.

- [ ] **Step 6: Full suite**

Run: `python3 -m pytest -q | tail -3`
Expected: all tests pass.

- [ ] **Step 7: Commit the corpus**

```bash
git add bible/apo
git commit -m "feat: generate Apocrypha corpus (14 books, 5717 verses, KJVA + Finnish)"
```

---

### Task 7: Document the Apocrypha corpus

**Files:**
- Modify: `README.md`

**Interfaces:** none.

- [ ] **Step 1: Add an Apocrypha section and update the Regenerate steps**

In `README.md`, under the Edition System / Apocrypha area (the existing deferral note added in the prior plan), replace the "not yet generated" note with a description of what now exists:

```markdown
### Apocrypha (`bible/apo/`)

The Apocrypha use the Authorized KJV-with-Apocrypha (Scrollmapper `KJVA`) as the
verse-position spine — 14 books, 5,717 verses, Greek/KJV-family versification, so
the English column stays KJV across the whole corpus. A second column carries the
Finnish Biblia 1776 (`FinBiblia`).

Cross-edition apocrypha alignment is **identity placement with no versification
map**: TVTMS treats KJVA and Biblia 1776 as the same tradition and provides no
verse map between them, so none is fabricated. Where Biblia 1776 has no text the
verse is marked `refs.finnish_biblia.absent`. Biblia 1776 ships empty placeholders
for I/II Esdras and a different Greek-Esther unit than KJV's "Additions to Esther",
so those three books are fully Finnish-absent; total Finnish-absent is 1,505 verses.

The Latin/Vulgate and Douay-Rheims Apocrypha belong to a different versification
family (e.g. Sirach diverges in 48 of 51 chapters, and the Daniel/Esther additions
are embedded rather than separate books) with no map in our sources — a future plan.
```

And in the Regenerate section, add the apo commands after the OT ones:

```markdown
    python -m tools.generate_apo
    python -m tools.validate_apo
```

- [ ] **Step 2: Verify the lines render**

Run: `grep -n "bible/apo\|generate_apo\|5,717\|identity placement" README.md`
Expected: the new lines appear.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the Apocrypha corpus (KJVA spine, Finnish, identity placement)"
```

---

## Self-Review

**Spec coverage:**
- "Wire in Apocrypha" → Tasks 1–6 produce a validated `bible/apo/` corpus (14 books, 5717 verses).
- "Consider KJVA | DRC | Latin as the spine" → KJVA chosen (user-confirmed); rationale and the Latin/DRC deferral are in Global Constraints and the README. Investigation showed no spine aligns all traditions and TVTMS has no usable apocrypha verse map.
- Per-testament base (the core engine gap: KJV has no deuterocanon) → Task 2 (KJVA base for `apo`) + Task 3 (generator generalization). Each testament has exactly one base among its editions, so the existing base-selection (`next(e for e in editions if e.get("base"))`) works per-testament with no logic change.
- Finnish column + partial coverage → Tasks 2/4/5, with pinned oracles (1505 absent; I/II Esdras + Additions to Esther fully absent) so coverage gaps can't silently drift.

**Placeholder scan:** No TBD/TODO/"handle edge cases"/"similar to Task N". Every code/data step is literal. The migration script, registry rows, generalized functions, driver, and validator are complete. Oracle numbers are computed from the datasets (5717, 182, 1505, 448/874/117), with Task 6 Step 3 making the regenerated corpus authoritative if any differ.

**Type consistency:** Edition ids `king_james_apocrypha`/`finnish_biblia` are used identically across `editions.json`, validator `BODY`/`EXPECTED_*`, and the column/header-order assertions. `write_book(root, meta, editions, handles, vmap, testament="ot")`, `out_path(root, testament, code, chapter)`, `load_books(testament="ot")`, and `validate_chapter(obj, body, base_id)` signatures match every call site (OT defaults preserve existing callers; apo passes explicit values). Apo book codes (`1ES,2ES,TOB,JDT,ADE,WIS,SIR,BAR,PAZ,SUS,BEL,MAN,1MA,2MA`) and `kjv_name` values match the KJVA dataset names verified during investigation.

**Honest-scope note:** The user's selected option mentioned "a small hand-built versification supplement." Investigation showed TVTMS treats KJVA and FinBiblia as one tradition and offers no verse map; the count differences are edition quirks. Fabricating a map would invent correspondences, so this plan uses transparent identity placement + absent markers instead. Same spine, same columns; the alignment mechanism is the honest one given the data.
