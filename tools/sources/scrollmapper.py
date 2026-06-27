"""Load a Scrollmapper bible_databases JSON dataset into a book/chapter/verse index."""
import json
from pathlib import Path

from tools.fetch import fetch_cached

BASE = ("https://raw.githubusercontent.com/scrollmapper/bible_databases/master/"
        "formats/json")


def dataset_url(key):
    return f"{BASE}/{key}.json"


def load_dataset(key, cache_dir):
    cache = Path(cache_dir) / "scrollmapper" / f"{key}.json"
    raw = fetch_cached(dataset_url(key), cache, delay=0.0)
    data = json.loads(raw)
    index = {}
    for book in data["books"]:
        chapters = {}
        for ch in book["chapters"]:
            verses = {int(v["verse"]): v["text"] for v in ch["verses"]}
            chapters[int(ch["chapter"])] = verses
        index[book["name"]] = chapters
    return index
