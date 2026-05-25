"""Audit logging for MCP tool calls.

Records tool call metadata for traceability and compliance.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def audit_record(
    tool: str,
    project: str,
    arguments: dict[str, Any],
    result_size: int = 0,
) -> dict[str, Any]:
    """Create an audit record for a tool call.

    Args:
        tool: The tool name.
        project: The project identifier.
        arguments: The tool call arguments (will be hashed).
        result_size: Size of the result in bytes.

    Returns:
        An audit record dict with 5 required fields.
    """
    arg_json = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
    arg_hash = hashlib.sha256(arg_json.encode("utf-8")).hexdigest()[:16]

    return {
        "user": "mock_user",
        "project": project,
        "tool": tool,
        "arg_hash": arg_hash,
        "timestamp": datetime.now(UTC).isoformat(),
        "result_size": result_size,
    }
