"""Register MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - reg_find_fields_affecting_feature: find register fields related to a feature
  - reg_find_field: find a register field by exact name (case-insensitive)
  - reg_search_by_description: search register fields by description keyword
  - reg_get_ral_path: get the RAL access path for a register field
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


def reg_find_field(
    project: str,
    field_name: str,
) -> dict[str, Any]:
    """Find a register field by exact name (case-insensitive).

    Args:
        project: Project ID or manifest path.
        field_name: Field name to search for (e.g. 'LL_MODE_EN').

    Returns:
        Envelope with the matching field details including register,
        offset, bit_range, access, reset, description, ral_path, and
        feature_tags.
    """
    tool = "reg_find_field"
    try:
        reader = get_index_reader(project)
        data = reader.read(_REG_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    field_lower = field_name.lower()
    registers = data.get("registers", [])

    for reg in registers:
        reg_name = reg.get("register", "")
        reg_offset = reg.get("offset", "")
        for field in reg.get("fields", []):
            if field.get("field", "").lower() == field_lower:
                evidence_list = [
                    register_evidence(
                        reg_name,
                        field.get("field", ""),
                        f"{reg_name}[{field.get('bit_range', '?')}]",
                        field.get("description", ""),
                    ),
                ]
                return envelope(
                    tool=tool,
                    project=project,
                    result={
                        "register": reg_name,
                        "field": field.get("field"),
                        "offset": reg_offset,
                        "bit_range": field.get("bit_range"),
                        "access": field.get("access"),
                        "reset": field.get("reset"),
                        "description": field.get("description"),
                        "ral_path": field.get("ral_path"),
                        "feature_tags": field.get("feature_tags"),
                    },
                    evidence=evidence_list,
                    truncated=False,
                    next_actions=[
                        "reg_get_ral_path",
                        "reg_search_by_description",
                        "rtl_find_signal",
                    ],
                )

    return error_envelope(tool, project, f"Field not found: {field_name}")


def reg_search_by_description(
    project: str,
    query: str,
) -> dict[str, Any]:
    """Search register fields by description keyword.

    Scores matches against feature_tags (weight 5), register name (weight 2),
    and description (weight 1) per term. Returns top 10 results.

    Args:
        project: Project ID or manifest path.
        query: Search query string.

    Returns:
        Envelope with matching register fields sorted by relevance.
    """
    tool = "reg_search_by_description"
    try:
        reader = get_index_reader(project)
        data = reader.read(_REG_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    registers = data.get("registers", [])
    query_lower = query.lower()
    query_terms = query_lower.replace("_", " ").replace("-", " ").split()

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
            for term in query_terms:
                if term in tags:
                    score += 5
                if term in reg_name.lower():
                    score += 2
                if term in desc:
                    score += 1

            # Exact tag match
            if query_lower in tags:
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

    # Truncate to top 10
    was_truncated = len(matches) > 10
    matches = matches[:10]

    return envelope(
        tool=tool,
        project=project,
        result={"query": query, "matches": matches, "total_matches": len(matches)},
        evidence=evidence_list[:10],
        truncated=was_truncated,
        next_actions=["reg_find_field", "reg_get_ral_path"],
    )


def reg_get_ral_path(
    project: str,
    field_name: str,
) -> dict[str, Any]:
    """Get the RAL access path for a register field.

    Args:
        project: Project ID or manifest path.
        field_name: Field name to look up (case-insensitive).

    Returns:
        Envelope with the field's RAL path, register, offset, and bit_range.
    """
    tool = "reg_get_ral_path"
    try:
        reader = get_index_reader(project)
        data = reader.read(_REG_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    field_lower = field_name.lower()
    registers = data.get("registers", [])

    for reg in registers:
        reg_name = reg.get("register", "")
        reg_offset = reg.get("offset", "")
        for field in reg.get("fields", []):
            if field.get("field", "").lower() == field_lower:
                ral_path = field.get("ral_path", "")
                evidence_list = [
                    register_evidence(
                        reg_name,
                        field.get("field", ""),
                        ral_path,
                        f"RAL path for {field.get('field', '')}",
                    ),
                ]
                return envelope(
                    tool=tool,
                    project=project,
                    result={
                        "field": field.get("field"),
                        "register": reg_name,
                        "ral_path": ral_path,
                        "offset": reg_offset,
                        "bit_range": field.get("bit_range"),
                    },
                    evidence=evidence_list,
                    truncated=False,
                    next_actions=["reg_find_field", "tb_find_config_knob"],
                )

    return error_envelope(tool, project, f"Field not found: {field_name}")
