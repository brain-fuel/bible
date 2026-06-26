from pathlib import Path
from tools.fetch import chapter_url, fetch_cached

def test_chapter_url_pads_to_two_digits():
    meta = {"dir": "james", "prefix": "jam"}
    assert chapter_url(meta, 1).endswith("/james/jam01.htm")
    assert chapter_url(meta, 22).endswith("/jam22.htm")

def test_fetch_cached_reads_existing_cache_without_network(tmp_path):
    cache = tmp_path / "x.htm"
    cache.write_text("CACHED", encoding="utf-8")
    # url is deliberately unreachable; cache hit must avoid the network
    out = fetch_cached("http://0.0.0.0/should-not-be-called", cache, delay=0.0)
    assert out == "CACHED"
