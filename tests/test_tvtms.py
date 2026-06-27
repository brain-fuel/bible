from pathlib import Path
from tools.tvtms import parse_condensed, build_map

ROOT = Path(__file__).resolve().parents[1]

FRAGMENT = "\n".join([
    "#DataStart(Condensed)",
    "\t".join(["$Mal.4:1-4:6","English KJV","Hebrew","Latin","Greek*"]),
    "\t".join(["OneToOne","Mal.4:1-3","Mal.3:19-21","Mal.4:1-3","x"]),
    "\t".join(["OneToOne","Mal.4:4","Mal.3:22","Mal.4:4","x"]),
    "\t".join(["OneToOne","Mal.4:5","Mal.3:23","Mal.4:5","x"]),
    "\t".join(["OneToOne","Mal.4:6","Mal.3:24","Mal.4:6","x"]),
    "\t".join(["$Psa.3:1-3:8","English KJV","Hebrew","Latin","Greek"]),
    "\t".join(["OneToOne","Psa.3:Title","Psa.3:1","Psa.3:1","Psa.3:1"]),
    "\t".join(["OneToOne","Psa.3:1","Psa.3:2","Psa.3:2","Psa.3:2"]),
    "\t".join(["OneToOne","Psa.3:2-8","Psa.3:3-9","Psa.3:3-9","Psa.3:3-9"]),
])

def test_malachi_hebrew_divergence_mapped():
    m = build_map(FRAGMENT)
    # KJV Malachi 4:4 is Hebrew 3:22
    assert m["hebrew"]["MAL 4:4"] == "3:22"
    assert m["hebrew"]["MAL 4:1"] == "3:19"
    assert m["hebrew"]["MAL 4:6"] == "3:24"
    # Latin follows KJV for Malachi, so no latin entry
    assert "MAL 4:4" not in m["latin"]

def test_psalm3_superscription_mapped():
    m = build_map(FRAGMENT)
    # KJV Psa 3:1 is Hebrew 3:2; KJV 3:8 is Hebrew 3:9
    assert m["hebrew"]["PSA 3:1"] == "3:2"
    assert m["hebrew"]["PSA 3:8"] == "3:9"

def test_identity_verses_absent_from_map():
    m = build_map(FRAGMENT)
    # KJV Malachi 4:1 Latin equals KJV, so not recorded
    assert "MAL 4:1" not in m["latin"]
