# WP-3 Coding Agent Prompt: tb_find_tests_for_gap — Gap→TB 语义桥接

> **Phase**: 5a WP-3
> **前置**: WP-1 (sv_parser + build_tb_index.py) 和 WP-2 (MCP tb_tools scope/api_methods) 已完成
> **目标**: 新增 MCP 工具 `tb_find_tests_for_gap`，输入 gap_id，自动返回语义关键词 + 匹配的 tests/sequences + 覆盖评估
> **验收**: `make accept` 全部通过（ruff 0 + mypy 0 + 所有测试 pass + smoke-server）

---

## 背景

Triage 工作流中，DV 工程师需要回答一个核心问题："这个 gap 现有 TB 能不能覆盖？是需要加回归次数还是写新 test？"

当前工具链的断层：

```
triage 输出: GAP_0006 = coverpoint=cp_ahb_burst, bin=wrap8
                                    ↓
现有工具: tb_get_existing_tests_for_feature(feature="wrap")
         → 返回 wrap 相关 sequences（手动选 feature 关键词）
                                    ↓
缺失: 自动从 gap 的 coverpoint/bin 推断该搜什么 + 评估现有 test 是否已覆盖
```

`tb_find_tests_for_gap` 填补这个断层：自动提取语义 → 搜索 TB → 给出评估。

### 已有数据（不要修改）

**axi2ahb coverage_index.json** — 16 个 functional gaps：

| Gap | Coverpoint | Bin |
|---|---|---|
| GAP_0001 | cp_ahb_trans | seq |
| GAP_0002 | cp_ahb_trans | nonseq |
| GAP_0003 | cp_ahb_burst | incr16 |
| GAP_0004 | cp_ahb_burst | wrap16 |
| GAP_0005 | cp_ahb_burst | incr8 |
| GAP_0006 | cp_ahb_burst | wrap8 |
| GAP_0007 | cp_ahb_burst | incr4 |
| GAP_0008 | cp_ahb_burst | wrap4 |
| GAP_0009 | cp_ahb_burst | incr |
| GAP_0010 | cp_ahb_wait | waited |
| GAP_0011 | cp_ahb_wait_delay | wait_6_max |
| GAP_0012 | cp_ahb_wait_delay | wait_3_5 |
| GAP_0013 | cp_ahb_wait_delay | wait_1_2 |
| GAP_0014 | cr_ahb_rw_burst | `* x [incr16 , wrap16 , incr8 , wrap8 , incr4 , wrap4 , incr]` |
| GAP_0015 | cr_ahb_wait_rw | `* x [waited]` |
| GAP_0016 | cr_ahb_trans_rw | `[seq , nonseq] x *` |

**axi2ahb tb_index.json** — sequences 及其 feature_tags：

| Sequence | Feature Tags |
|---|---|
| base_virtual_sequence | burst, error, fixed, read, reset, wrap, write |
| incr_random_len_size_wr_virt_seq | incr, random, read, write |
| wrap_random_len_size_wr_virt_seq | random, read, wrap, write |
| fixed_random_len_size_wr_virt_seq | fixed, random, read, write |
| mixed_random_traffic_virt_seq | backend, burst, frontend, mixed, random, read, traffic, write |
| random_traffic_virt_seq | random, read, traffic, write |
| fifo_full_stress_virt_seq | backend, fifo, frontend, read, stress, write |
| single_write_read_virt_seq | read, single, write |
| frontend_exception_virt_seq | burst, error, frontend, random, read, write |
| backend_exception_virt_seq | backend, error, read, write |
| reset_recovery_virt_seq | read, reset, write |
| bd_write_fd_read_virt_seq | read, write |
| fd_write_bd_read_virt_seq | read, write |

**dma_subsystem coverage_index.json** — 15 个 functional gaps，例如：

| Gap | Coverpoint | Bin |
|---|---|---|
| GAP_0001 | desc_mode_cp | linked_list |
| GAP_0003 | desc_chaining_cp | chain_of_3 |

---

## Task 1: 新增 `lib/semantic_matcher.py`

创建 `lib/semantic_matcher.py`，包含三个核心函数：

### 1.1 `extract_semantic_keywords(coverpoint: str, bin_name: str) -> list[str]`

从 coverpoint 名和 bin 名提取语义关键词。

**算法**：

```python
import re

def extract_semantic_keywords(coverpoint: str, bin_name: str) -> list[str]:
    """Extract semantic keywords from coverpoint and bin names.
    
    Strategy:
    1. Strip common prefixes (cp_, cr_, bin_, auto_)
    2. Split by _ and letter↔digit boundaries
    3. For cross bins (* x [...]), extract inner values
    4. Filter noise words, return deduplicated lowercase keywords
    """
    keywords: set[str] = set()
    
    # --- Process coverpoint name ---
    cp = coverpoint
    # Strip known prefixes
    for prefix in ("cp_", "cr_", "bin_", "auto_"):
        if cp.lower().startswith(prefix):
            cp = cp[len(prefix):]
            break
    
    # Split by underscore
    cp_parts = [p.lower() for p in cp.split("_") if p]
    keywords.update(cp_parts)
    
    # --- Process bin name ---
    bin_str = bin_name.strip()
    
    # Handle cross bin format: "* x [val1 , val2]" or "[v1, v2] x *"
    # Extract the bracketed values
    bracket_values = re.findall(r'\[([^\]]+)\]', bin_str)
    if bracket_values:
        for bv in bracket_values:
            # Split comma-separated values
            for val in bv.split(","):
                val = val.strip()
                if val and val != "*":
                    # Recursively split each value
                    keywords.update(_split_identifier(val))
        # Also extract non-bracket parts (the axis names)
        non_bracket = re.sub(r'\[[^\]]*\]', '', bin_str)
        non_bracket = non_bracket.replace("*", "").replace("x", "").strip()
        for part in non_bracket.split("_"):
            part = part.strip().lower()
            if part and part not in ("", "x"):
                keywords.update(_split_identifier(part))
    else:
        # Simple bin name
        keywords.update(_split_identifier(bin_str))
    
    # Filter noise words
    noise = {"cp", "cr", "bin", "auto", "default", "x"}
    keywords -= noise
    
    return sorted(keywords)


def _split_identifier(name: str) -> list[str]:
    """Split an identifier into semantic parts.
    
    Examples:
        "incr16" → ["incr", "16"]
        "wrap8" → ["wrap", "8"]
        "wait_6_max" → ["wait", "6", "max"]
        "seq" → ["seq"]
        "linked_list" → ["linked", "list"]
    """
    parts: list[str] = []
    name = name.strip()
    
    # Split by underscore first
    for segment in name.split("_"):
        segment = segment.strip()
        if not segment:
            continue
        # Split letter↔digit boundaries: "incr16" → "incr", "16"
        sub_parts = re.split(r'(?<=[a-zA-Z])(?=\d)|(?<=\d)(?=[a-zA-Z])', segment)
        for sp in sub_parts:
            sp = sp.strip().lower()
            if sp:
                parts.append(sp)
    
    return parts
```

**预期输出**（用于测试验证）：

| coverpoint | bin | 预期 keywords |
|---|---|---|
| cp_ahb_trans | seq | ["ahb", "seq", "trans"] |
| cp_ahb_trans | nonseq | ["ahb", "nonseq", "trans"] |
| cp_ahb_burst | incr16 | ["16", "ahb", "burst", "incr"] |
| cp_ahb_burst | wrap8 | ["8", "ahb", "burst", "wrap"] |
| cp_ahb_burst | incr | ["ahb", "burst", "incr"] |
| cp_ahb_wait | waited | ["ahb", "wait", "waited"] |
| cp_ahb_wait_delay | wait_6_max | ["6", "ahb", "delay", "max", "wait"] |
| cp_ahb_wait_delay | wait_3_5 | ["3", "5", "ahb", "delay", "wait"] |
| cr_ahb_rw_burst | `* x [incr16 , wrap16 , incr8 , wrap8 , incr4 , wrap4 , incr]` | ["16", "4", "8", "ahb", "burst", "incr", "rw", "wrap"] |
| cr_ahb_wait_rw | `* x [waited]` | ["ahb", "rw", "wait", "waited"] |
| cr_ahb_trans_rw | `[seq , nonseq] x *` | ["ahb", "nonseq", "rw", "seq", "trans"] |
| desc_mode_cp | linked_list | ["desc", "linked", "list", "mode"] |

### 1.2 `score_tb_match(keywords, entry, entry_type) -> float`

评分函数，衡量 keywords 与 TB entry 的匹配程度。

```python
def score_tb_match(
    keywords: list[str],
    entry: dict,
    entry_type: str = "sequence",  # "sequence" or "test"
) -> float:
    """Score how well a TB entry matches the semantic keywords.
    
    Scoring dimensions:
    - feature_tags exact match: +5 per keyword
    - name substring match: +3 per keyword
    - (sequences only) api_methods name/signature match: +1 per hit
    
    Returns a raw score (higher = better match).
    """
    score = 0.0
    kw_set = set(keywords)
    
    # Feature tags (highest weight)
    tags = {t.lower() for t in entry.get("feature_tags", [])}
    tag_hits = len(kw_set & tags)
    score += tag_hits * 5.0
    
    # Name substring match
    name_lower = entry.get("name", "").lower()
    for kw in keywords:
        if len(kw) >= 3 and kw in name_lower:  # min 3 chars to avoid noise
            score += 3.0
    
    # API method match (sequences only)
    if entry_type == "sequence":
        for method in entry.get("api_methods", []):
            method_name = method.get("name", "").lower()
            method_sig = method.get("signature", "").lower()
            for kw in keywords:
                if len(kw) >= 3 and (kw in method_name or kw in method_sig):
                    score += 1.0
                    break  # one hit per method is enough
    
    return score
```

### 1.3 `assess_gap_coverage(gap, matching_sequences, matching_tests) -> tuple[str, float]`

评估现有 TB 是否可能覆盖 gap。

```python
def assess_gap_coverage(
    gap: dict,
    matching_sequences: list[dict],
    matching_tests: list[dict],
) -> tuple[str, float]:
    """Assess whether existing TB likely covers this gap.
    
    Returns:
        (assessment, confidence) tuple.
        
        assessment is one of:
        - "existing_test_likely_covers": a test directly uses a high-relevance sequence
        - "partial_coverage": high-relevance sequences exist but no test uses them
        - "new_stimulus_needed": no good matches found
        
        confidence is 0.0-1.0.
    """
    if not matching_sequences:
        return "new_stimulus_needed", 0.9
    
    # Find the best sequence relevance
    best_seq_score = max((s.get("relevance", 0) for s in matching_sequences), default=0)
    
    if best_seq_score < 0.3:
        return "new_stimulus_needed", 0.7
    
    # Check if any test directly uses a high-scoring sequence
    high_score_seq_names = {
        s["name"] for s in matching_sequences if s.get("relevance", 0) >= 0.5
    }
    
    for test in matching_tests:
        test_seqs = set(test.get("sequences", []))
        if test_seqs & high_score_seq_names:
            return "existing_test_likely_covers", min(best_seq_score + 0.1, 1.0)
    
    # Good sequences exist but no test uses them
    if best_seq_score >= 0.5:
        return "partial_coverage", best_seq_score
    
    return "new_stimulus_needed", 1.0 - best_seq_score
```

---

## Task 2: 新增 `tb_find_tests_for_gap` 到 `dv_mcp/dv_context_server/tools/tb_tools.py`

在现有 tb_tools.py 中**添加**新函数（不要修改已有的 `tb_get_existing_tests_for_feature`）：

```python
from lib.semantic_matcher import extract_semantic_keywords, score_tb_match, assess_gap_coverage

_COVERAGE_INDEX = "coverage_index.json"


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
        return error_envelope(
            tool, project,
            f"tb_find_tests_for_gap only supports functional gaps, "
            f"got coverage_type='{cov_type}' for {gap_id}"
        )
    
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
            # Build api_methods output (same truncation as tb_get_existing_tests_for_feature)
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
            
            seq_scores.append((s, {
                "name": seq.get("name"),
                "file": seq.get("file"),
                "extends": seq.get("extends"),
                "feature_tags": seq.get("feature_tags"),
                "api_methods": methods_out,
                "api_methods_truncated": methods_truncated,
                "relevance": min(s / 15.0, 1.0),  # normalize to 0-1
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
    
    # Sort by score descending
    seq_scores.sort(key=lambda x: -x[0])
    test_scores.sort(key=lambda x: -x[0])
    
    matched_seqs = [s for _, s in seq_scores]
    matched_tests = [t for _, t in test_scores]
    
    # Step 4: Assess coverage
    assessment, confidence = assess_gap_coverage(gap, matched_seqs, matched_tests)
    
    # Build evidence
    all_evidence: list[dict] = []
    for seq in matched_seqs[:5]:  # top 5
        all_evidence.append(
            tb_evidence("sequence", seq["name"], seq.get("file", ""),
                        f"Sequence matching gap {gap_id} keywords")
        )
    for test in matched_tests[:5]:
        all_evidence.append(
            tb_evidence("test", test["name"], test.get("file", ""),
                        f"Test matching gap {gap_id} keywords")
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
```

**注意**：
- 使用已有的 `_is_base_sequence()` 和 `_MAX_BASE_METHODS` 常量
- 使用已有的 `tb_evidence()` 和 `envelope()` / `error_envelope()`
- relevance 归一化用 `/15.0`（feature_tag 5 + name 3 + methods 的合理上限）

---

## Task 3: 注册新工具到 `dv_mcp/dv_context_server/server.py`

在 `# Testbench tools` 部分添加：

```python
from dv_mcp.dv_context_server.tools.tb_tools import (
    tb_find_tests_for_gap,
    tb_get_existing_tests_for_feature,
)

# ... existing tool_tb_get_existing_tests_for_feature ...

@mcp.tool()
def tool_tb_find_tests_for_gap(
    project: str,
    gap_id: str,
) -> dict:
    """Find existing tests/sequences that may cover a coverage gap.

    Extracts semantic keywords from the gap's coverpoint/bin names,
    searches the TB index, and assesses whether existing tests likely
    cover the gap. Only supports functional coverage gaps.
    """
    return tb_find_tests_for_gap(project, gap_id)
```

---

## Task 4: 测试

### 4.1 新增 `tests/test_semantic_matcher.py`

```python
"""Unit tests for lib/semantic_matcher.py."""

from lib.semantic_matcher import (
    assess_gap_coverage,
    extract_semantic_keywords,
    score_tb_match,
)


class TestExtractSemanticKeywords:
    """Tests for keyword extraction from coverpoint/bin names."""

    def test_simple_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_trans", "seq")
        assert "seq" in kw
        assert "ahb" in kw
        assert "trans" in kw

    def test_bin_with_number_suffix(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr16")
        assert "incr" in kw
        assert "16" in kw
        assert "burst" in kw
        assert "ahb" in kw

    def test_wrap_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "wrap8")
        assert "wrap" in kw
        assert "8" in kw

    def test_incr_only(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr")
        assert "incr" in kw
        assert "burst" in kw

    def test_wait_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_wait", "waited")
        assert "wait" in kw or "waited" in kw

    def test_wait_range_bin(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_wait_delay", "wait_6_max")
        assert "wait" in kw
        assert "6" in kw
        assert "max" in kw

    def test_wait_range_numeric(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_wait_delay", "wait_3_5")
        assert "wait" in kw
        assert "3" in kw
        assert "5" in kw

    def test_cross_bin_star_x_bracket(self) -> None:
        kw = extract_semantic_keywords(
            "cr_ahb_rw_burst",
            "* x [incr16 , wrap16 , incr8 , wrap8 , incr4 , wrap4 , incr]",
        )
        assert "incr" in kw
        assert "wrap" in kw
        assert "16" in kw
        assert "8" in kw
        assert "4" in kw
        assert "rw" in kw
        assert "burst" in kw

    def test_cross_bin_bracket_x_star(self) -> None:
        kw = extract_semantic_keywords(
            "cr_ahb_trans_rw",
            "[seq , nonseq] x *",
        )
        assert "seq" in kw
        assert "nonseq" in kw
        assert "trans" in kw
        assert "rw" in kw

    def test_cross_bin_simple_bracket(self) -> None:
        kw = extract_semantic_keywords(
            "cr_ahb_wait_rw",
            "* x [waited]",
        )
        assert "waited" in kw or "wait" in kw
        assert "rw" in kw

    def test_dma_descriptor_gap(self) -> None:
        kw = extract_semantic_keywords("desc_mode_cp", "linked_list")
        assert "linked" in kw
        assert "list" in kw
        assert "desc" in kw
        assert "mode" in kw

    def test_no_noise_words(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_burst", "incr16")
        assert "cp" not in kw
        assert "cr" not in kw
        assert "bin" not in kw

    def test_nonseq_not_split_wrong(self) -> None:
        kw = extract_semantic_keywords("cp_ahb_trans", "nonseq")
        assert "nonseq" in kw


class TestScoreTbMatch:
    """Tests for TB entry scoring."""

    def test_high_score_tag_match(self) -> None:
        entry = {
            "name": "incr_random_len_size_wr_virt_seq",
            "feature_tags": ["incr", "random", "read", "write"],
            "api_methods": [],
        }
        kw = ["incr", "16", "ahb", "burst"]
        score = score_tb_match(kw, entry, "sequence")
        assert score >= 8.0  # "incr" tag(5) + "incr" name(3) = 8

    def test_low_score_no_match(self) -> None:
        entry = {
            "name": "reset_recovery_virt_seq",
            "feature_tags": ["read", "reset", "write"],
            "api_methods": [],
        }
        kw = ["incr", "16", "burst"]
        score = score_tb_match(kw, entry, "sequence")
        assert score == 0.0

    def test_api_method_bonus(self) -> None:
        entry = {
            "name": "some_seq",
            "feature_tags": ["burst"],
            "api_methods": [
                {"name": "fd_write_burst", "signature": "addr, data, burst", "is_task": True},
            ],
        }
        kw = ["burst", "write"]
        score = score_tb_match(kw, entry, "sequence")
        # "burst" tag(5) + "burst" name(no, "burst" not in "some_seq")
        # + "burst" in api_method_name "fd_write_burst"(1)
        # + "write" in api_method_name "fd_write_burst"(already counted? no, break per method)
        # Actually: "burst" in tags(5) + method "burst" hit(1) + method "write" hit(1) = 7
        assert score >= 5.0

    def test_name_substring_match(self) -> None:
        entry = {
            "name": "wrap_random_len_size_wr_virt_seq",
            "feature_tags": ["wrap"],
            "api_methods": [],
        }
        kw = ["wrap", "8", "burst"]
        score = score_tb_match(kw, entry, "sequence")
        # "wrap" tag(5) + "wrap" in name(3) = 8
        assert score >= 8.0


class TestAssessGapCoverage:
    """Tests for gap coverage assessment."""

    def test_existing_test_likely_covers(self) -> None:
        seqs = [{"name": "incr_seq", "relevance": 0.8}]
        tests = [{"name": "incr_test", "sequences": ["incr_seq"]}]
        assessment, confidence = assess_gap_coverage({}, seqs, tests)
        assert assessment == "existing_test_likely_covers"
        assert confidence > 0.5

    def test_partial_coverage(self) -> None:
        seqs = [{"name": "burst_seq", "relevance": 0.7}]
        tests = []  # no test uses burst_seq
        assessment, confidence = assess_gap_coverage({}, seqs, tests)
        assert assessment == "partial_coverage"

    def test_new_stimulus_needed_no_matches(self) -> None:
        assessment, confidence = assess_gap_coverage({}, [], [])
        assert assessment == "new_stimulus_needed"
        assert confidence > 0.5

    def test_new_stimulus_low_relevance(self) -> None:
        seqs = [{"name": "weak_seq", "relevance": 0.1}]
        tests = []
        assessment, _ = assess_gap_coverage({}, seqs, tests)
        assert assessment == "new_stimulus_needed"
```

### 4.2 新增 `tests/test_tb_find_tests_for_gap.py`

```python
"""Integration tests for tb_find_tests_for_gap MCP tool."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_find_tests_for_gap

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"
DMA = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestAxi2ahbBurstGaps:
    """Burst-type gaps should match incr/wrap sequences."""

    def test_incr16_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0003")
        assert result["ok"] is True
        r = result["result"]
        assert "incr" in r["semantic_keywords"]
        assert "16" in r["semantic_keywords"]
        seq_names = [s["name"] for s in r["matching_sequences"]]
        assert "incr_random_len_size_wr_virt_seq" in seq_names

    def test_wrap8_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0006")
        assert result["ok"] is True
        r = result["result"]
        assert "wrap" in r["semantic_keywords"]
        assert "8" in r["semantic_keywords"]
        seq_names = [s["name"] for s in r["matching_sequences"]]
        assert "wrap_random_len_size_wr_virt_seq" in seq_names

    def test_burst_gap_assessment(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0003")
        r = result["result"]
        # incr test exists and uses incr sequence
        assert r["gap_assessment"] == "existing_test_likely_covers"

    def test_incr_only_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0009")
        assert result["ok"] is True
        assert "incr" in result["result"]["semantic_keywords"]


class TestAxi2ahbWaitGaps:
    """Wait-related gaps."""

    def test_wait_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0010")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert any("wait" in k for k in kw)

    def test_wait_delay_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0011")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "wait" in kw or "6" in kw


class TestAxi2ahbCrossGaps:
    """Cross coverage gaps with bracket format."""

    def test_cross_rw_burst_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0014")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "incr" in kw
        assert "wrap" in kw
        seq_names = [s["name"] for s in result["result"]["matching_sequences"]]
        assert len(seq_names) > 0

    def test_cross_wait_rw_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0015")
        assert result["ok"] is True

    def test_cross_trans_rw_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0016")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "seq" in kw or "nonseq" in kw


class TestDmaSubsystemGaps:
    """Backward compatibility with dma_subsystem mock data."""

    def test_dma_linked_list_gap(self) -> None:
        result = tb_find_tests_for_gap(DMA, "GAP_0001")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "linked" in kw
        assert "list" in kw

    def test_dma_chain_gap(self) -> None:
        result = tb_find_tests_for_gap(DMA, "GAP_0003")
        assert result["ok"] is True
        assert "chain" in result["result"]["semantic_keywords"]


class TestErrorCases:
    """Error handling."""

    def test_nonexistent_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_9999")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_code_coverage_gap_rejected(self) -> None:
        result = tb_find_tests_for_gap(DMA, "GAP_L001")
        assert result["ok"] is False
        assert "functional" in result["error"].lower()

    def test_bad_project(self) -> None:
        result = tb_find_tests_for_gap("nonexistent_manifest.yaml", "GAP_0001")
        assert result["ok"] is False
```

### 4.3 更新 `tests/test_tool_contracts.py`

在已有文件中添加：

```python
class TestTbFindTestsForGapContract:
    def test_success(self) -> None:
        resp = tb_find_tests_for_gap(AXI2AHB_PROJECT, "GAP_0003")
        _check_success(resp, "tb_find_tests_for_gap")

    def test_error_bad_gap(self) -> None:
        resp = tb_find_tests_for_gap(PROJECT, "GAP_9999")
        _check_error(resp, "tb_find_tests_for_gap")
```

记得在文件顶部添加 import：
```python
from dv_mcp.dv_context_server.tools.tb_tools import tb_find_tests_for_gap
```

---

## Task 5: 文档更新

### 5.1 CLAUDE.md

将 Phase 5a 段落中的 WP-2 状态更新为 Done，添加 WP-3：

```markdown
- **WP-2 MCP TB Tool Integration** (Done): `tb_get_existing_tests_for_feature` upgraded with scope filter and api_methods display
- **WP-3 Gap→TB Semantic Bridge** (In Progress): `tb_find_tests_for_gap` — auto-extracts semantic keywords from coverpoint/bin names, searches TB index, assesses coverage; `lib/semantic_matcher.py` module
```

### 5.2 README.md

更新 Phase 5a 状态描述，添加 WP-3 信息。

---

## 验证步骤

```bash
source .venv/bin/activate

# 1. Lint + typecheck
ruff check .
ruff format --check .
mypy lib/ scripts/ dv_mcp/

# 2. 全部测试
python -m pytest tests/ -v

# 3. 新工具快速验证
python -c "
from dv_mcp.dv_context_server.tools.tb_tools import tb_find_tests_for_gap
from dv_mcp.dv_context_server.services.project_loader import clear_cache

clear_cache()
r = tb_find_tests_for_gap('mock_data/axi2ahb/project_manifest.yaml', 'GAP_0006')
print(f'ok={r[\"ok\"]}')
print(f'keywords={r[\"result\"][\"semantic_keywords\"]}')
print(f'assessment={r[\"result\"][\"gap_assessment\"]}')
print(f'sequences={[s[\"name\"] for s in r[\"result\"][\"matching_sequences\"]]}')
print(f'tests={[t[\"name\"] for t in r[\"result\"][\"matching_tests\"]]}')
"

# 4. Smoke server
PYTHONPATH=. python scripts/smoke_server.py
# 预期输出: MCP server smoke OK: 12 tools registered（新增 1 个）

# 5. Full accept
make accept
```

---

## 文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `lib/semantic_matcher.py` | **新增** | 关键词提取 + 评分 + 评估逻辑 |
| `dv_mcp/dv_context_server/tools/tb_tools.py` | **修改** | 新增 `tb_find_tests_for_gap` 函数 + `_COVERAGE_INDEX` 常量 |
| `dv_mcp/dv_context_server/server.py` | **修改** | 注册 `tool_tb_find_tests_for_gap`，更新 import |
| `tests/test_semantic_matcher.py` | **新增** | ~25 个单元测试 |
| `tests/test_tb_find_tests_for_gap.py` | **新增** | ~15 个集成测试 |
| `tests/test_tool_contracts.py` | **修改** | 新增 2 个 contract test |
| `CLAUDE.md` | **修改** | 更新 WP-3 状态 |
| `README.md` | **修改** | 更新状态 |

---

## 注意事项

1. **不要修改** `lib/sv_parser.py`、`scripts/build_tb_index.py`（WP-1）
2. **不要修改** `tb_get_existing_tests_for_feature` 的已有逻辑（WP-2）
3. **不要修改** `lib/source_resolver.py`、`lib/project_registry.py`（Phase 4）
4. **ruff 0 + mypy 0** 是硬性要求
5. **不要自动 commit**，完成所有验证后报告结果
6. `smoke-server` 应显示 **12 tools registered**（11 → 12）
7. `lib/semantic_matcher.py` 的 `extract_semantic_keywords` 函数是纯函数，不依赖任何项目数据，应可独立测试
8. 关键词提取是**启发式的**——不追求完美，追求"在大多数情况下给出有用结果"。评估结果附带 `assessment_confidence` 字段，让 AI 知道何时该信任、何时该质疑
