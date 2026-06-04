"""Testbench MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - tb_get_existing_tests_for_feature: find existing tests/sequences for a feature
  - tb_find_tests_for_gap: find tests/sequences that may cover a specific gap
  - tb_read_source: read the full source code of a testbench component
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import tb_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader, get_manifest
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope
from lib.semantic_matcher import assess_gap_coverage, extract_semantic_keywords, score_tb_match
from lib.source_resolver import SourceResolver

_TB_INDEX = "tb_index.json"
_COVERAGE_INDEX = "coverage_index.json"
_MAX_BASE_METHODS = 10
_MAX_READ_LINES = 1000
_MAX_READ_BYTES = 65536
_VALID_COMPONENT_TYPES = ("sequence", "test", "base_test", "env")


def _is_base_sequence(seq: dict) -> bool:
    """Determine whether a sequence entry is a base/abstract sequence."""
    extends = seq.get("extends", "")
    name = seq.get("name", "")
    return extends in ("uvm_sequence", "uvm_sequence_base") or name.startswith("base_")


def tb_get_existing_tests_for_feature(
    project: str,
    feature: str,
    scope: str = "all",
) -> dict[str, Any]:
    """Find existing UVM tests and sequences related to a feature.

    Matches against:
    - sequence feature_tags
    - test feature_tags
    - test/sequence name and description

    Args:
        project: Project ID or manifest path.
        feature: Feature keyword (e.g. 'linked_list', 'interrupt', 'burst').
        scope: Return scope filter. One of:
            - "all": return sequences + existing_tests + base_tests + config_knobs (default)
            - "tests": return existing_tests + base_tests + config_knobs only
            - "sequences": return sequences only

    Returns:
        Envelope with matching tests and sequences. Matched sequences include
        api_methods; base sequences (extends uvm_sequence or name starting with
        'base_') are truncated to 10 methods with api_methods_truncated=true.
    """
    tool = "tb_get_existing_tests_for_feature"
    if scope not in ("all", "tests", "sequences"):
        msg = f"Invalid scope '{scope}': must be all|tests|sequences"
        return error_envelope(tool, project, msg)

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

    result: dict[str, Any] = {"feature": feature}

    # Search sequences (scope "all" or "sequences")
    if scope in ("all", "sequences"):
        seq_matches = []
        seq_evidence = []
        for seq in data.get("sequences", []):
            s = _score(
                seq.get("feature_tags", []),
                seq.get("name", ""),
                seq.get("description", ""),
            )
            if s > 0:
                # api_methods with base-sequence truncation
                all_methods = seq.get("api_methods", [])
                is_base = _is_base_sequence(seq)
                if is_base and len(all_methods) > _MAX_BASE_METHODS:
                    methods_out = [
                        {
                            "name": m.get("name"),
                            "signature": m.get("signature", ""),
                            "is_task": m.get("is_task", False),
                        }
                        for m in all_methods[:_MAX_BASE_METHODS]
                    ]
                    methods_truncated = True
                else:
                    methods_out = [
                        {
                            "name": m.get("name"),
                            "signature": m.get("signature", ""),
                            "is_task": m.get("is_task", False),
                        }
                        for m in all_methods
                    ]
                    methods_truncated = False

                seq_matches.append({
                    "name": seq.get("name"),
                    "file": seq.get("file"),
                    "extends": seq.get("extends"),
                    "description": seq.get("description"),
                    "feature_tags": seq.get("feature_tags"),
                    "relevance": min(s / 10.0, 1.0),
                    "api_methods": methods_out,
                    "api_methods_truncated": methods_truncated,
                })
                seq_evidence.append(
                    tb_evidence(
                        "sequence",
                        seq.get("name", "unknown"),
                        seq.get("file", ""),
                        seq.get("description", ""),
                    )
                )

        seq_matches.sort(key=lambda m: -m["relevance"])
        result["sequences"] = seq_matches

    # Search existing tests (scope "all" or "tests")
    if scope in ("all", "tests"):
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

        test_matches.sort(key=lambda m: -m["relevance"])
        result["existing_tests"] = test_matches

        # base_tests and config_knobs are included when scope includes tests
        result["base_tests"] = data.get("base_tests", [])
        result["config_knobs"] = data.get("config_knobs", [])

    all_evidence: list[dict] = []
    if scope in ("all", "sequences"):
        all_evidence.extend(seq_evidence)
    if scope in ("all", "tests"):
        all_evidence.extend(test_evidence)

    return envelope(
        tool=tool,
        project=project,
        result=result,
        evidence=all_evidence,
        truncated=False,
        next_actions=["reg_find_fields_affecting_feature", "rtl_find_signal"],
    )


def _build_methods_output(seq: dict) -> tuple[list[dict], bool]:
    """Build api_methods output with base-sequence truncation."""
    all_methods = seq.get("api_methods", [])
    is_base = _is_base_sequence(seq)
    if is_base and len(all_methods) > _MAX_BASE_METHODS:
        methods_out = [
            {
                "name": m.get("name"),
                "signature": m.get("signature", ""),
                "is_task": m.get("is_task", False),
            }
            for m in all_methods[:_MAX_BASE_METHODS]
        ]
        return methods_out, True
    methods_out = [
        {
            "name": m.get("name"),
            "signature": m.get("signature", ""),
            "is_task": m.get("is_task", False),
        }
        for m in all_methods
    ]
    return methods_out, False


def tb_find_tests_for_gap(
    project: str,
    gap_id: str,
) -> dict[str, Any]:
    """Find existing tests/sequences that may cover a specific coverage gap.

    Extracts semantic keywords from the gap's coverpoint and bin names,
    searches the TB index for matching tests and sequences, and assesses
    whether existing testbench infrastructure likely covers the gap.

    Only supports functional coverage gaps. Code coverage gaps (GAP_L/B/C/T/M/A)
    return an error.

    Args:
        project: Project ID or manifest path.
        gap_id: Coverage gap identifier (e.g. 'GAP_0003').

    Returns:
        Envelope with semantic keywords, matching tests/sequences, and
        gap assessment.
    """
    tool = "tb_find_tests_for_gap"

    try:
        reader = get_index_reader(project)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    # Step 1: Get gap detail from coverage_index.json
    try:
        cov_data = reader.read(_COVERAGE_INDEX)
    except IndexNotFoundError as e:
        return error_envelope(tool, project, str(e))

    gaps = cov_data.get("gaps", [])
    gap = next((g for g in gaps if g.get("gap_id") == gap_id), None)

    if gap is None:
        return error_envelope(tool, project, f"Gap not found: {gap_id}")

    cov_type = gap.get("coverage_type", "functional")
    if cov_type != "functional":
        msg = (
            f"tb_find_tests_for_gap only supports functional gaps, "
            f"got coverage_type='{cov_type}' for {gap_id}"
        )
        return error_envelope(tool, project, msg)

    coverpoint = gap.get("coverpoint", "")
    bin_name = gap.get("bin", "")

    # Step 2: Extract semantic keywords
    keywords = extract_semantic_keywords(coverpoint, bin_name)

    # Step 3: Search TB index
    try:
        tb_data = reader.read(_TB_INDEX)
    except IndexNotFoundError as e:
        return error_envelope(tool, project, str(e))

    # Score all sequences
    seq_scores: list[tuple[float, dict]] = []
    for seq in tb_data.get("sequences", []):
        s = score_tb_match(keywords, seq, entry_type="sequence")
        if s > 0:
            methods_out, methods_truncated = _build_methods_output(seq)
            seq_scores.append((s, {
                "name": seq.get("name"),
                "file": seq.get("file"),
                "extends": seq.get("extends"),
                "feature_tags": seq.get("feature_tags"),
                "api_methods": methods_out,
                "api_methods_truncated": methods_truncated,
                "relevance": min(s / 15.0, 1.0),
            }))

    # Score all tests
    test_scores: list[tuple[float, dict]] = []
    for test in tb_data.get("existing_tests", []):
        s = score_tb_match(keywords, test, entry_type="test")
        if s > 0:
            test_scores.append((s, {
                "name": test.get("name"),
                "file": test.get("file"),
                "extends": test.get("extends"),
                "sequences": test.get("sequences"),
                "feature_tags": test.get("feature_tags"),
                "relevance": min(s / 15.0, 1.0),
            }))

    seq_scores.sort(key=lambda x: -x[0])
    test_scores.sort(key=lambda x: -x[0])

    matched_seqs = [s for _, s in seq_scores]
    matched_tests = [t for _, t in test_scores]

    # Step 4: Assess coverage
    assessment, confidence = assess_gap_coverage(gap, matched_seqs, matched_tests)

    # Build evidence
    all_evidence: list[dict] = []
    for seq in matched_seqs[:5]:
        all_evidence.append(
            tb_evidence(
                "sequence",
                seq["name"],
                seq.get("file", ""),
                f"Sequence matching gap {gap_id} keywords",
            )
        )
    for test in matched_tests[:5]:
        all_evidence.append(
            tb_evidence(
                "test",
                test["name"],
                test.get("file", ""),
                f"Test matching gap {gap_id} keywords",
            )
        )

    return envelope(
        tool=tool,
        project=project,
        result={
            "gap_id": gap_id,
            "covergroup": gap.get("covergroup"),
            "coverpoint": coverpoint,
            "bin": bin_name,
            "coverage_type": cov_type,
            "semantic_keywords": keywords,
            "matching_sequences": matched_seqs,
            "matching_tests": matched_tests,
            "gap_assessment": assessment,
            "assessment_confidence": round(confidence, 2),
        },
        evidence=all_evidence,
        truncated=False,
        next_actions=[
            "cov_get_coverpoint_source",
            "tb_get_existing_tests_for_feature",
            "spec_search",
        ],
    )


def _resolve_tb_file(
    allowed_root: Path,
    file_rel: str,
) -> tuple[Path | None, str]:
    """Resolve a TB file path under an allowed root with security checks.

    Returns:
        (resolved_path, status) where status is one of:
        'ok', 'path_traversal', 'access_denied', 'symlink_escape', 'file_not_found'.
    """
    if ".." in file_rel:
        return None, "path_traversal"

    raw = Path(file_rel)
    if raw.is_absolute():
        resolved = raw.resolve(strict=False)
    else:
        resolved = (allowed_root / raw).resolve(strict=False)

    # Security: must be under allowed root
    try:
        resolved.relative_to(allowed_root.resolve())
    except ValueError:
        return None, "access_denied"

    # Security: symlink escape check
    if resolved.is_symlink():
        real = resolved.resolve(strict=False)
        try:
            real.relative_to(allowed_root.resolve())
        except ValueError:
            return None, "symlink_escape"

    if not resolved.is_file():
        return None, "file_not_found"

    return resolved, "ok"


def _read_file_bounded(
    resolved: Path,
    max_lines: int,
    max_bytes: int,
) -> tuple[str, int, bool]:
    """Read a file with line and byte bounds.

    Returns:
        (content, total_lines, truncated)
    """
    with open(resolved, encoding="utf-8", errors="replace") as fh:
        all_lines = fh.readlines()

    total = len(all_lines)
    capped = min(max_lines, _MAX_READ_LINES)
    output_lines = all_lines[:capped]
    content = "".join(output_lines)

    # Byte truncation
    truncated = total > capped
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        content = encoded[:max_bytes].decode("utf-8", errors="ignore")
        content += "\n... [byte-truncated]"
        truncated = True

    return content, total, truncated


def tb_read_source(
    project: str,
    component_type: str,
    name: str,
    max_lines: int = 500,
) -> dict[str, Any]:
    """Read the source code of a testbench component.

    Reads from the TB index with security boundaries (path traversal
    protection, symlink checks, max_lines/max_bytes caps).  Use this to
    inspect sequence API signatures, constraint patterns, and coding style
    for testcase generation.

    Args:
        project: Project ID or manifest path.
        component_type: One of 'sequence', 'test', 'base_test', 'env'.
        name: Component name (e.g. 'wrap_random_len_size_wr_virt_seq')
            or file basename for env components.
        max_lines: Maximum lines to return (default 500, capped at 1000).

    Returns:
        Envelope with component source content, total_lines, truncated,
        and source_mode indicator.
    """
    tool = "tb_read_source"

    # --- Validate component_type ---
    if component_type not in _VALID_COMPONENT_TYPES:
        msg = (
            f"Invalid component_type '{component_type}': "
            f"must be {'|'.join(_VALID_COMPONENT_TYPES)}"
        )
        return error_envelope(tool, project, msg)

    # --- Load TB index ---
    try:
        reader = get_index_reader(project)
        tb_data = reader.read(_TB_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    # --- Look up component by name ---
    file_rel: str | None = None

    if component_type == "sequence":
        seqs = tb_data.get("sequences", [])
        found = next((s for s in seqs if s.get("name") == name), None)
        if found:
            file_rel = found.get("file")
        else:
            available = [s.get("name") for s in seqs]
            msg = (
                f"Component not found: sequence '{name}'. "
                f"Available sequences: {available}"
            )
            return error_envelope(tool, project, msg)

    elif component_type == "test":
        tests = tb_data.get("existing_tests", [])
        found = next((t for t in tests if t.get("name") == name), None)
        if found:
            file_rel = found.get("file")
        else:
            available = [t.get("name") for t in tests]
            msg = (
                f"Component not found: test '{name}'. "
                f"Available tests: {available}"
            )
            return error_envelope(tool, project, msg)

    elif component_type == "base_test":
        bases = tb_data.get("base_tests", [])
        found = next((t for t in bases if t.get("name") == name), None)
        if found:
            file_rel = found.get("file")
        else:
            available = [t.get("name") for t in bases]
            msg = (
                f"Component not found: base_test '{name}'. "
                f"Available base_tests: {available}"
            )
            return error_envelope(tool, project, msg)

    else:  # env
        env_root_idx = tb_data.get("env_root", "")
        file_rel = f"{env_root_idx}/{name}" if env_root_idx else name

    if not file_rel:
        return error_envelope(
            tool, project, f"Could not determine file path for {component_type} '{name}'",
        )

    # --- Load manifest and determine allowed root ---
    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool, project, f"Manifest load failure: {e}")

    # File paths in the TB index are relative to project_root (e.g. "seq_lib/foo.sv").
    # Use project_root as the allowed root so paths resolve correctly.
    allowed_root = manifest.project_root

    if not allowed_root.is_dir():
        allowed_root = manifest.base_dir

    # --- Security validation via SourceResolver ---
    # Use SourceResolver with minimal params to validate path security.
    # The actual file read is done separately to support larger line counts.
    resolver = SourceResolver(allowed_roots=[allowed_root], max_lines=1, max_bytes=1)
    probe = resolver.resolve(file_rel, source_line=1, context_lines=1)

    if probe.status == "access_denied":
        return error_envelope(
            tool, project, f"Access denied: {probe.message}",
        )
    if probe.status == "file_not_found":
        return error_envelope(
            tool, project, f"File not found: {file_rel} (under {allowed_root})",
        )
    if probe.status != "ok":
        return error_envelope(
            tool, project, f"Source resolver error: {probe.status} — {probe.message}",
        )

    # --- Resolve and read file directly with proper bounds ---
    resolved_path, status = _resolve_tb_file(allowed_root, file_rel)
    if resolved_path is None or status != "ok":
        return error_envelope(
            tool, project, f"Cannot read file: {status} — {file_rel}",
        )

    capped_lines = min(max_lines, _MAX_READ_LINES)
    content, total_lines, was_truncated = _read_file_bounded(
        resolved_path, capped_lines, _MAX_READ_BYTES,
    )

    ev = [
        tb_evidence(
            component_type, name, file_rel,
            f"Source code for {component_type} '{name}' ({total_lines} lines)",
        ),
    ]

    return envelope(
        tool=tool,
        project=project,
        result={
            "component_type": component_type,
            "name": name,
            "file": file_rel,
            "total_lines": total_lines,
            "content": content,
            "max_lines": capped_lines,
            "source_mode": "real",
        },
        evidence=ev,
        truncated=was_truncated,
        next_actions=["tb_get_existing_tests_for_feature", "tb_find_tests_for_gap"],
    )
