from pathlib import Path
from tools.parse import parse_chapter, clean_text

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "tests" / "fixtures" / "jam01.htm").read_text(encoding="utf-8")
META = {"code":"JAM","latin_name":"Epistula Jacobi","greek_name":"Ἰάκωβος",
        "english_name":"The General Epistle of James"}

def test_headers_come_from_meta():
    ch = parse_chapter(HTML, META, 1)
    assert ch["book_id"] == "JAM"
    assert ch["latin_name"] == "Epistula Jacobi"
    assert ch["greek_name"] == "Ἰάκωβος"
    assert ch["english_name"] == "The General Epistle of James"
    assert ch["chapter"] == 1

def test_james_one_has_27_contiguous_verses():
    ch = parse_chapter(HTML, META, 1)
    assert [v["verse"] for v in ch["verses"]] == list(range(1, 28))

def test_verse_one_bodies_match_source():
    v = parse_chapter(HTML, META, 1)["verses"][0]
    assert v["latin_vulgate"] == ("Jacobus, Dei et Domini nostri Jesu Christi servus, "
                                  "duodecim tribubus, quæ sunt in dispersione, salutem.")
    assert v["greek_textus_receptus"] == ("ἰάκωβος θεοῦ καὶ κυρίου ἰησοῦ χριστοῦ δοῦλος "
                                          "ταῖς δώδεκα φυλαῖς ταῖς ἐν τῇ διασπορᾷ χαίρειν")
    assert v["king_james"] == ("James, a servant of God and of the Lord Jesus Christ, "
                               "to the twelve tribes which are scattered abroad, greeting.")

def test_inline_emphasis_stripped_verse_three():
    v = parse_chapter(HTML, META, 1)["verses"][2]
    assert v["king_james"] == ("Knowing this, that the trying of your faith "
                               "worketh patience.")
    assert "<" not in v["king_james"]

def test_clean_text_unescapes_and_collapses():
    assert clean_text("  a&amp;b   c <em>d</em> ") == "a&b c d"
