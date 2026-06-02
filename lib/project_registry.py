"""Project registry: resolves project names to manifest paths.

Search order:
1. COV_FLOW_PROJECTS environment variable (path to projects.yaml)
2. ./projects.yaml (current working directory or repo root)
3. ~/.cov_flow/projects.yaml (user home directory)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class ProjectRegistryError(Exception):
    """Raised when the project registry cannot be loaded or queried."""


class ProjectRegistry:
    """Resolves project names to manifest paths via projects.yaml."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._projects: dict[str, dict[str, Any]] = {}
        self._source: str = "none"
        self._base_dir = base_dir
        self._load()

    def _load(self) -> None:
        """Load projects from the first available source."""
        # 1. COV_FLOW_PROJECTS environment variable
        env_path = os.environ.get("COV_FLOW_PROJECTS")
        if env_path:
            p = Path(env_path)
            if p.is_file():
                self._load_from_file(p, source=f"env:COV_FLOW_PROJECTS={env_path}")
                return

        # 2. ./projects.yaml (try base_dir if set, otherwise cwd)
        search_dir = self._base_dir if self._base_dir is not None else Path.cwd()
        candidate = search_dir / "projects.yaml"
        if candidate.is_file():
            self._load_from_file(candidate, source=str(candidate))
            return

        # 3. ~/.cov_flow/projects.yaml
        home_candidate = Path.home() / ".cov_flow" / "projects.yaml"
        if home_candidate.is_file():
            self._load_from_file(home_candidate, source=str(home_candidate))
            return

        # No registry found — empty registry is valid (graceful degradation)
        self._source = "none"

    def _load_from_file(self, path: Path, source: str) -> None:
        """Load projects from a YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except (yaml.YAMLError, OSError) as e:
            raise ProjectRegistryError(
                f"Failed to load project registry from {path}: {e}"
            ) from e

        if not isinstance(data, dict):
            raise ProjectRegistryError(
                f"Project registry must be a YAML mapping, got {type(data).__name__}"
            )

        projects = data.get("projects", {})
        if not isinstance(projects, dict):
            raise ProjectRegistryError(
                f"'projects' field must be a mapping, got {type(projects).__name__}"
            )

        self._projects = {}
        base = path.parent
        for name, info in projects.items():  # noqa: B007
            if not isinstance(info, dict):
                continue
            manifest_rel = info.get("manifest")
            if not manifest_rel:
                continue
            manifest_path = Path(manifest_rel)
            if not manifest_path.is_absolute():
                manifest_path = base / manifest_path
            self._projects[str(name)] = {
                "manifest": manifest_path.resolve(),
                "description": str(info.get("description", "")),
            }
        self._source = source

    @property
    def source(self) -> str:
        """Return the source description of the loaded registry."""
        return self._source

    def resolve(self, project_name: str) -> Path:
        """Resolve a project name to its manifest path.

        Args:
            project_name: The project identifier (e.g. 'dma_subsystem').

        Returns:
            Resolved Path to the project_manifest.yaml file.

        Raises:
            FileNotFoundError: If the project name is not registered.
        """
        entry = self._projects.get(project_name)
        if entry is None:
            available = ", ".join(sorted(self._projects.keys())) or "(none)"
            raise FileNotFoundError(
                f"Project '{project_name}' not found in registry. "
                f"Registered projects: {available}"
            )
        return Path(str(entry["manifest"]))

    def list_projects(self) -> list[dict[str, str]]:
        """List all registered projects with their descriptions."""
        result = []
        for name, info in sorted(self._projects.items()):
            result.append({
                "name": name,
                "manifest": str(info["manifest"]),
                "description": info.get("description", ""),
            })
        return result

    def __contains__(self, project_name: str) -> bool:
        return project_name in self._projects

    def __len__(self) -> int:
        return len(self._projects)
