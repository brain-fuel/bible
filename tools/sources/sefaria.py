"""Fetch Hebrew Masoretic chapter text from the Sefaria API."""
import json
import re
import urllib.parse
from pathlib import Path

from tools.fetch import fetch_cached
from tools.parse import clean_text

BASE = "https://www.sefaria.org/api/texts"


def chapter_url(sefaria_name, chapter):
    ref = urllib.parse.quote(f"{sefaria_name}.{chapter}")
    return f"{BASE}/{ref}?context=0&commentary=0&pad=0"


def load_chapter(sefaria_name, chapter, cache_dir):
    safe = sefaria_name.replace(" ", "_")
    cache = Path(cache_dir) / "sefaria" / f"{safe}.{chapter}.json"
    raw = fetch_cached(chapter_url(sefaria_name, chapter), cache, delay=0.5)
    data = json.loads(raw)
    he = data.get("he") or []
    verses = {}
    for i, text in enumerate(he, start=1):
        # Remove sup/sub tags and their content before clean_text
        text = re.sub(r'<sup[^>]*>.*?</sup>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<sub[^>]*>.*?</sub>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove footnote markup (e.g., <i class="footnote">note text</i>) and its content
        text = re.sub(r'<i\b[^>]*footnote[^>]*>.*?</i>', '', text, flags=re.IGNORECASE | re.DOTALL)
        cleaned = clean_text(text)  # strips tags, unescapes, collapses ws, NFC
        if cleaned:
            verses[i] = cleaned
    return verses
