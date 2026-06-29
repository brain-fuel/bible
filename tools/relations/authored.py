"""authored.py — Loader and validator for hand-curated CC0 authored relation overlays.

Authored JSONL files live in relations/authored/*.jsonl.  They represent
canonical human-edited truth and are NEVER written by builders.  Every line
is validated on load; malformed lines raise immediately (fail loud).

Allowed rel values (subset of full relation taxonomy):
  domain-sibling, shared-root, cross-language, synonym, antonym

Constraints enforced by validate_authored_line:
  - method must be "authored"
  - rank must be in 0..65535
  - both src and dst must be in valid_keys
  - rel must be one of ALLOWED_RELS
  - no self-loop (src != dst)
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.relations.edge import Edge
from tools.relations.lexkeys import lexicon_keys

ROOT = Path(__file__).parent.parent.parent  # repo root

ALLOWED_RELS: frozenset[str] = frozenset(
    {"domain-sibling", "shared-root", "cross-language", "synonym", "antonym"}
)


def validate_authored_line(d: dict, valid_keys: "set[str]") -> Edge:
    """Parse and validate a raw JSONL dict from an authored file.

    Raises ValueError with a descriptive message on any violation.
    Returns a valid Edge on success.
    """
    # Parse via shared Edge.from_json (handles provenance nesting)
    try:
        edge = Edge.from_json(d)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"authored line missing required field: {exc}") from exc

    # method must be "authored"
    if edge.method != "authored":
        raise ValueError(
            f"authored file line has method={edge.method!r}; expected 'authored'"
        )

    # rank must be in 0..65535
    if not (0 <= edge.rank <= 65535):
        raise ValueError(
            f"authored line has rank={edge.rank} outside valid range 0..65535"
        )

    # rel must be in ALLOWED_RELS
    if edge.rel not in ALLOWED_RELS:
        raise ValueError(
            f"authored line has rel={edge.rel!r}; allowed: {sorted(ALLOWED_RELS)}"
        )

    # no self-loop
    if edge.src == edge.dst:
        raise ValueError(
            f"authored line is a self-loop: src==dst=={edge.src!r}"
        )

    # both endpoints must be in valid_keys
    if edge.src not in valid_keys:
        raise ValueError(
            f"authored line src={edge.src!r} is not a known lexicon key"
        )
    if edge.dst not in valid_keys:
        raise ValueError(
            f"authored line dst={edge.dst!r} is not a known lexicon key"
        )

    return edge


def load_authored() -> list[Edge]:
    """Load every relations/authored/*.jsonl file, validate each line, return combined list.

    Raises ValueError on any malformed line (authored files are hand-edited
    canonical truth; we fail loud rather than skip silently).
    """
    authored_dir = ROOT / "relations" / "authored"
    valid_keys = lexicon_keys()
    edges: list[Edge] = []
    for path in sorted(authored_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    d = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"{path.name}:{lineno}: invalid JSON: {exc}"
                    ) from exc
                try:
                    edge = validate_authored_line(d, valid_keys=valid_keys)
                except ValueError as exc:
                    raise ValueError(
                        f"{path.name}:{lineno}: {exc}"
                    ) from exc
                edges.append(edge)
    return edges
