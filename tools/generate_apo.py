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
