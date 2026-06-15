"""Integration tests for the 3 source indexers (Phase 6B).

Tests build_spec_index.py, build_reg_index.py, and build_rtl_index.py
using the dma_subsystem mock project.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parent.parent
    / "mock_data" / "dma_subsystem" / "project_manifest.yaml"
)
PROJECT_ROOT = Path(__file__).parent.parent


def _run_indexer(script: str, tmp_path: Path) -> tuple[dict, str]:
    """Run an indexer script and return (parsed_json, stdout)."""
    out_dir = tmp_path / f"{script}_out"
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / script),
            "--manifest",
            str(MANIFEST_PATH),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        env={**os.environ},
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"{script} failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Determine output filename from script name
    filename_map = {
        "build_spec_index.py": "spec_index.json",
        "build_reg_index.py": "reg_db.json",
        "build_rtl_index.py": "rtl_index.json",
    }
    out_file = out_dir / filename_map[script]
    assert out_file.exists(), f"Output file not found: {out_file}"
    with open(out_file, encoding="utf-8") as f:
        return json.load(f), result.stdout


# ===========================================================================
# build_spec_index.py tests
# ===========================================================================


class TestBuildSpecIndex:
    def test_schema_version(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        assert data["schema_version"] == "spec_index.v1"

    def test_source_field(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        assert data["source"] == "spec/dma_fs.md"

    def test_section_count(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        assert len(data["sections"]) >= 8

    def test_section_ids_unique(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        ids = [s["section_id"] for s in data["sections"]]
        assert len(ids) == len(set(ids)), "Duplicate section IDs"

    def test_section_ids_start_with_spec(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        for sec in data["sections"]:
            assert sec["section_id"].startswith("spec_")

    def test_linked_list_section(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        ll = next(
            s for s in data["sections"]
            if s["section_id"] == "spec_linked_list_descriptor_mode"
        )
        assert "linked_list" in ll["feature_tags"]
        assert "Linked-List" in ll["title"]

    def test_sections_have_required_fields(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        for sec in data["sections"]:
            assert "section_id" in sec
            assert "title" in sec
            assert "page_range" in sec
            assert "feature_tags" in sec
            assert "summary" in sec
            assert isinstance(sec["feature_tags"], list)

    def test_summary_not_empty(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_spec_index.py", tmp_path)
        # At least the numbered sections (not the top-level heading) should have summaries
        numbered = [s for s in data["sections"] if s["title"][0].isdigit()]
        for sec in numbered:
            assert len(sec["summary"]) > 0, f"Empty summary for {sec['section_id']}"

    def test_bad_manifest(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "build_spec_index.py"),
                "--manifest",
                str(tmp_path / "nonexistent.yaml"),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0


# ===========================================================================
# build_reg_index.py tests
# ===========================================================================


class TestBuildRegIndex:
    def test_schema_version(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        assert data["schema_version"] == "reg_db.v1"

    def test_register_count(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        assert len(data["registers"]) >= 6

    def test_total_field_count(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        total = sum(len(r["fields"]) for r in data["registers"])
        assert total >= 12

    def test_dma_cfg_register(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        cfg = next(r for r in data["registers"] if r["register"] == "DMA_CFG")
        assert cfg["offset"] == "0x000"
        assert cfg["block"] == "DMA"
        field_names = [f["field"] for f in cfg["fields"]]
        assert "LL_MODE_EN" in field_names
        assert "SG_MODE_EN" in field_names

    def test_ll_mode_en_field(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        cfg = next(r for r in data["registers"] if r["register"] == "DMA_CFG")
        ll = next(f for f in cfg["fields"] if f["field"] == "LL_MODE_EN")
        assert ll["bit_range"] == "[0]"
        assert ll["access"] == "RW"
        assert ll["ral_path"] == "ral.DMA.DMA_CFG.LL_MODE_EN"
        assert "linked_list" in ll["feature_tags"]

    def test_ral_path_format(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        for reg in data["registers"]:
            for fld in reg["fields"]:
                expected = f"ral.{reg['block']}.{reg['register']}.{fld['field']}"
                assert fld["ral_path"] == expected

    def test_registers_have_required_fields(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_reg_index.py", tmp_path)
        for reg in data["registers"]:
            assert "block" in reg
            assert "register" in reg
            assert "offset" in reg
            assert "fields" in reg
            for fld in reg["fields"]:
                assert "field" in fld
                assert "bit_range" in fld
                assert "access" in fld
                assert "ral_path" in fld
                assert "feature_tags" in fld

    def test_bad_manifest(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "build_reg_index.py"),
                "--manifest",
                str(tmp_path / "nonexistent.yaml"),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0


# ===========================================================================
# build_rtl_index.py tests
# ===========================================================================


class TestBuildRtlIndex:
    def test_schema_version(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        assert data["schema_version"] == "rtl_index.v1"

    def test_elaborated_flag(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        assert data["elaborated"] is False

    def test_module_count(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        assert len(data["modules"]) == 7

    def test_module_names(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        names = {m["name"] for m in data["modules"]}
        expected = {
            "dma_subsystem", "dma_core", "dma_desc_parser",
            "dma_axi_master", "dma_int_ctrl", "dma_power_ctrl",
            "dma_monitor",
        }
        assert names == expected

    def test_dma_core_instances(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        core = next(m for m in data["modules"] if m["name"] == "dma_core")
        inst_names = [i["name"] for i in core["instances"]]
        assert "u_desc_parser" in inst_names
        assert "u_axi_master" in inst_names
        assert "u_int_ctrl" in inst_names
        assert "u_power" in inst_names
        assert "u_monitor" in inst_names

    def test_dma_core_parameter(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        core = next(m for m in data["modules"] if m["name"] == "dma_core")
        assert len(core["parameters"]) == 1
        assert core["parameters"][0]["name"] == "NUM_CHANNELS"

    def test_desc_parser_fsm_states(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        parser = next(m for m in data["modules"] if m["name"] == "dma_desc_parser")
        assert "IDLE" in parser["fsm_states"]
        assert "FETCH_DESC" in parser["fsm_states"]
        assert "PARSE_LINKED" in parser["fsm_states"]
        assert len(parser["fsm_states"]) == 6

    def test_desc_parser_ports(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        parser = next(m for m in data["modules"] if m["name"] == "dma_desc_parser")
        assert "ll_mode_en" in parser["ports"]
        assert "sg_mode_en" in parser["ports"]
        assert "xfer_size" in parser["ports"]

    def test_desc_parser_signals(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        parser = next(m for m in data["modules"] if m["name"] == "dma_desc_parser")
        sig_names = [s["name"] for s in parser["signals"]]
        assert "src_addr" in sig_names
        assert "dst_addr" in sig_names

    def test_hierarchy_tree(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        hierarchy = data["hierarchy"]
        assert "dma_subsystem" in hierarchy
        assert "u_dma" in hierarchy["dma_subsystem"]

    def test_port_directions_stripped(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        for mod in data["modules"]:
            for port in mod["ports"]:
                assert not port.startswith("input")
                assert not port.startswith("output")
                assert not port.startswith("inout")

    def test_modules_have_required_fields(self, tmp_path: Path) -> None:
        data, _ = _run_indexer("build_rtl_index.py", tmp_path)
        for mod in data["modules"]:
            assert "name" in mod
            assert "file" in mod
            assert "line_range" in mod
            assert "ports" in mod
            assert "signals" in mod
            assert "instances" in mod
            assert "fsm_states" in mod
            assert "parameters" in mod

    def test_bad_manifest(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "build_rtl_index.py"),
                "--manifest",
                str(tmp_path / "nonexistent.yaml"),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0
