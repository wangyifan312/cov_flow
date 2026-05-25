"""JSON index file readers.

Provides a unified interface for reading pre-built index files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class IndexNotFoundError(FileNotFoundError):
    """Raised when a required index file does not exist."""


class IndexReader:
    """Reads and caches JSON index files."""

    def __init__(self, index_dir: Path) -> None:
        self._index_dir = index_dir
        self._cache: dict[str, Any] = {}

    @property
    def index_dir(self) -> Path:
        return self._index_dir

    def read(self, index_name: str) -> dict[str, Any]:
        """Read a JSON index file by name (e.g. 'coverage_index.json').

        Results are cached after first read.

        Raises:
            IndexNotFoundError: If the index file does not exist.
        """
        if index_name in self._cache:
            return dict(self._cache[index_name])

        path = self._index_dir / index_name
        if not path.exists():
            raise IndexNotFoundError(f"Index file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        self._cache[index_name] = data
        return data

    def clear_cache(self) -> None:
        """Clear the read cache."""
        self._cache.clear()

    def available_indexes(self) -> list[str]:
        """List available index files in the index directory."""
        if not self._index_dir.exists():
            return []
        return sorted(p.name for p in self._index_dir.iterdir() if p.suffix == ".json")
