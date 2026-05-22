"""Index path conventions for DV AI Coverage Closure.

All pre-built indexes are stored under a project's `.dv_ai_index/` directory.
This module provides the canonical file names and path resolution helpers.
"""

from pathlib import Path

# Canonical index file names within .dv_ai_index/
COVERAGE_INDEX = "coverage_index.json"
RTL_INDEX = "rtl_index.json"
SPEC_INDEX = "spec_index.json"
REG_DB = "reg_db.json"
TB_INDEX = "tb_index.json"
SIM_HISTORY = "sim_history.json"
MANIFEST_CHECK = "manifest_check.json"

INDEX_DIR_NAME = ".dv_ai_index"

# Map from index type to canonical file name
INDEX_FILES: dict[str, str] = {
    "coverage": COVERAGE_INDEX,
    "rtl": RTL_INDEX,
    "spec": SPEC_INDEX,
    "registers": REG_DB,
    "tb": TB_INDEX,
    "sim_history": SIM_HISTORY,
}


def get_index_dir(project_root: Path) -> Path:
    """Return the index directory for a project.

    Checks in order:
    1. project_root/.dv_ai_index/
    2. Falls back to project_root itself (for pre-built indexes stored alongside data)
    """
    index_dir = project_root / INDEX_DIR_NAME
    return index_dir


def get_index_path(project_root: Path, index_type: str) -> Path:
    """Return the full path to a specific index file.

    Args:
        project_root: Root directory of the project (where .dv_ai_index/ lives).
        index_type: One of 'coverage', 'rtl', 'spec', 'registers', 'tb', 'sim_history'.

    Raises:
        ValueError: If index_type is not recognized.
    """
    if index_type not in INDEX_FILES:
        valid = ", ".join(sorted(INDEX_FILES.keys()))
        raise ValueError(f"Unknown index type '{index_type}'. Valid types: {valid}")
    return get_index_dir(project_root) / INDEX_FILES[index_type]


def get_manifest_check_path(project_root: Path) -> Path:
    """Return the path for the manifest validation report."""
    return get_index_dir(project_root) / MANIFEST_CHECK
