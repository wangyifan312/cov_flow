#!/usr/bin/env python3
"""Build spec index from a functional specification markdown file.

Parses markdown headings (# and ##) to produce spec_index.json compatible
with the MCP spec_search and spec_get_section tools.

Usage:
    python scripts/build_spec_index.py --manifest mock_data/dma_subsystem/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lib.manifest import Manifest, ManifestError

# ---------------------------------------------------------------------------
# Heading extraction
# ---------------------------------------------------------------------------

RE_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


def _to_section_id(title: str) -> str:
    """Convert a heading title to a snake_case section_id.

    Examples:
        '1. DMA Subsystem Overview' -> 'spec_subsystem_overview'
        '3. Linked-List Descriptor Mode' -> 'spec_linked_list_descriptor_mode'
        '10. AXI Burst Configuration' -> 'spec_axi_burst_configuration'
    """
    # Strip leading number and period: "1. ", "10. "
    text = re.sub(r"^\d+\.\s*", "", title).strip()
    # Strip common prefixes that add noise
    for prefix in ("DMA ", "dma "):
        if text.startswith(prefix):
            text = text[len(prefix):]
    # Replace hyphens and spaces with underscores
    text = re.sub(r"[-\s]+", "_", text)
    # Lowercase, keep only alphanumeric and underscores
    text = re.sub(r"[^a-z0-9_]", "", text.lower())
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text).strip("_")
    return f"spec_{text}"


def _infer_feature_tags(title: str, body: str) -> list[str]:
    """Infer feature tags from heading title and section body text."""
    text = (title + " " + body).lower()
    tag_keywords: dict[str, list[str]] = {
        "dma": ["dma"],
        "overview": ["overview"],
        "descriptor": ["descriptor"],
        "normal_mode": ["normal descriptor", "normal mode"],
        "descriptor_format": ["descriptor format", "descriptor layout"],
        "linked_list": ["linked-list", "linked list", "chaining"],
        "scatter_gather": ["scatter-gather", "scatter gather"],
        "chaining": ["chaining", "back-to-back", "pipeline"],
        "alignment": ["alignment", "misaligned"],
        "error": ["error", "bus error"],
        "interrupt": ["interrupt", "irq"],
        "coalescing": ["coalescing", "coal"],
        "masking": ["mask", "masked"],
        "power": ["power", "clock gating", "retention"],
        "clock_gating": ["clock gating"],
        "retention": ["retention"],
        "burst": ["burst"],
        "axi": ["axi"],
        "wrap": ["wrap"],
        "increment": ["incr"],
        "performance": ["performance", "throughput"],
        "back_to_back": ["back-to-back"],
        "completion": ["completion"],
        "timeout": ["timeout"],
    }
    tags: set[str] = set()
    for tag, keywords in tag_keywords.items():
        for kw in keywords:
            if kw in text:
                tags.add(tag)
                break
    return sorted(tags)


def _extract_summary(body: str) -> str:
    """Extract the first non-empty paragraph as a summary (max 200 chars)."""
    lines = body.strip().split("\n")
    summary_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if summary_lines:
                break
            continue
        # Skip markdown lists and code blocks
        if stripped.startswith(("- ", "* ", "```", "    ")):
            continue
        summary_lines.append(stripped)
    summary = " ".join(summary_lines)
    if len(summary) > 200:
        summary = summary[:197] + "..."
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_spec_sections(md_text: str) -> list[dict]:
    """Parse a markdown spec into indexed sections.

    Returns a list of section dicts with: section_id, title, page_range
    (expressed as line range string), feature_tags, and summary.
    """
    headings = list(RE_HEADING.finditer(md_text))
    sections: list[dict] = []

    for idx, m in enumerate(headings):
        title = m.group(2).strip()

        # Determine body: text from after this heading to the next heading
        body_start = m.end()
        body_end = headings[idx + 1].start() if idx + 1 < len(headings) else len(md_text)
        body = md_text[body_start:body_end].strip()

        # Line range
        start_line = md_text[:m.start()].count("\n") + 1
        end_line = md_text[:body_end].count("\n") + 1
        # Page range is expressed as line range in markdown sources
        page_range = f"{start_line}-{end_line}"

        section_id = _to_section_id(title)
        summary = _extract_summary(body)
        feature_tags = _infer_feature_tags(title, body)

        sections.append(
            {
                "section_id": section_id,
                "title": title,
                "page_range": page_range,
                "feature_tags": feature_tags,
                "summary": summary,
            }
        )

    return sections


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build spec index from a functional specification markdown file"
    )
    parser.add_argument(
        "--manifest", required=True, help="Path to project manifest YAML"
    )
    parser.add_argument(
        "--out", default=None, help="Output directory (default: manifest index_path)"
    )
    args = parser.parse_args()

    # Load manifest
    manifest_path = Path(args.manifest)
    try:
        manifest = Manifest.load(manifest_path)
    except ManifestError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    project_root = manifest.project_root

    # Read spec path from manifest
    spec_path_str: str | None = manifest.get("spec", "fs", "path")
    if not spec_path_str:
        print("ERROR: manifest has no spec.fs.path", file=sys.stderr)
        return 1

    spec_file = manifest.resolve_path(spec_path_str)
    if spec_file is None or not spec_file.exists():
        print(f"ERROR: spec file not found: {spec_file}", file=sys.stderr)
        return 1

    # Determine output directory
    index_path_str: str | None = manifest.get("spec", "fs", "index_path")
    if args.out:
        out_dir = Path(args.out)
    elif index_path_str:
        out_dir = manifest.resolve_path(index_path_str) or (project_root / index_path_str)
    else:
        out_dir = project_root / ".dv_ai_index"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building spec index for project: {manifest.project}")
    print(f"  Spec file: {spec_file}")
    print(f"  Output:    {out_dir}")

    # Parse markdown
    md_text = spec_file.read_text(encoding="utf-8")
    sections = parse_spec_sections(md_text)

    # Build index
    index = {
        "schema_version": "spec_index.v1",
        "source": spec_path_str,
        "sections": sections,
    }

    out_file = out_dir / "spec_index.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nWrote: {out_file}")
    print(f"  sections: {len(sections)}")
    for sec in sections:
        print(f"    {sec['section_id']}: {sec['title']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
