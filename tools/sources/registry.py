"""Dispatch an edition's ``source`` declaration to a concrete loader.

Each edition row in ``data/editions.json`` declares ``source.type`` plus a
``book_name_field`` naming the ``books.json`` field that gives the source's
per-book name. ``prepare_source`` returns a handle exposing a uniform
interface, so the generator never special-cases an edition:

    handle.chapter(book_meta, src_chapter) -> {verse:int -> text}
    handle.chapters(book_meta)             -> sorted list of source chapters

Adding a new parallel text means adding a registry row (and, for a new source
backend, one class here) -- not editing the generator.
"""
from tools.sources.scrollmapper import load_dataset
from tools.sources.sefaria import load_chapter


class ScrollmapperSource:
    """Whole-bible JSON dataset, loaded once and indexed by source book name."""

    def __init__(self, key, cache_dir, book_name_field):
        self.index = load_dataset(key, cache_dir)
        self.field = book_name_field

    def chapter(self, meta, src_chapter):
        return self.index.get(meta[self.field], {}).get(src_chapter, {})

    def chapters(self, meta):
        return sorted(self.index.get(meta[self.field], {}))


class SefariaSource:
    """Per-chapter API source, fetched lazily and cached within a run."""

    def __init__(self, cache_dir, book_name_field):
        self.cache_dir = cache_dir
        self.field = book_name_field
        self._cache = {}

    def chapter(self, meta, src_chapter):
        name = meta[self.field]
        k = (name, src_chapter)
        if k not in self._cache:
            self._cache[k] = load_chapter(name, src_chapter, self.cache_dir)
        return self._cache[k]

    def chapters(self, meta):  # pragma: no cover - only the base edition enumerates
        raise NotImplementedError(
            "Sefaria source cannot enumerate chapters; use the base edition")


def prepare_source(edition, cache_dir):
    """Build a source handle for an edition row, dispatching on ``source.type``."""
    src = edition["source"]
    stype = src["type"]
    field = edition["book_name_field"]
    if stype == "scrollmapper":
        return ScrollmapperSource(src["key"], cache_dir, field)
    if stype == "sefaria":
        return SefariaSource(cache_dir, field)
    raise NotImplementedError(f"source type {stype!r} is not wired for merge generation")
