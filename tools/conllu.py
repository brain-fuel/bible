from dataclasses import dataclass, field

COLS = ("idx","form","lemma","upos","xpos","feats","head","deprel","misc")

@dataclass
class Token:
    idx: str
    form: str
    lemma: str
    upos: str
    xpos: str
    feats: str
    head: str = "_"
    deprel: str = "_"
    misc: str = "_"

def format_misc(strong, translit, glosses, align):
    parts = []
    if strong:
        parts.append(f"Strong={strong}")
    if translit and translit != "_":
        parts.append(f"Translit={translit}")
    for lang, text in glosses.items():
        if text:
            parts.append(f"gloss_{lang}={text}")
    if align:
        parts.append(f"Align={align}")
    return "|".join(parts) if parts else "_"

def write_sentence(ref, tokens):
    lines = [f"# ref = {ref}"]
    for t in tokens:
        lines.append("\t".join(getattr(t, c) for c in COLS))
    return "\n".join(lines) + "\n\n"

def parse_sentence(block):
    ref = None
    tokens = []
    for line in block.splitlines():
        if line.startswith("# ref ="):
            ref = line.split("=", 1)[1].strip()
        elif line and not line.startswith("#"):
            tokens.append(Token(*line.split("\t")))
    return ref, tokens

def write_file(path, sentences):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(write_sentence(r, t) for r, t in sentences), encoding="utf-8")

def parse_file(path):
    text = path.read_text(encoding="utf-8")
    out = []
    for block in text.split("\n\n"):
        if block.strip():
            out.append(parse_sentence(block + "\n"))
    return out
