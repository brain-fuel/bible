from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_license_is_cc_by_40():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Creative Commons Attribution 4.0 International" in text
    assert "CC0" not in text
