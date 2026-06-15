"""Tests for generate_mock_index.py script."""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MOCK_MANIFEST = PROJECT_ROOT / "mock_data" / "dma_subsystem" / "project_manifest.yaml"
INDEX_DIR = PROJECT_ROOT / "mock_data" / "dma_subsystem" / ".dv_ai_index"

EXPECTED_INDEXES = [
    "coverage_index.json",
    "spec_index.json",
    "reg_db.json",
    "rtl_index.json",
    "tb_index.json",
]


class TestGenerateMockIndex:
    """Tests for the mock index generation script."""

    def test_generates_all_indexes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_mock_index.py"),
             "--manifest", str(MOCK_MANIFEST)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        for idx_name in EXPECTED_INDEXES:
            idx_path = INDEX_DIR / idx_name
            assert idx_path.exists(), f"Missing index: {idx_path}"

    def test_coverage_index_structure(self) -> None:
        data = json.loads((INDEX_DIR / "coverage_index.json").read_text())
        assert data["project"] == "dma_subsystem"
        assert "gaps" in data
        assert len(data["gaps"]) == 27
        assert "clusters" in data

    def test_code_coverage_gaps_present(self) -> None:
        """Code coverage gaps should be in the coverage index."""
        data = json.loads((INDEX_DIR / "coverage_index.json").read_text())
        gap_ids = [g["gap_id"] for g in data["gaps"]]
        for code_gap_id in ["GAP_L001", "GAP_B001", "GAP_C001", "GAP_T001", "GAP_M001", "GAP_A001"]:
            assert code_gap_id in gap_ids, f"Missing code coverage gap: {code_gap_id}"

    def test_code_coverage_gap_has_type(self) -> None:
        """Code coverage gaps should have coverage_type field."""
        data = json.loads((INDEX_DIR / "coverage_index.json").read_text())
        gap_l001 = next(g for g in data["gaps"] if g["gap_id"] == "GAP_L001")
        assert gap_l001["coverage_type"] == "line"
        gap_m001 = next(g for g in data["gaps"] if g["gap_id"] == "GAP_M001")
        assert gap_m001["coverage_type"] == "fsm"

    def test_spec_index_structure(self) -> None:
        data = json.loads((INDEX_DIR / "spec_index.json").read_text())
        assert "sections" in data
        assert len(data["sections"]) > 0
        for section in data["sections"]:
            assert "section_id" in section
            assert "title" in section
            assert "feature_tags" in section

    def test_reg_db_structure(self) -> None:
        data = json.loads((INDEX_DIR / "reg_db.json").read_text())
        assert "registers" in data
        assert len(data["registers"]) > 0
        for reg in data["registers"]:
            assert "register" in reg
            assert "fields" in reg

    def test_rtl_index_structure(self) -> None:
        data = json.loads((INDEX_DIR / "rtl_index.json").read_text())
        assert "modules" in data
        assert "hierarchy" in data
        assert len(data["modules"]) > 0
        for mod in data["modules"]:
            assert "name" in mod
            assert "file" in mod

    def test_tb_index_structure(self) -> None:
        data = json.loads((INDEX_DIR / "tb_index.json").read_text())
        assert "base_tests" in data
        assert "sequences" in data
        assert "existing_tests" in data
        assert "config_knobs" in data
        assert len(data["base_tests"]) > 0

    def test_traceable_gap_chain(self) -> None:
        """Verify that GAP_0001 (linked_list) has a full evidence chain across all indexes."""
        cov = json.loads((INDEX_DIR / "coverage_index.json").read_text())
        spec = json.loads((INDEX_DIR / "spec_index.json").read_text())
        reg = json.loads((INDEX_DIR / "reg_db.json").read_text())
        rtl = json.loads((INDEX_DIR / "rtl_index.json").read_text())
        tb = json.loads((INDEX_DIR / "tb_index.json").read_text())

        # GAP_0001 exists
        gap = next(g for g in cov["gaps"] if g["gap_id"] == "GAP_0001")
        assert gap["bin"] == "linked_list"

        # Related spec section exists
        spec_section = next(
            s for s in spec["sections"]
            if s["section_id"] == "spec_linked_list_descriptor_mode"
        )
        assert "linked_list" in spec_section["feature_tags"]

        # Related register field exists
        reg_field = None
        for r in reg["registers"]:
            for f in r["fields"]:
                if f["field"] == "LL_MODE_EN":
                    reg_field = f
                    break
        assert reg_field is not None
        assert "linked_list" in reg_field["feature_tags"]

        # Related RTL signal exists
        parser_mod = next(m for m in rtl["modules"] if m["name"] == "dma_desc_parser")
        sig_names = [s["name"] for s in parser_mod["signals"]] + parser_mod["ports"]
        assert "ll_mode_en" in sig_names

        # Related TB sequence exists
        desc_seq = next(s for s in tb["sequences"] if s["name"] == "dma_desc_base_seq")
        assert "linked_list" in desc_seq["feature_tags"]
