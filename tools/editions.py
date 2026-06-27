"""Edition registry loader."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Order OT editions deterministically: base (KJV) first, then by registry order.
def load_editions():
    data = json.loads((ROOT / "data" / "editions.json").read_text(encoding="utf-8"))
    return data["editions"]


def editions_for(testament):
    eds = [e for e in load_editions() if testament in e["testaments"]]
    eds.sort(key=lambda e: (0 if e.get("base") else 1))
    return eds
