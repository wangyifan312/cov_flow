"""Evidence ID generation for traceability.

Every MCP tool return includes an evidence list that links the result
back to its source. This module generates standardized evidence entries.
"""

from __future__ import annotations

from typing import Any


def make_evidence(
    evidence_id: str,
    source_type: str,
    source_ref: str,
    summary: str,
) -> dict[str, Any]:
    """Create a single evidence entry.

    Args:
        evidence_id: Unique identifier (e.g. 'cov:GAP_0012:source').
        source_type: One of 'coverage_report', 'coverage_model', 'spec',
            'register', 'rtl', 'testbench', 'simulation'.
        source_ref: Reference to the source (e.g. 'tb/cov/dma_cov.sv:88-96').
        summary: Human-readable description of what this evidence provides.
    """
    return {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_ref": source_ref,
        "summary": summary,
    }


def coverage_evidence(
    gap_id: str, detail_type: str, source_ref: str, summary: str,
) -> dict[str, Any]:
    """Create a coverage-type evidence entry."""
    return make_evidence(
        f"cov:{gap_id}:{detail_type}",
        "coverage_report",
        source_ref,
        summary,
    )


def spec_evidence(section_id: str, source_ref: str, summary: str) -> dict[str, Any]:
    """Create a spec-type evidence entry."""
    return make_evidence(
        f"spec:{section_id}",
        "spec",
        source_ref,
        summary,
    )


def register_evidence(register: str, field: str, source_ref: str, summary: str) -> dict[str, Any]:
    """Create a register-type evidence entry."""
    return make_evidence(
        f"reg:{register}.{field}",
        "register",
        source_ref,
        summary,
    )


def rtl_evidence(module: str, signal: str, source_ref: str, summary: str) -> dict[str, Any]:
    """Create an RTL-type evidence entry."""
    return make_evidence(
        f"rtl:{module}.{signal}",
        "rtl",
        source_ref,
        summary,
    )


def tb_evidence(component_type: str, name: str, source_ref: str, summary: str) -> dict[str, Any]:
    """Create a testbench-type evidence entry."""
    return make_evidence(
        f"tb:{component_type}:{name}",
        "testbench",
        source_ref,
        summary,
    )


def simulation_evidence(test: str, seed: int, source_ref: str, summary: str) -> dict[str, Any]:
    """Create a simulation-type evidence entry."""
    return make_evidence(
        f"sim:{test}:{seed}",
        "simulation",
        source_ref,
        summary,
    )
