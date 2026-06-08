"""Tests for lib/sim_log_parser.py."""

from lib.sim_log_parser import (
    SimLogSummary,
    detect_pass_fail,
    parse_vcs_log,
)


class TestParseVcsLog:
    """Tests for parse_vcs_log()."""

    def test_empty_log(self) -> None:
        result = parse_vcs_log("")
        assert result.status == "unknown"
        assert result.uvm_info == 0
        assert result.uvm_fatal == 0
        assert result.finish_detected is False
        assert result.test_pass_line == ""
        assert result.duration_hint == ""

    def test_explicit_pass_marker(self) -> None:
        log = "Some output...\nTEST PASSED\nUVM_INFO : 5\n"
        result = parse_vcs_log(log)
        assert result.status == "pass"
        assert "TEST PASSED" in result.test_pass_line

    def test_explicit_pass_uvm_test_pass(self) -> None:
        log = "Simulation done\n+UVM_TEST_PASS\nUVM_INFO : 10\n"
        result = parse_vcs_log(log)
        assert result.status == "pass"

    def test_explicit_pass_uvm_test_passed(self) -> None:
        log = "UVM TEST PASSED\nUVM_INFO : 3\n"
        result = parse_vcs_log(log)
        assert result.status == "pass"

    def test_explicit_fail_marker(self) -> None:
        log = "Some output...\nTEST FAILED\nUVM_INFO : 5\n"
        result = parse_vcs_log(log)
        assert result.status == "fail"
        assert "TEST FAILED" in result.test_pass_line

    def test_explicit_fail_uvm_test_fail(self) -> None:
        log = "+UVM_TEST_FAIL\nUVM_ERROR : 2\n"
        result = parse_vcs_log(log)
        assert result.status == "fail"

    def test_explicit_fail_overrides_pass(self) -> None:
        """If both pass and fail markers exist, fail wins."""
        log = "TEST PASSED\nTEST FAILED\n"
        result = parse_vcs_log(log)
        assert result.status == "fail"

    def test_uvm_fatal_causes_fail(self) -> None:
        log = "UVM_FATAL : 3\nUVM_ERROR : 0\nUVM_INFO : 5\n"
        result = parse_vcs_log(log)
        assert result.status == "fail"
        assert result.uvm_fatal == 3

    def test_uvm_error_causes_fail(self) -> None:
        log = "UVM_FATAL : 0\nUVM_ERROR : 2\nUVM_WARNING : 1\n"
        result = parse_vcs_log(log)
        assert result.status == "fail"
        assert result.uvm_error == 2

    def test_fatal_overrides_error(self) -> None:
        """UVM_FATAL takes priority over UVM_ERROR."""
        log = "UVM_FATAL : 1\nUVM_ERROR : 5\n"
        result = parse_vcs_log(log)
        assert result.status == "fail"

    def test_dollar_finish_means_pass(self) -> None:
        log = "Simulation output...\n$finish called\nUVM_INFO : 0\n"
        result = parse_vcs_log(log)
        assert result.status == "pass"
        assert result.finish_detected is True

    def test_no_markers_unknown(self) -> None:
        log = "Just some random output\nNo markers here\n"
        result = parse_vcs_log(log)
        assert result.status == "unknown"
        assert result.finish_detected is False

    def test_all_counts_extracted(self) -> None:
        log = (
            "UVM_INFO : 42\n"
            "UVM_WARNING : 3\n"
            "UVM_ERROR : 0\n"
            "UVM_FATAL : 0\n"
            "$finish\n"
        )
        result = parse_vcs_log(log)
        assert result.uvm_info == 42
        assert result.uvm_warning == 3
        assert result.uvm_error == 0
        assert result.uvm_fatal == 0
        assert result.status == "pass"
        assert result.finish_detected is True

    def test_bracket_format_counts(self) -> None:
        """Test [UVM_INFO] format (with brackets)."""
        log = "[UVM_INFO] : 7\n[UVM_WARNING] : 2\n$finish\n"
        result = parse_vcs_log(log)
        assert result.uvm_info == 7
        assert result.uvm_warning == 2
        assert result.status == "pass"

    def test_multiple_count_lines_summed(self) -> None:
        """Multiple UVM_INFO lines should be summed."""
        log = "UVM_INFO : 10\nUVM_INFO : 20\n$finish\n"
        result = parse_vcs_log(log)
        assert result.uvm_info == 30

    def test_case_insensitive_explicit_markers(self) -> None:
        log = "test passed\n"
        result = parse_vcs_log(log)
        assert result.status == "pass"

    def test_counts_default_to_zero_on_no_match(self) -> None:
        log = "$finish\n"
        result = parse_vcs_log(log)
        assert result.uvm_info == 0
        assert result.uvm_warning == 0
        assert result.uvm_error == 0
        assert result.uvm_fatal == 0

    def test_duration_hint_extracted(self) -> None:
        log = "Simulation time: 12345 ns\n$finish\n"
        result = parse_vcs_log(log)
        assert "Simulation time" in result.duration_hint

    def test_duration_hint_empty_when_missing(self) -> None:
        log = "$finish\n"
        result = parse_vcs_log(log)
        assert result.duration_hint == ""


class TestDetectPassFail:
    """Tests for detect_pass_fail() helper."""

    def test_pass(self) -> None:
        assert detect_pass_fail("TEST PASSED\n") == "pass"

    def test_fail(self) -> None:
        assert detect_pass_fail("UVM_FATAL : 1\n") == "fail"

    def test_unknown(self) -> None:
        assert detect_pass_fail("nothing here\n") == "unknown"

    def test_empty(self) -> None:
        assert detect_pass_fail("") == "unknown"

    def test_dollar_finish(self) -> None:
        assert detect_pass_fail("$finish\n") == "pass"

    def test_explicit_fail_overrides_finish(self) -> None:
        """Explicit fail overrides $finish."""
        assert detect_pass_fail("TEST FAILED\n$finish\n") == "fail"

    def test_uvm_error_overrides_finish(self) -> None:
        """UVM_ERROR overrides $finish."""
        assert detect_pass_fail("UVM_ERROR : 1\n$finish\n") == "fail"

    def test_explicit_pass_overrides_fatal(self) -> None:
        """Explicit PASSED marker overrides UVM_FATAL."""
        assert detect_pass_fail("TEST PASSED\nUVM_FATAL : 1\n") == "pass"


class TestSimLogSummary:
    """Tests for the SimLogSummary dataclass."""

    def test_defaults(self) -> None:
        s = SimLogSummary(status="pass")
        assert s.uvm_info == 0
        assert s.uvm_warning == 0
        assert s.uvm_error == 0
        assert s.uvm_fatal == 0
        assert s.finish_detected is False
        assert s.test_pass_line == ""
        assert s.duration_hint == ""

    def test_custom_values(self) -> None:
        s = SimLogSummary(
            status="fail",
            uvm_info=10,
            uvm_warning=2,
            uvm_error=1,
            uvm_fatal=3,
            finish_detected=True,
            test_pass_line="TEST FAILED",
            duration_hint="Simulation time: 100 ns",
        )
        assert s.status == "fail"
        assert s.uvm_fatal == 3
        assert s.finish_detected is True
        assert s.test_pass_line == "TEST FAILED"
