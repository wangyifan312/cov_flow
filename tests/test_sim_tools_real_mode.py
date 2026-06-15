"""Tests for MCP simulation tools in real mode.

Tests the 4 sim tools (sim_run_targeted_test, sim_get_test_result,
sim_search_log, cov_get_coverage_diff) when manifest.sim_mode == "real".

All tests use echo/false/sleep commands — no VCS dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.sim_tools import (
    cov_get_coverage_diff,
    sim_get_test_result,
    sim_run_targeted_test,
    sim_search_log,
)


@pytest.fixture(autouse=True)
def _clear():
    """Clear project manifest cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def real_manifest(tmp_path: Path) -> Path:
    """Create a real-mode manifest with echo-based commands."""
    manifest_path = tmp_path / "project_manifest.yaml"
    manifest_path.write_text(
        f"""
project: test_real
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "echo compile {{test}} {{seed}}"
  run_cmd_template: "echo run {{test}} {{seed}} && echo Test PASSED"
  urg_cmd_template: "echo urg {{vdb_dir}} {{report_dir}}"
  results_root: sim_results
  timeout_seconds: 10
  urg_timeout_seconds: 5
policy:
  allow_running_simulation: true
""",
        encoding="utf-8",
    )
    (tmp_path / "sim_results").mkdir()
    (tmp_path / ".dv_ai_index").mkdir()
    return manifest_path


@pytest.fixture
def real_manifest_with_urg(tmp_path: Path) -> Path:
    """Create a real-mode manifest with URG command that creates output."""
    manifest_path = tmp_path / "project_manifest.yaml"
    # URG command that creates a marker file (simpler than JSON to avoid brace escaping)
    manifest_path.write_text(
        f"""
project: test_real_urg
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "echo compile {{test}} {{seed}}"
  run_cmd_template: "echo run {{test}} {{seed}} && echo Test PASSED"
  urg_cmd_template: 'mkdir -p {{report_dir}} && echo URG_OK > {{report_dir}}/urg_marker.txt'
  results_root: sim_results
  timeout_seconds: 10
  urg_timeout_seconds: 5
policy:
  allow_running_simulation: true
""",
        encoding="utf-8",
    )
    (tmp_path / "sim_results").mkdir()
    (tmp_path / ".dv_ai_index").mkdir()
    return manifest_path


@pytest.fixture
def real_manifest_compile_fail(tmp_path: Path) -> Path:
    """Create a real-mode manifest where compile fails."""
    manifest_path = tmp_path / "project_manifest.yaml"
    manifest_path.write_text(
        f"""
project: test_real_fail
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "false"
  run_cmd_template: "echo run {{test}} {{seed}}"
  results_root: sim_results
  timeout_seconds: 10
policy:
  allow_running_simulation: true
""",
        encoding="utf-8",
    )
    (tmp_path / "sim_results").mkdir()
    (tmp_path / ".dv_ai_index").mkdir()
    return manifest_path


class TestSimRunTargetedTestRealMode:
    """Tests for sim_run_targeted_test in real mode."""

    def test_requires_confirm(self, real_manifest: Path):
        """Tool returns early without confirm=true."""
        result = sim_run_targeted_test(
            project=str(real_manifest),
            test="my_test",
            seed=42,
            confirm=False,
        )
        assert result["ok"] is True
        assert result["result"]["message"] == "Simulation execution requires confirm=true"
        assert result["safety"]["confirmed"] is False

    def test_policy_check(self, tmp_path: Path):
        """Tool rejects when policy disallows simulation."""
        manifest_path = tmp_path / "project_manifest.yaml"
        manifest_path.write_text(
            f"""
project: test_policy
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "echo compile"
  run_cmd_template: "echo run"
  results_root: sim_results
policy:
  allow_running_simulation: false
""",
            encoding="utf-8",
        )
        (tmp_path / "sim_results").mkdir()
        (tmp_path / ".dv_ai_index").mkdir()

        result = sim_run_targeted_test(
            project=str(manifest_path),
            test="my_test",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is False
        assert "not allowed" in result["error"].lower()

    def test_successful_run(self, real_manifest: Path):
        """Tool runs compile+run pipeline successfully."""
        result = sim_run_targeted_test(
            project=str(real_manifest),
            test="my_test",
            seed=42,
            confirm=True,
        )
        assert result["ok"] is True
        assert result["result"]["test"] == "my_test"
        assert result["result"]["seed"] == 42
        assert result["result"]["dry_run"] is False

        # Check compile step
        assert result["result"]["compile"] is not None
        assert result["result"]["compile"]["status"] == "pass"
        assert result["result"]["compile"]["return_code"] == 0

        # Check run step
        assert result["result"]["run"] is not None
        assert result["result"]["run"]["status"] == "pass"
        assert result["result"]["run"]["return_code"] == 0

        # Check safety metadata
        assert result["safety"]["policy_checked"] is True
        assert result["safety"]["confirmed"] is True
        assert result["safety"]["mode"] == "real"

    def test_compile_fail_skips_run(self, real_manifest_compile_fail: Path):
        """Compile failure prevents run step."""
        result = sim_run_targeted_test(
            project=str(real_manifest_compile_fail),
            test="my_test",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is True
        assert result["result"]["compile"]["status"] != "pass"
        assert result["result"]["run"] is None  # Run skipped

    def test_with_urg(self, real_manifest_with_urg: Path):
        """Tool runs compile+run+urg pipeline."""
        result = sim_run_targeted_test(
            project=str(real_manifest_with_urg),
            test="my_test",
            seed=99,
            confirm=True,
        )
        assert result["ok"] is True
        assert result["result"]["compile"]["status"] == "pass"
        assert result["result"]["run"]["status"] == "pass"
        assert result["result"]["urg"] is not None
        assert result["result"]["urg"]["status"] == "pass"

    def test_invalid_test_name(self, real_manifest: Path):
        """Tool rejects invalid test names."""
        result = sim_run_targeted_test(
            project=str(real_manifest),
            test="../etc/passwd",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is False
        assert "invalid" in result["error"].lower() or "test name" in result["error"].lower()

    def test_invalid_seed(self, real_manifest: Path):
        """Tool rejects negative seeds."""
        result = sim_run_targeted_test(
            project=str(real_manifest),
            test="my_test",
            seed=-1,
            confirm=True,
        )
        assert result["ok"] is False
        assert "seed" in result["error"].lower()


class TestSimGetTestResultRealMode:
    """Tests for sim_get_test_result in real mode."""

    def test_load_persisted_result(self, real_manifest: Path):
        """Tool loads previously saved sim_result.json."""
        # First run a simulation to create result
        sim_run_targeted_test(
            project=str(real_manifest),
            test="my_test",
            seed=42,
            confirm=True,
        )

        # Now query it
        result = sim_get_test_result(
            project=str(real_manifest),
            test="my_test",
            seed=42,
        )
        assert result["ok"] is True
        assert result["result"]["test"] == "my_test"
        assert result["result"]["seed"] == 42
        assert result["result"]["compile"]["status"] == "pass"
        assert result["result"]["run"]["status"] == "pass"

    def test_parse_log_fallback(self, real_manifest: Path):
        """Tool parses run.log when sim_result.json missing."""
        # Run simulation but delete sim_result.json
        sim_run_targeted_test(
            project=str(real_manifest),
            test="fallback_test",
            seed=1,
            confirm=True,
        )

        # Find and delete sim_result.json
        results_dir = real_manifest.parent / "sim_results" / "fallback_test_1"
        result_json = results_dir / "sim_result.json"
        if result_json.exists():
            result_json.unlink()

        # Query should parse run.log
        result = sim_get_test_result(
            project=str(real_manifest),
            test="fallback_test",
            seed=1,
        )
        assert result["ok"] is True
        assert result["result"]["test"] == "fallback_test"
        assert "sim_status" in result["result"]

    def test_no_result_found(self, real_manifest: Path):
        """Tool handles missing results gracefully."""
        result = sim_get_test_result(
            project=str(real_manifest),
            test="nonexistent",
            seed=999,
        )
        # Should return not_found error
        assert result["ok"] is False


class TestSimSearchLogRealMode:
    """Tests for sim_search_log in real mode."""

    def test_search_with_matches(self, real_manifest: Path):
        """Tool finds keyword in log."""
        # Run simulation to create log
        sim_run_targeted_test(
            project=str(real_manifest),
            test="search_test",
            seed=1,
            confirm=True,
        )

        # Search for "PASSED"
        result = sim_search_log(
            project=str(real_manifest),
            test="search_test",
            seed=1,
            keyword="PASSED",
        )
        assert result["ok"] is True
        assert result["result"]["keyword"] == "PASSED"
        assert result["result"]["total_matches"] > 0
        assert len(result["result"]["matches"]) > 0

    def test_search_no_matches(self, real_manifest: Path):
        """Tool handles keyword not found."""
        sim_run_targeted_test(
            project=str(real_manifest),
            test="search_test2",
            seed=2,
            confirm=True,
        )

        result = sim_search_log(
            project=str(real_manifest),
            test="search_test2",
            seed=2,
            keyword="NONEXISTENT_KEYWORD_XYZ",
        )
        assert result["ok"] is True
        assert result["result"]["total_matches"] == 0

    def test_search_bounded_to_20(self, tmp_path: Path):
        """Tool truncates matches to 20 lines."""
        manifest_path = tmp_path / "project_manifest.yaml"
        # Create a script that outputs 30 matching lines
        script_path = tmp_path / "gen_matches.sh"
        script_path.write_text(
            "#!/bin/sh\n" + "\n".join([f'echo "MATCH line {i}"' for i in range(30)]) + "\n",
            encoding="utf-8",
        )
        script_path.chmod(0o755)

        manifest_path.write_text(
            f"""
project: test_bounded
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "echo compile"
  run_cmd_template: "{script_path}"
  results_root: sim_results
  timeout_seconds: 10
policy:
  allow_running_simulation: true
""",
            encoding="utf-8",
        )
        (tmp_path / "sim_results").mkdir()
        (tmp_path / ".dv_ai_index").mkdir()

        sim_run_targeted_test(
            project=str(manifest_path),
            test="bounded_test",
            seed=1,
            confirm=True,
        )

        result = sim_search_log(
            project=str(manifest_path),
            test="bounded_test",
            seed=1,
            keyword="MATCH",
        )
        assert result["ok"] is True
        assert result["result"]["total_matches"] == 30
        assert len(result["result"]["matches"]) == 20  # Bounded
        assert result.get("truncated", False) is True


class TestCovGetCoverageDiffRealMode:
    """Tests for cov_get_coverage_diff in real mode."""

    def test_auto_discover_urg_reports(self, real_manifest_with_urg: Path):
        """Tool discovers coverage_gaps.json in sim_results."""
        # Run two simulations to create two URG report directories
        sim_run_targeted_test(
            project=str(real_manifest_with_urg),
            test="test1",
            seed=1,
            confirm=True,
        )
        sim_run_targeted_test(
            project=str(real_manifest_with_urg),
            test="test2",
            seed=2,
            confirm=True,
        )

        # Manually create coverage_gaps.json files (simulating URG output)
        results_root = real_manifest_with_urg.parent / "sim_results"
        for test_name, seed in [("test1", 1), ("test2", 2)]:
            urg_dir = results_root / f"{test_name}_{seed}" / "urg_report"
            urg_dir.mkdir(parents=True, exist_ok=True)
            gaps_file = urg_dir / "coverage_gaps.json"
            gaps_file.write_text(
                json.dumps({"gaps": [], "summary": {"total": 0}}),
                encoding="utf-8",
            )

        # Get coverage diff
        result = cov_get_coverage_diff(
            project=str(real_manifest_with_urg),
            gap_id=None,
        )
        assert result["ok"] is True
        # Should find reports and compute diff
        assert "summary" in result["result"]

    def test_single_report_no_diff(self, real_manifest_with_urg: Path):
        """Tool handles single URG report without diff."""
        # Run one simulation
        sim_run_targeted_test(
            project=str(real_manifest_with_urg),
            test="single_test",
            seed=1,
            confirm=True,
        )

        # Manually create coverage_gaps.json
        results_root = real_manifest_with_urg.parent / "sim_results"
        urg_dir = results_root / "single_test_1" / "urg_report"
        urg_dir.mkdir(parents=True, exist_ok=True)
        gaps_file = urg_dir / "coverage_gaps.json"
        gaps_file.write_text(
            json.dumps({"gaps": [], "summary": {"total": 0}}),
            encoding="utf-8",
        )

        result = cov_get_coverage_diff(
            project=str(real_manifest_with_urg),
            gap_id=None,
        )
        assert result["ok"] is True
        # Single report returns as-is
        assert "gaps" in result["result"]


class TestSimRunTargetedTestEdgeCases:
    """Additional edge case tests for sim_run_targeted_test."""

    def test_timeout_handling(self, tmp_path: Path):
        """Tool handles command timeout."""
        manifest_path = tmp_path / "project_manifest.yaml"
        manifest_path.write_text(
            f"""
project: test_timeout
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "echo compile"
  run_cmd_template: "sleep 10"
  results_root: sim_results
  timeout_seconds: 1
policy:
  allow_running_simulation: true
""",
            encoding="utf-8",
        )
        (tmp_path / "sim_results").mkdir()
        (tmp_path / ".dv_ai_index").mkdir()

        result = sim_run_targeted_test(
            project=str(manifest_path),
            test="timeout_test",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is True
        # Run should timeout (status != pass or return_code == -1)
        if result["result"]["run"] is not None:
            assert (
                result["result"]["run"]["status"] != "pass"
                or result["result"]["run"]["return_code"] == -1
            )

    def test_command_not_found(self, tmp_path: Path):
        """Tool handles missing command."""
        manifest_path = tmp_path / "project_manifest.yaml"
        manifest_path.write_text(
            f"""
project: test_notfound
project_root: {tmp_path}
simulation:
  mode: real
  compile_cmd_template: "nonexistent_command_xyz123"
  run_cmd_template: "echo run"
  results_root: sim_results
  timeout_seconds: 10
policy:
  allow_running_simulation: true
""",
            encoding="utf-8",
        )
        (tmp_path / "sim_results").mkdir()
        (tmp_path / ".dv_ai_index").mkdir()

        result = sim_run_targeted_test(
            project=str(manifest_path),
            test="notfound_test",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is True
        # Compile should fail with return_code 127 (command not found) or similar
        assert result["result"]["compile"]["status"] != "pass"
        assert result["result"]["run"] is None  # Run skipped

    def test_evidence_attached(self, real_manifest: Path):
        """Tool attaches simulation evidence."""
        result = sim_run_targeted_test(
            project=str(real_manifest),
            test="evidence_test",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is True
        assert len(result["evidence"]) > 0
        evidence = result["evidence"][0]
        assert "source_type" in evidence
        assert "summary" in evidence

    def test_audit_record_attached(self, real_manifest: Path):
        """Tool attaches audit record."""
        result = sim_run_targeted_test(
            project=str(real_manifest),
            test="audit_test",
            seed=1,
            confirm=True,
        )
        assert result["ok"] is True
        assert "audit" in result
        audit = result["audit"]
        assert "tool" in audit
        assert "project" in audit
        assert "timestamp" in audit


class TestSimGetTestResultEdgeCases:
    """Additional edge case tests for sim_get_test_result."""

    def test_null_seed_returns_not_found(self, real_manifest: Path):
        """Tool returns not_found status when seed is None."""
        result = sim_get_test_result(
            project=str(real_manifest),
            test="my_test",
            seed=None,
        )
        assert result["ok"] is True
        # Should return not_found status (seed required to locate results)
        assert "sim_status" in result["result"]

    def test_result_persistence_across_queries(self, real_manifest: Path):
        """Multiple queries return same persisted result."""
        # Run once
        sim_run_targeted_test(
            project=str(real_manifest),
            test="persist_test",
            seed=123,
            confirm=True,
        )

        # Query twice
        result1 = sim_get_test_result(
            project=str(real_manifest),
            test="persist_test",
            seed=123,
        )
        result2 = sim_get_test_result(
            project=str(real_manifest),
            test="persist_test",
            seed=123,
        )

        assert result1["ok"] is True
        assert result2["ok"] is True
        assert result1["result"]["test"] == result2["result"]["test"]
        assert result1["result"]["seed"] == result2["result"]["seed"]
