from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_license_is_agpl():
    """Software license (root LICENSE) is AGPL-3.0-or-later."""
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3" in text


def test_data_license_texts_present():
    """CC0 (content default) and CC-BY (third-party-derived) texts are shipped."""
    cc0 = (ROOT / "licenses" / "CC0-1.0.txt").read_text(encoding="utf-8")
    assert "CC0 1.0 Universal" in cc0
    ccby = (ROOT / "licenses" / "CC-BY-4.0.txt").read_text(encoding="utf-8")
    assert "Creative Commons Attribution 4.0 International" in ccby
    agpl = (ROOT / "licenses" / "AGPL-3.0.txt").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in agpl


def test_licensing_policy_doc_present():
    """The authoritative per-artifact license map exists."""
    doc = (ROOT / "docs" / "LICENSING.md").read_text(encoding="utf-8")
    assert "AGPL-3.0" in doc
    assert "CC0-1.0" in doc
    assert "CC-BY-4.0" in doc
