"""Authentication strategies for ModelForge providers."""

import getpass
import json
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import keyring
import requests

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


class ApiKeyAuth(AuthStrategy):
    """API key authentication strategy."""

    def authenticate(self) -> dict[str, Any] | None:
        """Prompt for API key and store it securely."""
        api_key = getpass.getpass(f"Enter API key for {self.provider_name}: ")
        if api_key:
            # Store the API key in the keyring
            keyring.set_password(
                self.provider_name, f"{self.provider_name}_user", api_key
            )
            logger.info("API key stored securely for %s", self.provider_name)
            return {"api_key": api_key}
        logger.warning("No API key provided for %s", self.provider_name)
        return None

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored API key from keyring."""
        try:
            api_key = keyring.get_password(
                self.provider_name, f"{self.provider_name}_user"
            )
            if api_key:
                logger.debug("Retrieved API key for %s", self.provider_name)
                return {"api_key": api_key}
        except Exception:
            logger.exception("Failed to retrieve API key for %s", self.provider_name)
            return None
        else:
            logger.warning("No stored API key found for %s", self.provider_name)
            return None

    def clear_credentials(self) -> None:
        """Clear stored API key from keyring."""
        try:
            keyring.delete_password(self.provider_name, f"{self.provider_name}_user")
            logger.info("Cleared stored API key for %s.", self.provider_name)
        except keyring.errors.PasswordDeleteError:
            logger.debug("No stored API key to clear for %s.", self.provider_name)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while clearing API key for %s: %s",
                self.provider_name,
                e,
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
            return response.json()
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
                        logger.error(
                            "Unrecoverable error from %s: %s",
                            self.provider_name,
                            error_code,
                        )
                        raise AuthenticationError(f"Authentication failed: {error_code}") from e
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
                logger.info("Successfully obtained access token for %s", self.provider_name)
                self._save_token_info(token_data)
                return token_data

    def _save_token_info(self, token_data: dict[str, Any]) -> None:
        """Save token information to keyring."""
        # Calculate expiry time and add to token_data
        if "expires_in" in token_data:
            expires_in = token_data["expires_in"]
            expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
            token_data["expires_at"] = expires_at.isoformat()

        try:
            keyring.set_password(
                self.provider_name, "token_info", json.dumps(token_data)
            )
            logger.info("Successfully saved token for %s", self.provider_name)
        except Exception:
            logger.exception("Failed to save token for %s", self.provider_name)
            raise ConfigurationError("Could not save token information securely.") from None

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

            if "refresh_token" not in new_token_data:
                new_token_data["refresh_token"] = token_info["refresh_token"]

            self._save_token_info(new_token_data)
            logger.info("Successfully refreshed token for %s", self.provider_name)
            return new_token_data
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to refresh token for %s. Re-authentication will be required. Error: %s",
                self.provider_name,
                e,
            )
            self.clear_credentials()
            return None

    def get_token_info(self) -> dict[str, Any] | None:
        """Retrieve token information from keyring."""
        try:
            stored_token = keyring.get_password(self.provider_name, "token_info")
            if stored_token:
                return json.loads(stored_token)
            return None
        except Exception:
            logger.exception("Could not retrieve token for %s", self.provider_name)
            return None

    def clear_credentials(self) -> None:
        """Clear stored token from keyring."""
        try:
            keyring.delete_password(self.provider_name, "token_info")
            logger.info("Cleared stored token for %s.", self.provider_name)
        except keyring.errors.PasswordDeleteError:
            logger.debug("No stored token to clear for %s.", self.provider_name)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while clearing token for %s: %s",
                self.provider_name,
                e,
            )


def get_auth_strategy(
    provider_name: str,
    model_alias: str | None = None,  # noqa: ARG001
) -> AuthStrategy:
    """
    Factory function to get the correct authentication strategy for a provider.
    Args:
        provider_name: The name of the provider.
        model_alias: The model alias (currently unused but for future use).
    Returns:
        An instance of an AuthStrategy subclass.
    Raises:
        ConfigurationError: If the provider is not found or misconfigured.
    """
    from . import config  # Late import to avoid circular dependency

    # Get the merged configuration
    providers_config, _ = config.get_config()
    provider_data = providers_config.get("providers", {}).get(provider_name)

    if not provider_data:
        raise ConfigurationError(f"Provider '{provider_name}' not found in configuration.")

    strategy_name = provider_data.get("auth_strategy")
    if not strategy_name:
        return NoAuth(provider_name)

    if strategy_name == "api_key":
        return ApiKeyAuth(provider_name)

    if strategy_name == "device_flow":
        client_id = provider_data.get("client_id")
        device_code_url = provider_data.get("device_code_url")
        token_url = provider_data.get("token_url")
        scope = provider_data.get("scope")

        if not all([client_id, device_code_url, token_url, scope]):
            raise ConfigurationError(
                f"Provider '{provider_name}' is missing required device flow settings."
            )

        return DeviceFlowAuth(
            provider_name, client_id, device_code_url, token_url, scope
        )

    raise ConfigurationError(
        f"Unknown auth strategy '{strategy_name}' for provider '{provider_name}'."
    )


def get_credentials(
    provider_name: str, model_alias: str, verbose: bool = False
) -> dict[str, Any] | None:
    """
    Get credentials for a given provider and model.

    This function will first try to retrieve stored credentials. If they are
    not available or invalid, it will trigger the authentication process.
    """
    if verbose:
        logger.setLevel("DEBUG")

    try:
        strategy = get_auth_strategy(provider_name, model_alias)
        creds = strategy.get_credentials()
        if creds:
            logger.info("Successfully retrieved credentials for %s", provider_name)
            return creds

        logger.info(
            "No valid credentials found for %s. Initiating authentication.",
            provider_name,
        )
        return strategy.authenticate()

    except (ConfigurationError, AuthenticationError) as e:
        logger.error("Authentication failed for %s: %s", provider_name, e)
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred during authentication for %s", provider_name)
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
        pass
