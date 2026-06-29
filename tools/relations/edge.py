"""edge.py — Edge dataclass, JSONL I/O, and orientation helpers.

An Edge represents a relation between two lexical endpoints (src, dst).
Provenance is nested under "provenance" in the JSON serialisation; rank sits
at top level.  JSONL files are sorted by (src, rel, dst, source), UTF-8, LF.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(eq=True, frozen=True)
class Edge:
    """A single relation edge between two lexical endpoints."""

    src: str
    dst: str
    rel: str
    directed: bool
    source: str
    method: str
    rank: int
    note: "str | None"

    def to_json(self) -> dict:
        """Serialise to a dict.  Provenance is nested; rank is at top level."""
        return {
            "src": self.src,
            "dst": self.dst,
            "rel": self.rel,
            "directed": self.directed,
            "provenance": {"source": self.source, "method": self.method},
            "rank": self.rank,
            "note": self.note,
        }

    @classmethod
    def from_json(cls, d: dict) -> "Edge":
        """Deserialise from a dict produced by to_json()."""
        prov = d["provenance"]
        return cls(
            src=d["src"],
            dst=d["dst"],
            rel=d["rel"],
            directed=d["directed"],
            source=prov["source"],
            method=prov["method"],
            rank=d["rank"],
            note=d.get("note"),
        )


def canonical_orient(a: str, b: str) -> "tuple[str, str]":
    """Return (a, b) sorted lexicographically for stable orientation of symmetric edges."""
    return (a, b) if a <= b else (b, a)


def write_jsonl(path: "str | Path", edges: "Iterable[Edge]") -> None:
    """Write edges to a JSONL file sorted by (src, rel, dst, source), UTF-8, LF."""
    sorted_edges = sorted(edges, key=lambda e: (e.src, e.rel, e.dst, e.source))
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="") as f:
        for e in sorted_edges:
            f.write(json.dumps(e.to_json(), ensure_ascii=False) + "\n")


def read_jsonl(path: "str | Path") -> "list[Edge]":
    """Read edges from a JSONL file, returning them sorted by (src, rel, dst, source).

    The sort is applied on read so callers get a deterministic order regardless
    of the on-disk file ordering (important when loading JSONL into the DB).
    """
    path = Path(path)
    edges: list[Edge] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                edges.append(Edge.from_json(json.loads(line)))
    return sorted(edges, key=lambda e: (e.src, e.rel, e.dst, e.source))
