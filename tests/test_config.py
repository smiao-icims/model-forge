"""Tests for the config module."""

from typing import Any

from modelforge import config


def test_get_config_creates_global_if_none_exist() -> None:
    """Verify get_config() returns empty config and path if no file exists."""
    config_data, config_path = config.get_config()
    # The get_config function now returns empty dict and path without creating the file
    assert config_path == config.GLOBAL_CONFIG_FILE
    assert config_data == {}


def test_get_config_prefers_local_over_global() -> None:
    """Verify get_config() returns local config if both exist."""
    # Arrange
    global_data: dict[str, Any] = {"providers": {"global_provider": {}}}
    local_data: dict[str, Any] = {"providers": {"local_provider": {}}}

    config.save_config(global_data, local=False)
    config.save_config(local_data, local=True)

    # Act
    read_data, read_path = config.get_config()

    # Assert
    assert read_path == config.LOCAL_CONFIG_FILE
    assert read_data == local_data


def test_save_and_get_local_config() -> None:
    """Verify saving to and getting from a local config works."""
    # Arrange
    test_data: dict[str, Any] = {
        "providers": {"test_provider": {"models": {"test_model": {}}}}
    }

    # Act
    config.save_config(test_data, local=True)
    read_data, _ = config.get_config_from_path(config.LOCAL_CONFIG_FILE)

    # Assert
    assert config.LOCAL_CONFIG_FILE.exists()
    assert read_data == test_data


def test_set_current_model_in_local_config() -> None:
    """Verify setting the current model in the local config."""
    # Arrange
    initial_config: dict[str, Any] = {
        "providers": {
            "test": {"models": {"test-model": {"api_model_name": "actual-model"}}}
        }
    }
    config.save_config(initial_config, local=True)

    # Act
    success = config.set_current_model("test", "test-model", local=True)
    current_model = config.get_current_model()

    # Assert
    assert success is True
    assert current_model == {"provider": "test", "model": "test-model"}

    # Check that only the local file was modified
    local_config, _ = config.get_config_from_path(config.LOCAL_CONFIG_FILE)
    global_config, _ = config.get_config_from_path(config.GLOBAL_CONFIG_FILE)

    assert "current_model" in local_config
    assert "current_model" not in global_config
