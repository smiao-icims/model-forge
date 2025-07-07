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
            raise AuthenticationError("Network error") from e

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
            raise AuthenticationError("Invalid response") from e
        except requests.exceptions.HTTPError as e:
            # Check if this is a recoverable error
            try:
                error_info = response.json()
                logger.exception(
                    "HTTP error requesting device code from %s: %s",
                    self.provider_name,
                    error_info.get("error"),
                )
                raise AuthenticationError("Authentication failed") from e
            except requests.exceptions.JSONDecodeError:
                logger.exception(
                    "HTTP error while polling for token from %s", self.provider_name
                )
                raise AuthenticationError("HTTP error") from e
        except requests.exceptions.RequestException as e:
            logger.exception(
                "Network error while polling for token from %s",
                self.provider_name,
            )
            raise AuthenticationError(
                f"Network error while polling for token from {self.provider_name}"
            ) from e

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
                raise AuthenticationError(
                    f"Invalid response from {self.provider_name} token endpoint"
                ) from e
            except requests.exceptions.HTTPError as e:
                # Check if this is a recoverable error
                try:
                    error_info = token_response.json()
                    logger.exception(
                        "HTTP error while polling for token from %s: %s",
                        self.provider_name,
                        error_info.get("error"),
                    )
                    raise AuthenticationError(
                        f"Authentication failed for {self.provider_name}: "
                        f"{error_info.get('error_description', 'Unknown error')}"
                    ) from e
                except requests.exceptions.JSONDecodeError:
                    logger.exception(
                        "HTTP error while polling for token from %s", self.provider_name
                    )
                    raise AuthenticationError(
                        f"HTTP error while polling for token from {self.provider_name}"
                    ) from e
            except requests.exceptions.RequestException as e:
                logger.exception(
                    "Network error while polling for token from %s",
                    self.provider_name,
                )
                raise AuthenticationError(
                    f"Network error while polling for token from {self.provider_name}"
                ) from e

            if "access_token" in token_data:
                # Success! Store the token
                expires_in = token_data.get("expires_in", 28800)  # Default to 8 hours
                token_info = {
                    "access_token": token_data["access_token"],
                    "expires_in": expires_in,
                    "expires_at": (
                        datetime.now(UTC) + timedelta(seconds=expires_in)
                    ).isoformat(),
                    "acquired_at": datetime.now(UTC).isoformat(),
                    "scope": token_data.get("scope", self.scope),
                }

                try:
                    # Store as JSON in keyring for structured data
                    keyring.set_password(
                        self.provider_name,
                        f"{self.provider_name}_user",
                        json.dumps(token_info),
                    )
                    logger.info(
                        "Access token stored successfully for %s", self.provider_name
                    )
                    print(
                        f"Successfully authenticated and stored token for "
                        f"{self.provider_name}."
                    )
                    return {"access_token": token_data["access_token"]}
                except Exception as e:
                    logger.exception("Failed to store token for %s", self.provider_name)
                    raise AuthenticationError(
                        f"Failed to store token for {self.provider_name}"
                    ) from e
            elif token_data.get("error") == "authorization_pending":
                logger.debug(
                    "Authorization still pending for %s, continuing to poll",
                    self.provider_name,
                )
                continue  # Continue polling
            elif token_data.get("error") == "slow_down":
                logger.debug(
                    "Rate limited, slowing down polling for %s", self.provider_name
                )
                time.sleep(5)  # Add extra delay for rate limiting
                continue
            else:
                # Error occurred
                error_desc = token_data.get(
                    "error_description", token_data.get("error", "Unknown error")
                )
                logger.error(
                    "Authentication failed for %s: %s",
                    self.provider_name,
                    error_desc,
                )
                raise AuthenticationError(
                    f"Failed to get access token for {self.provider_name}: {error_desc}"
                )

    def get_credentials(self) -> dict[str, Any] | None:
        """Retrieve stored token from keyring."""
        try:
            stored_data = keyring.get_password(
                self.provider_name, f"{self.provider_name}_user"
            )
            if not stored_data:
                logger.debug("No stored token found for %s", self.provider_name)
                return None

            # Try to parse as JSON (new format)
            try:
                token_info = json.loads(stored_data)
                if "expires_at" in token_info:
                    expiry_time = datetime.fromisoformat(
                        token_info["expires_at"].replace("Z", "+00:00")
                    )
                    # Add 5-minute buffer for token expiration
                    buffer_time = expiry_time - timedelta(minutes=5)

                    if datetime.now(UTC) >= buffer_time:
                        logger.warning(
                            "Token for %s is expired or expiring soon",
                            self.provider_name,
                        )
                        print(
                            f"Token for {self.provider_name} is expired or expiring "
                            f"soon. Please re-authenticate."
                        )
                        print(
                            f"Run: modelforge config add --provider "
                            f"{self.provider_name} --model <model> --dev-auth"
                        )
                        return None

                    logger.debug("Valid token found for %s", self.provider_name)
                    return {"access_token": token_info["access_token"]}

            except (json.JSONDecodeError, KeyError):
                # Fallback to old format (plain string token)
                if stored_data.startswith(("gho_", "ghr_")):
                    logger.warning(
                        "Legacy token format detected for %s. "
                        "Consider re-authenticating",
                        self.provider_name,
                    )
                    print(
                        f"Warning: Legacy token format detected for "
                        f"{self.provider_name}. Consider re-authenticating for "
                        f"better expiration handling."
                    )
                    return {"access_token": stored_data}

                logger.warning("Invalid token format for %s", self.provider_name)
                return None

        except Exception:
            logger.exception(
                "Failed to retrieve credentials for %s", self.provider_name
            )
            return None

    def get_token_info(self) -> dict[str, Any] | None:
        """Get detailed token information for debugging."""
        try:
            stored_data = keyring.get_password(
                self.provider_name, f"{self.provider_name}_user"
            )
            if not stored_data:
                return None

            try:
                token_info = json.loads(stored_data)
                if "expires_at" in token_info:
                    expiry_time = datetime.fromisoformat(
                        token_info["expires_at"].replace("Z", "+00:00")
                    )
                    expires_in = int((expiry_time - datetime.now(UTC)).total_seconds())

                    return {
                        "expires_in": expires_in,
                        "expiry_time": expiry_time,
                        "time_remaining": expiry_time - datetime.now(UTC),
                        "is_expired": datetime.now(UTC) >= expiry_time,
                        "token_preview": token_info["access_token"][-10:]
                        if token_info.get("access_token")
                        else None,
                        "scope": token_info.get("scope"),
                    }
            except (json.JSONDecodeError, KeyError):
                return {"legacy_token": True, "token_preview": stored_data[-10:]}

        except Exception:
            logger.exception("Failed to get token info for %s", self.provider_name)
            return None


def get_auth_strategy(
    provider_name: str,
    model_alias: str | None = None,  # noqa: ARG001
) -> AuthStrategy:
    """
    Get the appropriate authentication strategy for a provider.

    Args:
        provider_name: The name of the provider.
        model_alias: The alias of the model (not directly used here but good
            for context).

    Returns:
        An instance of the appropriate AuthStrategy subclass.

    Raises:
        ConfigurationError: If the provider is not found in configuration.
        AuthenticationError: If the auth strategy is unknown.
    """
    from . import config  # Import here to avoid circular imports

    try:
        config_data, _ = config.get_config()
        providers = config_data.get("providers", {})

        if provider_name not in providers:
            logger.error(
                "Provider '%s' not found in configuration for auth", provider_name
            )
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration"
            )

        provider_data = providers[provider_name]
        auth_strategy_name = provider_data.get("auth_strategy")

        # Default authentication strategies based on llm_type
        if not auth_strategy_name:
            llm_type = provider_data.get("llm_type", "")
            if llm_type in ["openai_compatible", "google_genai"]:
                auth_strategy_name = "api_key"
            elif llm_type == "github_copilot":
                auth_strategy_name = "device_flow"
            elif llm_type == "ollama":
                auth_strategy_name = "local"  # No authentication needed

        # Instantiate the appropriate auth strategy
        if auth_strategy_name == "api_key":
            return ApiKeyAuth(provider_name)
        if auth_strategy_name == "device_flow":
            # Get auth details from provider configuration
            auth_details = provider_data.get("auth_details", {})
            required_fields = ["client_id", "device_code_url", "token_url", "scope"]
            for field in required_fields:
                if field not in auth_details:
                    logger.error(
                        "Missing required auth detail '%s' for provider '%s'",
                        field,
                        provider_name,
                    )
                    raise ConfigurationError(
                        f"Missing auth detail '{field}' for provider '{provider_name}'"
                    )
            return DeviceFlowAuth(provider_name, **auth_details)
        if auth_strategy_name == "local":
            return NoAuth(provider_name)
        logger.error(
            "Unknown auth_strategy '%s' for provider '%s'",
            auth_strategy_name,
            provider_name,
        )
        raise AuthenticationError(
            f"Unknown auth_strategy '{auth_strategy_name}' for provider "
            f"'{provider_name}'"
        )

    except Exception:
        logger.exception("Failed to get auth strategy for %s", provider_name)
        raise


def get_credentials(
    provider_name: str, model_alias: str, verbose: bool = False
) -> dict[str, Any] | None:
    """
    Get stored credentials for a provider.

    Args:
        provider_name: The name of the provider.
        model_alias: The alias of the model.
        verbose: If True, print debug information.

    Returns:
        Dictionary of credentials or None if not found.
    """
    try:
        auth_strategy = get_auth_strategy(provider_name, model_alias)
        credentials = auth_strategy.get_credentials()

        if credentials and verbose and logger.isEnabledFor(10):  # DEBUG level
            cred_keys = list(credentials.keys())
            logger.debug("Credential keys for %s: %s", provider_name, cred_keys)
    except Exception:
        logger.exception("Failed to get credentials for %s", provider_name)
        raise
    else:
        return credentials


class NoAuth(AuthStrategy):
    """No authentication strategy for local providers."""

    def authenticate(self) -> dict[str, Any] | None:
        """No authentication needed."""
        return {}

    def get_credentials(self) -> dict[str, Any] | None:
        """No credentials needed."""
        return {}
