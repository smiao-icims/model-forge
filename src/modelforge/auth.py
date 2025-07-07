# Standard library imports
import getpass
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

# Third-party imports
import keyring
import requests

# Local imports
from .exceptions import AuthenticationError, ConfigurationError
from .logging_config import get_logger

logger = get_logger(__name__)


class AuthStrategy(ABC):
    """Abstract base class for all authentication strategies."""

    @abstractmethod
    def authenticate(self) -> dict[str, Any]:
        """
        Perform the authentication flow.

        Returns:
            A dictionary containing the necessary credentials (e.g., api_key, token).
        """

    @abstractmethod
    def get_credentials(self) -> dict[str, Any] | None:
        """
        Retrieve stored credentials without performing a new authentication.

        Returns:
            A dictionary of stored credentials or None if not found.
        """


class ApiKeyAuth(AuthStrategy):
    """Handles simple API key authentication using the system's keyring."""

    def __init__(self, provider_name: str) -> None:
        """
        Initializes the strategy for a specific provider.

        Args:
            provider_name: The unique name of the provider (e.g., 'openai').
                           This is used as the service name in the keyring.
        """
        self.provider_name = provider_name
        self.username = (
            f"{provider_name}_user"  # A consistent username for the keyring entry
        )

    def authenticate(self) -> dict[str, Any]:
        """
        Prompts the user for an API key and saves it to the keyring.

        Returns:
            A dictionary containing the API key.

        Raises:
            AuthenticationError: If the API key is empty or keyring storage fails.
        """
        logger.info(
            "Starting API key authentication for provider: %s", self.provider_name
        )
        print(f"Please enter the API key for {self.provider_name}:")
        api_key = getpass.getpass("API Key: ")

        if not api_key or not api_key.strip():
            logger.error("Empty API key provided for provider: %s", self.provider_name)
            raise AuthenticationError("API key cannot be empty")

        try:
            keyring.set_password(self.provider_name, self.username, api_key)
            logger.info(
                "API key stored successfully for provider: %s", self.provider_name
            )
            print(f"API key for {self.provider_name} has been stored securely.")
            return {"api_key": api_key}
        except Exception as e:
            logger.exception(
                "Failed to store API key for provider %s: %s",
                self.provider_name,
                str(e),
            )
            raise AuthenticationError(
                f"Failed to store API key for {self.provider_name}"
            ) from e

    def get_credentials(self) -> dict[str, Any] | None:
        """
        Retrieves the API key from the keyring.

        Returns:
            A dictionary containing the API key if found, None otherwise.
        """
        try:
            api_key = keyring.get_password(self.provider_name, self.username)
            if api_key:
                logger.debug("Retrieved API key for provider: %s", self.provider_name)
                return {"api_key": api_key}
            logger.debug("No API key found for provider: %s", self.provider_name)
            return None
        except Exception as e:
            logger.exception(
                "Failed to retrieve API key for provider %s: %s",
                self.provider_name,
                str(e),
            )
            return None


class DeviceFlowAuth(AuthStrategy):
    """Handles the OAuth 2.0 Device Authorization Grant flow."""

    def __init__(
        self,
        provider_name: str,
        client_id: str,
        device_code_url: str,
        token_url: str,
        scope: str,
    ) -> None:
        self.provider_name = provider_name
        self.client_id = client_id
        self.device_code_url = device_code_url
        self.token_url = token_url
        self.scope = scope
        self.username = f"{provider_name}_user"

    def authenticate(self) -> dict[str, Any]:
        """
        Performs the full device auth flow and stores the token.

        Returns:
            A dictionary containing the access token.

        Raises:
            AuthenticationError: If the device code request fails or authentication fails.
        """
        logger.info(
            "Starting device authentication flow for provider: %s", self.provider_name
        )
        # Step 1: Get the device and user codes
        headers = {"Accept": "application/json"}
        payload = {"client_id": self.client_id, "scope": self.scope}

        try:
            response = requests.post(
                self.device_code_url, data=payload, headers=headers
            )
            response.raise_for_status()
            device_code_data = response.json()
        except requests.exceptions.HTTPError as e:
            logger.exception(
                "HTTP error requesting device code for %s: %s",
                self.provider_name,
                str(e),
            )
            raise AuthenticationError(
                f"Failed to request device code for {self.provider_name}"
            ) from e
        except requests.exceptions.JSONDecodeError as e:
            logger.exception(
                "Invalid JSON response from device code request for %s",
                self.provider_name,
            )
            raise AuthenticationError(
                f"Invalid response from {self.provider_name} device code endpoint"
            ) from e
        except requests.exceptions.RequestException as e:
            logger.exception(
                "Network error requesting device code for %s: %s",
                self.provider_name,
                str(e),
            )
            raise AuthenticationError(
                f"Network error connecting to {self.provider_name}"
            ) from e

        logger.info("Device code obtained for %s", self.provider_name)
        print("\n--- Device Authentication ---")
        print(
            f"Please open the following URL in your browser: {device_code_data['verification_uri']}"
        )
        print(f"And enter this code: {device_code_data['user_code']}")
        print("---------------------------\n")

        # Step 2: Poll for the access token
        logger.info("Polling for access token for %s", self.provider_name)
        while True:
            time.sleep(device_code_data["interval"])
            token_payload = {
                "client_id": self.client_id,
                "device_code": device_code_data["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }

            try:
                token_response = requests.post(
                    self.token_url, data=token_payload, headers=headers
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
                    if error_info.get("error") == "authorization_pending":
                        logger.debug(
                            "Authorization pending for %s, continuing to poll",
                            self.provider_name,
                        )
                        continue
                    if error_info.get("error") == "slow_down":
                        logger.debug(
                            "Rate limited while polling for %s, slowing down",
                            self.provider_name,
                        )
                        time.sleep(5)
                        continue
                    logger.exception(
                        "Authentication failed for %s: %s",
                        self.provider_name,
                        error_info.get("error"),
                    )
                    raise AuthenticationError(
                        f"Authentication failed for {self.provider_name}: {error_info.get('error_description', 'Unknown error')}"
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
                    "Network error while polling for token from %s: %s",
                    self.provider_name,
                    str(e),
                )
                raise AuthenticationError(
                    f"Network error while polling for token from {self.provider_name}"
                ) from e

            if "access_token" in token_data:
                # Store the complete token information including expiration
                token_info = {
                    "access_token": token_data["access_token"],
                    "token_type": token_data.get("token_type", "bearer"),
                    "expires_in": token_data.get(
                        "expires_in", 28800
                    ),  # Default to 8 hours
                    "acquired_at": datetime.now().isoformat(),
                    "scope": token_data.get("scope", self.scope),
                }

                # Store refresh token if provided
                if "refresh_token" in token_data:
                    token_info["refresh_token"] = token_data["refresh_token"]

                # Store as JSON string in keyring
                try:
                    keyring.set_password(
                        self.provider_name, self.username, json.dumps(token_info)
                    )
                    logger.info(
                        "Successfully authenticated and stored token for %s",
                        self.provider_name,
                    )
                    print(
                        f"Successfully authenticated and stored token for {self.provider_name}."
                    )
                    return {"access_token": token_data["access_token"]}
                except Exception as e:
                    logger.exception(
                        "Failed to store token for %s: %s", self.provider_name, str(e)
                    )
                    raise AuthenticationError(
                        f"Failed to store token for {self.provider_name}"
                    ) from e
            elif token_data.get("error") == "authorization_pending":
                logger.debug(
                    "Authorization still pending for %s, continuing to poll",
                    self.provider_name,
                )
                continue
            elif token_data.get("error") == "slow_down":
                logger.debug(
                    "Rate limited while polling for %s, slowing down",
                    self.provider_name,
                )
                time.sleep(5)
                continue
            else:
                error_desc = token_data.get("error_description", "Unknown error")
                logger.error(
                    "Failed to get access token for %s: %s",
                    self.provider_name,
                    error_desc,
                )
                raise AuthenticationError(
                    f"Failed to get access token for {self.provider_name}: {error_desc}"
                )

    def get_credentials(self) -> dict[str, Any] | None:
        """
        Retrieves the stored access token from the keyring, checking for expiration.

        Returns:
            A dictionary containing the access token if valid, None otherwise.
        """
        try:
            stored_data = keyring.get_password(self.provider_name, self.username)
            if not stored_data:
                logger.debug(
                    "No stored credentials found for provider: %s", self.provider_name
                )
                return None

            try:
                # Try to parse as JSON (new format)
                token_info = json.loads(stored_data)

                # Check if token is expired
                acquired_at = datetime.fromisoformat(token_info["acquired_at"])
                expires_in = token_info.get("expires_in", 28800)  # Default 8 hours
                expiry_time = acquired_at + timedelta(seconds=expires_in)

                # Add 5-minute buffer before expiration
                buffer_time = expiry_time - timedelta(minutes=5)

                if datetime.now() >= buffer_time:
                    logger.warning(
                        "Token for %s is expired or expiring soon", self.provider_name
                    )
                    print(
                        f"Token for {self.provider_name} is expired or expiring soon. Please re-authenticate."
                    )
                    print(
                        f"Run: modelforge config add --provider {self.provider_name} --model <model> --dev-auth"
                    )
                    return None

                logger.debug(
                    "Retrieved valid access token for provider: %s", self.provider_name
                )
                return {"access_token": token_info["access_token"]}

            except (json.JSONDecodeError, KeyError, ValueError):
                # Handle legacy format (just the token string)
                # This is for backward compatibility
                if stored_data.startswith(("gho_", "ghr_")):
                    logger.warning(
                        "Legacy token format detected for %s. Consider re-authenticating",
                        self.provider_name,
                    )
                    print(
                        f"Warning: Legacy token format detected for {self.provider_name}. Consider re-authenticating for better expiration handling."
                    )
                    return {"access_token": stored_data}
                logger.debug(
                    "Stored data for %s is not a valid token format", self.provider_name
                )
                return None
        except Exception as e:
            logger.exception(
                "Failed to retrieve credentials for %s: %s", self.provider_name, str(e)
            )
            return None

    def get_token_info(self) -> dict[str, Any] | None:
        """Get detailed token information for debugging purposes."""
        stored_data = keyring.get_password(self.provider_name, self.username)
        if not stored_data:
            return None

        try:
            token_info = json.loads(stored_data)
            acquired_at = datetime.fromisoformat(token_info["acquired_at"])
            expires_in = token_info.get("expires_in", 28800)
            expiry_time = acquired_at + timedelta(seconds=expires_in)

            return {
                "acquired_at": acquired_at,
                "expires_in": expires_in,
                "expiry_time": expiry_time,
                "time_remaining": expiry_time - datetime.now(),
                "is_expired": datetime.now() >= expiry_time,
                "token_preview": token_info["access_token"][-10:]
                if token_info.get("access_token")
                else "N/A",
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return {
                "legacy_format": True,
                "token_preview": stored_data[-10:] if stored_data else "N/A",
            }


class LocalAuth(AuthStrategy):
    """Handles local models like Ollama that require no authentication."""

    def authenticate(self) -> dict[str, Any]:
        """
        Local models do not require authentication.

        Returns:
            An empty dictionary indicating no credentials are needed.
        """
        logger.info("Local model selected, no authentication required")
        print("Local model selected. No authentication is required.")
        return {}

    def get_credentials(self) -> dict[str, Any] | None:
        """
        Local models do not have stored credentials.

        Returns:
            An empty dictionary indicating no credentials are needed.
        """
        logger.debug("Local model credentials requested - returning empty dict")
        return {}


# We will later implement concrete strategies that inherit from this base class:
#
# class DeviceFlowAuth(AuthStrategy):
#     """Handles the OAuth 2.0 Device Authorization Grant flow."""
#     ...
#
# class LocalAuth(AuthStrategy):
#     """Handles connection to local models like Ollama that require no auth."""
#     ...

# A mapping from auth_strategy names in the config to the classes that handle them.
AUTH_STRATEGY_MAP = {
    "api_key": ApiKeyAuth,
    "device_flow": DeviceFlowAuth,
    "local": LocalAuth,
}


def get_credentials(
    provider_name: str, model_alias: str, verbose: bool = False
) -> dict[str, Any] | None:
    """
    A factory function that retrieves stored credentials for a given provider.

    It reads the main config, determines the correct auth strategy,
    instantiates the handler, and returns the credentials.

    Args:
        provider_name: The name of the provider.
        model_alias: The alias of the model (not directly used here but good for context).
        verbose: If True, print debug information.

    Returns:
        A dictionary of credentials, or None if not found or on error.

    Raises:
        ConfigurationError: If the provider is not found in configuration.
        AuthenticationError: If the authentication strategy is invalid.
    """
    from . import config as app_config  # Use a different name to avoid confusion

    try:
        full_config, _ = app_config.get_config()
        provider_data = full_config.get("providers", {}).get(provider_name)

        if not provider_data:
            logger.error(
                "Provider '%s' not found in configuration for auth", provider_name
            )
            raise ConfigurationError(
                f"Provider '{provider_name}' not found in configuration"
            )

        auth_strategy_name = provider_data.get("auth_strategy")
        auth_class = AUTH_STRATEGY_MAP.get(auth_strategy_name)

        if verbose:
            logger.debug(
                "Getting credentials for provider: %s, model: %s, auth_strategy: %s",
                provider_name,
                model_alias,
                auth_strategy_name,
            )

        if not auth_class:
            logger.error(
                "Unknown auth_strategy '%s' for provider '%s'",
                auth_strategy_name,
                provider_name,
            )
            raise AuthenticationError(
                f"Unknown auth_strategy '{auth_strategy_name}' for provider '{provider_name}'"
            )

        # Instantiate the auth strategy class
        if auth_strategy_name == "device_flow":
            auth_details = provider_data.get("auth_details", {})
            if verbose:
                logger.debug(
                    "Device flow details for %s: %s",
                    provider_name,
                    list(auth_details.keys()),
                )
            auth_handler = auth_class(provider_name=provider_name, **auth_details)
        else:
            auth_handler = auth_class(provider_name)

        credentials = auth_handler.get_credentials()
        if verbose:
            logger.debug(
                "Retrieved credentials for %s: %s",
                provider_name,
                "Yes" if credentials else "None",
            )
            if credentials:
                cred_keys = list(credentials.keys())
                logger.debug("Credential keys for %s: %s", provider_name, cred_keys)

        return credentials
    except Exception as e:
        logger.exception("Failed to get credentials for %s: %s", provider_name, str(e))
        raise
