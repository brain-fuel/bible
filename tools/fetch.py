"""Fetch chapter pages from Logos Apostolic with an on-disk cache."""
import time
import urllib.request
from pathlib import Path

BASE = ("https://www.logosapostolic.org/bibles/"
        "latin_vulgate_textus_receptus_king_james")
USER_AGENT = "brain-fuel-bible-scraper/1.0 (one-time corpus build)"


def chapter_url(meta: dict, chapter: int) -> str:
    return f"{BASE}/{meta['dir']}/{meta['prefix']}{chapter:02d}.htm"


def fetch_cached(url: str, cache_path: Path, delay: float = 0.5) -> str:
    cache_path = Path(cache_path)
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(raw, encoding="utf-8")
    if delay:
        time.sleep(delay)
    return raw
