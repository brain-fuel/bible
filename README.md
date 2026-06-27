# bible

The Bible as structured JSON, one file per chapter, with multiple parallel texts per verse. New Testament: Latin Vulgate, Greek Textus Receptus, and English King James. Old Testament: Latin Vulgate, Hebrew Masoretic (full pointing), and English King James. Verse-by-verse alignment across traditions.

## Layout

    bible/<testament>/<CODE>/<NNN>.json

`testament` is `nt` (New Testament) or `ot` (Old Testament); `apo` is reserved for apocrypha. `CODE` is the canonical uppercase three-character book code. `NNN` is the chapter, zero-padded to three digits so every book (including Psalms with 150 chapters) sorts consistently.

## Schema

### New Testament Verse

    {
      "verse": 1,
      "latin_vulgate": "...",
      "greek_textus_receptus": "...",
      "king_james": "..."
    }

### Old Testament Verse

    {
      "verse": 1,
      "latin_vulgate": "...",
      "hebrew_masoretic": "...",
      "king_james": "...",
      "refs": {
        "hebrew_masoretic": { "src": "1:1" },
        "latin_vulgate": { "absent": true }
      }
    }

#### Schema notes

- The OT `verse` field uses KJV versification for all traditions.
- The `refs` field is present only when a tradition diverges, and is keyed by edition id with a uniform per-edition object:
  - `refs.<edition>.src` — the source `"chapter:verse"` when that edition's versification places the verse elsewhere than KJV numbering (e.g. Hebrew psalm titles, the Latin psalter).
  - `refs.<edition>.absent: true` — the edition has no text at that position (the edition's column is empty). Ten KJV verses are absent in the Clementine Vulgate; no Hebrew verse is currently absent.
  - Both keys can appear together for one edition (relocated *and* empty). The base edition (KJV) never appears in `refs`.
- Hebrew text includes full Masoretic pointing (vowels and cantillation marks), normalized to NFC form.

## Edition System

Each parallel text is registered in `data/editions.json`. A row is self-describing and **drives generation by itself** — the OT pipeline names no edition. A row carries:

- `id` — the verse-column key (and header is taken from `display_name_field`).
- `source` — `{ "type": ..., ... }`; `type` selects a source backend (`scrollmapper`, `sefaria`) via `tools/sources/registry.py`.
- `book_name_field` — which `data/books.json` field holds this source's per-book name.
- `vmap_key` — the versification namespace in `data/versification/ot-versification.json` (omitted for the base edition, which defines verse positions).
- `base: true` — the edition that defines verse positions (KJV). Non-base editions render first; the base renders last.

**Adding a new parallel OT text needs only a registry row** (plus the source's per-book name in `data/books.json`, and a cache/network fetch). The generator (`tools/generate_ot.py`), merge engine (`tools/merge_ot.py`), and validator (`tools/validate_ot.py`) iterate the registry and need no per-edition edits. Only a genuinely new *source backend* (a `source.type` not yet handled) requires one new class in `tools/sources/registry.py`.

## Sources

All underlying texts are in the public domain:

- **King James Version** (1611): Sourced from Scrollmapper's bible_databases datasets.
- **Clementine Vulgate** (Latin, 1592): Sourced from Scrollmapper's bible_databases datasets. Ten OT verses are merged into the preceding verse in the Vulgate tradition (recorded as `refs.latin_vulgate.absent`).
- **Hebrew Masoretic Text** (Westminster Leningrad Codex): Sourced via the Sefaria API. Includes full Masoretic pointing with vowels and cantillation marks.
- **Greek Textus Receptus** (NT only): Sourced from the Logos Apostolic interlinear (https://www.logosapostolic.org/bibles/latin_vulgate_textus_receptus_king_james/).

## Versification Mapping and Attribution

The OT cross-tradition verse alignment is derived from **STEPBible's TVTMS** (Translators Versification Traditions Mapping System), produced by Tyndale House Cambridge. This data is licensed CC BY 4.0. A small hand-authored CC0 supplement (`data/versification/ot-versification-supplement.json`) aligns the Decalogue chapters (Exodus 20, Deuteronomy 5) to the Sefaria verse division.

**Credit STEPBible and link to** https://github.com/STEPBible when using this compilation.

## License

This repository is licensed CC BY 4.0 (see LICENSE file). The underlying biblical texts (Westminster Leningrad Codex, Clementine Vulgate, King James Version) are in the public domain. CC BY 4.0 applies to the compilation, code, and derived data in this repository. Attribution to STEPBible and Tyndale House Cambridge is required for the TVTMS-derived versification mapping.

## Regenerate

### New Testament

Generate NT chapters from the Logos Apostolic interlinear:

    python -m tools.generate

Validate structure and pin output against the independently produced james JSON:

    python -m tools.validate

### Old Testament

Generate the OT versification map from STEPBible data and Sefaria sources:

    python -m tools.tvtms

Generate OT chapters:

    python -m tools.generate_ot

Validate OT structure. This checks all 23,145 OT verses, contiguity, non-empty verse bodies (except marked-absent), and alignment against versification oracles:

    python -m tools.validate_ot

Raw sources are cached in `data/cache/` (gitignored).
