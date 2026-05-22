"""Manifest loading and path resolution.

Loads a project_manifest.yaml, resolves relative paths against the manifest's
own directory, and provides typed access to manifest fields.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ManifestError(Exception):
    """Raised when a manifest cannot be loaded or has invalid content."""


class Manifest:
    """Parsed and resolved project manifest.

    All path fields are resolved relative to the manifest file's parent directory.
    """

    def __init__(self, data: dict[str, Any], manifest_path: Path) -> None:
        self._data = data
        self._manifest_path = manifest_path.resolve()
        self._base_dir = self._manifest_path.parent

    @classmethod
    def load(cls, path: str | Path) -> Manifest:
        """Load a manifest from a YAML file.

        Args:
            path: Path to the project_manifest.yaml file.

        Returns:
            A Manifest instance with resolved paths.

        Raises:
            ManifestError: If the file cannot be read or parsed.
        """
        path = Path(path)
        if not path.exists():
            raise ManifestError(f"Manifest file not found: {path}")
        if not path.is_file():
            raise ManifestError(f"Manifest path is not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ManifestError(f"Failed to parse YAML: {e}") from e

        if not isinstance(data, dict):
            raise ManifestError(f"Manifest must be a YAML mapping, got {type(data).__name__}")

        return cls(data, path)

    @property
    def data(self) -> dict[str, Any]:
        """Return the raw manifest data."""
        return self._data

    @property
    def manifest_path(self) -> Path:
        """Return the resolved path to the manifest file."""
        return self._manifest_path

    @property
    def base_dir(self) -> Path:
        """Return the base directory (parent of manifest file)."""
        return self._base_dir

    @property
    def project(self) -> str:
        """Return the project identifier."""
        return self._data.get("project", "")

    @property
    def top_instance(self) -> str:
        """Return the top-level DUT instance path."""
        return self._data.get("top_instance", "")

    def resolve_path(self, path_str: str | None) -> Path | None:
        """Resolve a path string from the manifest against the base directory.

        Supports environment variable expansion (e.g. $PROJ_ROOT or ${PROJ_ROOT}).

        Returns None if path_str is None or empty.
        """
        if not path_str:
            return None
        # Expand environment variables
        expanded = os.path.expandvars(str(path_str))
        p = Path(expanded)
        if p.is_absolute():
            return p
        return self._base_dir / p

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested value from the manifest data.

        Example: manifest.get("coverage", "reports_root")
        """
        current: Any = self._data
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key, default)
            if current is default:
                return default
        return current

    def get_path(self, *keys: str) -> Path | None:
        """Get a nested path value and resolve it against the base directory.

        Example: manifest.get_path("coverage", "reports_root")
        """
        value = self.get(*keys)
        if value is None:
            return None
        return self.resolve_path(str(value))

    def get_all_data_paths(self) -> dict[str, Path | None]:
        """Return all configured data paths with their labels.

        Used by validate_manifest.py to check path existence.
        """
        paths: dict[str, Path | None] = {}

        path_fields = [
            ("coverage.reports_root", ("coverage", "reports_root")),
            ("coverage.coverage_model_root", ("coverage", "coverage_model_root")),
            ("rtl.filelist", ("rtl", "filelist")),
            ("rtl.design_db.path", ("rtl", "design_db", "path")),
            ("rtl.index_path", ("rtl", "index_path")),
            ("spec.fs.path", ("spec", "fs", "path")),
            ("spec.fs.index_path", ("spec", "fs", "index_path")),
            ("spec.micro_arch.path", ("spec", "micro_arch", "path")),
            ("spec.micro_arch.index_path", ("spec", "micro_arch", "index_path")),
            ("registers.source.path", ("registers", "source", "path")),
            ("registers.ral_root", ("registers", "ral_root")),
            ("registers.index_path", ("registers", "index_path")),
            ("testbench.env_root", ("testbench", "env_root")),
            ("testbench.sequence_root", ("testbench", "sequence_root")),
            ("testbench.index_path", ("testbench", "index_path")),
        ]

        for label, keys in path_fields:
            paths[label] = self.get_path(*keys)

        return paths
