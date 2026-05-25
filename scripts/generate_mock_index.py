#!/usr/bin/env python3
"""Generate mock index files for the DMA subsystem mock project.

Reads coverage_gaps.json and generates:
  - coverage_index.json (derived from gaps)
  - spec_index.json     (mock spec sections with feature tags)
  - reg_db.json         (mock register/field database)
  - rtl_index.json      (mock RTL module/signal index)
  - tb_index.json       (mock UVM test/sequence index)

Usage:
    python scripts/generate_mock_index.py --manifest mock_data/dma_subsystem/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.manifest import Manifest  # noqa: E402

# ---------------------------------------------------------------------------
# Mock spec index
# ---------------------------------------------------------------------------
MOCK_SPEC_INDEX = {
    "schema_version": "spec_index.v1",
    "source": "spec/dma_fs.md",
    "sections": [
        {
            "section_id": "spec_dma_overview",
            "title": "1. DMA Subsystem Overview",
            "page_range": "1-5",
            "feature_tags": ["dma", "overview"],
            "summary": (
                "High-level architecture of the DMA subsystem including "
                "block diagram, address map, and operating modes."
            )
        },
        {
            "section_id": "spec_dma_descriptor_format",
            "title": "2. Descriptor Format",
            "page_range": "6-15",
            "feature_tags": ["descriptor", "normal_mode", "descriptor_format"],
            "summary": (
                "Defines the normal descriptor layout: source address, "
                "destination address, transfer size, control flags."
            )
        },
        {
            "section_id": "spec_dma_linked_list",
            "title": "3. Linked-List Descriptor Mode",
            "page_range": "16-22",
            "feature_tags": ["descriptor", "linked_list", "chaining"],
            "summary": (
                "Linked-list mode allows chaining multiple descriptors via a "
                "next-pointer field. Enabled by DMA_CFG.LL_MODE_EN. Parser "
                "transitions to LINK_DESC state when ll_mode_en is asserted."
            )
        },
        {
            "section_id": "spec_dma_scatter_gather",
            "title": "4. Scatter-Gather Descriptor Mode",
            "page_range": "23-30",
            "feature_tags": ["descriptor", "scatter_gather"],
            "summary": (
                "Scatter-gather mode supports non-contiguous memory regions. "
                "Enabled by DMA_CFG.SG_MODE_EN."
            )
        },
        {
            "section_id": "spec_dma_chaining",
            "title": "5. Descriptor Chaining",
            "page_range": "31-38",
            "feature_tags": ["descriptor", "chaining", "back_to_back"],
            "summary": (
                "Descriptor chaining allows back-to-back descriptor processing "
                "without CPU intervention. Chain of 3+ descriptors exercises "
                "the pipeline depth."
            )
        },
        {
            "section_id": "spec_dma_alignment",
            "title": "6. Address Alignment Rules",
            "page_range": "39-42",
            "feature_tags": ["descriptor", "alignment", "error"],
            "summary": (
                "Source and destination addresses must be aligned to transfer "
                "size. Misaligned addresses trigger an error interrupt."
            )
        },
        {
            "section_id": "spec_dma_interrupts",
            "title": "7. Interrupt System",
            "page_range": "43-55",
            "feature_tags": ["interrupt", "coalescing", "masking"],
            "summary": (
                "DMA supports completion, error, and coalescing interrupts. "
                "Coalescing can be by count threshold or timeout. Masked "
                "interrupts remain pending until unmasked."
            )
        },
        {
            "section_id": "spec_dma_errors",
            "title": "8. Error Handling",
            "page_range": "56-62",
            "feature_tags": ["error", "interrupt", "bus_error"],
            "summary": (
                "Error conditions: bus error, descriptor fetch error, "
                "alignment error, timeout. Each generates an error "
                "interrupt if unmasked."
            )
        },
        {
            "section_id": "spec_dma_power",
            "title": "9. Power Management",
            "page_range": "63-70",
            "feature_tags": ["power", "clock_gating", "retention"],
            "summary": (
                "Clock gating on idle channels. Retention mode preserves "
                "register state during power-down. Retention mode is only "
                "available in specific silicon revisions."
            )
        },
        {
            "section_id": "spec_dma_burst",
            "title": "10. AXI Burst Configuration",
            "page_range": "71-80",
            "feature_tags": ["burst", "axi", "wrap", "increment"],
            "summary": (
                "Supports INCR, WRAP, and FIXED burst types. Max burst length "
                "configurable up to 256 beats. WRAP burst wraps at power-of-2 "
                "boundaries."
            )
        },
        {
            "section_id": "spec_dma_performance",
            "title": "11. Performance Characteristics",
            "page_range": "81-90",
            "feature_tags": ["performance", "throughput", "back_to_back"],
            "summary": (
                "Back-to-back descriptor fetch achieves peak throughput when "
                "pipeline is full. Measured via monitor timestamps."
            )
        }
    ]
}

# ---------------------------------------------------------------------------
# Mock register database
# ---------------------------------------------------------------------------
MOCK_REG_DB = {
    "schema_version": "reg_db.v1",
    "registers": [
        {
            "block": "DMA",
            "register": "DMA_CFG",
            "offset": "0x000",
            "fields": [
                {
                    "field": "LL_MODE_EN",
                    "bit_range": "[0]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Enable linked-list descriptor mode",
                    "ral_path": "ral.dma.DMA_CFG.LL_MODE_EN",
                    "feature_tags": ["linked_list", "descriptor"]
                },
                {
                    "field": "SG_MODE_EN",
                    "bit_range": "[1]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Enable scatter-gather descriptor mode",
                    "ral_path": "ral.dma.DMA_CFG.SG_MODE_EN",
                    "feature_tags": ["scatter_gather", "descriptor"]
                },
                {
                    "field": "CH_ENABLE",
                    "bit_range": "[7:4]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Channel enable bits (4 channels)",
                    "ral_path": "ral.dma.DMA_CFG.CH_ENABLE",
                    "feature_tags": ["channel", "control"]
                }
            ]
        },
        {
            "block": "DMA",
            "register": "DMA_DESC_CTRL",
            "offset": "0x010",
            "fields": [
                {
                    "field": "XFER_SIZE",
                    "bit_range": "[15:0]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Transfer size in bytes (max 4096)",
                    "ral_path": "ral.dma.DMA_DESC_CTRL.XFER_SIZE",
                    "feature_tags": ["descriptor", "transfer"]
                },
                {
                    "field": "DESC_TYPE",
                    "bit_range": "[17:16]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Descriptor type: 0=normal, 1=linked, 2=scatter-gather",
                    "ral_path": "ral.dma.DMA_DESC_CTRL.DESC_TYPE",
                    "feature_tags": ["descriptor"]
                }
            ]
        },
        {
            "block": "DMA",
            "register": "DMA_INT_MASK",
            "offset": "0x020",
            "fields": [
                {
                    "field": "COMP_MASK",
                    "bit_range": "[0]",
                    "access": "RW",
                    "reset": "1",
                    "description": "Mask completion interrupt",
                    "ral_path": "ral.dma.DMA_INT_MASK.COMP_MASK",
                    "feature_tags": ["interrupt", "completion"]
                },
                {
                    "field": "ERROR_MASK",
                    "bit_range": "[1]",
                    "access": "RW",
                    "reset": "1",
                    "description": "Mask error interrupt",
                    "ral_path": "ral.dma.DMA_INT_MASK.ERROR_MASK",
                    "feature_tags": ["interrupt", "error"]
                }
            ]
        },
        {
            "block": "DMA",
            "register": "DMA_INT_COAL",
            "offset": "0x024",
            "fields": [
                {
                    "field": "COUNT_THRESH",
                    "bit_range": "[7:0]",
                    "access": "RW",
                    "reset": "1",
                    "description": "Interrupt coalescing count threshold",
                    "ral_path": "ral.dma.DMA_INT_COAL.COUNT_THRESH",
                    "feature_tags": ["interrupt", "coalescing"]
                },
                {
                    "field": "TIMEOUT_VAL",
                    "bit_range": "[23:8]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Interrupt coalescing timeout value (cycles)",
                    "ral_path": "ral.dma.DMA_INT_COAL.TIMEOUT_VAL",
                    "feature_tags": ["interrupt", "coalescing", "timeout"]
                },
                {
                    "field": "COAL_EN",
                    "bit_range": "[24]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Enable interrupt coalescing",
                    "ral_path": "ral.dma.DMA_INT_COAL.COAL_EN",
                    "feature_tags": ["interrupt", "coalescing"]
                }
            ]
        },
        {
            "block": "DMA",
            "register": "DMA_POWER",
            "offset": "0x030",
            "fields": [
                {
                    "field": "CLOCK_GATE_EN",
                    "bit_range": "[0]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Enable clock gating on idle channels",
                    "ral_path": "ral.dma.DMA_POWER.CLOCK_GATE_EN",
                    "feature_tags": ["power", "clock_gating"]
                },
                {
                    "field": "RET_EN",
                    "bit_range": "[1]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Enable retention mode (silicon rev B+)",
                    "ral_path": "ral.dma.DMA_POWER.RET_EN",
                    "feature_tags": ["power", "retention"]
                }
            ]
        },
        {
            "block": "DMA",
            "register": "DMA_BURST_CTRL",
            "offset": "0x040",
            "fields": [
                {
                    "field": "WRAP_EN",
                    "bit_range": "[0]",
                    "access": "RW",
                    "reset": "0",
                    "description": "Enable AXI WRAP burst type",
                    "ral_path": "ral.dma.DMA_BURST_CTRL.WRAP_EN",
                    "feature_tags": ["burst", "axi", "wrap"]
                },
                {
                    "field": "MAX_LEN",
                    "bit_range": "[8:1]",
                    "access": "RW",
                    "reset": "16",
                    "description": "Maximum burst length (1-256)",
                    "ral_path": "ral.dma.DMA_BURST_CTRL.MAX_LEN",
                    "feature_tags": ["burst", "axi"]
                }
            ]
        }
    ]
}

# ---------------------------------------------------------------------------
# Mock RTL index
# ---------------------------------------------------------------------------
MOCK_RTL_INDEX = {
    "schema_version": "rtl_index.v1",
    "source": "text_analysis",
    "elaborated": False,
    "modules": [
        {
            "name": "dma_subsystem",
            "file": "rtl/dma_subsystem.sv",
            "line_range": [1, 50],
            "ports": ["clk", "rst_n", "axi_aw", "axi_ar", "axi_w", "axi_r", "axi_b", "irq_out"],
            "instances": [{"module": "dma_core", "name": "u_dma", "line": 25}],
            "parameters": []
        },
        {
            "name": "dma_core",
            "file": "rtl/dma_core.sv",
            "line_range": [1, 200],
            "ports": ["clk", "rst_n", "cfg_if", "desc_if", "axi_m", "irq"],
            "instances": [
                {"module": "dma_desc_parser", "name": "u_desc_parser", "line": 80},
                {"module": "dma_axi_master", "name": "u_axi_master", "line": 95},
                {"module": "dma_int_ctrl", "name": "u_int_ctrl", "line": 110},
                {"module": "dma_power_ctrl", "name": "u_power", "line": 125},
                {"module": "dma_monitor", "name": "u_monitor", "line": 140}
            ],
            "parameters": [{"name": "NUM_CHANNELS", "default": 4}]
        },
        {
            "name": "dma_desc_parser",
            "file": "rtl/dma_desc_parser.sv",
            "line_range": [1, 300],
            "ports": [
                "clk", "rst_n", "ll_mode_en", "sg_mode_en",
                "desc_valid", "desc_data", "chain_valid",
                "xfer_size", "addr_misaligned", "fetch_ack"
            ],
            "signals": [
                {"name": "ll_mode_en", "type": "logic", "width": 1, "line": 42},
                {"name": "sg_mode_en", "type": "logic", "width": 1, "line": 43},
                {"name": "chain_valid", "type": "logic", "width": 1, "line": 60},
                {"name": "xfer_size", "type": "logic", "width": 16, "line": 75},
                {"name": "addr_misaligned", "type": "logic", "width": 1, "line": 90},
                {"name": "fetch_ack", "type": "logic", "width": 1, "line": 110}
            ],
            "instances": [],
            "parameters": [],
            "fsm_states": ["IDLE", "FETCH_DESC", "PARSE_NORMAL", "PARSE_LINKED", "PARSE_SG", "DONE"]
        },
        {
            "name": "dma_axi_master",
            "file": "rtl/dma_axi_master.sv",
            "line_range": [1, 250],
            "ports": [
                "clk", "rst_n", "burst_wrap", "burst_len",
                "awaddr", "araddr", "wdata", "rdata"
            ],
            "signals": [
                {"name": "burst_wrap", "type": "logic", "width": 1, "line": 35},
                {"name": "burst_len", "type": "logic", "width": 8, "line": 36}
            ],
            "instances": [],
            "parameters": []
        },
        {
            "name": "dma_int_ctrl",
            "file": "rtl/dma_int_ctrl.sv",
            "line_range": [1, 180],
            "ports": [
                "clk", "rst_n", "error_irq", "comp_irq",
                "coal_timer_exp", "coal_count_hit",
                "masked_irq", "irq_out"
            ],
            "signals": [
                {"name": "error_irq", "type": "logic", "width": 1, "line": 30},
                {"name": "coal_timer_exp", "type": "logic", "width": 1, "line": 55},
                {"name": "coal_count_hit", "type": "logic", "width": 1, "line": 70},
                {"name": "masked_irq", "type": "logic", "width": 4, "line": 90}
            ],
            "instances": [],
            "parameters": []
        },
        {
            "name": "dma_power_ctrl",
            "file": "rtl/dma_power_ctrl.sv",
            "line_range": [1, 100],
            "ports": [
                "clk", "rst_n", "clk_gate_en", "retention_mode",
                "idle_detect", "power_state"
            ],
            "signals": [
                {"name": "clk_gate_en", "type": "logic", "width": 1, "line": 25},
                {"name": "retention_mode", "type": "logic", "width": 1, "line": 30},
                {"name": "idle_detect", "type": "logic", "width": 4, "line": 45}
            ],
            "instances": [],
            "parameters": []
        },
        {
            "name": "dma_monitor",
            "file": "rtl/dma_monitor.sv",
            "line_range": [1, 120],
            "ports": [
                "clk", "rst_n", "fetch_timestamp",
                "desc_valid", "xfer_complete"
            ],
            "signals": [
                {"name": "fetch_timestamp", "type": "logic", "width": 32, "line": 30}
            ],
            "instances": [],
            "parameters": []
        }
    ],
    "hierarchy": {
        "tb_top": {
            "u_dut": {
                "u_dma_subsys": {
                    "u_dma": {
                        "u_desc_parser": {},
                        "u_axi_master": {},
                        "u_int_ctrl": {},
                        "u_power": {},
                        "u_monitor": {}
                    }
                }
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Mock TB index
# ---------------------------------------------------------------------------
MOCK_TB_INDEX = {
    "schema_version": "tb_index.v1",
    "env_root": "tb/env",
    "sequence_root": "tb/sequences",
    "base_tests": [
        {
            "name": "dma_base_test",
            "file": "tb/tests/dma_base_test.sv",
            "extends": "uvm_test",
            "description": (
                "Base test for all DMA tests. Sets up env, config, "
                "and default sequences."
            ),
            "config_knobs": ["num_channels", "enable_interrupts", "descriptor_mode"]
        }
    ],
    "sequences": [
        {
            "name": "dma_base_seq",
            "file": "tb/sequences/dma_base_seq.sv",
            "extends": "uvm_sequence",
            "description": "Base sequence providing common DMA operations.",
            "feature_tags": ["dma", "base"]
        },
        {
            "name": "dma_normal_desc_seq",
            "file": "tb/sequences/dma_normal_desc_seq.sv",
            "extends": "dma_base_seq",
            "description": "Sequence for normal descriptor transfers.",
            "feature_tags": ["descriptor", "normal_mode"]
        },
        {
            "name": "dma_desc_base_seq",
            "file": "tb/sequences/dma_desc_base_seq.sv",
            "extends": "dma_base_seq",
            "description": (
                "Base sequence for descriptor operations including "
                "linked-list and scatter-gather."
            ),
            "feature_tags": ["descriptor", "linked_list", "scatter_gather", "chaining"]
        },
        {
            "name": "dma_interrupt_seq",
            "file": "tb/sequences/dma_interrupt_seq.sv",
            "extends": "dma_base_seq",
            "description": "Sequence for interrupt generation and handling.",
            "feature_tags": ["interrupt", "error", "coalescing"]
        },
        {
            "name": "dma_burst_seq",
            "file": "tb/sequences/dma_burst_seq.sv",
            "extends": "dma_base_seq",
            "description": "Sequence for AXI burst operations.",
            "feature_tags": ["burst", "axi", "wrap"]
        },
        {
            "name": "dma_power_seq",
            "file": "tb/sequences/dma_power_seq.sv",
            "extends": "dma_base_seq",
            "description": "Sequence for power management operations.",
            "feature_tags": ["power", "clock_gating", "retention"]
        }
    ],
    "existing_tests": [
        {
            "name": "dma_normal_desc_test",
            "file": "tb/tests/dma_normal_desc_test.sv",
            "extends": "dma_base_test",
            "sequences": ["dma_normal_desc_seq"],
            "feature_tags": ["descriptor", "normal_mode"]
        },
        {
            "name": "dma_single_desc_random_test",
            "file": "tb/tests/dma_single_desc_random_test.sv",
            "extends": "dma_base_test",
            "sequences": ["dma_normal_desc_seq"],
            "feature_tags": ["descriptor", "normal_mode", "random"]
        }
    ],
    "config_knobs": [
        {"name": "num_channels", "type": "int", "default": 4, "plusarg": "+NUM_CHANNELS=%d"},
        {"name": "enable_interrupts", "type": "bit", "default": 1, "plusarg": "+EN_INT=%d"},
        {
            "name": "descriptor_mode",
            "type": "string",
            "default": "normal",
            "plusarg": "+DESC_MODE=%s",
        },
    ]
}


def generate_coverage_index(gaps_data: dict) -> dict:
    """Generate coverage_index.json from coverage_gaps.json."""
    return {
        "project": gaps_data.get("project", "unknown"),
        "report_id": gaps_data.get("report_id", "unknown"),
        "schema_version": "coverage_index.v1",
        "gaps": gaps_data.get("gaps", []),
        "total_gaps": len(gaps_data.get("gaps", [])),
        "clusters": list({
            g.get("cluster_id", "unknown")
            for g in gaps_data.get("gaps", [])
            if g.get("cluster_id")
        }),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate mock index files for DV AI Coverage Closure.",
    )
    parser.add_argument("--manifest", required=True, help="Path to project_manifest.yaml")
    args = parser.parse_args()

    manifest = Manifest.load(args.manifest)
    project_root = manifest.base_dir

    # Read coverage gaps
    gaps_path = project_root / "coverage_gaps.json"
    if not gaps_path.exists():
        print(f"Error: coverage_gaps.json not found at {gaps_path}", file=sys.stderr)
        return 1

    with open(gaps_path, encoding="utf-8") as f:
        gaps_data = json.load(f)

    # Index output directory
    index_dir = project_root / ".dv_ai_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    indexes = {
        "coverage_index.json": generate_coverage_index(gaps_data),
        "spec_index.json": MOCK_SPEC_INDEX,
        "reg_db.json": MOCK_REG_DB,
        "rtl_index.json": MOCK_RTL_INDEX,
        "tb_index.json": MOCK_TB_INDEX,
    }

    for filename, data in indexes.items():
        out_path = index_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Generated: {out_path}")

    print(f"\nAll {len(indexes)} indexes written to {index_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
