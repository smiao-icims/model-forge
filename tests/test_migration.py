"""Tests for configuration migration functionality."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from modelforge import config
from modelforge.cli import cli

# Test-specific old config paths
OLD_CONFIG_DIR = Path.home() / ".config" / "model-forge"
OLD_CONFIG_FILE = OLD_CONFIG_DIR / "models.json"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def setup_old_config() -> None:
    """Helper to create a dummy old config file for testing."""
    OLD_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with OLD_CONFIG_FILE.open("w") as f:
        json.dump({"providers": {"migrated_provider": {}}}, f)


def cleanup_old_config() -> None:
    """Helper to clean up the dummy old config file."""
    if OLD_CONFIG_FILE.exists():
        OLD_CONFIG_FILE.unlink()
    if OLD_CONFIG_DIR.exists() and not any(OLD_CONFIG_DIR.iterdir()):
        OLD_CONFIG_DIR.rmdir()


def test_migrate_successful(runner: CliRunner) -> None:
    """Test the successful migration of an old config file."""
    # Arrange
    setup_old_config()
    new_global_config_file = config.GLOBAL_CONFIG_FILE

    # Ensure the new config file doesn't exist
    if new_global_config_file.exists():
        new_global_config_file.unlink()

    # Act
    result = runner.invoke(cli, ["config", "migrate"])

    # Assert
    assert result.exit_code == 0
    assert "Configuration migrated from" in result.output
    assert new_global_config_file.exists()

    # Clean up
    cleanup_old_config()
    if new_global_config_file.exists():
        new_global_config_file.unlink()


def test_migrate_new_config_exists(runner: CliRunner) -> None:
    """Test that migration is skipped if a new config already exists."""
    # Arrange
    setup_old_config()
    new_global_config_file = config.GLOBAL_CONFIG_FILE
    # Create a dummy new config
    with new_global_config_file.open("w") as f:
        json.dump({"providers": {"new_provider": {}}}, f)

    # Act
    result = runner.invoke(cli, ["config", "migrate"])

    # Assert
    assert result.exit_code == 0
    assert "new global configuration already exists" in result.output
    assert OLD_CONFIG_FILE.exists()  # Old file should NOT be moved

    # Verify new config is untouched
    with new_global_config_file.open() as f:
        data = json.load(f)
        assert "new_provider" in data["providers"]
        assert "migrated_provider" not in data.get("providers", {})

    cleanup_old_config()


def test_migrate_no_old_config(runner: CliRunner) -> None:
    """Test the case where no old config file exists."""
    # Arrange
    cleanup_old_config()  # Ensure no old config exists

    # Act
    result = runner.invoke(cli, ["config", "migrate"])

    # Assert
    assert result.exit_code == 0
    assert "No old configuration file found" in result.output
