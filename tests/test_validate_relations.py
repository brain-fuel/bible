"""test_validate_relations.py — Unit tests for the relation-graph validator.

Tests the helper functions endpoints_resolve() and no_self_loops() from
tools/validate_relations.  These are pure, fast, and require no fixture data.
"""

from tools.validate_relations import endpoints_resolve, no_self_loops
from tools.relations.edge import Edge


def test_endpoints_and_self_loops():
    keys = {"G0026", "G0025"}
    good = Edge("G0026", "G0025", "shared-root", False, "strongs-root", "derived", 65535, None)
    assert endpoints_resolve(good, keys) is True
    assert no_self_loops(Edge("G0026", "G0026", "synonym", False, "hand", "authored", 65535, None)) is False
