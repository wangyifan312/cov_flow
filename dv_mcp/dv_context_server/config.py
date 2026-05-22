"""DV Context MCP Server configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    """Configuration for the DV Context MCP Server."""

    # Maximum bytes for source snippet returns
    max_snippet_bytes: int = 8192

    # Maximum lines for source snippet returns
    max_snippet_lines: int = 200

    # Maximum results in list queries
    max_list_results: int = 50

    # Default project root (overridden by manifest)
    project_root: Path | None = None

    # Allowed projects (empty = allow all)
    allowed_projects: list[str] = field(default_factory=list)

    # Audit logging enabled
    audit_log: bool = True

    @classmethod
    def default(cls) -> ServerConfig:
        """Return default configuration."""
        return cls()
