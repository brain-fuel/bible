"""
tools/fetch_macula.py — MACULA domain-map downloader/builder (CC-BY 4.0)

Downloads linguistic domain data from:
  - Clear Bible macula-greek Nestle1904 TSV (Louw-Nida codes, `ln` column)
  - Clear Bible macula-hebrew WLC nodes XML files (SDBH LexDomain codes)

Both datasets are CC-BY 4.0. Attribution:
  "MACULA Greek/Hebrew Linguistic Datasets, Clear Bible Inc., CC-BY 4.0,
   https://github.com/Clear-Bible/macula-greek and
   https://github.com/Clear-Bible/macula-hebrew"

Caches results as JSON under data/cache/morph/raw/macula/:
  grc_domain_map.json  — {G####: [sorted LN codes]}
  hbo_domain_map.json  — {H####: [sorted SDBH LexDomain codes]}

Usage (standalone):
  python -m tools.fetch_macula            # build + cache both maps
  python -m tools.fetch_macula --greek    # Greek only
  python -m tools.fetch_macula --hebrew   # Hebrew only
  python -m tools.fetch_macula --report   # print coverage stats
"""

from __future__ import annotations

import csv
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MACULA_GRC_TSV_URL = (
    "https://raw.githubusercontent.com/Clear-Bible/macula-greek/main"
    "/Nestle1904/tsv/macula-greek-Nestle1904.tsv"
)

MACULA_HBO_API_URL = (
    "https://api.github.com/repos/Clear-Bible/macula-hebrew/contents/WLC/nodes"
)

MACULA_HBO_RAW_BASE = (
    "https://raw.githubusercontent.com/Clear-Bible/macula-hebrew/main/WLC/nodes"
)

# Attribution label written into entry sources (matches brief's TDD test assertions)
GRC_SOURCE_LABEL = "ln-map"    # Louw-Nida via MACULA Greek Nestle1904 TSV (CC-BY 4.0)
HBO_SOURCE_LABEL = "sdbh"      # SDBH LexDomain via MACULA Hebrew WLC nodes (CC-BY 4.0)

# ---------------------------------------------------------------------------
# Greek domain map (Louw-Nida) from TSV
# ---------------------------------------------------------------------------

def build_grc_domain_map(tsv_path: str | Path) -> dict[str, list[str]]:
    """Parse MACULA Greek Nestle1904 TSV → {G####: [sorted LN codes]}.

    The TSV `strong` column holds bare integers (e.g. "976"); the `ln` column
    holds space-separated Louw-Nida references (e.g. "25.43 25.44").
    Multiple rows per lemma are merged into a single sorted set.
    """
    result: dict[str, set] = {}
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            strong_raw = (row.get("strong") or "").strip()
            ln_raw = (row.get("ln") or "").strip()
            if not strong_raw or not ln_raw:
                continue
            # Normalise strong to G#### — strip any trailing letter/punctuation
            strong_clean = re.sub(r"[^0-9]", "", strong_raw)
            if not strong_clean:
                continue
            try:
                snum = int(strong_clean)
            except ValueError:
                continue
            strong_id = f"G{snum:04d}"
            for code in ln_raw.split():
                code = code.strip()
                if code:
                    result.setdefault(strong_id, set()).add(code)
    return {k: sorted(v) for k, v in result.items()}


# ---------------------------------------------------------------------------
# Hebrew domain map (SDBH LexDomain) from MACULA XML nodes
# ---------------------------------------------------------------------------

def _normalize_hbo_strong(raw: str) -> Optional[str]:
    """Convert OSHB strong tag to H#### canonical form.

    OSHB uses forms like "7225", "1254a", "430", "0871a", "b" (prefixes).
    Returns None for non-lexical entries (bare letters, empty).
    """
    if not raw:
        return None
    # Strip trailing letters (disambiguation suffix like 'a', 'b', 'c')
    num_part = re.sub(r"[a-zA-Z]+$", "", raw).strip()
    if not num_part:
        return None
    try:
        snum = int(num_part)
    except ValueError:
        return None
    if snum == 0:
        return None
    return f"H{snum:04d}"


def _extract_from_xml_bytes(content: bytes) -> dict[str, set]:
    """Extract oshb-strongs → LexDomain pairs from one MACULA Hebrew XML file."""
    pairs: dict[str, set] = {}
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return pairs
    for elem in root.iter("m"):
        raw_strong = elem.get("oshb-strongs", "")
        lex_domain = elem.get("LexDomain", "").strip()
        if not raw_strong or not lex_domain:
            continue
        strong_id = _normalize_hbo_strong(raw_strong)
        if strong_id is None:
            continue
        pairs.setdefault(strong_id, set()).add(lex_domain)
    return pairs


def _fetch_url_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bible-tools/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _get_hebrew_xml_urls() -> list[str]:
    """Fetch the list of all MACULA Hebrew XML node file URLs via GitHub API."""
    content = _fetch_url_bytes(MACULA_HBO_API_URL)
    items = json.loads(content)
    urls = []
    for item in items:
        name = item.get("name", "")
        if name.endswith(".xml") and name != "macula-hebrew.xml":
            urls.append(f"{MACULA_HBO_RAW_BASE}/{name}")
    return sorted(urls)


def build_hbo_domain_map(
    max_workers: int = 16,
    progress: bool = True,
) -> dict[str, list[str]]:
    """Fetch all MACULA Hebrew XML files and build {H####: [sorted SDBH LexDomain codes]}.

    Downloads 930 chapter-level XML files from GitHub concurrently (CC-BY 4.0).
    This runs once; the result is cached by the caller.
    """
    urls = _get_hebrew_xml_urls()
    if progress:
        print(f"  Found {len(urls)} Hebrew XML files to process")

    result: dict[str, set] = {}
    completed = 0
    failed = 0

    def fetch_and_parse(url: str) -> dict[str, set]:
        data = _fetch_url_bytes(url)
        return _extract_from_xml_bytes(data)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_and_parse, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                pairs = future.result()
                for strong_id, domains in pairs.items():
                    result.setdefault(strong_id, set()).update(domains)
                completed += 1
            except Exception as exc:
                failed += 1
                if progress:
                    print(f"  WARNING: failed {url.split('/')[-1]}: {exc}")
            if progress and (completed + failed) % 100 == 0:
                print(f"  {completed + failed}/{len(urls)} done, {len(result)} unique strongs so far")

    if progress:
        print(f"  Done: {completed} ok, {failed} failed, {len(result)} unique H-strongs")
    return {k: sorted(v) for k, v in result.items()}


# ---------------------------------------------------------------------------
# Cache load/save helpers
# ---------------------------------------------------------------------------

def load_cached_map(cache_path: Path) -> Optional[dict]:
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_map(data: dict, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Public entry point: load_or_build_domain_maps
# ---------------------------------------------------------------------------

def load_or_build_domain_maps(
    base: Path,
    *,
    force_rebuild: bool = False,
    progress: bool = True,
) -> tuple[dict, dict]:
    """Return (grc_domain_map, hbo_domain_map), building from MACULA if not cached.

    Both maps are {Strong_ID: [sorted domain codes]}.
    Returns empty dicts on any download/parse failure (logged to stderr).
    """
    macula_dir = base / "data" / "cache" / "morph" / "raw" / "macula"
    grc_cache = macula_dir / "grc_domain_map.json"
    hbo_cache = macula_dir / "hbo_domain_map.json"
    grc_tsv = macula_dir / "macula-greek-Nestle1904.tsv"

    # ---- Greek ----
    grc_map: dict = {}
    if not force_rebuild:
        grc_map = load_cached_map(grc_cache) or {}
    if not grc_map:
        if progress:
            print("Building MACULA Greek domain map (Louw-Nida)...")
        try:
            if not grc_tsv.exists():
                if progress:
                    print(f"  Downloading MACULA Greek TSV ({MACULA_GRC_TSV_URL})...")
                data = _fetch_url_bytes(MACULA_GRC_TSV_URL)
                macula_dir.mkdir(parents=True, exist_ok=True)
                grc_tsv.write_bytes(data)
            grc_map = build_grc_domain_map(grc_tsv)
            save_map(grc_map, grc_cache)
            if progress:
                print(f"  Greek domain map: {len(grc_map)} strongs with LN codes")
        except Exception as exc:
            print(f"  WARNING: could not build Greek domain map: {exc}")
            grc_map = {}

    # ---- Hebrew ----
    hbo_map: dict = {}
    if not force_rebuild:
        hbo_map = load_cached_map(hbo_cache) or {}
    if not hbo_map:
        if progress:
            print("Building MACULA Hebrew domain map (SDBH LexDomain)...")
        try:
            hbo_map = build_hbo_domain_map(progress=progress)
            save_map(hbo_map, hbo_cache)
        except Exception as exc:
            print(f"  WARNING: could not build Hebrew domain map: {exc}")
            hbo_map = {}

    return grc_map, hbo_map


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    import sys
    args = set(sys.argv[1:])
    base = Path(__file__).parent.parent
    macula_dir = base / "data" / "cache" / "morph" / "raw" / "macula"
    grc_tsv = macula_dir / "macula-greek-Nestle1904.tsv"
    grc_cache = macula_dir / "grc_domain_map.json"
    hbo_cache = macula_dir / "hbo_domain_map.json"

    do_greek = "--hebrew" not in args
    do_hebrew = "--greek" not in args
    do_report = "--report" in args

    if do_report:
        grc = load_cached_map(grc_cache) or {}
        hbo = load_cached_map(hbo_cache) or {}
        print(f"Greek domain map: {len(grc)} strongs with LN codes")
        print(f"Hebrew domain map: {len(hbo)} strongs with SDBH codes")
        if grc:
            sample = sorted(grc.items())[:5]
            print("Greek sample:", sample)
        if hbo:
            sample = sorted(hbo.items())[:5]
            print("Hebrew sample:", sample)
        return

    if do_greek:
        print("Building Greek domain map...")
        if not grc_tsv.exists():
            print(f"  Downloading MACULA Greek TSV...")
            data = _fetch_url_bytes(MACULA_GRC_TSV_URL)
            macula_dir.mkdir(parents=True, exist_ok=True)
            grc_tsv.write_bytes(data)
        grc_map = build_grc_domain_map(grc_tsv)
        save_map(grc_map, grc_cache)
        print(f"  Saved {len(grc_map)} Greek entries to {grc_cache}")

    if do_hebrew:
        print("Building Hebrew domain map (downloading 930 XML files)...")
        hbo_map = build_hbo_domain_map(progress=True)
        save_map(hbo_map, hbo_cache)
        print(f"  Saved {len(hbo_map)} Hebrew entries to {hbo_cache}")


if __name__ == "__main__":
    _main()
