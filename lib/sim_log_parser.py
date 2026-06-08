"""VCS/UVM simulation log parser.

Parses VCS simulation logs to extract UVM message counts and pass/fail status.
Pure functions with no I/O side effects.

Pass/fail detection priority (high to low):
1. Explicit markers: "Test PASSED" / "Test FAILED" → pass / fail
2. UVM_FATAL count > 0 → fail
3. UVM_ERROR count > 0 → fail
4. "$finish" found → pass (VCS normal exit)
5. Otherwise → unknown
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SimLogSummary:
    """Parsed summary of a VCS/UVM simulation log."""

    status: str
    """One of: 'pass', 'fail', 'unknown'."""

    uvm_info: int = 0
    """Count of UVM_INFO messages."""

    uvm_warning: int = 0
    """Count of UVM_WARNING messages."""

    uvm_error: int = 0
    """Count of UVM_ERROR messages."""

    uvm_fatal: int = 0
    """Count of UVM_FATAL messages."""

    finish_detected: bool = False
    """Whether $finish was detected in the log."""

    test_pass_line: str = ""
    """The line containing PASSED/FAILED, or empty string."""

    duration_hint: str = ""
    """'simulation time' line if found, or empty string."""


# Compiled patterns for UVM message counting (supports both formats)
# Format 1: UVM_INFO : 5
# Format 2: [UVM_INFO] : 5
_UVM_INFO_RE = re.compile(r"\[?UVM_INFO\]?\s*:\s*(\d+)")
_UVM_WARNING_RE = re.compile(r"\[?UVM_WARNING\]?\s*:\s*(\d+)")
_UVM_ERROR_RE = re.compile(r"\[?UVM_ERROR\]?\s*:\s*(\d+)")
_UVM_FATAL_RE = re.compile(r"\[?UVM_FATAL\]?\s*:\s*(\d+)")

# Explicit pass/fail markers
_EXPLICIT_PASS_RE = re.compile(
    r"TEST\s+PASSED|\+UVM_TEST_PASS|UVM\s+TEST\s+PASSED",
    re.IGNORECASE,
)
_EXPLICIT_FAIL_RE = re.compile(
    r"TEST\s+FAILED|\+UVM_TEST_FAIL|UVM\s+TEST\s+FAILED",
    re.IGNORECASE,
)

# $finish marker
_FINISH_RE = re.compile(r"\$finish")

# Simulation time hint
_SIM_TIME_RE = re.compile(r"simulation time.*", re.IGNORECASE)


def _count_matches(pattern: re.Pattern[str], text: str) -> int:
    """Return the sum of all integers captured by pattern in text."""
    matches = pattern.findall(text)
    total = 0
    for match in matches:
        try:
            total += int(match)
        except (ValueError, TypeError):
            pass
    return total


def detect_pass_fail(log_content: str) -> str:
    """Determine pass/fail from log content.

    Priority (highest first):
    1. Explicit "Test PASSED" or "Test FAILED" → "pass" / "fail"
    2. UVM_FATAL present → "fail"
    3. UVM_ERROR present → "fail"
    4. "$finish" present → "pass" (VCS normal exit)
    5. Otherwise → "unknown"

    Args:
        log_content: Raw log text from a VCS simulation run.

    Returns:
        One of: 'pass', 'fail', 'unknown'.
    """
    if not log_content:
        return "unknown"

    # Priority 1: Explicit markers
    has_explicit_pass = bool(_EXPLICIT_PASS_RE.search(log_content))
    has_explicit_fail = bool(_EXPLICIT_FAIL_RE.search(log_content))

    if has_explicit_fail:
        return "fail"
    if has_explicit_pass:
        return "pass"

    # Priority 2: UVM_FATAL
    fatal_count = _count_matches(_UVM_FATAL_RE, log_content)
    if fatal_count > 0:
        return "fail"

    # Priority 3: UVM_ERROR
    error_count = _count_matches(_UVM_ERROR_RE, log_content)
    if error_count > 0:
        return "fail"

    # Priority 4: $finish
    if _FINISH_RE.search(log_content):
        return "pass"

    # Priority 5: unknown
    return "unknown"


def parse_vcs_log(log_content: str) -> SimLogSummary:
    """Parse a VCS/UVM simulation log and extract message counts and status.

    Counts UVM message types by regex:
    - UVM_INFO:    r'UVM_INFO'     or r'[UVM_INFO]'
    - UVM_WARNING: r'UVM_WARNING'  or r'[UVM_WARNING]'
    - UVM_ERROR:   r'UVM_ERROR'    or r'[UVM_ERROR]'
    - UVM_FATAL:   r'UVM_FATAL'    or r'[UVM_FATAL]'

    Args:
        log_content: Raw log text from a VCS simulation run.

    Returns:
        SimLogSummary with status, message counts, and metadata.
    """
    if not log_content:
        return SimLogSummary(status="unknown")

    # Extract counts using findall
    info_count = _count_matches(_UVM_INFO_RE, log_content)
    warning_count = _count_matches(_UVM_WARNING_RE, log_content)
    error_count = _count_matches(_UVM_ERROR_RE, log_content)
    fatal_count = _count_matches(_UVM_FATAL_RE, log_content)

    # Detect pass/fail
    status = detect_pass_fail(log_content)

    # Check for $finish
    finish_detected = bool(_FINISH_RE.search(log_content))

    # Extract test_pass_line if present
    test_pass_line = ""
    if _EXPLICIT_PASS_RE.search(log_content):
        test_pass_line = _EXPLICIT_PASS_RE.search(log_content).group(0)  # type: ignore
    elif _EXPLICIT_FAIL_RE.search(log_content):
        test_pass_line = _EXPLICIT_FAIL_RE.search(log_content).group(0)  # type: ignore

    # Extract duration hint
    duration_hint = ""
    sim_time_match = _SIM_TIME_RE.search(log_content)
    if sim_time_match:
        duration_hint = sim_time_match.group(0)

    return SimLogSummary(
        status=status,
        uvm_info=info_count,
        uvm_warning=warning_count,
        uvm_error=error_count,
        uvm_fatal=fatal_count,
        finish_detected=finish_detected,
        test_pass_line=test_pass_line,
        duration_hint=duration_hint,
    )
