"""Tests for lib/sim_executor.py."""

from pathlib import Path

import pytest

from lib.sim_executor import SimExecutor, SimResult, SimStepResult


@pytest.fixture
def executor(tmp_path: Path) -> SimExecutor:
    """Create a SimExecutor with tmp_path as project_root and results_root."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    results_root = tmp_path / "results"
    results_root.mkdir()
    return SimExecutor(
        project_root=project_root,
        results_root=results_root,
        timeout_seconds=10,
    )


class TestValidation:
    """Tests for test name and seed validation."""

    def test_valid_test_name(self, executor: SimExecutor) -> None:
        executor.validate_test_name("my_test_01")

    def test_valid_test_name_with_dots(self, executor: SimExecutor) -> None:
        executor.validate_test_name("pkg.my_test")

    def test_valid_test_name_with_dashes(self, executor: SimExecutor) -> None:
        executor.validate_test_name("my-test-v2")

    def test_empty_test_name_raises(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            executor.validate_test_name("")

    def test_test_name_with_path_traversal_dots(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            executor.validate_test_name("../etc/passwd")

    def test_test_name_with_path_traversal_slash(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            executor.validate_test_name("test/../../")

    def test_test_name_with_only_dots(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            executor.validate_test_name("../../../")

    def test_test_name_with_spaces_raises(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="Invalid test name"):
            executor.validate_test_name("test name")

    def test_test_name_with_semicolon_raises(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="Invalid test name"):
            executor.validate_test_name("test;echo pwned")

    def test_test_name_with_shell_chars_raises(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="Invalid test name"):
            executor.validate_test_name("test$(whoami)")

    def test_valid_seed(self, executor: SimExecutor) -> None:
        executor.validate_seed(0)
        executor.validate_seed(42)
        executor.validate_seed(999999)

    def test_negative_seed_raises(self, executor: SimExecutor) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            executor.validate_seed(-1)


class TestProperties:
    """Tests for SimExecutor properties."""

    def test_project_root(self, executor: SimExecutor) -> None:
        assert executor.project_root.exists()

    def test_results_root(self, executor: SimExecutor) -> None:
        assert executor.results_root.exists()

    def test_timeout(self, executor: SimExecutor) -> None:
        assert executor.timeout_seconds == 10

    def test_urg_timeout(self, executor: SimExecutor) -> None:
        assert executor.urg_timeout_seconds == 300

    def test_timeout_clamped_max(self, tmp_path: Path) -> None:
        e = SimExecutor(tmp_path, tmp_path, timeout_seconds=99999)
        assert e.timeout_seconds == 3600

    def test_timeout_clamped_min(self, tmp_path: Path) -> None:
        e = SimExecutor(tmp_path, tmp_path, timeout_seconds=0)
        assert e.timeout_seconds == 1


class TestCompile:
    """Tests for the compile() method."""

    def test_compile_success(self, executor: SimExecutor) -> None:
        result = executor.compile("echo compile_ok", "test1", 42)
        assert isinstance(result, SimStepResult)
        assert result.step == "compile"
        assert result.status == "pass"
        assert result.return_code == 0
        assert "compile" in result.log_path
        log_content = Path(result.log_path).read_text()
        assert "compile_ok" in log_content
        assert "compile completed successfully" in result.message

    def test_compile_failure(self, executor: SimExecutor) -> None:
        result = executor.compile("false", "test_fail", 1)
        assert result.step == "compile"
        assert result.status == "fail"
        assert result.return_code != 0
        assert "failed" in result.message

    def test_compile_command_not_found(self, executor: SimExecutor) -> None:
        result = executor.compile("nonexistent_command_xyz", "test_cnf", 1)
        assert result.step == "compile"
        assert result.status == "error"
        assert result.return_code == 127
        assert "not found" in result.message

    def test_compile_stdout_tail(self, executor: SimExecutor) -> None:
        result = executor.compile("echo hello", "tail_test", 1)
        assert "hello" in result.stdout_tail


class TestRunSimulation:
    """Tests for the run_simulation() method."""

    def test_run_success(self, executor: SimExecutor) -> None:
        result = executor.run_simulation("echo sim_done", "runtest", 7)
        assert result.step == "run"
        assert result.status == "pass"
        assert result.return_code == 0
        assert "sim_done" in Path(result.log_path).read_text()

    def test_run_failure(self, executor: SimExecutor) -> None:
        result = executor.run_simulation("false", "runtest", 7)
        assert result.step == "run"
        assert result.status == "fail"
        assert result.return_code != 0

    def test_run_duration_positive(self, executor: SimExecutor) -> None:
        result = executor.run_simulation("echo quick", "test_dur", 1)
        assert result.duration_seconds >= 0.0


class TestRunUrg:
    """Tests for the run_urg() method."""

    def test_run_urg_success(self, executor: SimExecutor) -> None:
        result = executor.run_urg("echo urg_done", "urgtest", 1)
        assert result.step == "urg"
        assert result.status == "pass"
        assert "urg_done" in Path(result.log_path).read_text()

    def test_run_urg_failure(self, executor: SimExecutor) -> None:
        result = executor.run_urg("false", "urgtest", 1)
        assert result.step == "urg"
        assert result.status == "fail"

    def test_run_urg_log_path(self, executor: SimExecutor) -> None:
        result = executor.run_urg("echo ok", "urgtest", 1)
        assert "urg.log" in result.log_path


class TestExecuteStep:
    """Tests for _execute_step() internals."""

    def test_stderr_captured(self, executor: SimExecutor) -> None:
        cmd = "python3 -c \"import sys; sys.stderr.write('err_msg\\n')\""
        log_path = executor.get_log_path("stderr", 1, "run")
        result = executor._execute_step("run", cmd, log_path, 10)
        log_content = Path(result.log_path).read_text()
        assert "STDERR" in log_content
        assert "err_msg" in log_content

    def test_timeout_handling(self, executor: SimExecutor) -> None:
        # Create an executor with 1 second timeout
        e = SimExecutor(executor.project_root, executor.results_root, timeout_seconds=1)
        result = e.run_simulation("sleep 10", "timeout_test", 1)
        assert result.status == "timeout"
        assert result.return_code == -1
        assert "timed out" in result.message

    def test_stdout_tail_last_50_lines(self, executor: SimExecutor) -> None:
        # Generate 100 lines of output
        cmd = "python3 -c \"for i in range(100): print(f'line_{i}')\""
        log_path = executor.get_log_path("tail50", 1, "run")
        result = executor._execute_step("run", cmd, log_path, 10)
        lines = result.stdout_tail.strip().split("\n")
        assert len(lines) == 50
        assert "line_50" in result.stdout_tail
        assert "line_99" in result.stdout_tail

    def test_cwd_is_project_root(self, executor: SimExecutor) -> None:
        # Verify subprocess runs with cwd set to project_root
        cmd = "pwd"
        log_path = executor.get_log_path("cwd_test", 1, "run")
        result = executor._execute_step("run", cmd, log_path, 10)
        # The log should contain the project_root path
        log_content = Path(result.log_path).read_text()
        assert str(executor.project_root) in log_content


class TestSaveLoadResult:
    """Tests for save_result() and load_result()."""

    def test_save_and_load(self, executor: SimExecutor) -> None:
        compile_res = SimStepResult(
            step="compile", status="pass", return_code=0,
            log_path="/tmp/compile.log", duration_seconds=1.5,
            message="ok", stdout_tail="done",
        )
        sim_result = SimResult(
            test="mytest", seed=42,
            compile=compile_res, run=None, urg=None,
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:02",
        )
        path = executor.save_result("mytest", 42, sim_result)
        assert path.exists()

        loaded = executor.load_result("mytest", 42)
        assert loaded is not None
        assert loaded.test == "mytest"
        assert loaded.seed == 42
        assert loaded.compile is not None
        assert loaded.compile.status == "pass"
        assert loaded.run is None

    def test_load_nonexistent_returns_none(self, executor: SimExecutor) -> None:
        assert executor.load_result("nope", 0) is None

    def test_save_with_all_steps(self, executor: SimExecutor) -> None:
        step = SimStepResult(
            step="compile", status="pass", return_code=0,
            log_path="/tmp/x.log", duration_seconds=0.5,
            message="ok", stdout_tail="",
        )
        sim_result = SimResult(
            test="full", seed=1,
            compile=step, run=step, urg=step,
            started_at="2026-01-01T00:00:00",
            finished_at="2026-01-01T00:00:03",
        )
        executor.save_result("full", 1, sim_result)
        loaded = executor.load_result("full", 1)
        assert loaded is not None
        assert loaded.compile is not None
        assert loaded.run is not None
        assert loaded.urg is not None


class TestReadLog:
    """Tests for read_log()."""

    def test_read_existing_log(self, executor: SimExecutor) -> None:
        executor.compile("echo hello_log", "rl_test", 5)
        content = executor.read_log("rl_test", 5, "compile")
        assert content is not None
        assert "hello_log" in content

    def test_read_nonexistent_log(self, executor: SimExecutor) -> None:
        assert executor.read_log("no_test", 0, "run") is None


class TestSearchLog:
    """Tests for search_log()."""

    def test_search_found(self, executor: SimExecutor) -> None:
        executor.run_simulation("echo TARGET_FOUND", "search_test", 1)
        result = executor.search_log("search_test", 1, "TARGET_FOUND", step="run")
        assert result["total_matches"] >= 1
        assert result["returned"] >= 1

    def test_search_not_found(self, executor: SimExecutor) -> None:
        executor.run_simulation("echo nothing", "search_miss", 1)
        result = executor.search_log("search_miss", 1, "NONEXISTENT_KW", step="run")
        assert result["total_matches"] == 0
        assert result["returned"] == 0

    def test_search_case_insensitive(self, executor: SimExecutor) -> None:
        executor.run_simulation("echo Hello_World", "search_ci", 1)
        result = executor.search_log("search_ci", 1, "hello_world", step="run")
        assert result["total_matches"] >= 1

    def test_search_nonexistent_log(self, executor: SimExecutor) -> None:
        result = executor.search_log("no_test", 0, "keyword", step="run")
        assert result["total_matches"] == 0
        assert result["returned"] == 0

    def test_search_bounded_to_20(self, executor: SimExecutor) -> None:
        # Write a log with 30 matching lines
        log_path = executor.get_log_path("bounded", 1, "run")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        lines = "\n".join(f"match line {i}" for i in range(30))
        log_path.write_text(lines)
        result = executor.search_log("bounded", 1, "match", step="run")
        assert result["total_matches"] == 30
        assert result["returned"] == 20
        assert len(result["matches"]) == 20


class TestGetPaths:
    """Tests for get_results_dir() and get_log_path()."""

    def test_results_dir_created(self, executor: SimExecutor) -> None:
        d = executor.get_results_dir("mytest", 42)
        assert d.is_dir()
        assert "mytest_42" in str(d)

    def test_log_path(self, executor: SimExecutor) -> None:
        p = executor.get_log_path("mytest", 42, "compile")
        assert p.name == "compile.log"
        assert "mytest_42" in str(p)


class TestRunPipeline:
    """Tests for run_pipeline()."""

    def test_full_pipeline_success(self, executor: SimExecutor) -> None:
        result = executor.run_pipeline(
            test="pipe_test", seed=1,
            compile_cmd="echo compile_ok",
            run_cmd="echo run_ok",
            urg_cmd="echo urg_ok",
        )
        assert isinstance(result, SimResult)
        assert result.test == "pipe_test"
        assert result.seed == 1
        assert result.compile is not None
        assert result.compile.status == "pass"
        assert result.run is not None
        assert result.run.status == "pass"
        assert result.urg is not None
        assert result.urg.status == "pass"
        assert result.started_at != ""
        assert result.finished_at != ""

    def test_pipeline_compile_fail_skips_run(self, executor: SimExecutor) -> None:
        result = executor.run_pipeline(
            test="pipe_fail", seed=1,
            compile_cmd="false",
            run_cmd="echo should_not_run",
        )
        assert result.compile is not None
        assert result.compile.status == "fail"
        assert result.run is None
        assert result.urg is None

    def test_pipeline_run_fail_skips_urg(self, executor: SimExecutor) -> None:
        result = executor.run_pipeline(
            test="pipe_run_fail", seed=1,
            compile_cmd="echo ok",
            run_cmd="false",
            urg_cmd="echo should_not_run",
        )
        assert result.compile is not None
        assert result.compile.status == "pass"
        assert result.run is not None
        assert result.run.status == "fail"
        assert result.urg is None

    def test_pipeline_no_urg_cmd(self, executor: SimExecutor) -> None:
        result = executor.run_pipeline(
            test="no_urg", seed=1,
            compile_cmd="echo ok",
            run_cmd="echo ok",
        )
        assert result.compile is not None
        assert result.run is not None
        assert result.urg is None
