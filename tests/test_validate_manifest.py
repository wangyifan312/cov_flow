"""Tests for manifest validation."""

from pathlib import Path

import pytest

from lib.manifest import Manifest, ManifestError
from lib.schema_validator import load_schema, validate


class TestManifestLoading:
    """Tests for Manifest.load()."""

    def test_load_valid_manifest(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.project == "dma_subsystem"
        assert manifest.top_instance == "tb_top.u_dut.u_dma"

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestError, match="not found"):
            Manifest.load(tmp_path / "nonexistent.yaml")

    def test_load_directory_as_manifest(self, mock_data_dir: Path) -> None:
        with pytest.raises(ManifestError, match="not a file"):
            Manifest.load(mock_data_dir)

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{invalid yaml content:::", encoding="utf-8")
        with pytest.raises(ManifestError, match="Failed to parse YAML"):
            Manifest.load(bad_yaml)

    def test_load_non_mapping_yaml(self, tmp_path: Path) -> None:
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ManifestError, match="must be a YAML mapping"):
            Manifest.load(list_yaml)


class TestManifestPathResolution:
    """Tests for path resolution against manifest base directory."""

    def test_resolve_relative_path(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        resolved = manifest.resolve_path("coverage/urg_report")
        assert resolved is not None
        assert resolved == mock_manifest_path.parent / "coverage" / "urg_report"

    def test_resolve_absolute_path(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        resolved = manifest.resolve_path("/absolute/path/to/something")
        assert resolved == Path("/absolute/path/to/something")

    def test_resolve_none(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.resolve_path(None) is None

    def test_resolve_empty_string(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.resolve_path("") is None

    def test_get_nested_value(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.get("coverage", "format") == "urg_html"
        assert manifest.get("policy", "allow_direct_file_modification") is False

    def test_get_missing_value(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.get("nonexistent", "key") is None
        assert manifest.get("nonexistent", "key", default="fallback") == "fallback"

    def test_get_path(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        path = manifest.get_path("coverage", "reports_root")
        assert path is not None
        assert path.name == "urg_report"

    def test_get_all_data_paths(self, mock_manifest_path: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        all_paths = manifest.get_all_data_paths()
        assert "coverage.reports_root" in all_paths
        assert "rtl.filelist" in all_paths
        assert "registers.source.path" in all_paths


class TestSchemaValidation:
    """Tests for schema validation of the mock manifest."""

    def test_schema_loads(self, schemas_dir: Path) -> None:
        schema = load_schema("project_manifest.schema.json", schemas_dir)
        assert schema["title"] == "DV Project Manifest"

    def test_mock_manifest_validates(self, mock_manifest_path: Path, schemas_dir: Path) -> None:
        manifest = Manifest.load(mock_manifest_path)
        schema = load_schema("project_manifest.schema.json", schemas_dir)
        errors = validate(manifest.data, schema, raise_on_error=False)
        assert errors == [], f"Unexpected validation errors: {errors}"

    def test_missing_required_field(self, schemas_dir: Path) -> None:
        schema = load_schema("project_manifest.schema.json", schemas_dir)
        incomplete_data = {"project": "test"}  # missing many required fields
        errors = validate(incomplete_data, schema, raise_on_error=False)
        assert len(errors) > 0

    def test_invalid_policy_type(self, schemas_dir: Path) -> None:
        schema = load_schema("project_manifest.schema.json", schemas_dir)
        bad_data = {
            "project": "test",
            "top_instance": "tb_top",
            "coverage": {
                "reports_root": "/tmp/cov",
                "coverage_model_root": "/tmp/cov_model",
            },
            "rtl": {"filelist": "/tmp/rtl.f"},
            "registers": {
                "source": {"type": "yaml", "path": "/tmp/regs.yaml"},
            },
            "testbench": {"type": "uvm", "env_root": "/tmp/tb"},
            "policy": {
                "allow_direct_file_modification": "yes",  # should be bool
                "allow_running_simulation": True,
                "require_human_review_before_commit": True,
            },
        }
        errors = validate(bad_data, schema, raise_on_error=False)
        assert any("allow_direct_file_modification" in e["path"] for e in errors)


class TestProjectRoot:
    """Tests for the project_root property and path resolution."""

    def test_project_root_from_manifest_field(self, tmp_path: Path) -> None:
        """When project_root is set, paths resolve against it."""
        project_dir = tmp_path / "real_project"
        project_dir.mkdir()
        manifest_file = tmp_path / "manifest_dir" / "project_manifest.yaml"
        manifest_file.parent.mkdir()
        manifest_file.write_text(
            f"project: test\n"
            f"top_instance: tb_top\n"
            f"project_root: {project_dir}\n"
            f"coverage:\n"
            f"  reports_root: cov_reports\n"
            f"  coverage_model_root: cov_model\n"
            f"rtl:\n"
            f"  filelist: rtl.f\n"
            f"registers:\n"
            f"  source:\n"
            f"    type: none\n"
            f"testbench:\n"
            f"  type: uvm\n"
            f"  env_root: env\n"
            f"policy:\n"
            f"  allow_direct_file_modification: false\n"
            f"  allow_running_simulation: false\n"
            f"  require_human_review_before_commit: true\n",
            encoding="utf-8",
        )
        manifest = Manifest.load(manifest_file)
        assert manifest.project_root == project_dir
        # resolve_path uses project_root, not manifest parent
        resolved = manifest.resolve_path("rtl.f")
        assert resolved == project_dir / "rtl.f"

    def test_project_root_fallback_to_base_dir(self, mock_manifest_path: Path) -> None:
        """When project_root is not set, falls back to base_dir (manifest parent)."""
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.project_root == mock_manifest_path.parent

    def test_project_root_env_var_expansion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables in project_root are expanded."""
        project_dir = tmp_path / "env_project"
        project_dir.mkdir()
        monkeypatch.setenv("TEST_PROJECT_ROOT", str(project_dir))

        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "project: test\n"
            "top_instance: tb_top\n"
            "project_root: $TEST_PROJECT_ROOT\n"
            "coverage:\n"
            "  reports_root: cov\n"
            "  coverage_model_root: cov\n"
            "rtl:\n"
            "  filelist: rtl.f\n"
            "registers:\n"
            "  source:\n"
            "    type: none\n"
            "testbench:\n"
            "  type: uvm\n"
            "  env_root: env\n"
            "policy:\n"
            "  allow_direct_file_modification: false\n"
            "  allow_running_simulation: false\n"
            "  require_human_review_before_commit: true\n",
            encoding="utf-8",
        )
        manifest = Manifest.load(manifest_file)
        assert manifest.project_root == project_dir
        resolved = manifest.resolve_path("rtl.f")
        assert resolved == project_dir / "rtl.f"

    def test_dma_subsystem_no_project_root(self, mock_manifest_path: Path) -> None:
        """dma_subsystem has no project_root — base_dir is used, backward compatible."""
        manifest = Manifest.load(mock_manifest_path)
        assert manifest.project_root == mock_manifest_path.parent
        # Verify get_path still resolves correctly
        reports = manifest.get_path("coverage", "reports_root")
        assert reports is not None
        assert reports == mock_manifest_path.parent / "coverage" / "urg_report"
