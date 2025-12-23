# tests/conftest.py
"""Global test configuration and fixtures."""
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment before running tests."""
    # Create assets directory structure if it doesn't exist
    root_dir = Path(__file__).parent.parent
    assets_dir = root_dir / "assets"
    cookies_dir = assets_dir / "cookies"
    data_dir = assets_dir / "data"

    cookies_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Cleanup (optional - we keep assets for now)

