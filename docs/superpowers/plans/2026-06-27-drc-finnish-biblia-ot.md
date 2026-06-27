# Douay-Rheims + Finnish Biblia 1776 OT Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Douay-Rheims (Challoner) and Finnish Biblia 1776 as two new parallel OT columns, driven entirely by the edition registry (no generator/merge code changes).

**Architecture:** The OT pipeline is already registry-driven (`generate_ot`/`merge_ot`/`validate_ot` iterate `data/editions.json`). Adding a column is therefore data work: two registry rows + two per-book display-name fields in `books.json` + updated validation oracles + a corpus regeneration. Douay-Rheims uses Vulgate versification, which is **identical to the existing Latin column**, so it reuses the existing `"latin"` versification map (`vmap_key: "latin"`). Finnish Biblia 1776 is already KJV-versified, so it is pure identity (no `vmap_key`).

**Tech Stack:** Python 3, pytest, Scrollmapper `bible_databases` JSON datasets (`DRC`, `FinBiblia`), STEPBible-derived versification map.

## Global Constraints

- **Public domain only.** Both texts are PD by age (Douay-Rheims Challoner revision 19th c.; Biblia 1776 published 1776). Each registry row sets `"license":"PD"`.
- **Verse totals are invariant.** OT total stays `23145` verses. New columns are placed at existing KJV positions; no verse is added or removed.
- **Column order = registry order, base last.** Output column/header order is non-base editions in `editions.json` array order, then the base (`king_james`) last. New rows are appended after `hebrew_masoretic`, so output order becomes: `latin_vulgate, hebrew_masoretic, douay_rheims, finnish_biblia, king_james`.
- **Normalized refs.** Per-edition refs use the uniform object shape `refs[<edition_id>] = {"src": "c:v", "absent": true}`. The base edition never appears in `refs`.
- **Edition ids:** `douay_rheims`, `finnish_biblia`. These are the verse-column keys and `refs` keys.
- **Source book names:** both datasets key books by English KJV names (verified), so both rows use `"book_name_field":"kjv_name"` — no new source-name column is required.
- **Out of scope (separate plans):** (1) **Apocrypha** — the merge engine uses KJV as the verse-position spine, and KJV contains no deuterocanonical books; apocrypha needs its own base edition, `bible/apo/` corpus tree, apo book metadata, and apo versification spine. The DRC/FinBiblia datasets *do* carry the apocrypha (already downloaded), so the data is in hand for that future plan. (2) **NT columns** — NT generation is scrape-based (`tools/generate.py`) and does not consume the registry; adding DRC/FinBiblia NT columns requires migrating NT to registry-driven generation first. Both new rows therefore declare `"testaments":["ot"]`.

---

## File Structure

- `data/books.json` — add `douay_name` and `finnish_name` to all 39 OT book objects (display labels for the two new header columns).
- `data/editions.json` — append two registry rows (`douay_rheims`, `finnish_biblia`).
- `tools/validate_ot.py` — extend `EXPECTED_ABSENT` and `EXPECTED_SRC` with the two new editions (validator already derives `BODY` from the registry; no logic change).
- `tools/generate_ot.py`, `tools/merge_ot.py`, `tools/sources/registry.py` — **no changes** (already registry-driven). This is the payoff of the prior refactor and is asserted by tests, not edited.
- `tests/test_editions.py` — assert the two new rows and their fields.
- `tests/test_generate_ot.py` — extend the fixture to 5 editions; assert the new column/header order and DRC `src` relocation.
- `tests/test_validate_ot.py` — update the registry-driven `BODY` assertion and pinned expectations.
- `README.md` — document the two new editions and the apocrypha follow-up.
- `data/cache/scrollmapper/DRC.json`, `data/cache/scrollmapper/FinBiblia.json` — local caches (gitignored) needed for regeneration; fetched in Task 1.

---

### Task 1: Per-book display names in `books.json`

Add `douay_name` (authentic Douay-Rheims/Challoner English titles, matching the existing `latin_name` convention) and `finnish_name` (standard Finnish book names — used as display labels for the 1776 text) to all 39 OT books. Also fetch the two datasets into the local cache so later tasks can regenerate offline.

**Files:**
- Modify: `data/books.json` (39 OT book objects)
- Test: `tests/test_books_ot.py`

**Interfaces:**
- Consumes: nothing.
- Produces: each OT book object gains string fields `douay_name` and `finnish_name`. Edition rows in Task 2 reference these via `display_name_field`.

- [ ] **Step 1: Fetch datasets into cache (idempotent)**

```bash
cd "$(git rev-parse --show-toplevel)"
mkdir -p data/cache/scrollmapper
for k in DRC FinBiblia; do
  f="data/cache/scrollmapper/$k.json"
  [ -f "$f" ] || curl -s "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/json/$k.json" -o "$f"
done
ls -l data/cache/scrollmapper/DRC.json data/cache/scrollmapper/FinBiblia.json
```
Expected: both files present, ~9–10 MB each.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_books_ot.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _ot_books():
    data = json.loads((ROOT / "data" / "books.json").read_text(encoding="utf-8"))
    return [b for b in data["books"] if b["testament"] == "ot"]


def test_all_ot_books_have_new_display_names():
    for b in _ot_books():
        assert b.get("douay_name"), f"{b['code']} missing douay_name"
        assert b.get("finnish_name"), f"{b['code']} missing finnish_name"


def test_display_name_spot_values():
    by = {b["code"]: b for b in _ot_books()}
    # Douay uses the Vulgate-style English titles (cf. latin_name).
    assert by["1KI"]["douay_name"] == "3 Kings"
    assert by["1CH"]["douay_name"] == "1 Paralipomenon"
    assert by["HOS"]["douay_name"] == "Osee"
    assert by["SOS"]["douay_name"] == "Canticle of Canticles"
    # Finnish standard book names.
    assert by["GEN"]["finnish_name"] == "1. Mooseksen kirja"
    assert by["PSA"]["finnish_name"] == "Psalmit"
    assert by["MAL"]["finnish_name"] == "Malakia"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_books_ot.py::test_all_ot_books_have_new_display_names -v`
Expected: FAIL with `KeyError`/`AssertionError` (`douay_name` absent).

- [ ] **Step 4: Apply the migration script**

This reads `books.json`, adds the two fields to OT books, and rewrites the file preserving its exact one-object-per-line compact style (2-space wrapper indent, 4-space per-book indent, `separators=(",",":")`).

```python
# scratch migration — run once, then discard
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if "__file__" in dir() else Path(".")
ROOT = Path("data").resolve().parent  # repo root when run from repo root

DOUAY = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Josue", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Kings", "2SA": "2 Kings", "1KI": "3 Kings", "2KI": "4 Kings",
    "1CH": "1 Paralipomenon", "2CH": "2 Paralipomenon", "EZR": "1 Esdras",
    "NEH": "2 Esdras", "EST": "Esther", "JOB": "Job", "PSA": "Psalms",
    "PRO": "Proverbs", "ECC": "Ecclesiastes", "SOS": "Canticle of Canticles",
    "ISA": "Isaias", "JER": "Jeremias", "LAM": "Lamentations", "EZE": "Ezechiel",
    "DAN": "Daniel", "HOS": "Osee", "JOE": "Joel", "AMO": "Amos",
    "OBA": "Abdias", "JON": "Jonas", "MIC": "Micheas", "NAH": "Nahum",
    "HAB": "Habacuc", "ZEP": "Sophonias", "HAG": "Aggeus", "ZEC": "Zacharias",
    "MAL": "Malachias",
}
FINNISH = {
    "GEN": "1. Mooseksen kirja", "EXO": "2. Mooseksen kirja",
    "LEV": "3. Mooseksen kirja", "NUM": "4. Mooseksen kirja",
    "DEU": "5. Mooseksen kirja", "JOS": "Joosuan kirja", "JDG": "Tuomarien kirja",
    "RUT": "Ruutin kirja", "1SA": "1. Samuelin kirja", "2SA": "2. Samuelin kirja",
    "1KI": "1. Kuningasten kirja", "2KI": "2. Kuningasten kirja",
    "1CH": "1. Aikakirja", "2CH": "2. Aikakirja", "EZR": "Esran kirja",
    "NEH": "Nehemian kirja", "EST": "Esterin kirja", "JOB": "Jobin kirja",
    "PSA": "Psalmit", "PRO": "Sananlaskut", "ECC": "Saarnaaja",
    "SOS": "Laulujen laulu", "ISA": "Jesaja", "JER": "Jeremia",
    "LAM": "Valitusvirret", "EZE": "Hesekiel", "DAN": "Daniel", "HOS": "Hoosea",
    "JOE": "Jooel", "AMO": "Aamos", "OBA": "Obadja", "JON": "Joona",
    "MIC": "Miika", "NAH": "Nahum", "HAB": "Habakuk", "ZEP": "Sefanja",
    "HAG": "Haggai", "ZEC": "Sakarja", "MAL": "Malakia",
}

p = Path("data/books.json")
d = json.loads(p.read_text(encoding="utf-8"))
for b in d["books"]:
    if b["testament"] == "ot":
        b["douay_name"] = DOUAY[b["code"]]
        b["finnish_name"] = FINNISH[b["code"]]
objs = d["books"]
lines = ["{", '  "books": [']
for i, b in enumerate(objs):
    comma = "," if i < len(objs) - 1 else ""
    lines.append("    " + json.dumps(b, ensure_ascii=False, separators=(",", ":")) + comma)
lines += ["  ]", "}"]
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("books.json updated")
```

Run: `python3 - <<'PY'` … `PY` (paste the script) from the repo root, or save to `scratch_migrate.py` and `python3 scratch_migrate.py` then delete it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_books_ot.py -v`
Expected: PASS (all OT books have both fields; spot values match).

- [ ] **Step 6: Verify books.json still parses and NT untouched**

Run: `python3 -c "import json; d=json.load(open('data/books.json')); nt=[b for b in d['books'] if b['testament']=='nt']; print('books', len(d['books']), 'nt-with-douay', sum('douay_name' in b for b in nt))"`
Expected: `books 66 nt-with-douay 0`

- [ ] **Step 7: Commit**

```bash
git add data/books.json tests/test_books_ot.py
git commit -m "feat: add douay_name and finnish_name display labels for OT books"
```

---

### Task 2: Registry rows for the two editions

**Files:**
- Modify: `data/editions.json` (append two rows after `hebrew_masoretic`)
- Test: `tests/test_editions.py`

**Interfaces:**
- Consumes: `book_name_field`/`display_name_field`/`vmap_key` conventions established by the existing rows; the `"latin"` versification namespace in `data/versification/ot-versification.json`.
- Produces: `editions_for("ot")` returns five editions (base first): `king_james, latin_vulgate, hebrew_masoretic, douay_rheims, finnish_biblia`. `greek_textus_receptus` remains NT-only and is excluded from OT.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_editions.py`:

```python
def test_new_ot_editions_registered():
    eds = {e["id"]: e for e in load_editions()}
    drc = eds["douay_rheims"]
    fin = eds["finnish_biblia"]
    # Douay reuses the existing Latin versification map.
    assert drc["source"] == {"type": "scrollmapper", "key": "DRC"}
    assert drc["book_name_field"] == "kjv_name"
    assert drc["vmap_key"] == "latin"
    assert drc["display_name_field"] == "douay_name"
    assert drc["license"] == "PD"
    assert drc["testaments"] == ["ot"]
    # Finnish Biblia 1776 is already KJV-versified: identity, no vmap_key.
    assert fin["source"] == {"type": "scrollmapper", "key": "FinBiblia"}
    assert fin["book_name_field"] == "kjv_name"
    assert "vmap_key" not in fin
    assert fin["display_name_field"] == "finnish_name"
    assert fin["license"] == "PD"


def test_ot_output_order_with_new_editions():
    ot = [e["id"] for e in editions_for("ot")]
    assert ot == ["king_james", "latin_vulgate", "hebrew_masoretic",
                  "douay_rheims", "finnish_biblia"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_editions.py::test_new_ot_editions_registered -v`
Expected: FAIL with `KeyError: 'douay_rheims'`.

- [ ] **Step 3: Add the two rows**

In `data/editions.json`, insert these two lines immediately after the `hebrew_masoretic` row (and add a trailing comma to the `hebrew_masoretic` line). Final array order: `king_james, latin_vulgate, hebrew_masoretic, douay_rheims, finnish_biblia, greek_textus_receptus`.

```json
    {"id":"douay_rheims","name":"Douay-Rheims (Challoner)","language":"en","source":{"type":"scrollmapper","key":"DRC"},"versification":"latin","license":"PD","testaments":["ot"],"book_name_field":"kjv_name","vmap_key":"latin","display_name_field":"douay_name"},
    {"id":"finnish_biblia","name":"Biblia 1776","language":"fi","source":{"type":"scrollmapper","key":"FinBiblia"},"versification":"kjv","license":"PD","testaments":["ot"],"book_name_field":"kjv_name","display_name_field":"finnish_name"},
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_editions.py -v`
Expected: PASS (all editions tests, including the new two and the output-order assertion).

- [ ] **Step 5: Commit**

```bash
git add data/editions.json tests/test_editions.py
git commit -m "feat: register douay_rheims and finnish_biblia OT editions"
```

---

### Task 3: Generator covers five editions (no code change)

The generator is already registry-driven; this task **proves** it handles the two new columns by extending the fixture, and asserts the new column/header order and DRC's `src` relocation. No change to `tools/generate_ot.py` or `tools/merge_ot.py`.

**Files:**
- Modify: `tools/generate_ot.py` — **none expected** (assert this).
- Test: `tests/test_generate_ot.py` (replace the fixture and assertions)

**Interfaces:**
- Consumes: `editions_for("ot")` (now five), `prepare_source` (one handle per edition), `write_book(root, meta, editions, handles, vmap)`.
- Produces: chapter JSON with verse keys `["verse","latin_vulgate","hebrew_masoretic","douay_rheims","finnish_biblia","king_james","refs"?]` and header keys `["book_id","latin_name","hebrew_name","douay_name","finnish_name","english_name","chapter","verses"]`.

- [ ] **Step 1: Replace the test file with the five-edition fixture**

Overwrite `tests/test_generate_ot.py`:

```python
import json
from tools.generate_ot import write_book, out_path_ot
from tools.editions import editions_for
from tools.sources.registry import prepare_source


def _seed(tmp, he=("חֲזוֹן", "הִנֵּה")):
    cache = tmp / "data" / "cache"
    (cache / "scrollmapper").mkdir(parents=True)
    (cache / "sefaria").mkdir(parents=True)

    def sm(name, key, verses):
        book = {"translation": name, "books": [{"name": "Obadiah", "chapters": [
            {"chapter": "1", "verses": [{"verse": str(i + 1), "text": t}
                                        for i, t in enumerate(verses)]}]}]}
        (cache / "scrollmapper" / f"{key}.json").write_text(
            json.dumps(book), encoding="utf-8")

    sm("KJV", "KJV", ["The vision", "Behold"])
    sm("Vul", "VulgClementine", ["Visio", "Ecce"])
    sm("DRC", "DRC", ["The vision of Abdias", "Thus saith"])
    sm("Fin", "FinBiblia", ["Obadjan näky", "Näin sanoo"])
    (cache / "sefaria" / "Obadiah.1.json").write_text(
        json.dumps({"he": list(he), "sections": [1]}), encoding="utf-8")
    return cache


OBA = {"code": "OBA", "english_name": "Obadiah", "hebrew_name": "עֹבַדְיָה",
       "latin_name": "Abdias", "douay_name": "Abdias",
       "finnish_name": "Obadja", "chapters": 1, "kjv_name": "Obadiah",
       "vulgate_name": "Obadiah", "sefaria_name": "Obadiah"}


def _handles(editions, cache):
    return {e["id"]: prepare_source(e, cache) for e in editions}


def test_write_obadiah_five_columns_identity(tmp_path):
    cache = _seed(tmp_path)
    editions = editions_for("ot")
    n = write_book(tmp_path, OBA, editions, _handles(editions, cache),
                   {"hebrew": {}, "latin": {}})
    assert n == 1
    data = json.loads(out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8"))
    assert list(data) == ["book_id", "latin_name", "hebrew_name", "douay_name",
                          "finnish_name", "english_name", "chapter", "verses"]
    v1 = data["verses"][0]
    assert list(v1) == ["verse", "latin_vulgate", "hebrew_masoretic",
                        "douay_rheims", "finnish_biblia", "king_james"]
    assert v1["douay_rheims"] == "The vision of Abdias"
    assert v1["finnish_biblia"] == "Obadjan näky"
    assert "refs" not in v1   # identity (no latin vmap entries for OBA)


def test_douay_relocates_with_latin_vmap(tmp_path):
    # A latin-vmap entry relocates BOTH latin and douay to source 1:2.
    cache = _seed(tmp_path)
    cache_dir = cache
    # DRC source verse 2 holds the relocated text.
    editions = editions_for("ot")
    vmap = {"hebrew": {}, "latin": {"OBA 1:1": "1:2"}}
    write_book(tmp_path, OBA, editions, _handles(editions, cache_dir), vmap)
    v1 = json.loads(out_path_ot(tmp_path, "OBA", 1).read_text(encoding="utf-8"))["verses"][0]
    assert v1["douay_rheims"] == "Thus saith"          # fetched from DRC 1:2
    assert v1["refs"]["douay_rheims"] == {"src": "1:2"}
    assert v1["refs"]["latin_vulgate"] == {"src": "1:2"}
    assert "finnish_biblia" not in v1.get("refs", {})   # identity, no vmap_key
```

- [ ] **Step 2: Run tests to verify they pass (no generator edit)**

Run: `python3 -m pytest tests/test_generate_ot.py -v`
Expected: PASS. If they fail, the failure must be a fixture/assertion issue — do **not** edit `tools/generate_ot.py` unless a genuine missing-capability is proven (the generator is registry-agnostic by design).

- [ ] **Step 3: Confirm production source files are unchanged**

Run: `git status --short tools/`
Expected: empty (no `tools/` files modified).

- [ ] **Step 4: Commit**

```bash
git add tests/test_generate_ot.py
git commit -m "test: cover five-edition OT generation incl douay relocation"
```

---

### Task 4: Validator expectations for the new editions

`validate_ot.py` derives `BODY`/`BASE_ID` from the registry, so it already recognizes the new columns. Only the pinned absent/src oracles need the two new editions. Values come from the dataset simulation: Finnish identity (`absent 0`, `src 0`); Douay reuses the Latin map (`src 2835`, `absent 13` — three more than the Clementine Vulgate's 10 merges).

**Files:**
- Modify: `tools/validate_ot.py:EXPECTED_ABSENT`, `tools/validate_ot.py:EXPECTED_SRC`
- Test: `tests/test_validate_ot.py`

**Interfaces:**
- Consumes: `BODY`, `BASE_ID`, `EXPECTED_ABSENT`, `EXPECTED_SRC` from `tools.validate_ot`.
- Produces: validation that exits 0 against the regenerated corpus in Task 5.

- [ ] **Step 1: Update the registry-driven test assertion**

In `tests/test_validate_ot.py`, replace the body of `test_body_is_registry_driven_base_last`:

```python
def test_body_is_registry_driven_base_last():
    assert BODY == ("latin_vulgate", "hebrew_masoretic", "douay_rheims",
                    "finnish_biblia", "king_james")
    assert BASE_ID == "king_james"
```

Append a pinned-values test:

```python
from tools.validate_ot import EXPECTED_SRC


def test_expected_values_for_new_editions():
    assert EXPECTED_ABSENT["finnish_biblia"] == 0
    assert EXPECTED_SRC["finnish_biblia"] == 0
    assert EXPECTED_ABSENT["douay_rheims"] == 13
    assert EXPECTED_SRC["douay_rheims"] == 2835
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_validate_ot.py::test_body_is_registry_driven_base_last -v`
Expected: FAIL (`BODY` still three editions).

- [ ] **Step 3: Extend the pinned oracles**

In `tools/validate_ot.py`, replace the two constant dicts:

```python
EXPECTED_ABSENT = {"latin_vulgate": 10, "hebrew_masoretic": 0,
                   "douay_rheims": 13, "finnish_biblia": 0}
EXPECTED_SRC = {"latin_vulgate": 2835, "hebrew_masoretic": 1971,
                "douay_rheims": 2835, "finnish_biblia": 0}
```

- [ ] **Step 4: Run the validator unit tests**

Run: `python3 -m pytest tests/test_validate_ot.py -v`
Expected: PASS (registry-driven `BODY` and new pinned values).

- [ ] **Step 5: Commit**

```bash
git add tools/validate_ot.py tests/test_validate_ot.py
git commit -m "feat: pin absent/src oracles for douay_rheims and finnish_biblia"
```

---

### Task 5: Regenerate the OT corpus and verify end-to-end

Every OT chapter file gains two columns (and `douay_rheims` refs), so this is a large but mechanical regeneration. The validator confirms the pinned counts.

**Files:**
- Modify: `bible/ot/**/*.json` (all 929 chapter files)

**Interfaces:**
- Consumes: caches from Task 1, registry from Task 2, oracles from Task 4.
- Produces: a validated five-column OT corpus.

- [ ] **Step 1: Confirm caches are present**

Run: `ls -l data/cache/scrollmapper/DRC.json data/cache/scrollmapper/FinBiblia.json`
Expected: both present. If missing, re-run Task 1 Step 1.

- [ ] **Step 2: Regenerate**

Run: `python3 -m tools.generate_ot | tail -2`
Expected: `done: 929 chapters`.

- [ ] **Step 3: Validate (exit 0 with pinned counts)**

Run: `python3 -m tools.validate_ot | tail -4`
Expected:
```
OT validation: 0 error(s); 23145 verses
absent markers: {'latin_vulgate': 10, 'hebrew_masoretic': 0, 'douay_rheims': 13, 'finnish_biblia': 0}
src pointers: {'latin_vulgate': 2835, 'hebrew_masoretic': 1971, 'douay_rheims': 2835, 'finnish_biblia': 0}
```
If `douay_rheims` absent/src differs from `13`/`2835`, update `EXPECTED_ABSENT`/`EXPECTED_SRC` in `tools/validate_ot.py` to the reported values and re-run (the simulation predicted 13/2835; the regenerated corpus is authoritative). Commit any such correction with Task 4's files.

- [ ] **Step 4: Spot-check the new columns on a divergent verse**

Run:
```bash
python3 -c "import json; v=json.load(open('bible/ot/PSA/003.json'))['verses'][0]; print('cols', [k for k in v if k!='refs' and k!='verse']); print('refs', v.get('refs'))"
```
Expected: columns include `douay_rheims` and `finnish_biblia`; `refs` shows `douay_rheims` and `latin_vulgate` (and `hebrew_masoretic`) each `{"src":"3:2"}`, and no `finnish_biblia` key (identity).

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest -q | tail -3`
Expected: all tests pass (no failures).

- [ ] **Step 6: Commit the regenerated corpus**

```bash
git add bible/ot
git commit -m "feat: regenerate OT corpus with douay_rheims and finnish_biblia columns"
```

---

### Task 6: Document the new editions

**Files:**
- Modify: `README.md`

**Interfaces:** none.

- [ ] **Step 1: Add the editions to the Sources list and note the apocrypha follow-up**

In `README.md`, under the public-domain Sources list, add entries:

```markdown
- **Douay-Rheims (Challoner)** (English, 19th c. revision): Sourced from Scrollmapper's `DRC` dataset. Follows Vulgate versification, so it reuses the same KJV→Vulgate map as the Clementine Vulgate (`vmap_key: "latin"`); thirteen KJV verses are merged/absent in the Douay tradition.
- **Biblia 1776** (Finnish, 1776): Sourced from Scrollmapper's `FinBiblia` dataset. Already KJV-versified for the protocanon, so it is placed by identity with no versification map.
```

And under the Edition System section, add a note:

```markdown
The Scrollmapper `DRC` and `FinBiblia` datasets also carry deuterocanonical
books. The Apocrypha are not yet generated: the merge engine uses KJV as the
verse-position spine, and KJV has no deuterocanon, so the Apocrypha need a
separate base edition, an `bible/apo/` corpus, apocrypha book metadata, and an
apocrypha versification spine — a future plan.
```

- [ ] **Step 2: Verify the doc renders / no broken references**

Run: `grep -n "Douay-Rheims\|Biblia 1776\|Apocrypha" README.md`
Expected: the new lines appear.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document douay_rheims, finnish_biblia, and apocrypha follow-up"
```

---

## Self-Review

**Spec coverage:**
- DRC wired → Tasks 2 (row), 3 (generation), 4 (oracles), 5 (corpus). Versification reuse verified (13 empty / 23145 with `vmap_key:"latin"`).
- Finnish Biblia 1776 wired → same tasks. Identity verified (0 empty / 23145).
- "Biblia 1776 bears some of the apocrypha" → explicitly deferred to a separate plan with rationale (KJV base spine has no deuterocanon), noted in Global Constraints and Task 6. The datasets carrying the apocrypha are fetched and available for that plan.
- Display labels for the new columns → Task 1.

**Placeholder scan:** No TBD/TODO/"handle edge cases"/"similar to Task N". Every code and data step shows the actual content; the migration script and registry rows are complete and literal.

**Type consistency:** Edition ids `douay_rheims`/`finnish_biblia` are used identically across `editions.json`, `EXPECTED_ABSENT`/`EXPECTED_SRC`, `BODY`, verse-key assertions, and refs. `book_name_field`/`display_name_field`/`vmap_key` match the field names introduced in the prior registry-driven refactor. `write_book(root, meta, editions, handles, vmap)` signature matches the current generator. Header/verse key orders are consistent between Task 3 assertions and the documented column order.

**Note on counts:** `douay_rheims` absent=13/src=2835 are predicted by the dataset simulation; Task 5 Step 3 treats the regenerated corpus as authoritative and corrects the oracle if reality differs.
