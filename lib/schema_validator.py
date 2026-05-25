"""JSON Schema validation wrapper for DV AI Coverage Closure.

Provides a unified interface for validating data against JSON Schema files,
with consistent error reporting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

# Default schemas directory
_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


class SchemaValidationError(Exception):
    """Raised when data fails schema validation."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        messages = [f"  - {e['path']}: {e['message']}" for e in errors]
        super().__init__(
            f"Schema validation failed with {len(errors)} error(s):\n" + "\n".join(messages)
        )


def load_schema(schema_name: str, schemas_dir: Path | None = None) -> dict[str, Any]:
    """Load a JSON Schema file by name.

    Args:
        schema_name: Schema file name (e.g. 'project_manifest.schema.json').
        schemas_dir: Override schemas directory. Defaults to project schemas/.

    Returns:
        The parsed schema as a dict.

    Raises:
        FileNotFoundError: If the schema file does not exist.
    """
    base_dir = schemas_dir or _SCHEMAS_DIR
    schema_path = base_dir / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with open(schema_path, encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result


def validate(
    data: dict[str, Any],
    schema: dict[str, Any],
    *,
    raise_on_error: bool = True,
) -> list[dict[str, Any]]:
    """Validate data against a JSON Schema.

    Args:
        data: The data to validate.
        schema: The JSON Schema to validate against.
        raise_on_error: If True, raise SchemaValidationError on failure.

    Returns:
        A list of error dicts with keys: path, message, validator, validator_value.
        Empty list if validation passes.

    Raises:
        SchemaValidationError: If raise_on_error is True and validation fails.
    """
    validator = Draft7Validator(schema)
    errors: list[dict[str, Any]] = []

    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append({
            "path": path,
            "message": error.message,
            "validator": error.validator,
            "validator_value": error.validator_value,
        })

    if errors and raise_on_error:
        raise SchemaValidationError(errors)

    return errors


def validate_file(
    data_path: str | Path,
    schema_name: str,
    *,
    schemas_dir: Path | None = None,
    raise_on_error: bool = True,
) -> list[dict[str, Any]]:
    """Validate a JSON/YAML file against a named schema.

    Args:
        data_path: Path to the data file (.json or .yaml/.yml).
        schema_name: Schema file name (e.g. 'project_manifest.schema.json').
        schemas_dir: Override schemas directory.
        raise_on_error: If True, raise SchemaValidationError on failure.

    Returns:
        A list of error dicts. Empty list if validation passes.
    """
    import yaml

    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    with open(data_path, encoding="utf-8") as f:
        if data_path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)

    schema = load_schema(schema_name, schemas_dir)
    return validate(data, schema, raise_on_error=raise_on_error)
