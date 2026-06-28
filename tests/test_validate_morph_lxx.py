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

    def test_count_mismatch_is_separate_metric(self):
        """count_mismatch must be a distinct key from unmatched in the result dict."""
        result = validate("lxx")
        assert "count_mismatch" in result, (
            "validate('lxx') result must include 'count_mismatch' key"
        )
        # count_mismatch reflects whole-verse-aborts due to Swete-vs-CCAT word-count
        # divergence; it is non-negative and unrelated to the unmatched count.
        assert result["count_mismatch"] >= 0

    def test_result_keys_present(self):
        """validate('lxx') must return all required keys."""
        result = validate("lxx")
        required = {"verses", "tokens", "unmatched", "count_mismatch",
                    "source_extra", "missing_strong", "with_morph"}
        missing = required - set(result.keys())
        assert not missing, f"validate('lxx') result missing keys: {missing}"
