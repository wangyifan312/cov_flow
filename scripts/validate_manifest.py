#!/usr/bin/env python3
"""Validate a project manifest against its JSON Schema and check path existence.

Usage:
    python scripts/validate_manifest.py --manifest path/to/project_manifest.yaml
    python scripts/validate_manifest.py --manifest path/to/project_manifest.yaml --out report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path for lib imports
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.manifest import Manifest, ManifestError  # noqa: E402
from lib.schema_validator import load_schema, validate  # noqa: E402


def check_paths(manifest: Manifest) -> tuple[list[dict], list[dict]]:
    """Check existence of all configured data paths.

    Returns:
        Tuple of (found_paths, missing_paths), each a list of dicts
        with 'label' and 'path' keys.
    """
    found: list[dict] = []
    missing: list[dict] = []

    all_paths = manifest.get_all_data_paths()
    for label, resolved_path in all_paths.items():
        if resolved_path is None:
            continue
        entry = {"label": label, "path": str(resolved_path)}
        if resolved_path.exists():
            found.append(entry)
        else:
            missing.append(entry)

    return found, missing


def check_simulation_block(manifest: Manifest) -> list[dict]:
    """Validate the simulation block if policy allows running simulations.

    Returns:
        List of error dicts (empty if valid).
    """
    errors: list[dict] = []
    policy = manifest.policy
    sim_config = manifest.simulation_config

    allow_sim = policy.get("allow_running_simulation", False)

    if allow_sim and not sim_config:
        errors.append({
            "path": "simulation",
            "message": "policy.allow_running_simulation is true but simulation block is missing",
            "validator": "simulation_block",
        })
        return errors

    if sim_config:
        # Check that command templates are non-empty
        for template_key in ["compile_cmd_template", "run_cmd_template", "coverage_cmd_template"]:
            template = sim_config.get(template_key, "")
            if not template or not template.strip():
                errors.append({
                    "path": f"simulation.{template_key}",
                    "message": f"Simulation template '{template_key}' is empty or missing",
                    "validator": "simulation_block",
                })

    return errors


def build_report(
    manifest_path: Path,
    schema_errors: list[dict],
    found_paths: list[dict],
    missing_paths: list[dict],
    simulation_errors: list[dict] | None = None,
) -> dict:
    """Build the validation report as a structured dict."""
    all_errors = list(schema_errors)
    if simulation_errors:
        all_errors.extend(simulation_errors)

    ok = len(all_errors) == 0
    warnings = []

    # Missing paths are warnings (some may not exist yet, e.g. indexes)
    for mp in missing_paths:
        warnings.append({
            "type": "missing_path",
            "label": mp["label"],
            "path": mp["path"],
            "message": f"Path does not exist: {mp['path']}",
        })

    return {
        "ok": ok,
        "manifest": str(manifest_path),
        "errors": all_errors,
        "warnings": warnings,
        "paths_found": found_paths,
        "paths_missing": missing_paths,
        "summary": {
            "schema_valid": ok,
            "paths_checked": len(found_paths) + len(missing_paths),
            "paths_found": len(found_paths),
            "paths_missing": len(missing_paths),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a DV project manifest.")
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to the project_manifest.yaml file.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for the validation report JSON. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--schemas-dir",
        default=None,
        help="Override schemas directory. Defaults to <project_root>/schemas/.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    schemas_dir = Path(args.schemas_dir) if args.schemas_dir else None

    # Step 1: Load YAML
    try:
        manifest = Manifest.load(manifest_path)
    except ManifestError as e:
        report = {
            "ok": False,
            "manifest": str(manifest_path),
            "errors": [{"path": "(file)", "message": str(e), "validator": "yaml_parse"}],
            "warnings": [],
            "paths_found": [],
            "paths_missing": [],
            "summary": {
                "schema_valid": False,
                "paths_checked": 0,
                "paths_found": 0,
                "paths_missing": 0,
            },
        }
        _output(report, args.out)
        return 1

    # Step 2: Schema validation
    try:
        schema = load_schema("project_manifest.schema.json", schemas_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    schema_errors = validate(manifest.data, schema, raise_on_error=False)

    # Step 3: Path existence checks
    found_paths, missing_paths = check_paths(manifest)

    # Step 4: Simulation block validation
    simulation_errors = check_simulation_block(manifest)

    # Step 5: Build and output report
    report = build_report(
        manifest_path, schema_errors, found_paths, missing_paths, simulation_errors,
    )
    _output(report, args.out)

    return 0 if report["ok"] else 1


def _output(report: dict, out_path: str | None) -> None:
    """Output the report as JSON."""
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
