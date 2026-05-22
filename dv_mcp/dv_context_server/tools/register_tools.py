"""Register MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - reg_find_fields_affecting_feature: find register fields related to a feature
"""

from __future__ import annotations

from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import register_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope

_REG_INDEX = "reg_db.json"


def reg_find_fields_affecting_feature(
    project: str,
    feature: str,
) -> dict[str, Any]:
    """Find register fields likely controlling a given feature.

    Matches against:
    - field feature_tags
    - field name
    - field description
    - register name

    Args:
        project: Project ID or manifest path.
        feature: Feature keyword (e.g. 'linked_list', 'interrupt', 'power').

    Returns:
        Envelope with matching register fields.
    """
    tool = "reg_find_fields_affecting_feature"
    try:
        reader = get_index_reader(project)
        data = reader.read(_REG_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    registers = data.get("registers", [])
    feature_lower = feature.lower()
    feature_terms = feature_lower.replace("_", " ").replace("-", " ").split()

    matches: list[dict] = []
    evidence_list: list[dict] = []

    for reg in registers:
        reg_name = reg.get("register", "")
        reg_offset = reg.get("offset", "")
        for field in reg.get("fields", []):
            field_name = field.get("field", "")
            tags = [t.lower() for t in field.get("feature_tags", [])]
            desc = field.get("description", "").lower()

            score = 0
            for term in feature_terms:
                if term in tags:
                    score += 3
                if term in field_name.lower():
                    score += 2
                if term in desc:
                    score += 1
                if term in reg_name.lower():
                    score += 1

            # Exact tag match with underscores preserved
            if feature_lower in tags:
                score += 5

            if score > 0:
                match_entry = {
                    "register": reg_name,
                    "offset": reg_offset,
                    "field": field_name,
                    "bit_range": field.get("bit_range"),
                    "access": field.get("access"),
                    "reset": field.get("reset"),
                    "description": field.get("description"),
                    "ral_path": field.get("ral_path"),
                    "feature_tags": field.get("feature_tags"),
                    "relevance": min(score / 10.0, 1.0),
                }
                matches.append(match_entry)
                evidence_list.append(
                    register_evidence(
                        reg_name, field_name,
                        f"{reg_name}[{field.get('bit_range', '?')}]",
                        field.get("description", ""),
                    )
                )

    # Sort by relevance descending
    matches.sort(key=lambda m: -m["relevance"])

    return envelope(
        tool=tool,
        project=project,
        result={"feature": feature, "fields": matches, "total_matches": len(matches)},
        evidence=evidence_list,
        truncated=False,
        next_actions=["rtl_find_signal", "tb_get_existing_tests_for_feature"],
    )
