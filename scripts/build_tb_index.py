#!/usr/bin/env python3
"""Build TB index from real UVM SystemVerilog sources.

Manifest-driven CLI that parses UVM testbench directories and generates
tb_index.json compatible with the MCP tb_get_existing_tests_for_feature tool.

Usage:
    python scripts/build_tb_index.py --manifest mock_data/axi2ahb/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from lib.manifest import Manifest, ManifestError
from lib.sv_parser import (
    ParsedFile,
    SVClassInfo,
    classify_uvm_role,
    extract_config_knobs,
    infer_feature_tags,
    link_tests_to_sequences,
    parse_directory,
    resolve_extends_chain,
)


def _file_header_comment(raw_text: str) -> str:
    """Extract the first meaningful comment from a file as fallback description."""
    for line in raw_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") and len(stripped) > 4:
            text = stripped[2:].strip()
            # Skip boilerplate lines
            if any(
                skip in text.lower()
                for skip in ("copyright", "license", "author", "date", "company", "$")
            ):
                continue
            if len(text) > 10:
                return text
        if stripped.startswith("/*"):
            # Multi-line comment block — grab first meaningful line
            for cline in stripped.split("\n"):
                cline = cline.strip().lstrip("/*").strip()
                if len(cline) > 10 and not any(
                    skip in cline.lower()
                    for skip in ("copyright", "license", "author", "date", "company", "$")
                ):
                    return cline
    return ""


def _class_description(raw_text: str, class_name: str) -> str:
    """Extract a description for a class from the file text.

    Strategy:
    1. Look for a // comment immediately before the class declaration.
    2. Fall back to the file header comment.
    """
    # Find the class declaration position
    class_match = re.search(rf"\bclass\s+{re.escape(class_name)}\b", raw_text)
    if not class_match:
        return _file_header_comment(raw_text)

    pos = class_match.start()
    prefix = raw_text[:pos].rstrip()
    lines = prefix.split("\n")

    # Look backward for the last comment line before the class
    for i in range(len(lines) - 1, max(len(lines) - 8, -1), -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            text = stripped[2:].strip()
            if len(text) > 5:
                return text
        # Hit a non-comment, non-blank line — stop looking
        break

    return _file_header_comment(raw_text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build TB index from UVM SystemVerilog sources"
    )
    parser.add_argument(
        "--manifest", required=True, help="Path to project manifest YAML"
    )
    parser.add_argument(
        "--out", default=None, help="Output directory (default: manifest index_path)"
    )
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # Step 1: Load manifest
    # -----------------------------------------------------------------------
    manifest_path = Path(args.manifest)
    try:
        manifest = Manifest.load(manifest_path)
    except ManifestError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    project_root = manifest.project_root
    if not project_root.exists():
        print(
            f"ERROR: project_root does not exist: {project_root}\n"
            f"  Set the environment variable or update project_root in the manifest.",
            file=sys.stderr,
        )
        return 1

    # -----------------------------------------------------------------------
    # Step 2: Read testbench paths from manifest
    # -----------------------------------------------------------------------
    tb_conf: dict = manifest.get("testbench") or {}

    env_root_str: str | None = tb_conf.get("env_root")
    base_test_field: str | None = tb_conf.get("base_test")
    seq_root_str: str | None = tb_conf.get("sequence_root")
    agent_root_str: str | None = tb_conf.get("agent_root")
    config_root_str: str | None = tb_conf.get("config_root")
    test_root_str: str | None = tb_conf.get("test_root")
    index_path_str: str | None = tb_conf.get("index_path")

    # Resolve paths against project_root
    env_root = manifest.resolve_path(env_root_str) if env_root_str else None
    seq_root = manifest.resolve_path(seq_root_str) if seq_root_str else None
    agent_root = manifest.resolve_path(agent_root_str) if agent_root_str else None
    config_root = manifest.resolve_path(config_root_str) if config_root_str else None
    test_root = manifest.resolve_path(test_root_str) if test_root_str else None

    # -----------------------------------------------------------------------
    # Step 3: Determine output directory
    # -----------------------------------------------------------------------
    if args.out:
        out_dir = Path(args.out)
    elif index_path_str:
        out_dir = manifest.resolve_path(index_path_str) or (project_root / index_path_str)
    else:
        out_dir = project_root / ".dv_ai_index"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building TB index for project: {manifest.project}")
    print(f"  Project root: {project_root}")
    print(f"  env_root:     {env_root or '(not set)'}")
    print(f"  test_root:    {test_root or '(not set)'}")
    print(f"  sequence_root:{seq_root or '(not set)'}")
    print(f"  agent_root:   {agent_root or '(not set)'}")
    print(f"  config_root:  {config_root or '(not set)'}")
    print(f"  Output:       {out_dir}")

    # -----------------------------------------------------------------------
    # Step 4: Parse all SV files in TB directories
    # -----------------------------------------------------------------------
    print("\nParsing SV files...")
    all_parsed: list[ParsedFile] = []
    dirs_to_parse = [
        ("env", env_root),
        ("sequences", seq_root),
        ("agent", agent_root),
        ("config", config_root),
        ("tests", test_root),
    ]
    for label, dirpath in dirs_to_parse:
        if dirpath is None:
            continue
        if not dirpath.exists():
            print(f"  WARNING: {label} directory not found: {dirpath}")
            continue
        parsed = parse_directory(dirpath, project_root=project_root)
        print(f"  {label}: {len(parsed)} files from {dirpath}")
        all_parsed.extend(parsed)

    # -----------------------------------------------------------------------
    # Step 5: Flatten classes, modules, raw texts
    # -----------------------------------------------------------------------
    all_classes: list[SVClassInfo] = []
    raw_texts: dict[str, str] = {}

    for pf in all_parsed:
        all_classes.extend(pf.classes)
        if pf.raw_text:
            raw_texts[pf.file] = pf.raw_text

    print(f"\nTotal: {len(all_classes)} classes from {len(all_parsed)} files")

    # -----------------------------------------------------------------------
    # Step 6: Resolve extends chains and classify roles
    # -----------------------------------------------------------------------
    ancestry = resolve_extends_chain(all_classes)

    roles: dict[str, list[SVClassInfo]] = {}
    for cls in all_classes:
        role = classify_uvm_role(cls, ancestry)
        roles.setdefault(role, []).append(cls)

    for role, cls_list in sorted(roles.items()):
        if cls_list:
            print(f"  {role}: {len(cls_list)} classes")

    # -----------------------------------------------------------------------
    # Step 7: Classify test classes
    # -----------------------------------------------------------------------
    test_classes = roles.get("test", [])

    # Determine base test: match manifest base_test field against file path
    base_test_classes: list[SVClassInfo] = []
    concrete_test_classes: list[SVClassInfo] = []

    if base_test_field:
        base_test_norm = base_test_field.replace("\\", "/")
        for cls in test_classes:
            cls_file_norm = cls.file.replace("\\", "/")
            if (
                base_test_norm in cls_file_norm
                or cls_file_norm.endswith(base_test_norm)
            ):
                base_test_classes.append(cls)
            else:
                concrete_test_classes.append(cls)
    else:
        # Heuristic: if a test class is extended by other test classes, it's a base
        for cls in test_classes:
            is_base = any(
                cls.name in ancestry.get(other.name, [])
                for other in test_classes
                if other.name != cls.name
            )
            if is_base:
                base_test_classes.append(cls)
            else:
                concrete_test_classes.append(cls)

    # -----------------------------------------------------------------------
    # Step 8: Classify sequences
    # -----------------------------------------------------------------------
    seq_classes = roles.get("sequence", [])

    # -----------------------------------------------------------------------
    # Step 9: Link tests to sequences
    # -----------------------------------------------------------------------
    test_seq_links = link_tests_to_sequences(
        concrete_test_classes + base_test_classes, seq_classes, raw_texts
    )

    # -----------------------------------------------------------------------
    # Step 10: Build output entries
    # -----------------------------------------------------------------------

    # Base tests
    base_tests_out: list[dict] = []
    for cls in base_test_classes:
        desc = _class_description(raw_texts.get(cls.file, ""), cls.name)
        base_tests_out.append(
            {
                "name": cls.name,
                "file": cls.file,
                "extends": cls.extends or "",
                "description": desc,
                "config_knobs": [],  # Populated below if relevant
            }
        )

    # Sequences
    sequences_out: list[dict] = []
    for cls in seq_classes:
        desc = _class_description(raw_texts.get(cls.file, ""), cls.name)
        api_methods = [
            {
                "name": m.name,
                "signature": m.signature,
                "is_task": m.is_task,
                "description": m.description,
            }
            for m in cls.methods
        ]
        sequences_out.append(
            {
                "name": cls.name,
                "file": cls.file,
                "extends": cls.extends or "",
                "description": desc,
                "feature_tags": cls.feature_tags,
                "api_methods": api_methods,
            }
        )

    # Existing tests (concrete)
    existing_tests_out: list[dict] = []
    for cls in concrete_test_classes:
        linked_seqs = test_seq_links.get(cls.name, [])
        test_tags = infer_feature_tags(cls.name, cls.file)
        # Merge tags from linked sequences
        for seq_name in linked_seqs:
            for seq_cls in seq_classes:
                if seq_cls.name == seq_name:
                    for tag in seq_cls.feature_tags:
                        if tag not in test_tags:
                            test_tags.append(tag)
        existing_tests_out.append(
            {
                "name": cls.name,
                "file": cls.file,
                "extends": cls.extends or "",
                "sequences": linked_seqs,
                "feature_tags": sorted(set(test_tags)),
            }
        )

    # Config knobs
    config_classes = roles.get("object", []) + roles.get("unknown", [])
    # Filter to classes that look like config classes (name contains 'config' or 'cfg')
    config_like = [
        cls
        for cls in config_classes
        if "config" in cls.name.lower() or "cfg" in cls.name.lower()
    ]
    knobs = extract_config_knobs(config_like, raw_texts)

    # -----------------------------------------------------------------------
    # Step 11: Build and write index
    # -----------------------------------------------------------------------
    index: dict = {
        "schema_version": "tb_index.v1",
        "env_root": env_root_str or "",
        "sequence_root": seq_root_str or "",
        "generated_at": datetime.now(UTC).isoformat(),
        "base_tests": base_tests_out,
        "sequences": sequences_out,
        "existing_tests": existing_tests_out,
        "config_knobs": knobs,
    }

    out_file = out_dir / "tb_index.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nWrote: {out_file}")
    print(f"  base_tests:     {len(base_tests_out)}")
    print(f"  existing_tests: {len(existing_tests_out)}")
    print(f"  sequences:      {len(sequences_out)}")
    print(f"  config_knobs:   {len(knobs)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
