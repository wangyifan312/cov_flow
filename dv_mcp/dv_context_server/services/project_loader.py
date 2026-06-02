"""Project loading: resolves manifest to index paths and provides IndexReaders."""

from __future__ import annotations

from pathlib import Path

from dv_mcp.dv_context_server.indexes.readers import IndexReader
from lib.index_paths import INDEX_DIR_NAME
from lib.manifest import Manifest
from lib.project_registry import ProjectRegistry

# Global registry of loaded projects
_project_cache: dict[str, _ProjectContext] = {}

# Global project registry (lazy-initialized)
_registry: ProjectRegistry | None = None


def _get_registry() -> ProjectRegistry:
    """Get or create the global ProjectRegistry instance."""
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry


class _ProjectContext:
    """Internal container for a loaded project's context."""

    def __init__(self, manifest: Manifest, index_reader: IndexReader) -> None:
        self.manifest = manifest
        self.index_reader = index_reader


def resolve_project(project_id_or_path: str) -> _ProjectContext:
    """Resolve a project identifier to a ProjectContext.

    Resolution order:
    1. Check the project cache
    2. Try as a project name via ProjectRegistry
    3. Try as a direct manifest path
    4. Raise FileNotFoundError with registered project list

    Args:
        project_id_or_path: Either a project name (looked up in registry)
            or a direct path to a project_manifest.yaml file.

    Returns:
        A _ProjectContext with loaded manifest and index reader.

    Raises:
        FileNotFoundError: If the project cannot be resolved.
    """
    if project_id_or_path in _project_cache:
        return _project_cache[project_id_or_path]

    manifest_path: Path | None = None

    # Try as project name via registry
    registry = _get_registry()
    if project_id_or_path in registry:
        try:
            manifest_path = registry.resolve(project_id_or_path)
        except FileNotFoundError:
            manifest_path = None

    # Fallback: try as direct manifest path
    if manifest_path is None:
        direct = Path(project_id_or_path)
        if direct.is_file():
            manifest_path = direct

    # If still not found, raise with helpful error
    if manifest_path is None:
        projects = registry.list_projects()
        available = ", ".join(p["name"] for p in projects) if projects else "(none)"
        raise FileNotFoundError(
            f"Cannot resolve project '{project_id_or_path}'. "
            f"Registered projects: {available}. "
            "Or provide a direct path to a project_manifest.yaml file."
        )

    manifest = Manifest.load(manifest_path)

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
    """Clear the project cache and reset the registry. Useful for testing."""
    global _registry
    _project_cache.clear()
    _registry = None
