# AXI2AHB URG Report Demo Data

This directory contains a sample URG (Unified Report Generator) HTML coverage
report from an AXI2AHB bridge design, used to demonstrate the Phase 3 URG
parser functionality.

## Data Source

The URG report in this directory is **public/synthetic/sanitized demo data**.
It does not contain:
- Proprietary RTL source code
- Internal project codenames or customer information
- Private file paths or usernames
- Confidential design hierarchy

The module names (e.g., `axi2ahb_bridge_top`, `bridge_controller`,
`axi_frontend`, `ahb_backend`) are generic AXI-to-AHB bridge design components
commonly found in open-source or educational verification projects.

## Synopsys Library Paths

The URG report contains references to `/opt/synopsys/vcs-mx/O-2018.09-SP2/`
paths. These are standard Synopsys VCS tool installation paths (UVM library
files) and are automatically filtered by the URG parser during gap extraction.
They do not represent proprietary design data.

## Purpose

This demo data is used to:
1. Demonstrate the URG HTML parser (`lib/urg_parser/`)
2. Validate the `build_coverage_index.py` script
3. Test MCP tools with a realistic dataset (982 gaps across 7 coverage types)

## Usage

Build the coverage index:
```bash
make build-real-index
```

Query the gaps via MCP tools:
```python
cov_list_uncovered(project="axi2ahb", coverage_type="all", top_n=20)
cov_get_gap_detail(project="axi2ahb", gap_id="GAP_L001")
```

## Coverage Gap Summary

| Type | Count | Gap ID Prefix |
|------|-------|---------------|
| functional | 16 | `GAP_XXXX` |
| line | 126 | `GAP_LNNN` |
| branch | 40 | `GAP_BNNN` |
| condition | 32 | `GAP_CNNN` |
| toggle | 763 | `GAP_TNNN` |
| fsm | 1 | `GAP_MNNN` |
| assert | 4 | `GAP_ANNN` |
| **Total** | **982** | |

## Security Boundary

This directory must not contain:
- Real company RTL, FS, register documents, or UVM environments
- Real coverage databases or waveforms
- Internal project identifiers or customer names
- Proprietary design hierarchy or verification plans

If you are adding new URG report data, ensure it is sanitized and does not
violate these boundaries. See `CLAUDE.md` for full security rules.
