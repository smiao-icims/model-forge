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


def test_get_settings_with_defaults() -> None:
    """Test get_settings returns default values when no settings exist."""
    # Arrange - ensure clean state
    config_data: dict[str, Any] = {"providers": {}}
    config.save_config(config_data, local=False)

    # Act
    settings = config.get_settings()

    # Assert - should have default show_telemetry value
    assert settings == {"show_telemetry": True}


def test_get_settings_with_existing_values() -> None:
    """Test get_settings returns existing settings values."""
    # Arrange
    config_data: dict[str, Any] = {
        "providers": {},
        "settings": {"show_telemetry": False, "custom_setting": "test_value"},
    }
    config.save_config(config_data, local=False)

    # Act
    settings = config.get_settings()

    # Assert
    assert settings["show_telemetry"] is False
    assert settings["custom_setting"] == "test_value"


def test_update_setting_creates_settings_section() -> None:
    """Test update_setting creates settings section if it doesn't exist."""
    # Arrange
    config_data: dict[str, Any] = {"providers": {}}
    config.save_config(config_data, local=False)

    # Act
    config.update_setting("test_key", "test_value", local=False)

    # Assert
    updated_config, _ = config.get_config()
    assert "settings" in updated_config
    assert updated_config["settings"]["test_key"] == "test_value"


def test_update_setting_global() -> None:
    """Test update_setting updates global config."""
    # Arrange
    config_data: dict[str, Any] = {
        "providers": {},
        "settings": {"existing_key": "old_value"},
    }
    config.save_config(config_data, local=False)

    # Act
    config.update_setting("existing_key", "new_value", local=False)
    config.update_setting("new_key", "another_value", local=False)

    # Assert
    updated_config, _ = config.get_config_from_path(config.GLOBAL_CONFIG_FILE)
    assert updated_config["settings"]["existing_key"] == "new_value"
    assert updated_config["settings"]["new_key"] == "another_value"


def test_update_setting_local() -> None:
    """Test update_setting updates local config when local=True."""
    # Arrange
    global_config: dict[str, Any] = {
        "providers": {},
        "settings": {"show_telemetry": True},
    }
    local_config: dict[str, Any] = {"providers": {}}

    config.save_config(global_config, local=False)
    config.save_config(local_config, local=True)

    # Act
    config.update_setting("show_telemetry", False, local=True)

    # Assert
    # Local config should have the setting
    local_data, _ = config.get_config_from_path(config.LOCAL_CONFIG_FILE)
    assert local_data["settings"]["show_telemetry"] is False

    # Global config should remain unchanged
    global_data, _ = config.get_config_from_path(config.GLOBAL_CONFIG_FILE)
    assert global_data["settings"]["show_telemetry"] is True


def test_update_setting_boolean_values() -> None:
    """Test update_setting handles boolean values correctly."""
    # Arrange
    config.save_config({"providers": {}}, local=False)

    # Act & Assert for True
    config.update_setting("bool_setting", True, local=False)
    settings = config.get_settings()
    assert settings["bool_setting"] is True

    # Act & Assert for False
    config.update_setting("bool_setting", False, local=False)
    settings = config.get_settings()
    assert settings["bool_setting"] is False


def test_get_settings_merges_defaults() -> None:
    """Test get_settings merges defaults with existing settings."""
    # Arrange
    config_data: dict[str, Any] = {
        "providers": {},
        "settings": {"custom_setting": "value"},
    }
    config.save_config(config_data, local=False)

    # Act
    settings = config.get_settings()

    # Assert - should have both default and custom settings
    assert settings["show_telemetry"] is True  # default
    assert settings["custom_setting"] == "value"  # existing
