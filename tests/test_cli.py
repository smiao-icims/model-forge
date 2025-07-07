"""Tests for the CLI module."""

import json
from typing import Any

import pytest
from click.testing import CliRunner

from modelforge import config
from modelforge.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _parse_output(output: str) -> dict[str, Any]:
    """Helper to parse JSON output from CLI commands."""
    lines = output.strip().split("\n")

    # Find the start of JSON output (first line with "{")
    json_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_start = i
            break

    if json_start == -1:
        return {}

    # Join all lines from the JSON start to create complete JSON
    json_lines = lines[json_start:]
    json_text = "\n".join(json_lines)

    try:
        parsed = json.loads(json_text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def test_config_show_reports_global_by_default(runner: CliRunner) -> None:
    """Test `show` reports a global config by default."""
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "Active ModelForge Config (global)" in result.output
    assert "Configuration is empty" in result.output


def test_config_add_local_and_show(runner: CliRunner) -> None:
    """Test adding a model to a local config and showing it."""
    # Add a model with --local
    add_result = runner.invoke(
        cli,
        [
            "config",
            "add",
            "--provider",
            "local_ollama",
            "--model",
            "local_model",
            "--local",
        ],
    )
    assert add_result.exit_code == 0
    assert "in the local config" in add_result.output

    # `show` should now prefer the local config
    show_result = runner.invoke(cli, ["config", "show"])
    assert show_result.exit_code == 0
    assert "Active ModelForge Config (local)" in show_result.output

    config_data = _parse_output(show_result.output)
    assert "local_ollama" in config_data["providers"]


def test_config_use_local_model(runner: CliRunner) -> None:
    """Test using a model from a local config."""
    # Add a model to the local config first
    runner.invoke(cli, ["config", "add", "--provider", "p", "--model", "m", "--local"])

    # Use the model
    use_result = runner.invoke(
        cli, ["config", "use", "--provider", "p", "--model", "m", "--local"]
    )
    assert use_result.exit_code == 0
    assert "in the local config" in use_result.output

    # Verify that the correct (local) config was updated
    local_config, _ = config.get_config_from_path(config.LOCAL_CONFIG_FILE)
    assert local_config["current_model"] == {"provider": "p", "model": "m"}


def test_config_remove_local_model(runner: CliRunner) -> None:
    """Test removing a model from a local config."""
    # Add a model to the local config
    runner.invoke(cli, ["config", "add", "--provider", "p", "--model", "m", "--local"])

    # Remove the model
    remove_result = runner.invoke(
        cli, ["config", "remove", "--provider", "p", "--model", "m", "--local"]
    )
    assert remove_result.exit_code == 0
    assert "Removed provider 'p'" in remove_result.output

    # Verify the local config is now empty
    local_config, _ = config.get_config_from_path(config.LOCAL_CONFIG_FILE)
    assert "providers" not in local_config or not local_config["providers"]
