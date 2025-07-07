"""Test configuration and shared fixtures."""

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_mock import MockerFixture

# Dummy paths for testing
DUMMY_GLOBAL_CONFIG_FILE = Path("/tmp/global_config.json")  # noqa: S108
DUMMY_LOCAL_CONFIG_FILE = Path.cwd() / ".model-forge" / "config.json"


@pytest.fixture(autouse=True)
def _mock_config_paths(mocker: MockerFixture) -> None:
    """
    A fixture that automatically mocks the global and local config file paths for all
    tests. This prevents tests from accidentally using or modifying the real 
    config files.
    """
    # Mock the config file paths
    mocker.patch("modelforge.config.GLOBAL_CONFIG_FILE", DUMMY_GLOBAL_CONFIG_FILE)
    mocker.patch("modelforge.config.LOCAL_CONFIG_FILE", DUMMY_LOCAL_CONFIG_FILE)

    # Clean up dummy files before each test
    if DUMMY_GLOBAL_CONFIG_FILE.exists():
        DUMMY_GLOBAL_CONFIG_FILE.unlink()
    if DUMMY_LOCAL_CONFIG_FILE.exists():
        DUMMY_LOCAL_CONFIG_FILE.unlink()


def setup_dummy_config(data: dict[str, Any]) -> None:
    """Helper to set up a dummy configuration for testing."""
    DUMMY_GLOBAL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DUMMY_GLOBAL_CONFIG_FILE.open("w") as f:
        json.dump(data, f)
