"""Authentication strategies for ModelForge providers."""

import getpass
import json
import os
import time
import webbrowser
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from .config import get_config, save_config
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    JsonDecodeError,
    NetworkError,
)
from .logging_config import get_logger
from .retry import retry_on_error
from .validation import InputValidator

logger = get_logger(__name__)


def _normalize_provider_name_for_env(provider_name: str) -> str:
    """Normalize provider name for environment variable lookups.

    Converts provider names to uppercase and replaces hyphens with underscores.
    e.g., 'github-copilot' -> 'GITHUB_COPILOT'
    """
    return provider_name.upper().replace("-", "_")


def _get_env_var_for_provider(provider_name: str, credential_type: str) -> str | None:
    """Get environment variable value for a provider's credentials.

    Args:
        provider_name: The provider name (e.g., 'openai', 'github-copilot')
        credential_type: Type of credential ('API_KEY' or 'ACCESS_TOKEN')

    Returns:
        The environment variable value if set, None otherwise
    """
    normalized_name = _normalize_provider_name_for_env(provider_name)
    env_var_name = f"MODELFORGE_{normalized_name}_{credential_type}"

    value = os.getenv(env_var_name)
    if value:
        logger.debug("Found credential in environment variable: %s", env_var_name)
    return value


# Module-level functions for config operations
def get_auth_data(provider_name: str) -> dict[str, Any]:
    """Get authentication data from config file."""
    config_data, _ = get_config()
    providers = config_data.get("providers", {})
    provider_data = providers.get(provider_name, {})
    return dict(provider_data.get("auth_data", {}))


def save_auth_data(provider_name: str, auth_data: dict[str, Any]) -> None:
    """Save authentication data to config file."""
    config_data, _ = get_config()

    # Ensure providers section exists
    if "providers" not in config_data:
        config_data["providers"] = {}

    # Ensure provider section exists
    if provider_name not in config_data["providers"]:
        config_data["providers"][provider_name] = {}

    # Store auth data
    config_data["providers"][provider_name]["auth_data"] = auth_data

    # Save config
    save_config(config_data)
    logger.info("Successfully saved auth data for %s", provider_name)


def clear_auth_data(provider_name: str) -> None:
    """Clear authentication data from config file."""
    config_data, _ = get_config()
    providers = config_data.get("providers", {})

    if provider_name in providers:
        providers[provider_name].pop("auth_data", None)
        save_config(config_data)
        logger.info("Cleared stored auth data for %s", provider_name)


class AuthStrategy:
    """Base class for authentication strategies."""

    def __init__(self, provider_name: str) -> None:
        """Initialize the authentication strategy.
        Args:
            provider_name: The name of the provider this strategy is for
        """
        self.provider_name = provider_name

    def authenticate(self) -> dict[str, Any] | None:
        """Perform authentication and return credentials."""
        raise NotImplementedError

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored credentials."""
        raise NotImplementedError

    def clear_credentials(self) -> None:
        """Clear any stored credentials for the provider."""
        clear_auth_data(self.provider_name)

    def _get_auth_data(self) -> dict[str, Any]:
        """Get authentication data from config file."""
        return get_auth_data(self.provider_name)

    def _save_auth_data(self, auth_data: dict[str, Any]) -> None:
        """Save authentication data to config file."""
        save_auth_data(self.provider_name, auth_data)

    def _clear_auth_data(self) -> None:
        """Clear authentication data from config file."""
        clear_auth_data(self.provider_name)


class ApiKeyAuth(AuthStrategy):
    """API key authentication strategy."""

    def authenticate(self) -> dict[str, Any] | None:
        """Prompt for API key and store it in config."""
        api_key = getpass.getpass(f"Enter API key for {self.provider_name}: ")
        if api_key:
            # Validate the API key format if known provider
            try:
                validated_key = InputValidator.validate_api_key(
                    api_key, self.provider_name
                )
            except Exception:
                # If validation fails, still accept the key (for custom providers)
                validated_key = api_key

            auth_data = {"api_key": validated_key}
            self._save_auth_data(auth_data)
            logger.info("API key stored for %s", self.provider_name)
            return auth_data
        logger.warning("No API key provided for %s", self.provider_name)
        return None

    def store_api_key(self, api_key: str) -> None:
        """Store API key for the provider without prompting."""
        # Validate the API key format if known provider
        try:
            validated_key = InputValidator.validate_api_key(api_key, self.provider_name)
        except Exception:
            # If validation fails, still accept the key (for custom providers)
            validated_key = api_key

        auth_data = {"api_key": validated_key}
        self._save_auth_data(auth_data)
        logger.info("API key stored for %s", self.provider_name)

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve API key from environment or config.

        Checks in order:
        1. Environment variable (MODELFORGE_<PROVIDER>_API_KEY)
        2. Stored in config file
        """
        # Check environment variable first
        env_api_key = _get_env_var_for_provider(self.provider_name, "API_KEY")
        if env_api_key:
            logger.info(
                "Using API key from environment variable for %s", self.provider_name
            )
            # Validate the API key format if known provider
            try:
                validated_key = InputValidator.validate_api_key(
                    env_api_key, self.provider_name
                )
            except Exception:
                # If validation fails, still accept the key (for custom providers)
                validated_key = env_api_key
            return {"api_key": validated_key}

        # Fall back to config file
        auth_data = self._get_auth_data()
        if auth_data and "api_key" in auth_data:
            logger.debug("Retrieved API key from config for %s", self.provider_name)
            return auth_data
        logger.warning("No API key found for %s", self.provider_name)
        return None


class DeviceFlowAuth(AuthStrategy):
    """OAuth device flow authentication strategy."""

    def __init__(
        self,
        provider_name: str,
        client_id: str,
        device_code_url: str,
        token_url: str,
        scope: str,
    ) -> None:
        """Initialize device flow authentication.
        Args:
            provider_name: The name of the provider
            client_id: OAuth client ID
            device_code_url: URL to request device code
            token_url: URL to exchange device code for token
            scope: OAuth scope
        """
        super().__init__(provider_name)
        self.client_id = client_id
        self.device_code_url = device_code_url
        self.token_url = token_url
        self.scope = scope

    def authenticate(self) -> dict[str, Any] | None:
        """Perform device flow authentication."""
        logger.info("Starting device flow authentication for %s", self.provider_name)

        # Step 1: Request device code
        device_code_data = self._request_device_code()

        logger.info("Device code obtained for %s", self.provider_name)

        # Step 2: Show user instructions
        print("\n--- Device Authentication ---")
        print(
            f"Please open the following URL in your browser: "
            f"{device_code_data['verification_uri']}"
        )
        print(f"And enter this code: {device_code_data['user_code']}")
        print("Waiting for authentication...")

        # Try to open browser automatically
        try:
            webbrowser.open(device_code_data["verification_uri"])
            print("Browser opened automatically. If not, use the URL above.")
        except Exception:
            print("Please open the URL manually in your browser.")

        # Step 3: Poll for token
        return self._poll_for_token(device_code_data)

    @retry_on_error(max_retries=3)
    def _request_device_code(self) -> dict[str, Any]:
        """Request device code from the provider."""
        headers = {"Accept": "application/json"}
        data = {
            "client_id": self.client_id,
            "scope": self.scope,
        }

        response = requests.post(
            self.device_code_url, data=data, headers=headers, timeout=30
        )
        response.raise_for_status()
        return dict(response.json())

    def _poll_for_token(
        self, device_code_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Poll for access token after device code is obtained."""
        logger.info("Polling for access token for %s", self.provider_name)

        while True:
            time.sleep(device_code_data.get("interval", 5))
            token_payload = {
                "client_id": self.client_id,
                "device_code": device_code_data["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }
            headers = {"Accept": "application/json"}

            try:
                token_response = requests.post(
                    self.token_url, data=token_payload, headers=headers, timeout=30
                )
                token_data = token_response.json()
                token_response.raise_for_status()
            except json.JSONDecodeError as e:
                raise JsonDecodeError(
                    "token response",
                    reason=str(e),
                ) from e
            except requests.exceptions.HTTPError as e:
                # Check if this is a recoverable error
                try:
                    error_info = token_data
                    error_code = error_info.get("error")
                    if error_code == "authorization_pending":
                        # This is expected, continue polling
                        continue
                    if error_code == "slow_down":
                        # Increase interval and continue
                        new_interval = device_code_data.get("interval", 5) + 5
                        device_code_data["interval"] = new_interval
                        logger.info(
                            "Slowing down polling to %s seconds for %s",
                            new_interval,
                            self.provider_name,
                        )
                        continue
                    if error_code in ("expired_token", "access_denied"):
                        # Unrecoverable error, stop polling
                        raise AuthenticationError(
                            f"Authentication failed: {error_code}",
                            context=(
                                f"OAuth device flow failed for {self.provider_name}"
                            ),
                            suggestion="Try authenticating again",
                            error_code=error_code.upper(),
                        ) from e
                    # Unknown error
                    raise NetworkError(
                        "HTTP error during OAuth polling",
                        context=str(e),
                        suggestion="Check network connection and try again",
                        error_code="OAUTH_POLL_ERROR",
                    ) from e
                except (KeyError, TypeError):
                    raise NetworkError(
                        "Invalid error response format",
                        context="OAuth server returned unexpected error format",
                        suggestion="Try authenticating again",
                        error_code="OAUTH_ERROR_FORMAT",
                    ) from e

            if "access_token" in token_data:
                logger.info(
                    "Successfully obtained access token for %s", self.provider_name
                )
                self._save_token_info(token_data)
                return dict(token_data)

    def _save_token_info(self, token_data: dict[str, Any]) -> None:
        """Save token information to config file."""
        # Calculate expiry time and add to token_data
        if "expires_in" in token_data:
            expires_in = token_data["expires_in"]
            expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
            token_data["expires_at"] = expires_at.isoformat()

        self._save_auth_data(token_data)

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve token from environment or stored info.

        Checks in order:
        1. Environment variable (MODELFORGE_<PROVIDER>_ACCESS_TOKEN)
        2. Stored token (with refresh if expired)
        """
        # Check environment variable first
        env_token = _get_env_var_for_provider(self.provider_name, "ACCESS_TOKEN")
        if env_token:
            logger.info(
                "Using access token from environment variable for %s",
                self.provider_name,
            )
            # Environment tokens are assumed to be valid and don't expire
            return {"access_token": env_token}

        # Fall back to stored token
        token_info = self.get_token_info()
        if not token_info:
            logger.debug("No token info found for %s.", self.provider_name)
            return None

        # Check for expiry, with a 60-second buffer
        expires_at_str = token_info.get("expires_at")
        if not expires_at_str:
            logger.warning(
                "Token for %s has no expiration info. Assuming it's valid.",
                self.provider_name,
            )
            return token_info

        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(UTC) >= (expires_at - timedelta(seconds=60)):
            logger.info(
                "Access token for %s is expired or nearing expiry. Attempting refresh.",
                self.provider_name,
            )
            return self._refresh_token()

        logger.debug("Access token for %s is still valid.", self.provider_name)
        return token_info

    @retry_on_error(max_retries=2)
    def _refresh_token(self) -> dict[str, Any] | None:
        """Use a refresh token to get a new access token."""
        token_info = self.get_token_info()
        if not token_info or "refresh_token" not in token_info:
            logger.warning(
                "No refresh token found for %s. Cannot refresh.", self.provider_name
            )
            # Return None to maintain backward compatibility
            return None

        logger.info("Attempting to refresh token for %s", self.provider_name)
        payload = {
            "client_id": self.client_id,
            "refresh_token": token_info["refresh_token"],
            "grant_type": "refresh_token",
        }
        headers = {"Accept": "application/json"}

        response = requests.post(
            self.token_url, data=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        new_token_data = response.json()

        if "refresh_token" not in new_token_data:
            new_token_data["refresh_token"] = token_info["refresh_token"]

        self._save_token_info(new_token_data)
        logger.info("Successfully refreshed token for %s", self.provider_name)
        return dict(new_token_data)

    def get_token_info(self) -> dict[str, Any] | None:
        """Retrieve token information with calculated expiration details."""
        auth_data = self._get_auth_data()
        if not auth_data:
            return None

        # Make a copy to avoid modifying the original data
        token_info = dict(auth_data)

        # Add calculated expiration fields for CLI display
        expires_at_str = token_info.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                now = datetime.now(UTC)

                # Calculate time remaining
                time_remaining = expires_at - now
                if time_remaining.total_seconds() > 0:
                    token_info["time_remaining"] = str(time_remaining)
                else:
                    token_info["time_remaining"] = "expired"

                # Add human-readable expiry time
                token_info["expiry_time"] = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")

            except (ValueError, TypeError) as e:
                logger.warning(
                    "Invalid expires_at format for %s: %s", self.provider_name, e
                )

        return token_info


def get_auth_strategy(
    provider_name: str,
    provider_data: dict[str, Any],
    model_alias: str | None = None,  # noqa: ARG001
) -> AuthStrategy:
    """
    Get the correct authentication strategy for a provider.

    Args:
        provider_name: The name of the provider.
        provider_data: The configuration data for the provider.
        model_alias: The model alias (currently unused but for future use).

    Returns:
        An instance of an AuthStrategy subclass.

    Raises:
        ConfigurationError: If the provider is not found or misconfigured.
    """
    if provider_data is None:
        raise ConfigurationError(
            f"Provider '{provider_name}' not found",
            context="Provider configuration is missing",
            suggestion=f"Add provider '{provider_name}' to your configuration",
            error_code="PROVIDER_NOT_CONFIGURED",
        )

    if not provider_data:
        # Empty dict means no auth needed
        return NoAuth(provider_name)

    strategy_name = provider_data.get("auth_strategy", "")

    # Direct mapping of strategies
    if strategy_name == "api_key":
        return ApiKeyAuth(provider_name)

    if strategy_name == "device_flow":
        auth_details = provider_data.get("auth_details")
        if not auth_details:
            raise ConfigurationError(
                f"Device flow settings missing for '{provider_name}'",
                context="OAuth device flow requires client_id, URLs, and scope",
                suggestion="Check provider configuration for missing auth_details",
                error_code="DEVICE_FLOW_MISCONFIGURED",
            )
        return DeviceFlowAuth(
            provider_name,
            auth_details["client_id"],
            auth_details["device_code_url"],
            auth_details["token_url"],
            auth_details["scope"],
        )

    if strategy_name == "" or strategy_name is None:
        return NoAuth(provider_name)

    # Unknown strategy
    raise ConfigurationError(
        f"Unknown auth strategy '{strategy_name}'",
        context=f"Provider '{provider_name}' uses an unsupported authentication method",
        suggestion="Supported: 'api_key', 'device_flow', or omit for no auth",
        error_code="UNKNOWN_AUTH_STRATEGY",
    )


def get_credentials(
    provider_name: str,
    model_alias: str,
    provider_data: dict[str, Any],
    verbose: bool = False,
) -> dict[str, Any] | None:
    """
    Get credentials for a given provider and model.

    This function will first try to retrieve stored credentials. If they are
    not available or invalid, it will trigger the authentication process.
    """
    if verbose:
        logger.setLevel("DEBUG")

    strategy = get_auth_strategy(provider_name, provider_data, model_alias)
    creds = strategy.get_credentials()
    if creds:
        logger.info("Successfully retrieved credentials for %s", provider_name)
        return creds

    logger.info(
        "No valid credentials found for %s. Initiating authentication.",
        provider_name,
    )
    return strategy.authenticate()


class NoAuth(AuthStrategy):
    """Dummy authentication for providers that don't need it."""

    def authenticate(self) -> dict[str, Any] | None:
        """No authentication needed."""
        return {}

    def get_credentials(self) -> dict[str, Any] | None:
        """No credentials to retrieve."""
        return {}
