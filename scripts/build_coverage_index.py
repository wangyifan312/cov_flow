#!/usr/bin/env python3
"""Build coverage index from a real URG HTML report.

Usage:
    python scripts/build_coverage_index.py --manifest mock_data/axi2ahb/project_manifest.yaml
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

from lib.urg_parser import (
    assemble_gaps,
    build_coverage_gaps,
    build_coverage_index,
    parse_code_coverage,
    parse_functional_coverage,
    parse_group_list,
    parse_module_list,
    parse_session_xml,
    write_index_files,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build coverage index from URG HTML report")
    parser.add_argument("--manifest", required=True, help="Path to project manifest YAML")
    parser.add_argument("--out", default=None, help="Output directory (default: from manifest)")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root for path normalization (default: manifest parent directory)",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    project_dir = manifest_path.parent
    report_dir = project_dir / manifest["coverage"]["reports_root"]
    if not report_dir.exists():
        print(f"ERROR: coverage report dir not found: {report_dir}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else project_dir / ".dv_ai_index"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine project root for path normalization
    if args.project_root:
        project_root = args.project_root
    else:
        project_root = str(project_dir.resolve())

    # Step 1: Parse session.xml
    print(f"Parsing session.xml from {report_dir}...")
    session = parse_session_xml(report_dir)
    print(f"  Version: {session['version']}")
    print(f"  Top instance: {session['top_instance']}")
    for ctype, m in session["metrics"].items():
        print(f"  {ctype}: {m['covered']}/{m['total']} ({m['percent']}%)")

    # Step 2: Parse structure
    print("Parsing module list...")
    modules = parse_module_list(report_dir)
    print(f"  Found {len(modules)} modules")
    for mod in modules:
        print(f"    {mod.name} → {mod.mod_file} (score: {mod.score})")

    print("Parsing group list...")
    groups = parse_group_list(report_dir)
    print(f"  Found {len(groups)} functional coverage groups")
    for grp in groups:
        print(f"    {grp.name} → {grp.grp_file} (score: {grp.score}%)")

    # Step 3: Parse functional coverage from grp*.html
    print("\nParsing functional coverage from grp*.html files...")
    functional_gaps = parse_functional_coverage(report_dir, groups)
    print(f"  Found {len(functional_gaps)} functional coverage gaps")

    # Step 4: Parse code coverage from mod*.html (with Synopsys filtering)
    print("Parsing code coverage from mod*.html files...")
    code_coverage_gaps = parse_code_coverage(report_dir, modules, project_root)
    print(f"  Found {len(code_coverage_gaps)} code coverage gaps")

    # Step 5: Assemble gaps
    print("\nAssembling gaps...")
    all_gaps = assemble_gaps(functional_gaps, code_coverage_gaps, project_root)
    print(f"  Total gaps: {len(all_gaps)}")

    # Step 6: Build index and gaps JSON
    print("\nBuilding coverage index...")
    project_name = manifest["project"]
    report_id = manifest["coverage"]["default_report_id"]

    index = build_coverage_index(
        project=project_name,
        report_id=report_id,
        report_dir=report_dir,
        modules=modules,
        groups=groups,
        gaps=all_gaps,
        metrics=session.get("metrics", {}),
    )

    gaps_output = build_coverage_gaps(all_gaps, project_name, report_id)

    # Write output files
    index_path, gaps_path = write_index_files(out_dir, index, gaps_output)
    print(f"\nWrote: {index_path}")
    print(f"Wrote: {gaps_path}")

    # Also write coverage_gaps.json to project root for compatibility
    project_gaps_path = project_dir / "coverage_gaps.json"
    with open(project_gaps_path, "w", encoding="utf-8") as f:
        json.dump(gaps_output, f, indent=2)
    print(f"Wrote: {project_gaps_path}")

    # Summary
    print("\n=== Coverage Gap Summary ===")
    for cov_type, count in index["summary"]["gap_counts_by_type"].items():
        print(f"  {cov_type}: {count}")
    print(f"  TOTAL: {index['summary']['total_gaps']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
