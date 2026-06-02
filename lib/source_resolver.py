"""Bounded source snippet resolver with security boundaries.

Reads a bounded snippet from a source file within allowed directory roots.
Enforces path traversal protection, symlink checks, and byte/line limits.

Security:
- source_file must resolve under one of allowed_roots (after Path.resolve())
- Symlinks pointing outside allowed_roots are rejected
- Snippet bounded by max_lines and max_bytes
- Returns status='access_denied' or 'file_not_found' on failure
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceSnippet:
    """Result of a bounded source snippet read."""

    file: str
    """Relative path of the source file."""

    start_line: int
    """First line number of the snippet (1-based)."""

    end_line: int
    """Last line number of the snippet (1-based, inclusive)."""

    content: str
    """The snippet text."""

    truncated: bool = False
    """Whether the content was truncated due to max_bytes."""

    status: str = "ok"
    """One of: 'ok', 'file_not_found', 'access_denied', 'parse_error'."""

    message: str = ""
    """Human-readable status description."""


class SourceResolver:
    """Bounded source snippet resolver with strict security boundaries.

    Args:
        allowed_roots: Directories under which source files may be read.
        max_lines: Maximum number of lines in a snippet (default 40, max 100).
        max_bytes: Maximum byte size of snippet content (default 4096, max 16384).
    """

    MAX_LINES_LIMIT = 100
    MAX_BYTES_LIMIT = 16384

    def __init__(
        self,
        allowed_roots: list[Path],
        max_lines: int = 40,
        max_bytes: int = 4096,
    ) -> None:
        self._allowed_roots = [r.resolve() for r in allowed_roots]
        self._max_lines = min(max(1, max_lines), self.MAX_LINES_LIMIT)
        self._max_bytes = min(max(1, max_bytes), self.MAX_BYTES_LIMIT)

    @property
    def allowed_roots(self) -> list[Path]:
        """Return the resolved allowed root directories."""
        return list(self._allowed_roots)

    @property
    def max_lines(self) -> int:
        """Return the configured max lines."""
        return self._max_lines

    @property
    def max_bytes(self) -> int:
        """Return the configured max bytes."""
        return self._max_bytes

    def _is_under_allowed_root(self, resolved: Path) -> bool:
        """Check if a resolved path is under one of the allowed roots."""
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _find_allowed_root(self, resolved: Path) -> Path | None:
        """Find which allowed root contains the resolved path."""
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return root
            except ValueError:
                continue
        return None

    def resolve(
        self,
        source_file: str,
        source_line: int,
        context_lines: int = 5,
    ) -> SourceSnippet:
        """Read a bounded snippet from a source file.

        Args:
            source_file: Path to the source file (relative or absolute).
                If relative, it is resolved against each allowed root.
            source_line: The target line number (1-based).
            context_lines: Number of context lines before/after source_line.

        Returns:
            SourceSnippet with status 'ok' on success, or an error status.
        """
        # Reject obvious path traversal attempts in the raw string
        if ".." in source_file:
            return SourceSnippet(
                file=source_file,
                start_line=0,
                end_line=0,
                content="",
                status="access_denied",
                message="Path traversal detected: '..'  not allowed in source_file",
            )

        # Resolve the source file path
        raw_path = Path(source_file)

        if raw_path.is_absolute():
            # Absolute path: resolve and check
            try:
                resolved = raw_path.resolve(strict=False)
            except (OSError, ValueError):
                return SourceSnippet(
                    file=source_file,
                    start_line=0,
                    end_line=0,
                    content="",
                    status="access_denied",
                    message=f"Cannot resolve path: {source_file}",
                )
        else:
            # Relative path: try each allowed root, prefer root where file exists
            resolved = None
            for root in self._allowed_roots:
                candidate = (root / raw_path).resolve(strict=False)
                if candidate.is_file() and self._is_under_allowed_root(candidate):
                    resolved = candidate
                    break
            # If no existing file found, try first root for proper error reporting
            if resolved is None:
                for root in self._allowed_roots:
                    candidate = (root / raw_path).resolve(strict=False)
                    if self._is_under_allowed_root(candidate):
                        resolved = candidate
                        break
            if resolved is None:
                return SourceSnippet(
                    file=source_file,
                    start_line=0,
                    end_line=0,
                    content="",
                    status="access_denied",
                    message=f"Source file not under any allowed root: {source_file}",
                )

        # At this point resolved is guaranteed non-None
        assert resolved is not None  # for mypy

        # Security: check that the resolved path is under an allowed root
        if not self._is_under_allowed_root(resolved):
            return SourceSnippet(
                file=source_file,
                start_line=0,
                end_line=0,
                content="",
                status="access_denied",
                message=f"Resolved path escapes allowed roots: {resolved}",
            )

        # Security: check for symlink escape
        if resolved.is_symlink():
            real_target = resolved.resolve(strict=False)
            if not self._is_under_allowed_root(real_target):
                return SourceSnippet(
                    file=source_file,
                    start_line=0,
                    end_line=0,
                    content="",
                    status="access_denied",
                    message=f"Symlink escapes allowed roots: {source_file} -> {real_target}",
                )

        # Check file existence
        if not resolved.is_file():
            return SourceSnippet(
                file=source_file,
                start_line=0,
                end_line=0,
                content="",
                status="file_not_found",
                message=f"Source file not found: {source_file}",
            )

        # Read lines
        try:
            with open(resolved, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
        except OSError as e:
            return SourceSnippet(
                file=source_file,
                start_line=0,
                end_line=0,
                content="",
                status="parse_error",
                message=f"Cannot read file: {e}",
            )

        total_lines = len(all_lines)

        # Compute snippet range
        start = max(1, source_line - context_lines)
        end = min(total_lines, source_line + context_lines)

        # Also bound by max_lines
        if (end - start + 1) > self._max_lines:
            end = start + self._max_lines - 1
            if end > total_lines:
                end = total_lines
                start = max(1, end - self._max_lines + 1)

        # Extract snippet lines (convert 1-based to 0-based indexing)
        snippet_lines = all_lines[start - 1: end]
        content = "".join(snippet_lines)

        # Byte truncation
        truncated = False
        encoded = content.encode("utf-8")
        if len(encoded) > self._max_bytes:
            content = encoded[: self._max_bytes].decode("utf-8", errors="ignore")
            content += "\n... [truncated]"
            truncated = True

        # Compute relative path for display
        matched_root = self._find_allowed_root(resolved)
        if matched_root is not None:
            try:
                display_path = str(resolved.relative_to(matched_root))
            except ValueError:
                display_path = source_file
        else:
            display_path = source_file

        return SourceSnippet(
            file=display_path,
            start_line=start,
            end_line=end,
            content=content,
            truncated=truncated,
            status="ok",
            message=f"Read {end - start + 1} lines from {display_path}:{start}-{end}",
        )
