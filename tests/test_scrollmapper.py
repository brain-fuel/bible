import json
from pathlib import Path
from tools.sources.scrollmapper import dataset_url, load_dataset

ROOT = Path(__file__).resolve().parents[1]

SAMPLE = {"translation":"X","books":[
    {"name":"Genesis","chapters":[
        {"chapter":"1","verses":[{"verse":"1","text":"In principio"},
                                  {"verse":"2","text":"terra autem"}]}]}]}

def test_url():
    assert dataset_url("KJV").endswith("/formats/json/KJV.json")

def test_load_index(tmp_path):
    cache = tmp_path / "cache" / "scrollmapper" / "X.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps(SAMPLE), encoding="utf-8")
    idx = load_dataset("X", tmp_path / "cache")
    assert idx["Genesis"][1][1] == "In principio"
    assert idx["Genesis"][1][2] == "terra autem"
