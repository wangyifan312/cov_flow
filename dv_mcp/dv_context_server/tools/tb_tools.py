"""Testbench MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - tb_get_existing_tests_for_feature: find existing tests/sequences for a feature
"""

from __future__ import annotations

from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import tb_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope

_TB_INDEX = "tb_index.json"


def tb_get_existing_tests_for_feature(
    project: str,
    feature: str,
) -> dict[str, Any]:
    """Find existing UVM tests and sequences related to a feature.

    Matches against:
    - sequence feature_tags
    - test feature_tags
    - test/sequence name and description

    Args:
        project: Project ID or manifest path.
        feature: Feature keyword (e.g. 'linked_list', 'interrupt', 'burst').

    Returns:
        Envelope with matching tests and sequences.
    """
    tool = "tb_get_existing_tests_for_feature"
    try:
        reader = get_index_reader(project)
        data = reader.read(_TB_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    feature_lower = feature.lower()
    feature_terms = feature_lower.replace("_", " ").replace("-", " ").split()

    def _score(tags: list[str], name: str, desc: str) -> float:
        score = 0.0
        tags_lower = [t.lower() for t in tags]
        name_lower = name.lower()
        desc_lower = desc.lower()
        for term in feature_terms:
            if term in tags_lower:
                score += 3.0
            if term in name_lower:
                score += 2.0
            if term in desc_lower:
                score += 1.0
        if feature_lower in tags_lower:
            score += 5.0
        return score

    # Search sequences
    seq_matches = []
    seq_evidence = []
    for seq in data.get("sequences", []):
        s = _score(seq.get("feature_tags", []), seq.get("name", ""), seq.get("description", ""))
        if s > 0:
            seq_matches.append({
                "name": seq.get("name"),
                "file": seq.get("file"),
                "extends": seq.get("extends"),
                "description": seq.get("description"),
                "feature_tags": seq.get("feature_tags"),
                "relevance": min(s / 10.0, 1.0),
            })
            seq_evidence.append(
                tb_evidence(
                    "sequence",
                    seq.get("name", "unknown"),
                    seq.get("file", ""),
                    seq.get("description", ""),
                )
            )

    # Search existing tests
    test_matches = []
    test_evidence = []
    for test in data.get("existing_tests", []):
        s = _score(test.get("feature_tags", []), test.get("name", ""), "")
        if s > 0:
            test_matches.append({
                "name": test.get("name"),
                "file": test.get("file"),
                "extends": test.get("extends"),
                "sequences": test.get("sequences"),
                "feature_tags": test.get("feature_tags"),
                "relevance": min(s / 10.0, 1.0),
            })
            test_evidence.append(
                tb_evidence(
                    "test",
                    test.get("name", "unknown"),
                    test.get("file", ""),
                    f"Existing test for {feature}",
                )
            )

    # Sort by relevance
    seq_matches.sort(key=lambda m: -m["relevance"])
    test_matches.sort(key=lambda m: -m["relevance"])

    all_evidence = seq_evidence + test_evidence

    return envelope(
        tool=tool,
        project=project,
        result={
            "feature": feature,
            "sequences": seq_matches,
            "existing_tests": test_matches,
            "base_tests": data.get("base_tests", []),
            "config_knobs": data.get("config_knobs", []),
        },
        evidence=all_evidence,
        truncated=False,
        next_actions=["reg_find_fields_affecting_feature", "rtl_find_signal"],
    )
