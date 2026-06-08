"""Tests for lib/urg_runner.py."""

from pathlib import Path

import pytest

from lib.urg_runner import UrgResult, UrgRunner

AXI2AHB_REPORT = Path("mock_data/axi2ahb/urg_report")


@pytest.fixture
def runner() -> UrgRunner:
    return UrgRunner()


class TestInit:
    """Tests for UrgRunner initialization."""

    def test_defaults(self, runner: UrgRunner) -> None:
        assert runner.urg_binary == "urg"
        assert runner.timeout_seconds == 300

    def test_custom_binary(self) -> None:
        r = UrgRunner(urg_binary="/usr/local/bin/urg")
        assert r.urg_binary == "/usr/local/bin/urg"

    def test_custom_timeout(self) -> None:
        r = UrgRunner(timeout_seconds=600)
        assert r.timeout_seconds == 600

    def test_timeout_clamped_max(self) -> None:
        r = UrgRunner(timeout_seconds=99999)
        assert r.timeout_seconds == 1800

    def test_timeout_clamped_min(self) -> None:
        r = UrgRunner(timeout_seconds=0)
        assert r.timeout_seconds == 1


class TestGenerateReport:
    """Tests for generate_report() error paths.

    Note: actual urg execution requires a Synopsys VCS environment,
    so we only test error/validation paths here.
    """

    def test_not_configured_when_no_template(self, runner: UrgRunner, tmp_path: Path) -> None:
        result = runner.generate_report(
            vdb_dir=tmp_path,
            report_dir=tmp_path / "report",
            cmd_template=None,
        )
        assert result.status == "not_configured"
        assert result.gaps_count == 0
        assert "not configured" in result.message

    def test_not_configured_when_empty_template(self, runner: UrgRunner, tmp_path: Path) -> None:
        result = runner.generate_report(
            vdb_dir=tmp_path,
            report_dir=tmp_path / "report",
            cmd_template="",
        )
        assert result.status == "not_configured"

    def test_vdb_dir_not_found(self, runner: UrgRunner, tmp_path: Path) -> None:
        result = runner.generate_report(
            vdb_dir=tmp_path / "nonexistent.vdb",
            report_dir=tmp_path / "report",
            cmd_template="echo {vdb_dir} {report_dir}",
        )
        assert result.status == "error"
        assert "not found" in result.message

    def test_vdb_path_is_file(self, runner: UrgRunner, tmp_path: Path) -> None:
        vdb_file = tmp_path / "not_a_dir.vdb"
        vdb_file.write_text("fake")
        result = runner.generate_report(
            vdb_dir=vdb_file,
            report_dir=tmp_path / "report",
            cmd_template="echo {vdb_dir} {report_dir}",
        )
        assert result.status == "error"
        assert "not a directory" in result.message

    def test_urg_binary_not_found(self, tmp_path: Path) -> None:
        vdb_dir = tmp_path / "sim.vdb"
        vdb_dir.mkdir()
        r = UrgRunner(urg_binary="nonexistent_urg_binary_xyz")
        result = r.generate_report(
            vdb_dir=vdb_dir,
            report_dir=tmp_path / "report",
            cmd_template="nonexistent_urg_binary_xyz -dir {vdb_dir} -report {report_dir}",
        )
        assert result.status == "error"
        assert "not found" in result.message

    def test_cmd_template_success(self, runner: UrgRunner, tmp_path: Path) -> None:
        """Verify cmd_template placeholders are replaced and command runs."""
        vdb_dir = tmp_path / "sim.vdb"
        vdb_dir.mkdir()
        report_dir = tmp_path / "report"

        # Use echo as a mock urg command
        result = runner.generate_report(
            vdb_dir=vdb_dir,
            report_dir=report_dir,
            cmd_template="echo {vdb_dir} {report_dir}",
        )
        assert result.status == "ok"
        assert result.report_dir == str(report_dir.resolve())
        assert report_dir.is_dir()

    def test_command_failure(self, runner: UrgRunner, tmp_path: Path) -> None:
        vdb_dir = tmp_path / "sim.vdb"
        vdb_dir.mkdir()
        result = runner.generate_report(
            vdb_dir=vdb_dir,
            report_dir=tmp_path / "report",
            cmd_template="false",
        )
        assert result.status == "error"
        assert "exited with code" in result.message


class TestParseReport:
    """Tests for parse_report() using real mock data."""

    def test_parse_axi2ahb_report(self, runner: UrgRunner) -> None:
        if not AXI2AHB_REPORT.exists():
            pytest.skip("axi2ahb URG report not available")

        result = runner.parse_report(AXI2AHB_REPORT)
        assert "gaps" in result
        assert len(result["gaps"]) > 0

    def test_parse_report_gaps_structure(self, runner: UrgRunner) -> None:
        if not AXI2AHB_REPORT.exists():
            pytest.skip("axi2ahb URG report not available")

        result = runner.parse_report(AXI2AHB_REPORT)
        gaps = result["gaps"]
        assert len(gaps) > 0

        # Check a gap has required fields
        gap = gaps[0]
        assert "gap_id" in gap
        assert "coverage_type" in gap
        assert "hit_count" in gap

    def test_parse_nonexistent_report_returns_error(
        self, runner: UrgRunner, tmp_path: Path,
    ) -> None:
        result = runner.parse_report(tmp_path / "nonexistent_report")
        assert "error" in result
        assert result["gaps"] == []


class TestBuildCoverageDb:
    """Tests for build_coverage_db()."""

    def test_basic_transform(self, runner: UrgRunner) -> None:
        gaps_json = {
            "project": "test",
            "gaps": [
                {"gap_id": "GAP_0001", "coverage_type": "functional", "hit_count": 0},
                {"gap_id": "GAP_0002", "coverage_type": "functional", "hit_count": 5},
            ],
        }
        db = runner.build_coverage_db(gaps_json, "report_1")
        assert db["report_id"] == "report_1"
        assert db["schema_version"] == "coverage_db.v1"
        assert len(db["gaps"]) == 2
        assert db["gaps"][0]["gap_id"] == "GAP_0001"
        assert db["gaps"][1]["hit_count"] == 5

    def test_empty_gaps(self, runner: UrgRunner) -> None:
        db = runner.build_coverage_db({"gaps": []}, "empty")
        assert db["report_id"] == "empty"
        assert db["gaps"] == []

    def test_no_gaps_key(self, runner: UrgRunner) -> None:
        db = runner.build_coverage_db({}, "nokey")
        assert db["gaps"] == []

    def test_skips_gaps_without_gap_id(self, runner: UrgRunner) -> None:
        gaps_json = {
            "gaps": [
                {"coverage_type": "functional", "hit_count": 0},  # no gap_id
                {"gap_id": "GAP_0001", "hit_count": 3},
            ],
        }
        db = runner.build_coverage_db(gaps_json, "r1")
        assert len(db["gaps"]) == 1
        assert db["gaps"][0]["gap_id"] == "GAP_0001"

    def test_sets_default_hit_count(self, runner: UrgRunner) -> None:
        gaps_json = {
            "gaps": [
                {"gap_id": "GAP_0001"},  # no hit_count
            ],
        }
        db = runner.build_coverage_db(gaps_json, "r1")
        assert db["gaps"][0]["hit_count"] == 0

    def test_compute_diff_compatible(self, runner: UrgRunner) -> None:
        """Verify output works with compute_diff()."""
        from lib.coverage_diff import compute_diff

        before_json = {
            "gaps": [
                {"gap_id": "GAP_0001", "coverage_type": "functional", "hit_count": 0},
                {"gap_id": "GAP_0002", "coverage_type": "functional", "hit_count": 0},
            ],
        }
        after_json = {
            "gaps": [
                {"gap_id": "GAP_0001", "coverage_type": "functional", "hit_count": 5},
                {"gap_id": "GAP_0002", "coverage_type": "functional", "hit_count": 0},
            ],
        }
        before_db = runner.build_coverage_db(before_json, "before")
        after_db = runner.build_coverage_db(after_json, "after")

        diff = compute_diff(before_db, after_db)
        assert diff["ok"] is True
        assert diff["summary"]["newly_covered"] == 1
        assert diff["summary"]["unchanged"] == 1

    def test_default_report_id(self, runner: UrgRunner) -> None:
        db = runner.build_coverage_db({"gaps": []})
        assert db["report_id"] == "urg_report"

    def test_matches_mock_format(self, runner: UrgRunner) -> None:
        """Verify output matches mock_data/dma_subsystem format."""
        gaps_json = {
            "gaps": [
                {
                    "gap_id": "GAP_0001",
                    "coverage_type": "functional",
                    "covergroup": "test_cg",
                    "coverpoint": "test_cp",
                    "bin": "test_bin",
                    "hit_count": 3,
                },
            ],
        }
        db = runner.build_coverage_db(gaps_json, "test_report")
        assert db["report_id"] == "test_report"
        assert db["schema_version"] == "coverage_db.v1"
        assert len(db["gaps"]) == 1
        assert db["gaps"][0]["gap_id"] == "GAP_0001"
        assert db["gaps"][0]["coverage_type"] == "functional"
        assert db["gaps"][0]["hit_count"] == 3


class TestUrgResult:
    """Tests for UrgResult dataclass."""

    def test_ok_result(self) -> None:
        r = UrgResult(status="ok", report_dir="/tmp/report", message="success", gaps_count=10)
        assert r.status == "ok"
        assert r.gaps_count == 10

    def test_error_result(self) -> None:
        r = UrgResult(status="error", report_dir="/tmp", message="failed", gaps_count=0)
        assert r.status == "error"
        assert r.gaps_count == 0

    def test_not_configured(self) -> None:
        r = UrgResult(status="not_configured", report_dir="/tmp", message="not set")
        assert r.status == "not_configured"

    def test_timeout(self) -> None:
        r = UrgResult(status="timeout", report_dir="/tmp", message="timed out")
        assert r.status == "timeout"
