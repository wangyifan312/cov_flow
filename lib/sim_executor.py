"""Subprocess simulation executor with security boundaries.

Provides SimExecutor for running compile/simulate/urg commands via subprocess
with path validation, timeout protection, and bounded log capture.

Security:
- Test names validated by regex + path traversal checks
- Commands executed via shlex.split() + shell=False
- Working directory locked to project_root
- subprocess timeout enforced
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class SimStepResult:
    """Result of a single simulation step (compile, run, or urg)."""

    step: str
    """Step name: 'compile', 'run', or 'urg'."""

    status: str
    """Step outcome: 'pass', 'fail', 'timeout', or 'error'."""

    return_code: int
    """Subprocess return code. -1 for timeout, 127 for command not found."""

    log_path: str
    """Absolute path to the log file."""

    duration_seconds: float
    """Wall-clock duration in seconds."""

    message: str
    """Human-readable summary of the step outcome."""

    stdout_tail: str
    """Last 50 lines of stdout (for error diagnosis)."""


@dataclass
class SimResult:
    """Result of a complete simulation pipeline execution."""

    test: str
    """Test name."""

    seed: int
    """Random seed."""

    compile: SimStepResult | None
    """Compile step result, or None if skipped."""

    run: SimStepResult | None
    """Run step result, or None if skipped."""

    urg: SimStepResult | None
    """URG step result, or None if skipped."""

    started_at: str
    """ISO timestamp when pipeline started."""

    finished_at: str
    """ISO timestamp when pipeline finished."""


class SimExecutor:
    """Real VCS simulation executor with security boundaries.

    Args:
        project_root: Working directory for all subprocess execution.
        results_root: Base directory for storing results and logs.
        timeout_seconds: Maximum seconds per compile/run step (default 600, max 3600).
        urg_timeout_seconds: Maximum seconds for urg step (default 300, max 1800).
    """

    TEST_NAME_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.\-]*$")

    def __init__(
        self,
        project_root: Path,
        results_root: Path,
        timeout_seconds: int = 600,
        urg_timeout_seconds: int = 300,
    ) -> None:
        self._project_root = Path(project_root).resolve()
        self._results_root = Path(results_root).resolve()
        self._timeout = max(1, min(timeout_seconds, 3600))
        self._urg_timeout = max(1, min(urg_timeout_seconds, 1800))

    @property
    def project_root(self) -> Path:
        """Return the project root directory."""
        return self._project_root

    @property
    def results_root(self) -> Path:
        """Return the results root directory."""
        return self._results_root

    @property
    def timeout_seconds(self) -> int:
        """Return the configured compile/run timeout."""
        return self._timeout

    @property
    def urg_timeout_seconds(self) -> int:
        """Return the configured urg timeout."""
        return self._urg_timeout

    # --- Validation ---

    def validate_test_name(self, test: str) -> None:
        """Validate a test name against injection attacks.

        Checks:
        1. Non-empty
        2. Regex match (alphanumeric + underscore/dot/dash)
        3. No ".." (path traversal)
        4. No "/" (path traversal)

        Raises:
            ValueError: If the test name is invalid.
        """
        if not test:
            raise ValueError("Test name must not be empty")
        if ".." in test:
            raise ValueError(f"Test name '{test}' contains '..' (path traversal)")
        if "/" in test:
            raise ValueError(f"Test name '{test}' contains '/' (path traversal)")
        if not self.TEST_NAME_RE.match(test):
            raise ValueError(
                f"Invalid test name '{test}': must match {self.TEST_NAME_RE.pattern}"
            )

    def validate_seed(self, seed: int) -> None:
        """Validate a seed value.

        Raises:
            ValueError: If the seed is negative.
        """
        if seed < 0:
            raise ValueError(f"Seed must be non-negative, got {seed}")

    # --- Directory management ---

    def get_results_dir(self, test: str, seed: int) -> Path:
        """Get (and create) the results directory for a test/seed pair.

        Args:
            test: Test name.
            seed: Random seed.

        Returns:
            Path to {results_root}/{test}_{seed}/.
        """
        d = self._results_root / f"{test}_{seed}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_log_path(self, test: str, seed: int, step: str) -> Path:
        """Get the log file path for a test/seed/step combination.

        Args:
            test: Test name.
            seed: Random seed.
            step: Step name ('compile', 'run', or 'urg').

        Returns:
            Path to the log file.
        """
        return self.get_results_dir(test, seed) / f"{step}.log"

    # --- Execution ---

    def compile(
        self, command: str, test: str, seed: int,
    ) -> SimStepResult:
        """Run the compile step.

        Args:
            command: The compile command string.
            test: Test name (validated).
            seed: Random seed (validated).

        Returns:
            SimStepResult with step='compile'.
        """
        self.validate_test_name(test)
        self.validate_seed(seed)
        log_path = self.get_log_path(test, seed, "compile")
        return self._execute_step("compile", command, log_path, self._timeout)

    def run_simulation(
        self, command: str, test: str, seed: int,
    ) -> SimStepResult:
        """Run the simulation step.

        Args:
            command: The run command string.
            test: Test name (validated).
            seed: Random seed (validated).

        Returns:
            SimStepResult with step='run'.
        """
        self.validate_test_name(test)
        self.validate_seed(seed)
        log_path = self.get_log_path(test, seed, "run")
        return self._execute_step("run", command, log_path, self._timeout)

    def run_urg(
        self, command: str, test: str, seed: int,
    ) -> SimStepResult:
        """Run the URG report generation step.

        Args:
            command: The urg command string.
            test: Test name (validated).
            seed: Random seed (validated).

        Returns:
            SimStepResult with step='urg'.
        """
        self.validate_test_name(test)
        self.validate_seed(seed)
        log_path = self.get_log_path(test, seed, "urg")
        return self._execute_step("urg", command, log_path, self._urg_timeout)

    def _execute_step(
        self, step: str, command: str, log_path: Path, timeout: int,
    ) -> SimStepResult:
        """Execute a subprocess step with timeout and logging.

        Uses shlex.split(command) + shell=False.
        subprocess.run with cwd locked to project_root.

        Args:
            step: Step name for the result.
            command: Command string to execute.
            log_path: Path to write stdout+stderr.
            timeout: Timeout in seconds.

        Returns:
            SimStepResult with execution details.
        """
        log_path.parent.mkdir(parents=True, exist_ok=True)

        start = time.monotonic()
        status = "error"
        return_code = -1
        stdout_text = ""
        stderr_text = ""
        message = ""

        try:
            args = shlex.split(command)
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self._project_root),
            )
            return_code = proc.returncode
            stdout_text = proc.stdout
            stderr_text = proc.stderr

            if return_code == 0:
                status = "pass"
                message = f"{step} completed successfully"
            else:
                status = "fail"
                message = f"{step} failed with return code {return_code}"

        except subprocess.TimeoutExpired:
            status = "timeout"
            return_code = -1
            stdout_text = f"[TIMEOUT after {timeout}s]\n"
            stderr_text = ""
            message = f"{step} timed out after {timeout}s"

        except FileNotFoundError:
            status = "error"
            return_code = 127
            stdout_text = ""
            cmd_name = shlex.split(command)[0] if command else ""
            stderr_text = f"Command not found: {cmd_name}\n"
            message = f"Command not found: {cmd_name}"

        except OSError as exc:
            status = "error"
            return_code = 126
            stdout_text = ""
            stderr_text = f"OS error: {exc}\n"
            message = f"OS error: {exc}"

        duration = time.monotonic() - start

        # Build log content
        log_content = ""
        if stdout_text:
            log_content += stdout_text
        if stderr_text:
            log_content += "\n--- STDERR ---\n" + stderr_text

        log_path.write_text(log_content, encoding="utf-8")

        # Extract last 50 lines as stdout_tail
        lines = stdout_text.splitlines()
        stdout_tail = "\n".join(lines[-50:]) if lines else ""

        return SimStepResult(
            step=step,
            status=status,
            return_code=return_code,
            log_path=str(log_path.resolve()),
            duration_seconds=round(duration, 3),
            message=message,
            stdout_tail=stdout_tail,
        )

    # --- Result persistence ---

    def save_result(self, test: str, seed: int, result: SimResult) -> Path:
        """Save a simulation result as JSON.

        Args:
            test: Test name.
            seed: Random seed.
            result: SimResult to serialize.

        Returns:
            Path to the written sim_result.json.
        """
        results_dir = self.get_results_dir(test, seed)
        path = results_dir / "sim_result.json"
        data = asdict(result)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def load_result(self, test: str, seed: int) -> SimResult | None:
        """Load a previously saved simulation result.

        Args:
            test: Test name.
            seed: Random seed.

        Returns:
            The SimResult, or None if not found.
        """
        path = self._results_root / f"{test}_{seed}" / "sim_result.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        # Reconstruct SimResult from dict
        compile_res = None
        if data.get("compile"):
            compile_res = SimStepResult(**data["compile"])
        run_res = None
        if data.get("run"):
            run_res = SimStepResult(**data["run"])
        urg_res = None
        if data.get("urg"):
            urg_res = SimStepResult(**data["urg"])
        return SimResult(
            test=data["test"],
            seed=data["seed"],
            compile=compile_res,
            run=run_res,
            urg=urg_res,
            started_at=data["started_at"],
            finished_at=data["finished_at"],
        )

    # --- Log I/O ---

    def read_log(self, test: str, seed: int, step: str) -> str | None:
        """Read a log file for a test/seed/step combination.

        Args:
            test: Test name.
            seed: Random seed.
            step: Step name ('compile', 'run', or 'urg').

        Returns:
            Log content as string, or None if not found.
        """
        path = self.get_log_path(test, seed, step)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def search_log(
        self,
        test: str,
        seed: int,
        keyword: str,
        step: str = "run",
    ) -> dict:
        """Search a log file for a keyword (bounded to 20 matches).

        Args:
            test: Test name.
            seed: Random seed.
            keyword: Search keyword (case-insensitive).
            step: Step name ('compile', 'run', or 'urg').

        Returns:
            Dict with 'matches', 'total_matches', and 'returned'.
        """
        content = self.read_log(test, seed, step)

        if content is None:
            return {
                "matches": [],
                "total_matches": 0,
                "returned": 0,
            }

        keyword_lower = keyword.lower()
        all_matches = [
            line for line in content.splitlines() if keyword_lower in line.lower()
        ]
        total = len(all_matches)
        bounded = all_matches[:20]

        return {
            "matches": bounded,
            "total_matches": total,
            "returned": len(bounded),
        }

    # --- Full pipeline ---

    def run_pipeline(
        self,
        test: str,
        seed: int,
        compile_cmd: str,
        run_cmd: str,
        urg_cmd: str | None = None,
    ) -> SimResult:
        """Execute compile → run → (optional) urg pipeline.

        - On compile fail: skip run and urg
        - On run fail: skip urg
        - On run success + urg_cmd provided: run urg
        - Returns SimResult with all step results

        Args:
            test: Test name.
            seed: Random seed.
            compile_cmd: Compile command string.
            run_cmd: Run command string.
            urg_cmd: Optional URG command string.

        Returns:
            SimResult with compile/run/urg results.
        """
        started_at = datetime.now().isoformat()

        # Compile
        compile_res = self.compile(compile_cmd, test, seed)
        run_res = None
        urg_res = None

        # Run (only if compile passed)
        if compile_res.status == "pass":
            run_res = self.run_simulation(run_cmd, test, seed)

            # URG (only if run passed and urg_cmd provided)
            if run_res.status == "pass" and urg_cmd:
                urg_res = self.run_urg(urg_cmd, test, seed)

        finished_at = datetime.now().isoformat()

        return SimResult(
            test=test,
            seed=seed,
            compile=compile_res,
            run=run_res,
            urg=urg_res,
            started_at=started_at,
            finished_at=finished_at,
        )
