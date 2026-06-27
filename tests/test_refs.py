from tools.refs import parse_ref, expand

def test_simple_ref():
    r = parse_ref("Mal.4:1")
    assert r["book"] == "Mal" and r["chapter"] == 4 and r["verse"] == "1"

def test_title_ref():
    r = parse_ref("Psa.3:Title")
    assert r["title"] and r["verse"] == "Title"

def test_subverse_dot_and_bang():
    assert parse_ref("Gen.5:31.2")["subverse"] == "2"
    assert parse_ref("Gen.6:1!b")["subverse"] == "2"  # !a=1, !b=2

def test_absent_and_noverse():
    assert parse_ref("Absent [=Gen.3:1]")["absent"] is True
    assert parse_ref("NoVerse")["noverse"] is True

def test_expand_range_same_chapter():
    refs = expand("Mal.4:1-3")
    assert [r["verse"] for r in refs] == ["1", "2", "3"]
    assert all(r["book"] == "Mal" and r["chapter"] == 4 for r in refs)

def test_expand_single():
    assert len(expand("Psa.3:2")) == 1
