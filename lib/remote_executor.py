"""SSH-based remote simulation executor.

Extends SimExecutor interface to execute compile/run/urg commands via SSH
on a remote server. Command execution goes over SSH; results and logs are
saved locally for MCP tool access.

Security:
- All SimExecutor validations (test name, seed) are preserved
- SSH host must be configured in ~/.ssh/config
- Commands run via SSH using shlex.quote for argument protection
"""

from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path

from lib.sim_executor import SimExecutor, SimStepResult


class RemoteSimExecutor(SimExecutor):
    """SimExecutor that runs commands on a remote server via SSH.

    Args:
        host: SSH host alias (must be configured in ~/.ssh/config).
        project_root: Server-side project root directory.
        results_root: Local directory for storing results and logs.
        timeout_seconds: Max seconds per compile/run step.
        urg_timeout_seconds: Max seconds for urg step.
        env_setup: Optional shell commands to run before each step
                   (e.g. 'source /opt/synopsys/setup.sh').
    """

    def __init__(
        self,
        host: str,
        project_root: Path,
        results_root: Path,
        timeout_seconds: int = 600,
        urg_timeout_seconds: int = 300,
        env_setup: str = "",
    ) -> None:
        super().__init__(project_root, results_root, timeout_seconds, urg_timeout_seconds)
        self._host = host
        self._env_setup = env_setup

    @property
    def host(self) -> str:
        """Return the SSH host alias."""
        return self._host

    @property
    def env_setup(self) -> str:
        """Return the environment setup commands."""
        return self._env_setup

    def _execute_step(
        self, step: str, command: str, log_path: Path, timeout: int,
    ) -> SimStepResult:
        """Execute a step remotely via SSH.

        Runs the command on the remote server with cwd locked to project_root.
        Captures stdout/stderr locally and writes the log file locally.
        """
        log_path.parent.mkdir(parents=True, exist_ok=True)

        remote_parts = [f"cd {shlex.quote(str(self._project_root))}"]
        if self._env_setup:
            remote_parts.append(self._env_setup)
        remote_parts.append(f"{command} 2>&1")
        remote_cmd = " && ".join(remote_parts)

        ssh_cmd = ["ssh", "-o", "ConnectTimeout=10", self._host, remote_cmd]

        start = time.monotonic()
        status = "error"
        return_code = -1
        stdout_text = ""
        message = ""

        try:
            proc = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return_code = proc.returncode
            stdout_text = proc.stdout

            ssh_error_keywords = [
                "Could not resolve hostname",
                "Connection refused",
                "Permission denied",
                "No such file or directory",
                "Host key verification failed",
            ]
            is_ssh_error = proc.stderr and any(
                kw in proc.stderr for kw in ssh_error_keywords
            )

            if is_ssh_error:
                status = "error"
                return_code = 255
                message = f"SSH error: {proc.stderr.strip()}"
            elif return_code == 0:
                status = "pass"
                message = f"{step} completed successfully (remote)"
            else:
                status = "fail"
                message = f"{step} failed with return code {return_code}"

        except subprocess.TimeoutExpired:
            status = "timeout"
            return_code = -1
            stdout_text = f"[TIMEOUT after {timeout}s]\n"
            message = f"{step} timed out after {timeout}s"

        except FileNotFoundError:
            status = "error"
            return_code = 127
            message = "SSH command not found"

        except OSError as exc:
            status = "error"
            return_code = 126
            message = f"OS error: {exc}"

        duration = time.monotonic() - start

        log_content = ""
        if stdout_text:
            log_content += stdout_text

        log_path.write_text(log_content, encoding="utf-8")

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
