"""Tests for validate_morph LXX branch (Task 5).

Step 1: The reconcile_form test is a reuse check -- it must pass immediately
before any LXX generation work.

Step 2: validate("lxx") integration tests run against the generated morph/lxx/
tree.  They are deterministic because the morph files are committed to the repo.
"""

import pytest
from tools.validate_morph import reconcile_form, validate


def test_reconcile_form_lxx_present():
    """Smoke test: reconcile_form works for Greek LXX text (Task 5 reuse check)."""
    assert reconcile_form("αρχη", "εν αρχη εποιησεν") is True


def test_reconcile_form_lxx_absent():
    """reconcile_form returns False when the form is not in the verse text."""
    assert reconcile_form("λογος", "εν αρχη εποιησεν") is False


class TestValidateLxx:
    """Integration tests for validate('lxx') -- require generated morph/lxx/ tree."""

    def test_with_morph_is_zero(self):
        """LXX morph columns must be empty (morph deferred to TAGOT)."""
        result = validate("lxx")
        assert result["with_morph"] == 0, (
            f"Expected with_morph=0 (morph deferred to TAGOT; lemma+Strong's only), "
            f"got {result['with_morph']}"
        )

    def test_verses_and_tokens_positive(self):
        """Sanity: the LXX corpus must have non-trivial coverage."""
        result = validate("lxx")
        assert result["verses"] > 20000, (
            f"Expected >20000 verses for 54-book LXX, got {result['verses']}"
        )
        assert result["tokens"] > 300000, (
            f"Expected >300000 tokens for full LXX, got {result['tokens']}"
        )

    def test_count_mismatch_is_zero_after_resync(self):
        """count_mismatch must be 0 after difflib resync replaces whole-verse-abort."""
        result = validate("lxx")
        assert "count_mismatch" in result, (
            "validate('lxx') result must include 'count_mismatch' key"
        )
        # The difflib resync algorithm eliminates all whole-verse-aborts: every verse
        # is now processed word-by-word via SequenceMatcher.  count_mismatch==0 is the
        # invariant after Task 5 resync pass.
        assert result["count_mismatch"] == 0, (
            f"Expected count_mismatch=0 after difflib resync, got {result['count_mismatch']}"
        )

    def test_result_keys_present(self):
        """validate('lxx') must return all required keys including exact and positional."""
        result = validate("lxx")
        required = {"verses", "tokens", "exact", "positional", "unmatched",
                    "count_mismatch", "source_extra", "missing_strong", "with_morph"}
        missing = required - set(result.keys())
        assert not missing, f"validate('lxx') result missing keys: {missing}"

    def test_exact_and_positional_cover_majority_of_tokens(self):
        """After difflib resync, at least 80% of tokens must be exact- or positional-paired.

        The resync prototype showed ~87% paired; this test guards against regression to
        the old 68% coverage (whole-verse-abort era).
        """
        result = validate("lxx")
        assert "exact" in result and "positional" in result, (
            "validate('lxx') must return 'exact' and 'positional' keys"
        )
        paired = result["exact"] + result["positional"]
        pct_paired = 100.0 * paired / result["tokens"] if result["tokens"] else 0
        assert pct_paired >= 80.0, (
            f"Expected >= 80% paired tokens after resync, got {pct_paired:.1f}% "
            f"(exact={result['exact']}, positional={result['positional']}, "
            f"tokens={result['tokens']})"
        )
