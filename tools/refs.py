"""Parse TVTMS reference cells into structured refs."""
import re

_REF = re.compile(
    r"^(?P<book>[0-9A-Za-z]+)\.(?P<chap>\d+):(?P<verse>Title|\d+)"
    r"(?:\.(?P<sub>\d+))?(?:!(?P<bang>[a-z]))?$"
)


def _bang_to_num(letter):
    return str(ord(letter) - ord("a") + 1)


def parse_ref(s):
    s = (s or "").strip()
    if not s:
        return None
    if s.startswith("Absent"):
        return {"book": None, "chapter": None, "verse": None, "subverse": None,
                "absent": True, "noverse": False, "title": False}
    if s == "NoVerse":
        return {"book": None, "chapter": None, "verse": None, "subverse": None,
                "absent": False, "noverse": True, "title": False}
    m = _REF.match(s)
    if not m:
        return None
    sub = m.group("sub")
    if sub is None and m.group("bang"):
        sub = _bang_to_num(m.group("bang"))
    return {"book": m.group("book"), "chapter": int(m.group("chap")),
            "verse": m.group("verse"), "subverse": sub,
            "absent": False, "noverse": False, "title": m.group("verse") == "Title"}


def expand(cell):
    cell = (cell or "").strip()
    if not cell:
        return []
    if cell.startswith("Absent") or cell == "NoVerse":
        return [parse_ref(cell)]
    # Range form Book.C:a-b (same chapter). Split on the dash in the verse part.
    m = re.match(r"^([0-9A-Za-z]+)\.(\d+):(\d+)-(\d+)$", cell)
    if m:
        book, chap, a, b = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        out = []
        for v in range(a, b + 1):
            out.append({"book": book, "chapter": chap, "verse": str(v),
                        "subverse": None, "absent": False, "noverse": False,
                        "title": False})
        return out
    r = parse_ref(cell)
    return [r] if r else []
