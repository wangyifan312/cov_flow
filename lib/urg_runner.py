"""URG (Unified Report Generator) runner with parsing pipeline.

Provides UrgRunner for:
1. Running the urg binary to generate coverage reports (subprocess)
2. Parsing URG HTML reports via the existing lib.urg_parser pipeline
3. Building coverage databases compatible with lib.coverage_diff.compute_diff()

Security:
- Commands executed via shlex.split() + shell=False
- Subprocess timeout enforced
- All paths resolved and validated
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from lib.urg_parser import (
    assemble_gaps,
    build_coverage_gaps,
    parse_code_coverage,
    parse_functional_coverage,
    parse_group_list,
    parse_module_list,
    parse_session_xml,
)


@dataclass
class UrgResult:
    """Result of a URG report generation."""

    status: str
    """One of: 'ok', 'error', 'not_configured', 'timeout'."""

    report_dir: str
    """Path to the generated report directory (as string)."""

    message: str
    """Human-readable description of the result."""

    gaps_count: int = 0
    """Number of gaps parsed (0 if error or not_configured)."""


class UrgRunner:
    """URG report generator and parser.

    Args:
        urg_binary: Path to or name of the urg binary (default: 'urg').
        timeout_seconds: Maximum seconds for urg execution (default: 300, max: 1800).
    """

    def __init__(
        self,
        urg_binary: str = "urg",
        timeout_seconds: int = 300,
    ) -> None:
        self._urg_binary = urg_binary
        self._timeout_seconds = max(1, min(timeout_seconds, 1800))

    @property
    def urg_binary(self) -> str:
        """Return the configured urg binary path."""
        return self._urg_binary

    @property
    def timeout_seconds(self) -> int:
        """Return the configured timeout."""
        return self._timeout_seconds

    def generate_report(
        self,
        vdb_dir: str | Path,
        report_dir: str | Path,
        cmd_template: str | None = None,
    ) -> UrgResult:
        """Run urg to generate a coverage report from a VCS simulation database.

        If cmd_template is None or empty, returns UrgResult(status="not_configured").

        Otherwise:
            cmd = cmd_template.format(vdb_dir=str(vdb_dir), report_dir=str(report_dir))
            subprocess.run(shlex.split(cmd), shell=False, timeout=self._timeout_seconds)

        Args:
            vdb_dir: Path to the .vdb coverage database directory.
            report_dir: Path where the URG HTML report will be written.
            cmd_template: Optional command template string with {vdb_dir} and
                {report_dir} placeholders. If None or empty, returns not_configured.

        Returns:
            UrgResult with status and report_dir path.
        """
        vdb_dir = Path(vdb_dir).resolve()
        report_dir = Path(report_dir).resolve()

        # Check if cmd_template is configured
        if not cmd_template:
            return UrgResult(
                status="not_configured",
                report_dir=str(report_dir),
                message="URG command template not configured",
                gaps_count=0,
            )

        # Validate vdb_dir exists
        if not vdb_dir.exists():
            return UrgResult(
                status="error",
                report_dir=str(report_dir),
                message=f"VDB directory not found: {vdb_dir}",
                gaps_count=0,
            )

        if not vdb_dir.is_dir():
            return UrgResult(
                status="error",
                report_dir=str(report_dir),
                message=f"VDB path is not a directory: {vdb_dir}",
                gaps_count=0,
            )

        # Build command from template
        command = cmd_template.format(vdb_dir=str(vdb_dir), report_dir=str(report_dir))

        # Create report directory
        report_dir.mkdir(parents=True, exist_ok=True)

        # Execute
        try:
            args = shlex.split(command)
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                cwd=str(vdb_dir.parent),
            )
            if proc.returncode != 0:
                stderr_snippet = (proc.stderr or proc.stdout or "")[:500]
                return UrgResult(
                    status="error",
                    report_dir=str(report_dir),
                    message=f"urg exited with code {proc.returncode}: {stderr_snippet}",
                    gaps_count=0,
                )
        except subprocess.TimeoutExpired:
            return UrgResult(
                status="timeout",
                report_dir=str(report_dir),
                message=f"urg timed out after {self._timeout_seconds}s",
                gaps_count=0,
            )
        except FileNotFoundError:
            return UrgResult(
                status="error",
                report_dir=str(report_dir),
                message=f"urg binary not found: {self._urg_binary}",
                gaps_count=0,
            )
        except OSError as exc:
            return UrgResult(
                status="error",
                report_dir=str(report_dir),
                message=f"OS error running urg: {exc}",
                gaps_count=0,
            )

        # Success — try to parse the report to get gaps_count
        try:
            parsed = self.parse_report(report_dir)
            gaps_count = len(parsed.get("gaps", []))
        except Exception:
            gaps_count = 0

        return UrgResult(
            status="ok",
            report_dir=str(report_dir),
            message=f"URG report generated successfully at {report_dir}",
            gaps_count=gaps_count,
        )

    def parse_report(self, report_dir: str | Path) -> dict:
        """Parse a URG HTML report directory using the urg_parser pipeline.

        Calls the full pipeline: session.xml → modlist/groups → functional +
        code coverage → assemble gaps → build coverage_gaps JSON.

        Args:
            report_dir: Path to the URG report directory (containing session.xml).

        Returns:
            Dict with 'gaps' list (coverage_gaps.json structure compatible with
            compute_diff). If parsing fails, returns {"gaps": [], "error": str(e)}.
        """
        report_dir = Path(report_dir).resolve()

        try:
            # Step 1: Parse session.xml
            session = parse_session_xml(report_dir)

            # Step 2: Parse structure
            modules = parse_module_list(report_dir)
            groups = parse_group_list(report_dir)

            # Step 3: Parse functional coverage
            functional_gaps = parse_functional_coverage(report_dir, groups)

            # Step 4: Parse code coverage (project_root for path normalization)
            project_root = str(report_dir.parent)
            code_coverage_gaps = parse_code_coverage(report_dir, modules, project_root)

            # Step 5: Assemble gaps
            all_gaps = assemble_gaps(functional_gaps, code_coverage_gaps, project_root)

            # Step 6: Build gaps JSON
            report_id = session.get("report_id", "urg_report")
            project = session.get("project", "")
            gaps_output = build_coverage_gaps(all_gaps, project, report_id)

            return gaps_output

        except Exception as e:
            return {"gaps": [], "error": str(e)}

    def build_coverage_db(
        self,
        gaps: dict,
        report_id: str = "urg_report",
    ) -> dict:
        """Convert coverage_gaps dict to coverage_db format.

        The coverage_db format is what compute_diff() expects:
        {
            "report_id": report_id,
            "schema_version": "coverage_db.v1",
            "gaps": [
                {"gap_id": "...", "hit_count": N, "goal": N, ...},
                ...
            ]
        }

        Args:
            gaps: coverage_gaps dict with 'gaps' list.
                Each gap must have 'gap_id' and 'hit_count'.
            report_id: Identifier for this report run.

        Returns:
            Dict compatible with compute_diff() and mock_data format.
        """
        gaps_list = gaps.get("gaps", [])

        db_gaps = []
        for gap in gaps_list:
            entry = dict(gap)
            # Ensure required fields for compute_diff
            if "gap_id" not in entry:
                continue
            entry.setdefault("hit_count", 0)
            db_gaps.append(entry)

        return {
            "report_id": report_id,
            "schema_version": "coverage_db.v1",
            "gaps": db_gaps,
        }
