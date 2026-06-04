"""Semantic matching between coverage gaps and testbench resources.

Extracts keywords from coverpoint/bin names, scores TB entries against
those keywords, and assesses whether existing tests likely cover a gap.
"""

from __future__ import annotations

import re


def _split_identifier(name: str) -> list[str]:
    """Split an identifier into semantic parts.

    Splits by underscore and letter->digit boundaries.

    Examples:
        "incr16" -> ["incr", "16"]
        "wrap8" -> ["wrap", "8"]
        "wait_6_max" -> ["wait", "6", "max"]
        "seq" -> ["seq"]
        "linked_list" -> ["linked", "list"]
    """
    parts: list[str] = []
    name = name.strip()

    for segment in name.split("_"):
        segment = segment.strip()
        if not segment:
            continue
        sub_parts = re.split(
            r"(?<=[a-zA-Z])(?=\d)|(?<=\d)(?=[a-zA-Z])", segment
        )
        for sp in sub_parts:
            sp = sp.strip().lower()
            if sp:
                parts.append(sp)

    return parts


def extract_semantic_keywords(coverpoint: str, bin_name: str) -> list[str]:
    """Extract semantic keywords from coverpoint and bin names.

    Strategy:
    1. Strip common prefixes (cp_, cr_, bin_, auto_)
    2. Split by _ and letter->digit boundaries
    3. For cross bins (* x [...]), extract inner values
    4. Filter noise words, return deduplicated sorted lowercase keywords
    """
    keywords: set[str] = set()

    # --- Process coverpoint name ---
    cp = coverpoint
    for prefix in ("cp_", "cr_", "bin_", "auto_"):
        if cp.lower().startswith(prefix):
            cp = cp[len(prefix):]
            break

    cp_parts = [p.lower() for p in cp.split("_") if p]
    keywords.update(cp_parts)

    # --- Process bin name ---
    bin_str = bin_name.strip()

    # Handle cross bin format: "* x [val1 , val2]" or "[v1, v2] x *"
    bracket_values = re.findall(r"\[([^\]]+)\]", bin_str)
    if bracket_values:
        for bv in bracket_values:
            for val in bv.split(","):
                val = val.strip()
                if val and val != "*":
                    keywords.update(_split_identifier(val))
        # Extract non-bracket parts (axis names)
        non_bracket = re.sub(r"\[[^\]]*\]", "", bin_str)
        non_bracket = non_bracket.replace("*", "").replace("x", "").strip()
        for part in non_bracket.split("_"):
            part = part.strip().lower()
            if part and part not in ("", "x"):
                keywords.update(_split_identifier(part))
    else:
        keywords.update(_split_identifier(bin_str))

    # Filter noise words
    noise = {"cp", "cr", "bin", "auto", "default", "x"}
    keywords -= noise

    return sorted(keywords)


def score_tb_match(
    keywords: list[str],
    entry: dict,
    entry_type: str = "sequence",
) -> float:
    """Score how well a TB entry matches the semantic keywords.

    Scoring dimensions:
    - feature_tags exact match: +5 per keyword
    - name substring match (min 3 chars): +3 per keyword
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
        if len(kw) >= 3 and kw in name_lower:
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


def assess_gap_coverage(
    gap: dict,
    matching_sequences: list[dict],
    matching_tests: list[dict],
) -> tuple[str, float]:
    """Assess whether existing TB likely covers this gap.

    Returns:
        (assessment, confidence) tuple.

        assessment is one of:
        - "existing_test_likely_covers": a test directly uses a
          high-relevance sequence
        - "partial_coverage": high-relevance sequences exist but no test
          uses them
        - "new_stimulus_needed": no good matches found

        confidence is 0.0-1.0.
    """
    if not matching_sequences:
        return "new_stimulus_needed", 0.9

    best_seq_score = max(
        (s.get("relevance", 0) for s in matching_sequences), default=0
    )

    if best_seq_score < 0.3:
        return "new_stimulus_needed", 0.7

    high_score_seq_names = {
        s["name"] for s in matching_sequences if s.get("relevance", 0) >= 0.5
    }

    for test in matching_tests:
        test_seqs = set(test.get("sequences", []))
        if test_seqs & high_score_seq_names:
            return "existing_test_likely_covers", min(
                best_seq_score + 0.1, 1.0
            )

    if best_seq_score >= 0.5:
        return "partial_coverage", best_seq_score

    return "new_stimulus_needed", 1.0 - best_seq_score
