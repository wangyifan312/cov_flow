"""Project loading: resolves manifest to index paths and provides IndexReaders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.index_paths import INDEX_DIR_NAME
from lib.manifest import Manifest

from dv_mcp.dv_context_server.indexes.readers import IndexReader


# Global registry of loaded projects
_project_cache: dict[str, "_ProjectContext"] = {}


class _ProjectContext:
    """Internal container for a loaded project's context."""

    def __init__(self, manifest: Manifest, index_reader: IndexReader) -> None:
        self.manifest = manifest
        self.index_reader = index_reader


def resolve_project(project_id_or_path: str) -> _ProjectContext:
    """Resolve a project identifier to a ProjectContext.

    Args:
        project_id_or_path: Either a project ID (looked up in known projects)
            or a direct path to a project_manifest.yaml file.

    Returns:
        A _ProjectContext with loaded manifest and index reader.

    Raises:
        FileNotFoundError: If the manifest or index directory cannot be found.
    """
    if project_id_or_path in _project_cache:
        return _project_cache[project_id_or_path]

    # Try as direct manifest path
    manifest_path = Path(project_id_or_path)
    if manifest_path.is_file():
        manifest = Manifest.load(manifest_path)
    else:
        raise FileNotFoundError(
            f"Cannot resolve project '{project_id_or_path}'. "
            "Provide a path to a project_manifest.yaml file."
        )

    # Find index directory
    project_root = manifest.base_dir
    index_dir = project_root / INDEX_DIR_NAME
    if not index_dir.exists():
        raise FileNotFoundError(
            f"Index directory not found: {index_dir}. "
            "Run 'make build-indexes' to generate indexes."
        )

    reader = IndexReader(index_dir)
    ctx = _ProjectContext(manifest, reader)
    _project_cache[project_id_or_path] = ctx
    _project_cache[manifest.project] = ctx  # Also cache by project ID
    return ctx


def get_index_reader(project: str) -> IndexReader:
    """Get the IndexReader for a project. Convenience shortcut."""
    return resolve_project(project).index_reader


def get_manifest(project: str) -> Manifest:
    """Get the Manifest for a project. Convenience shortcut."""
    return resolve_project(project).manifest


def clear_cache() -> None:
    """Clear the project cache. Useful for testing."""
    _project_cache.clear()
