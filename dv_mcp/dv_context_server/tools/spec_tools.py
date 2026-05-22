"""Spec MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - spec_search: search spec sections by keyword or feature tag
"""

from __future__ import annotations

from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import spec_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope, truncate_list

_SPEC_INDEX = "spec_index.json"


def spec_search(
    project: str,
    query: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """Search spec sections by keyword or feature tag.

    Performs case-insensitive matching against:
    - section titles
    - feature tags
    - summary text

    Args:
        project: Project ID or manifest path.
        query: Search query string.
        max_results: Maximum results to return (default: 10, max: 20).

    Returns:
        Envelope with matching spec sections.
    """
    tool = "spec_search"
    try:
        reader = get_index_reader(project)
        data = reader.read(_SPEC_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    sections = data.get("sections", [])
    query_lower = query.lower()
    query_terms = query_lower.split()

    scored: list[tuple[float, dict]] = []
    for section in sections:
        score = 0.0
        title = section.get("title", "").lower()
        tags = [t.lower() for t in section.get("feature_tags", [])]
        summary = section.get("summary", "").lower()

        for term in query_terms:
            # Exact tag match (highest weight)
            if term in tags:
                score += 3.0
            # Title match
            if term in title:
                score += 2.0
            # Summary match
            if term in summary:
                score += 1.0

        # Also try exact query as a tag
        if query_lower in tags:
            score += 5.0

        if score > 0:
            scored.append((score, section))

    scored.sort(key=lambda x: -x[0])
    matches = [s for _, s in scored]

    max_results = min(max_results, 20)
    matches, was_truncated = truncate_list(matches, max_results)

    # Build result summaries
    results = []
    evidence_list = []
    for section in matches:
        results.append({
            "section_id": section.get("section_id"),
            "title": section.get("title"),
            "page_range": section.get("page_range"),
            "feature_tags": section.get("feature_tags"),
            "summary": section.get("summary"),
        })
        evidence_list.append(
            spec_evidence(
                section.get("section_id", "unknown"),
                data.get("source", "unknown"),
                section.get("summary", "")[:100],
            )
        )

    return envelope(
        tool=tool,
        project=project,
        result={"query": query, "matches": results, "total_matches": len(scored)},
        evidence=evidence_list,
        truncated=was_truncated,
        next_actions=["reg_find_fields_affecting_feature", "rtl_find_signal"],
    )
