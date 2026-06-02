"""Tests for lib.project_registry — project name → manifest path resolution."""

import os
from pathlib import Path

import pytest
import yaml

from lib.project_registry import ProjectRegistry, ProjectRegistryError


@pytest.fixture
def registry_file(tmp_path: Path) -> Path:
    """Create a temporary projects.yaml."""
    data = {
        "projects": {
            "test_project_a": {
                "manifest": "mock_data/project_a/manifest.yaml",
                "description": "Test project A",
            },
            "test_project_b": {
                "manifest": str(tmp_path / "data" / "manifest.yaml"),
                "description": "Test project B (absolute path)",
            },
        }
    }
    p = tmp_path / "projects.yaml"
    with open(p, "w") as f:
        yaml.dump(data, f)
    return p


@pytest.fixture
def env_registry(tmp_path: Path, registry_file: Path) -> Path:
    """Set COV_FLOW_PROJECTS env var pointing to registry_file."""
    os.environ["COV_FLOW_PROJECTS"] = str(registry_file)
    yield registry_file
    del os.environ["COV_FLOW_PROJECTS"]


class TestProjectRegistryLoad:
    def test_load_from_env(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        assert "test_project_a" in registry
        assert "env:COV_FLOW_PROJECTS" in registry.source

    def test_load_from_file(self, tmp_path: Path, registry_file: Path) -> None:
        registry = ProjectRegistry(base_dir=tmp_path)
        assert "test_project_a" in registry

    def test_empty_registry_when_no_file(self, tmp_path: Path) -> None:
        # Use a temp dir with no projects.yaml
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        # Clear env var to ensure no file found
        old = os.environ.pop("COV_FLOW_PROJECTS", None)
        try:
            registry = ProjectRegistry(base_dir=empty_dir)
            assert len(registry) == 0
            assert registry.source == "none"
        finally:
            if old is not None:
                os.environ["COV_FLOW_PROJECTS"] = old


class TestProjectRegistryResolve:
    def test_resolve_existing_project(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        manifest = registry.resolve("test_project_a")
        assert manifest.name == "manifest.yaml"
        assert manifest.is_absolute()

    def test_resolve_absolute_path_project(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        manifest = registry.resolve("test_project_b")
        assert manifest.is_absolute()

    def test_resolve_nonexistent_raises(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        with pytest.raises(FileNotFoundError, match="not found in registry"):
            registry.resolve("nonexistent_project")

    def test_error_lists_registered_projects(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        with pytest.raises(FileNotFoundError, match="test_project_a"):
            registry.resolve("missing")


class TestProjectRegistryList:
    def test_list_projects(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        projects = registry.list_projects()
        assert len(projects) == 2
        names = [p["name"] for p in projects]
        assert "test_project_a" in names
        assert "test_project_b" in names

    def test_list_projects_has_description(self, env_registry: Path) -> None:
        registry = ProjectRegistry()
        projects = registry.list_projects()
        descs = {p["name"]: p["description"] for p in projects}
        assert descs["test_project_a"] == "Test project A"


class TestProjectRegistryEdgeCases:
    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "projects.yaml"
        p.write_text("not: valid: yaml: [[[", encoding="utf-8")
        os.environ["COV_FLOW_PROJECTS"] = str(p)
        try:
            with pytest.raises(ProjectRegistryError):
                ProjectRegistry()
        finally:
            del os.environ["COV_FLOW_PROJECTS"]

    def test_non_mapping_yaml_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "projects.yaml"
        p.write_text("- item1\n- item2\n", encoding="utf-8")
        os.environ["COV_FLOW_PROJECTS"] = str(p)
        try:
            with pytest.raises(ProjectRegistryError):
                ProjectRegistry()
        finally:
            del os.environ["COV_FLOW_PROJECTS"]

    def test_missing_manifest_field_skipped(self, tmp_path: Path) -> None:
        data = {
            "projects": {
                "no_manifest": {"description": "Missing manifest field"},
                "has_manifest": {"manifest": "some/path.yaml"},
            }
        }
        p = tmp_path / "projects.yaml"
        with open(p, "w") as f:
            yaml.dump(data, f)
        os.environ["COV_FLOW_PROJECTS"] = str(p)
        try:
            registry = ProjectRegistry()
            assert "no_manifest" not in registry
            assert "has_manifest" in registry
        finally:
            del os.environ["COV_FLOW_PROJECTS"]
