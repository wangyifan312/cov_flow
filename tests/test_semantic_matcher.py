"""Unit tests for lib/semantic_matcher.py."""

from lib.semantic_matcher import (
    assess_gap_coverage,
    extract_semantic_keywords,
    score_tb_match,
)


class TestExtractSemanticKeywords:
    """Tests for keyword extraction from coverpoint and bin names."""

    def test_simple_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_trans", "seq")
        assert "seq" in kw
        assert "ahb" in kw
        assert "trans" in kw

    def test_bin_with_number_suffix(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr16")
        assert "incr" in kw
        assert "16" in kw
        assert "burst" in kw
        assert "ahb" in kw

    def test_wrap_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "wrap8")
        assert "wrap" in kw
        assert "8" in kw

    def test_incr_only(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr")
        assert "incr" in kw
        assert "burst" in kw

    def test_wait_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_wait", "waited")
        assert "wait" in kw or "waited" in kw

    def test_wait_range_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_wait_delay", "wait_6_max")
        assert "wait" in kw
        assert "6" in kw
        assert "max" in kw

    def test_wait_range_numeric(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_wait_delay", "wait_3_5")
        assert "wait" in kw
        assert "3" in kw
        assert "5" in kw

    def test_cross_bin_star_x_bracket(self) -> None:
        kw = extract_semantic_keywords(
            "cr_ahb_rw_burst",
            "* x [incr16 , wrap16 , incr8 , wrap8 , incr4 , wrap4 , incr]",
        )
        assert "incr" in kw
        assert "wrap" in kw
        assert "16" in kw
        assert "8" in kw
        assert "4" in kw
        assert "rw" in kw
        assert "burst" in kw

    def test_cross_bin_bracket_x_star(self) -> None:
        kw = extract_semantic_keywords(
            "cr_ahb_trans_rw",
            "[seq , nonseq] x *",
        )
        assert "seq" in kw
        assert "nonseq" in kw
        assert "trans" in kw
        assert "rw" in kw

    def test_cross_bin_simple_bracket(self) -> None:
        kw = extract_semantic_keywords("cr_ahb_wait_rw", "* x [waited]")
        assert "waited" in kw or "wait" in kw
        assert "rw" in kw

    def test_dma_descriptor_gap(self) -> None:
        kw = extract_semantic_keywords("desc_mode_cp", "linked_list")
        assert "linked" in kw
        assert "list" in kw
        assert "desc" in kw
        assert "mode" in kw

    def test_no_noise_words(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr16")
        assert "cp" not in kw
        assert "cr" not in kw
        assert "bin" not in kw

    def test_nonseq_not_split_wrong(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_trans", "nonseq")
        assert "nonseq" in kw

    def test_returns_sorted(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr16")
        assert kw == sorted(kw)

    def test_empty_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "")
        assert "ahb" in kw
        assert "burst" in kw


class TestScoreTbMatch:
    """Tests for TB entry scoring against keywords."""

    def test_high_score_tag_match(self) -> None:
        entry = {
            "name": "incr_random_len_size_wr_virt_seq",
            "feature_tags": ["incr", "random", "read", "write"],
            "api_methods": [],
        }
        kw = ["incr", "16", "ahb", "burst"]
        score = score_tb_match(kw, entry, "sequence")
        assert score >= 8.0

    def test_low_score_no_match(self) -> None:
        entry = {
            "name": "reset_recovery_virt_seq",
            "feature_tags": ["read", "reset", "write"],
            "api_methods": [],
        }
        kw = ["incr", "16", "burst"]
        score = score_tb_match(kw, entry, "sequence")
        assert score == 0.0

    def test_api_method_bonus(self) -> None:
        entry = {
            "name": "some_seq",
            "feature_tags": ["burst"],
            "api_methods": [
                {
                    "name": "fd_write_burst",
                    "signature": "addr, data, burst",
                    "is_task": True,
                },
            ],
        }
        kw = ["burst", "write"]
        score = score_tb_match(kw, entry, "sequence")
        assert score >= 5.0

    def test_name_substring_match(self) -> None:
        entry = {
            "name": "wrap_random_len_size_wr_virt_seq",
            "feature_tags": ["wrap"],
            "api_methods": [],
        }
        kw = ["wrap", "8", "burst"]
        score = score_tb_match(kw, entry, "sequence")
        assert score >= 8.0

    def test_test_entry_no_api_methods(self) -> None:
        entry = {
            "name": "wrap_random_len_size_wr_test",
            "feature_tags": ["wrap", "random"],
        }
        kw = ["wrap", "8", "burst"]
        score = score_tb_match(kw, entry, "test")
        assert score > 0.0

    def test_short_keywords_no_name_match(self) -> None:
        """Keywords < 3 chars should not match by substring in names."""
        entry = {
            "name": "my_sequence",
            "feature_tags": [],
            "api_methods": [],
        }
        kw = ["8", "rw"]
        score = score_tb_match(kw, entry, "sequence")
        assert score == 0.0


class TestAssessGapCoverage:
    """Tests for gap coverage assessment."""

    def test_existing_test_likely_covers(self) -> None:
        seqs = [{"name": "incr_seq", "relevance": 0.8}]
        tests = [{"name": "incr_test", "sequences": ["incr_seq"]}]
        assessment, confidence = assess_gap_coverage({}, seqs, tests)
        assert assessment == "existing_test_likely_covers"
        assert confidence > 0.5

    def test_partial_coverage(self) -> None:
        seqs = [{"name": "burst_seq", "relevance": 0.7}]
        tests: list[dict] = []
        assessment, confidence = assess_gap_coverage({}, seqs, tests)
        assert assessment == "partial_coverage"
        assert confidence > 0.0

    def test_new_stimulus_needed_no_matches(self) -> None:
        assessment, confidence = assess_gap_coverage({}, [], [])
        assert assessment == "new_stimulus_needed"
        assert confidence > 0.5

    def test_new_stimulus_low_relevance(self) -> None:
        seqs = [{"name": "weak_seq", "relevance": 0.1}]
        tests: list[dict] = []
        assessment, _ = assess_gap_coverage({}, seqs, tests)
        assert assessment == "new_stimulus_needed"

    def test_confidence_bounded(self) -> None:
        seqs = [{"name": "perfect_seq", "relevance": 1.0}]
        tests = [{"name": "perfect_test", "sequences": ["perfect_seq"]}]
        _, confidence = assess_gap_coverage({}, seqs, tests)
        assert 0.0 <= confidence <= 1.0
