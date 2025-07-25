"""Configuration management for ModelForge."""

import json
from pathlib import Path
from typing import Any

from .exceptions import (
    ConfigurationNotFoundError,
    FileValidationError,
    JsonDecodeError,
)
from .logging_config import get_logger
from .validation import InputValidator

logger = get_logger(__name__)

# Configuration file paths
GLOBAL_CONFIG_FILE = Path.home() / ".config" / "model-forge" / "config.json"
LOCAL_CONFIG_FILE = Path.cwd() / ".model-forge" / "config.json"


def get_config_path(local: bool = False) -> Path:
    """
    Determines which config file to use based on the local flag.

    Args:
        local: If True, returns path to local project config

    Returns:
        Path to the configuration file to use
    """
    if local:
        return LOCAL_CONFIG_FILE

    if LOCAL_CONFIG_FILE.exists():
        return LOCAL_CONFIG_FILE

    return GLOBAL_CONFIG_FILE


def get_config() -> tuple[dict[str, Any], Path]:
    """
    Gets the configuration, with local taking precedence over global.

    Returns:
        Tuple of (config_data, config_path)
    """
    config_path = get_config_path()
    return get_config_from_path(config_path)


def get_config_from_path(path: Path) -> tuple[dict[str, Any], Path]:
    """
    Load configuration from a specific path.

    Args:
        path: Path to the configuration file

    Returns:
        Tuple of (config_data, config_path)

    Raises:
        ConfigurationError: If the file cannot be read or is invalid JSON
    """
    if not path.exists():
        return {}, path

    try:
        with path.open() as f:
            config_data = json.load(f)
            logger.debug("Successfully loaded configuration from: %s", path)
            return config_data, path
    except json.JSONDecodeError as e:
        raise JsonDecodeError(
            f"configuration file {path}",
            line=e.lineno,
            column=e.colno,
            reason=e.msg,
        ) from e
    except OSError as e:
        raise FileValidationError(
            str(path),
            f"Cannot read configuration file: {e}",
            suggestion="Check file permissions or create a new configuration",
        ) from e


def save_config(config_data: dict[str, Any], local: bool = False) -> None:
    """
    Save configuration data to the appropriate config file.

    Args:
        config_data: The configuration data to save
        local: If True, saves to local project config

    Raises:
        ConfigurationError: If the file cannot be written
    """
    config_path = get_config_path(local=local)
    config_dir = config_path.parent

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        with config_path.open("w") as f:
            json.dump(config_data, f, indent=4)
        logger.debug("Successfully saved configuration to: %s", config_path)
    except OSError as e:
        raise FileValidationError(
            str(config_path),
            f"Cannot write configuration file: {e}",
            suggestion="Check directory permissions or disk space",
        ) from e


def set_current_model(provider: str, model: str, local: bool = False) -> bool:
    """
    Set the current model for the given provider.

    Args:
        provider: The provider name
        model: The model alias
        local: If True, modifies the local configuration

    Returns:
        True if successful

    Raises:
        ConfigurationNotFoundError: If provider or model not found
        ConfigurationValidationError: If configuration is invalid
    """
    # Validate inputs
    provider = InputValidator.validate_provider_name(provider)
    model = InputValidator.validate_model_name(model)

    # When setting a model, we should read from the specific config file,
    # not the merged one.
    target_config_path = get_config_path(local=local)
    config_data, _ = get_config_from_path(target_config_path)

    # Check if provider and model exist in the configuration
    providers = config_data.get("providers", {})
    if provider not in providers:
        raise ConfigurationNotFoundError(
            provider,
            model,
        )

    models = providers[provider].get("models", {})
    if model not in models:
        raise ConfigurationNotFoundError(
            provider,
            model,
        )

    # Set the current model
    config_data["current_model"] = {"provider": provider, "model": model}
    save_config(config_data, local=local)
    scope_msg = "local" if local else "global"
    success_message = (
        f"Successfully set '{model}' from provider '{provider}' as the current "
        f"model in the {scope_msg} config."
    )
    logger.info(success_message)
    print(success_message)
    return True


def get_settings() -> dict[str, Any]:
    """Get settings from configuration.

    Returns default values if settings don't exist.
    """
    config_data, _ = get_config()
    settings = config_data.get("settings", {})

    # Default settings
    defaults = {
        "show_telemetry": True,
    }

    # Merge with defaults
    return {**defaults, **settings}


def update_setting(key: str, value: Any, local: bool = False) -> None:
    """Update a specific setting.

    Args:
        key: Setting key to update
        value: New value for the setting
        local: Whether to update local config instead of global
    """
    target_config_path = get_config_path(local=local)
    config_data, _ = get_config_from_path(target_config_path)

    if "settings" not in config_data:
        config_data["settings"] = {}

    config_data["settings"][key] = value
    save_config(config_data, local=local)

    scope = "local" if local else "global"
    logger.info(f"Updated setting '{key}' to '{value}' in {scope} config")


def get_current_model() -> dict[str, str] | None:
    """
    Get the currently selected model.

    Returns:
        Dictionary with 'provider' and 'model' keys, or None if not set
    """
    config_data, _ = get_config()
    return config_data.get("current_model")


def migrate_old_config() -> None:
    """
    Migrate configuration from the old location to the new global location.

    Old location: ~/.config/model-forge/models.json
    New location: ~/.config/model-forge/config.json
    """
    # Define old and new paths
    old_config_file = Path.home() / ".config" / "model-forge" / "models.json"

    if old_config_file.exists():
        # Read old configuration
        with old_config_file.open() as f:
            old_config_data = json.load(f)

        # Check if new configuration already exists
        if not GLOBAL_CONFIG_FILE.exists():
            # Create new config directory
            GLOBAL_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Write old data to new location
            with GLOBAL_CONFIG_FILE.open("w") as f:
                json.dump(old_config_data, f, indent=4)

            logger.info(
                "Migrated configuration from %s to %s",
                old_config_file,
                GLOBAL_CONFIG_FILE,
            )
            print(f"Configuration migrated from {old_config_file}")
            print(f"  to: {GLOBAL_CONFIG_FILE}")
            print("You can safely delete the old file if migration was successful.")

        else:
            logger.info(
                "Old configuration file found, but new global configuration "
                "already exists"
            )
            print(
                "Old configuration file found, but a new global configuration "
                "already exists."
            )
            print(f"  - Old: {old_config_file}")
            print(f"  - New: {GLOBAL_CONFIG_FILE}")
            print("Please manually review and merge if needed.")
    else:
        print("No old configuration file found to migrate.")
        print(f"Looking for: {old_config_file}")
