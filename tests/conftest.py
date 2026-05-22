"""Shared pytest fixtures for DV AI Coverage Closure tests."""

from pathlib import Path

import pytest

# Project root is the parent of the tests/ directory
PROJECT_ROOT = Path(__file__).parent.parent
MOCK_DATA_DIR = PROJECT_ROOT / "mock_data" / "dma_subsystem"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def mock_data_dir() -> Path:
    """Return the mock data directory for dma_subsystem."""
    return MOCK_DATA_DIR


@pytest.fixture
def mock_manifest_path(mock_data_dir: Path) -> Path:
    """Return the path to the mock project manifest."""
    return mock_data_dir / "project_manifest.yaml"


@pytest.fixture
def schemas_dir() -> Path:
    """Return the schemas directory."""
    return SCHEMAS_DIR
