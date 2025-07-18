"""Authentication strategies for ModelForge providers."""

import getpass
import time
import webbrowser
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from .config import get_config, save_config
from .exceptions import AuthenticationError, ConfigurationError
from .logging_config import get_logger

logger = get_logger(__name__)


class AuthStrategy(ABC):
    """Abstract base class for authentication strategies."""

    def __init__(self, provider_name: str) -> None:
        """Initialize the authentication strategy.
        Args:
            provider_name: The name of the provider this strategy is for
        """
        self.provider_name = provider_name

    @abstractmethod
    def authenticate(self) -> dict[str, Any] | None:
        """Perform authentication and return credentials."""

    @abstractmethod
    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored credentials."""

    @abstractmethod
    def clear_credentials(self) -> None:
        """Clear any stored credentials for the provider."""

    def _get_auth_data(self) -> dict[str, Any]:
        """Get authentication data from config file."""
        config_data, _ = get_config()
        providers = config_data.get("providers", {})
        provider_data = providers.get(self.provider_name, {})
        return dict(provider_data.get("auth_data", {}))

    def _save_auth_data(self, auth_data: dict[str, Any]) -> None:
        """Save authentication data to config file."""
        config_data, _ = get_config()

        # Ensure providers section exists
        if "providers" not in config_data:
            config_data["providers"] = {}

        # Ensure provider section exists
        if self.provider_name not in config_data["providers"]:
            config_data["providers"][self.provider_name] = {}

        # Store auth data
        config_data["providers"][self.provider_name]["auth_data"] = auth_data

        # Save config
        save_config(config_data)
        logger.info("Successfully saved auth data for %s", self.provider_name)

    def _clear_auth_data(self) -> None:
        """Clear authentication data from config file."""
        config_data, _ = get_config()
        providers = config_data.get("providers", {})

        if self.provider_name in providers:
            providers[self.provider_name].pop("auth_data", None)
            save_config(config_data)
            logger.info("Cleared stored auth data for %s", self.provider_name)


class ApiKeyAuth(AuthStrategy):
    """API key authentication strategy."""

    def authenticate(self) -> dict[str, Any] | None:
        """Prompt for API key and store it in config."""
        api_key = getpass.getpass(f"Enter API key for {self.provider_name}: ")
        if api_key:
            auth_data = {"api_key": api_key}
            self._save_auth_data(auth_data)
            logger.info("API key stored for %s", self.provider_name)
            return auth_data
        logger.warning("No API key provided for %s", self.provider_name)
        return None

    def store_api_key(self, api_key: str) -> None:
        """Store API key for the provider without prompting."""
        auth_data = {"api_key": api_key}
        self._save_auth_data(auth_data)
        logger.info("API key stored for %s", self.provider_name)

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored API key from config."""
        try:
            auth_data = self._get_auth_data()
        except Exception:
            logger.exception("Failed to retrieve API key for %s", self.provider_name)
            return None
        else:
            if auth_data and "api_key" in auth_data:
                logger.debug("Retrieved API key for %s", self.provider_name)
                return auth_data
            logger.warning("No stored API key found for %s", self.provider_name)
            return None

    def clear_credentials(self) -> None:
        """Clear stored API key from config."""
        try:
            self._clear_auth_data()
        except Exception:
            logger.exception(
                "An unexpected error occurred while clearing API key for %s",
                self.provider_name,
            )


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
        try:
            device_code_data = self._request_device_code()
        except requests.exceptions.RequestException as e:
            logger.exception(
                "Network error requesting device code from %s",
                self.provider_name,
            )
            raise AuthenticationError from e

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

    def _request_device_code(self) -> dict[str, Any]:
        """Request device code from the provider."""
        headers = {"Accept": "application/json"}
        data = {
            "client_id": self.client_id,
            "scope": self.scope,
        }

        try:
            response = requests.post(
                self.device_code_url, data=data, headers=headers, timeout=30
            )
            response.raise_for_status()
            return dict(response.json())
        except requests.exceptions.JSONDecodeError as e:
            logger.exception(
                "Invalid response from %s device code endpoint",
                self.provider_name,
            )
            raise AuthenticationError from e
        except requests.exceptions.HTTPError as e:
            # Check if this is a recoverable error
            try:
                error_info = response.json()
                logger.exception(
                    "HTTP error requesting device code from %s: %s",
                    self.provider_name,
                    error_info.get("error"),
                )
                raise AuthenticationError from e
            except requests.exceptions.JSONDecodeError:
                logger.exception(
                    "HTTP error while polling for token from %s", self.provider_name
                )
                raise AuthenticationError from e
        except requests.exceptions.RequestException as e:
            logger.exception(
                "Network error while polling for token from %s",
                self.provider_name,
            )
            raise AuthenticationError from e

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
            except requests.exceptions.JSONDecodeError as e:
                logger.exception(
                    "Invalid JSON response while polling for token from %s",
                    self.provider_name,
                )
                raise AuthenticationError from e
            except requests.exceptions.HTTPError as e:
                # Check if this is a recoverable error
                try:
                    error_info = token_response.json()
                    logger.exception(
                        "HTTP error while polling for token from %s: %s",
                        self.provider_name,
                        error_info.get("error"),
                    )
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
                        logger.exception(
                            "Unrecoverable error from %s: %s",
                            self.provider_name,
                            error_code,
                        )
                        msg = f"Authentication failed: {error_code}"
                        raise AuthenticationError(msg) from e
                except (requests.exceptions.JSONDecodeError, KeyError):
                    logger.exception(
                        "Unexpected error format from %s", self.provider_name
                    )
                    raise AuthenticationError from e
            except requests.exceptions.RequestException as e:
                logger.exception(
                    "Network error while polling for token from %s",
                    self.provider_name,
                )
                raise AuthenticationError from e

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

        try:
            self._save_auth_data(token_data)
        except Exception:
            logger.exception("Failed to save token for %s", self.provider_name)
            msg = "Could not save token information."
            raise ConfigurationError(msg) from None

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored token info. If expired, try to refresh."""
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

    def _refresh_token(self) -> dict[str, Any] | None:
        """Use a refresh token to get a new access token."""
        token_info = self.get_token_info()
        if not token_info or "refresh_token" not in token_info:
            logger.warning(
                "No refresh token found for %s. Cannot refresh.", self.provider_name
            )
            return None

        logger.info("Attempting to refresh token for %s", self.provider_name)
        payload = {
            "client_id": self.client_id,
            "refresh_token": token_info["refresh_token"],
            "grant_type": "refresh_token",
        }
        headers = {"Accept": "application/json"}
        try:
            response = requests.post(
                self.token_url, data=payload, headers=headers, timeout=30
            )
            response.raise_for_status()
            new_token_data = response.json()
        except requests.exceptions.RequestException:
            logger.exception(
                "Failed to refresh token for %s. Re-authentication will be required.",
                self.provider_name,
            )
            self.clear_credentials()
            return None
        else:
            if "refresh_token" not in new_token_data:
                new_token_data["refresh_token"] = token_info["refresh_token"]

            self._save_token_info(new_token_data)
            logger.info("Successfully refreshed token for %s", self.provider_name)
            return dict(new_token_data)

    def get_token_info(self) -> dict[str, Any] | None:
        """Retrieve token information from config file."""
        try:
            auth_data = self._get_auth_data()
        except Exception:
            logger.exception("Could not retrieve token for %s", self.provider_name)
            return None
        else:
            return auth_data if auth_data else None

    def clear_credentials(self) -> None:
        """Clear stored token from config file."""
        try:
            self._clear_auth_data()
        except Exception:
            logger.exception(
                "An unexpected error occurred while clearing token for %s",
                self.provider_name,
            )


def get_auth_strategy(
    provider_name: str,
    provider_data: dict[str, Any],
    model_alias: str | None = None,  # noqa: ARG001
) -> AuthStrategy:
    """
    Factory function to get the correct authentication strategy for a provider.

    Args:
        provider_name: The name of the provider.
        provider_data: The configuration data for the provider.
        model_alias: The model alias (currently unused but for future use).

    Returns:
        An instance of an AuthStrategy subclass.

    Raises:
        ConfigurationError: If the provider is not found or misconfigured.
    """
    if not provider_data:
        msg = f"Provider '{provider_name}' not found in configuration."
        raise ConfigurationError(msg)

    strategy_name = provider_data.get("auth_strategy")
    if not strategy_name:
        return NoAuth(provider_name)

    if strategy_name == "api_key":
        return ApiKeyAuth(provider_name)

    if strategy_name == "device_flow":
        auth_details = provider_data.get("auth_details")
        if not auth_details:
            raise ConfigurationError(
                f"Provider '{provider_name}' is missing required device flow settings."
            )

        return DeviceFlowAuth(
            provider_name,
            auth_details["client_id"],
            auth_details["device_code_url"],
            auth_details["token_url"],
            auth_details["scope"],
        )

    raise ConfigurationError(
        f"Unknown auth strategy '{strategy_name}' for provider '{provider_name}'."
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

    try:
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

    except (ConfigurationError, AuthenticationError):
        logger.exception("Authentication failed for %s", provider_name)
        return None
    except Exception:
        logger.exception(
            "An unexpected error occurred during authentication for %s", provider_name
        )
        return None


class NoAuth(AuthStrategy):
    """Dummy authentication for providers that don't need it."""

    def authenticate(self) -> dict[str, Any] | None:
        """No authentication needed."""
        return {}

    def get_credentials(self) -> dict[str, Any] | None:
        """No credentials to retrieve."""
        return {}

    def clear_credentials(self) -> None:
        """No credentials to clear."""
