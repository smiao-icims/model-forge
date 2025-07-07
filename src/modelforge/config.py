import json
import os
from pathlib import Path
from typing import Any

# Local imports
from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger(__name__)

# --- Configuration Paths ---
"""
ModelForge uses a two-tier configuration system:

1. **Global Configuration** (~/.model-forge/config.json):
   - Stored in the user's home directory
   - Contains system-wide model configurations
   - Used as the default when no local config exists
   - Shared across all projects for the user

2. **Local Configuration** (./.model-forge/config.json):
   - Stored in the current working directory
   - Project-specific model configurations
   - Takes precedence over global config when present
   - Useful for project-specific model requirements

The configuration system follows a local-over-global precedence:
- If a local config exists, it is used
- If no local config exists, the global config is used
- If neither exists, a new global config is created

Both configuration files use the same JSON structure and can be managed
using the 'modelforge config' CLI commands.
"""

# Allow overriding the global config directory via an environment variable
_config_dir_override = os.environ.get("MODEL_FORGE_CONFIG_DIR")

# Global config: ~/.model-forge/config.json
GLOBAL_CONFIG_DIR = (
    Path(_config_dir_override) if _config_dir_override else Path.home() / ".model-forge"
)
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.json"

# Local config: ./.model-forge/config.json (renamed for consistency)
LOCAL_CONFIG_DIR = Path.cwd() / ".model-forge"
LOCAL_CONFIG_FILE = LOCAL_CONFIG_DIR / "config.json"


def get_config_path(local: bool = False) -> Path:
    """
    Determines the path to the configuration file to be used.

    If `local` is True, it returns the local path. Otherwise, it returns
    the path of the active configuration (local if it exists, global otherwise).

    Args:
        local: If True, force the use of the local configuration path.

    Returns:
        The Path object for the configuration file.
    """
    if local:
        return LOCAL_CONFIG_FILE

    # Precedence: Local > Global
    if LOCAL_CONFIG_FILE.exists():
        return LOCAL_CONFIG_FILE

    return GLOBAL_CONFIG_FILE


def get_config() -> tuple[dict[str, Any], Path]:
    """
    Loads model configuration with local-over-global precedence.

    Returns:
        A tuple containing:
        - A dictionary of the configuration data.
        - The path of the loaded configuration file.
    """
    config_path = get_config_path()

    if not config_path.exists():
        if config_path == GLOBAL_CONFIG_FILE:
            # Create a new global config if it doesn't exist
            GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            save_config({}, local=False)  # Explicitly save to global
            return {}, config_path
        # Local file doesn't exist, and we're not creating it automatically.
        # Fallback to checking the global file.
        return get_config_from_path(GLOBAL_CONFIG_FILE)

    return get_config_from_path(config_path)


def get_config_from_path(path: Path) -> tuple[dict[str, Any], Path]:
    """
    Reads a config file from a specific path.

    Args:
        path: The path to the configuration file.

    Returns:
        A tuple containing the configuration dictionary and the path.

    Raises:
        ConfigurationError: If the configuration file cannot be read or parsed.
    """
    if not path.exists():
        logger.debug("Configuration file does not exist: %s", path)
        return {}, path

    try:
        with open(path) as f:
            config_data = json.load(f)
            logger.debug("Successfully loaded configuration from: %s", path)
            return config_data, path
    except json.JSONDecodeError as e:
        logger.exception("Invalid JSON in configuration file %s: %s", path, str(e))
        raise ConfigurationError(f"Invalid JSON in configuration file {path}") from e
    except OSError as e:
        logger.exception("Could not read configuration file %s: %s", path, str(e))
        raise ConfigurationError(f"Could not read configuration file {path}") from e


def save_config(config_data: dict[str, Any], local: bool = False) -> None:
    """
    Saves configuration data to either the local or global file.

    Args:
        config_data: The configuration dictionary to save.
        local: If True, saves to the local config file. Otherwise, saves to global.

    Raises:
        ConfigurationError: If the configuration file cannot be saved.
    """
    config_path = LOCAL_CONFIG_FILE if local else GLOBAL_CONFIG_FILE
    config_dir = config_path.parent

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)
        logger.debug("Successfully saved configuration to: %s", config_path)
    except OSError as e:
        logger.exception("Could not save config file to %s: %s", config_path, str(e))
        raise ConfigurationError(f"Could not save config file to {config_path}") from e


def set_current_model(provider: str, model: str, local: bool = False) -> bool:
    """
    Sets the currently active model in the configuration.

    Args:
        provider: The name of the provider.
        model: The local alias of the model.
        local: If True, modifies the local configuration.
    """
    # When setting a model, we should read from the specific config file, not the merged one.
    target_config_path = get_config_path(local=local)
    config_data, _ = get_config_from_path(target_config_path)

    providers = config_data.get("providers", {})

    if provider not in providers or model not in providers[provider].get("models", {}):
        scope = "local" if local else "global"
        logger.error(
            "Model '%s' for provider '%s' not found in %s configuration",
            model,
            provider,
            scope,
        )
        print(
            f"Error: Model '{model}' for provider '{provider}' not found in {scope} configuration."
        )
        print("Please add it using 'modelforge config add' first.")
        return False

    config_data["current_model"] = {"provider": provider, "model": model}
    save_config(config_data, local=local)
    scope_msg = "local" if local else "global"
    success_message = f"Successfully set '{model}' from provider '{provider}' as the current model in the {scope_msg} config."
    logger.info(success_message)
    print(success_message)
    return True


def get_current_model() -> dict[str, str] | None:
    """
    Retrieves the currently active model from the active configuration.

    Returns:
        A dictionary containing the provider and model alias, or None.
    """
    config_data, _ = get_config()
    return config_data.get("current_model")


def migrate_old_config() -> None:
    """
    Migrates the configuration from the old location to the new global location.

    Old location: ~/.config/model-forge/models.json
    New location: ~/.model-forge/config.json
    """
    old_config_dir = Path.home() / ".config" / "model-forge"
    old_config_file = old_config_dir / "models.json"

    if old_config_file.exists():
        if not GLOBAL_CONFIG_FILE.exists():
            logger.info("Found old configuration at %s", old_config_file)
            logger.info("Migrating to new global location: %s", GLOBAL_CONFIG_FILE)
            print(f"Found old configuration at {old_config_file}.")
            print(f"Migrating to new global location: {GLOBAL_CONFIG_FILE}")

            # Ensure the new directory exists
            GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Move the file
            old_config_file.rename(GLOBAL_CONFIG_FILE)

            # Clean up the old directory if it's empty
            if not any(old_config_dir.iterdir()):
                old_config_dir.rmdir()

            logger.info("Migration successful")
            logger.info("Configuration now located at: %s", GLOBAL_CONFIG_FILE)
            print("Migration successful.")
            print(f"Your configuration is now located at {GLOBAL_CONFIG_FILE}.")
        else:
            logger.info(
                "Old configuration file found, but new global configuration already exists"
            )
            print(
                "Old configuration file found, but a new global configuration already exists."
            )
            print(f"  - Old: {old_config_file}")
            print(f"  - New: {GLOBAL_CONFIG_FILE}")
            print("Please merge them manually if needed.")
    else:
        logger.info("No old configuration file found to migrate")
        print("No old configuration file found to migrate.")
