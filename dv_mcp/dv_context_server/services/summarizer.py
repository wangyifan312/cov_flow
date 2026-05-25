"""Result summarization and truncation.

Ensures MCP tool returns stay within the context budget.
"""

from __future__ import annotations

from typing import Any


def truncate_text(text: str, max_bytes: int = 4096) -> tuple[str, bool]:
    """Truncate text to a maximum byte size.

    Returns:
        Tuple of (truncated_text, was_truncated).
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated + "\n... [truncated]", True


def truncate_list(items: list[Any], max_items: int = 50) -> tuple[list[Any], bool]:
    """Truncate a list to a maximum number of items.

    Returns:
        Tuple of (truncated_list, was_truncated).
    """
    if len(items) <= max_items:
        return items, False
    return items[:max_items], True


def envelope(
    tool: str,
    project: str,
    result: Any,
    evidence: list[dict[str, Any]],
    truncated: bool = False,
    next_actions: list[str] | None = None,
    audit: dict[str, Any] | None = None,
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the standard MCP tool response envelope.

    All MCP tools return this format for consistency and traceability.
    """
    resp: dict[str, Any] = {
        "ok": True,
        "tool": tool,
        "project": project,
        "result": result,
        "evidence": evidence,
        "truncated": truncated,
        "next_actions": next_actions or [],
    }
    if audit is not None:
        resp["audit"] = audit
    if safety is not None:
        resp["safety"] = safety
    return resp


def error_envelope(
    tool: str,
    project: str,
    error: str,
) -> dict[str, Any]:
    """Build an error response envelope."""
    return {
        "ok": False,
        "tool": tool,
        "project": project,
        "error": error,
        "evidence": [],
        "truncated": False,
        "next_actions": [],
    }
