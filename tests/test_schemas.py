"""Tests for JSON Schema definitions."""

from pathlib import Path

import pytest

from lib.schema_validator import load_schema, validate

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


@pytest.fixture
def valid_gap() -> dict:
    """A minimal valid coverage gap."""
    return {
        "gap_id": "GAP_0001",
        "coverage_type": "functional",
        "covergroup": "dma_desc_cg",
        "coverpoint": "desc_mode_cp",
        "bin": "linked_list",
        "hit_count": 0,
        "goal": 1,
    }


@pytest.fixture
def valid_scenario_card() -> dict:
    """A minimal valid scenario card."""
    return {
        "gap_id": "GAP_0001",
        "target_coverage": {
            "covergroup": "dma_desc_cg",
            "coverpoint": "desc_mode_cp",
            "bin": "linked_list",
        },
        "classification": "Config Missing",
        "semantic_interpretation": "Linked-list mode requires enabling DMA_CFG.LL_MODE_EN.",
        "required_config": [
            {"register": "DMA_CFG.LL_MODE_EN", "value": 1}
        ],
        "stimulus": [
            "Enable linked-list mode", "Build two linked descriptors", "Start DMA channel",
        ],
        "expected_behavior": ["Parser enters LINK_DESC state", "Next descriptor fetched"],
        "confidence": "medium",
    }


@pytest.fixture
def valid_patch() -> dict:
    """A minimal valid testcase patch."""
    return {
        "patch_id": "PATCH_GAP_0001_001",
        "gap_id": "GAP_0001",
        "new_files": ["tb/sequences/dma_ll_desc_seq.sv"],
        "modified_files": [],
        "base_reuse": {"base_test": "dma_base_test"},
        "compile_command": "make compile TEST=dma_ll_desc_test",
        "run_command": "make run TEST=dma_ll_desc_test SEED=1",
        "coverage_target": ["dma_desc_cg.desc_mode_cp.linked_list"],
        "review_checklist": ["Confirm RAL path for LL_MODE_EN"],
    }


class TestCoverageGapSchema:
    """Tests for coverage_gap.schema.json."""

    def test_valid_minimal_gap(self, valid_gap: dict) -> None:
        schema = load_schema("coverage_gap.schema.json")
        errors = validate(valid_gap, schema, raise_on_error=False)
        assert errors == []

    def test_valid_full_gap(self, valid_gap: dict) -> None:
        valid_gap.update({
            "source_file": "tb/cov/dma_cov.sv",
            "source_line": 88,
            "cluster_id": "dma_desc_mode",
            "classification": "Config Missing",
            "priority": "P0",
            "related_register": "DMA_CFG.LL_MODE_EN",
            "related_spec_section": "spec_dma_linked_list",
            "related_rtl_signal": "u_dma.u_desc_parser.ll_mode_en",
        })
        schema = load_schema("coverage_gap.schema.json")
        errors = validate(valid_gap, schema, raise_on_error=False)
        assert errors == []

    def test_null_related_fields_allowed(self, valid_gap: dict) -> None:
        valid_gap["related_register"] = None
        valid_gap["related_spec_section"] = None
        valid_gap["related_rtl_signal"] = None
        schema = load_schema("coverage_gap.schema.json")
        errors = validate(valid_gap, schema, raise_on_error=False)
        assert errors == []

    def test_invalid_gap_id_format(self, valid_gap: dict) -> None:
        valid_gap["gap_id"] = "gap_001"  # Wrong format
        schema = load_schema("coverage_gap.schema.json")
        errors = validate(valid_gap, schema, raise_on_error=False)
        assert any("gap_id" in e["path"] for e in errors)

    def test_invalid_classification(self, valid_gap: dict) -> None:
        valid_gap["classification"] = "Unknown Type"
        schema = load_schema("coverage_gap.schema.json")
        errors = validate(valid_gap, schema, raise_on_error=False)
        assert any("classification" in e["path"] for e in errors)

    def test_missing_required_field(self) -> None:
        schema = load_schema("coverage_gap.schema.json")
        errors = validate({"gap_id": "GAP_0001"}, schema, raise_on_error=False)
        assert len(errors) > 0


class TestScenarioCardSchema:
    """Tests for scenario_card.schema.json."""

    def test_valid_card(self, valid_scenario_card: dict) -> None:
        schema = load_schema("scenario_card.schema.json")
        errors = validate(valid_scenario_card, schema, raise_on_error=False)
        assert errors == []

    def test_with_all_optional_fields(self, valid_scenario_card: dict) -> None:
        valid_scenario_card["tb_reuse"] = {
            "base_test": "dma_base_test",
            "candidate_sequence": "dma_desc_base_seq",
        }
        valid_scenario_card["risk"] = ["Confirm LL_MODE_EN in current build"]
        schema = load_schema("scenario_card.schema.json")
        errors = validate(valid_scenario_card, schema, raise_on_error=False)
        assert errors == []

    def test_empty_stimulus_rejected(self, valid_scenario_card: dict) -> None:
        valid_scenario_card["stimulus"] = []
        schema = load_schema("scenario_card.schema.json")
        errors = validate(valid_scenario_card, schema, raise_on_error=False)
        assert any("stimulus" in e["path"] for e in errors)

    def test_invalid_confidence(self, valid_scenario_card: dict) -> None:
        valid_scenario_card["confidence"] = "super_high"
        schema = load_schema("scenario_card.schema.json")
        errors = validate(valid_scenario_card, schema, raise_on_error=False)
        assert any("confidence" in e["path"] for e in errors)


class TestTestcasePatchSchema:
    """Tests for testcase_patch.schema.json."""

    def test_valid_patch(self, valid_patch: dict) -> None:
        schema = load_schema("testcase_patch.schema.json")
        errors = validate(valid_patch, schema, raise_on_error=False)
        assert errors == []

    def test_invalid_patch_id(self, valid_patch: dict) -> None:
        valid_patch["patch_id"] = "patch_001"
        schema = load_schema("testcase_patch.schema.json")
        errors = validate(valid_patch, schema, raise_on_error=False)
        assert any("patch_id" in e["path"] for e in errors)

    def test_empty_coverage_target_rejected(self, valid_patch: dict) -> None:
        valid_patch["coverage_target"] = []
        schema = load_schema("testcase_patch.schema.json")
        errors = validate(valid_patch, schema, raise_on_error=False)
        assert any("coverage_target" in e["path"] for e in errors)

    def test_empty_review_checklist_rejected(self, valid_patch: dict) -> None:
        valid_patch["review_checklist"] = []
        schema = load_schema("testcase_patch.schema.json")
        errors = validate(valid_patch, schema, raise_on_error=False)
        assert any("review_checklist" in e["path"] for e in errors)


class TestProjectManifestSchema:
    """Tests for project_manifest.schema.json (existing schema)."""

    def test_schema_loads(self) -> None:
        schema = load_schema("project_manifest.schema.json")
        assert "properties" in schema
        assert "project" in schema["properties"]
