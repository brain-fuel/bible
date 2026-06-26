# bible

The New Testament as structured JSON: Latin Vulgate, Greek Textus Receptus, and
English King James, verse by verse, one file per chapter.

## Layout

    bible/<testament>/<CODE>/<NNN>.json

`testament` is `nt` (populated), `ot`, or `apo` (reserved). `CODE` is the
canonical uppercase three-character book code. `NNN` is the chapter, zero-padded
to three digits so every book (including Psalms, 150) sorts consistently.

Each file:

    {
      "book_id": "MAT",
      "latin_name": "...",
      "greek_name": "...",
      "english_name": "...",
      "chapter": 1,
      "verses": [
        {"verse": 1, "latin_vulgate": "...", "greek_textus_receptus": "...", "king_james": "..."}
      ]
    }

## Source and provenance

Scraped from the Logos Apostolic interlinear:
https://www.logosapostolic.org/bibles/latin_vulgate_textus_receptus_king_james/

Regenerate with `python -m tools.generate` (caches raw HTML under `data/cache/`)
and verify with `python -m tools.validate`, which structurally checks every
chapter and pins the James output against the independently produced
github.com/brain-fuel/james JSON.

## Scope

New Testament only. Old Testament and apocrypha folders are reserved scaffolds.
