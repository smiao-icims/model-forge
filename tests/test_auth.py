"""Tests for the authentication module."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from modelforge.auth import ApiKeyAuth, DeviceFlowAuth


@pytest.fixture
def mock_keyring(mocker: MockerFixture) -> Mock:
    """Mocks the keyring module."""
    return mocker.patch("modelforge.auth.keyring", autospec=True)


@pytest.fixture
def mock_getpass(mocker: MockerFixture) -> Mock:
    """Mocks the getpass.getpass function."""
    return mocker.patch("modelforge.auth.getpass.getpass", return_value="test-api-key")


@pytest.fixture
def mock_requests(mocker: MockerFixture) -> Mock:
    """Mocks the requests module."""
    return mocker.patch("modelforge.auth.requests", autospec=True)


def test_api_key_auth_authenticate(mock_keyring: Mock, mock_getpass: Mock) -> None:
    """Test that ApiKeyAuth prompts for a key and saves it."""
    auth_strategy = ApiKeyAuth("test_provider")

    credentials = auth_strategy.authenticate()

    mock_getpass.assert_called_once_with("Enter API key for test_provider: ")
    mock_keyring.set_password.assert_called_once_with(
        "test_provider", "test_provider_user", "test-api-key"
    )
    assert credentials == {"api_key": "test-api-key"}


def test_api_key_auth_get_credentials_found(mock_keyring: Mock) -> None:
    """Test retrieving a stored API key."""
    mock_keyring.get_password.return_value = "stored-api-key"
    auth_strategy = ApiKeyAuth("test_provider")

    credentials = auth_strategy.get_credentials()

    mock_keyring.get_password.assert_called_once_with(
        "test_provider", "test_provider_user"
    )
    assert credentials == {"api_key": "stored-api-key"}


def test_api_key_auth_get_credentials_not_found(mock_keyring: Mock) -> None:
    """Test retrieving a non-existent API key."""
    mock_keyring.get_password.return_value = None
    auth_strategy = ApiKeyAuth("test_provider")

    credentials = auth_strategy.get_credentials()

    assert credentials is None


def test_device_flow_auth_success(mock_keyring: Mock, mock_requests: Mock) -> None:
    """Test the successful device flow authentication."""
    # Arrange
    mock_post = mock_requests.post
    mock_post.side_effect = [
        # Device code response
        Mock(
            status_code=200,
            json=Mock(
                return_value={
                    "device_code": "test-device-code",
                    "user_code": "TEST-USER",
                    "verification_uri": "https://test.com/device",
                    "interval": 1,
                }
            ),
        ),
        # First token request (pending)
        Mock(
            status_code=400, json=Mock(return_value={"error": "authorization_pending"})
        ),
        # Second token request (success)
        Mock(
            status_code=200,
            json=Mock(
                return_value={"access_token": "test-access-token", "expires_in": 3600}
            ),
        ),
    ]

    auth_strategy = DeviceFlowAuth(
        provider_name="test_provider",
        client_id="test_client_id",
        device_code_url="https://test.com/device/code",
        token_url="https://test.com/login/oauth/access_token",  # noqa: S106
        scope="read:user",
    )

    # Act
    credentials = auth_strategy.authenticate()

    # Assert
    assert mock_requests.post.call_count == 3
    mock_keyring.set_password.assert_called_once()
    assert credentials is not None
    assert credentials["access_token"] == "test-access-token"
    assert "expires_at" in credentials
    assert "expires_in" in credentials


def test_device_flow_get_credentials_valid_token(mock_keyring: Mock) -> None:
    """Test retrieving a valid, non-expired device flow token."""
    # Arrange
    now = datetime.now(UTC)
    token_info = {
        "access_token": "valid-token",
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    mock_keyring.get_password.return_value = json.dumps(token_info)

    auth_strategy = DeviceFlowAuth(
        "test_provider",
        "test_client",
        "https://device.url",
        "https://token.url",
        "read:user",
    )

    # Act
    credentials = auth_strategy.get_credentials()

    # Assert
    assert credentials is not None
    assert credentials["access_token"] == "valid-token"
    assert "expires_at" in credentials


def test_device_flow_get_credentials_expired_token(mock_keyring: Mock) -> None:
    """Test that an expired token is not returned."""
    # Arrange
    yesterday = datetime.now(UTC) - timedelta(days=1)
    token_info = {
        "access_token": "expired-token",
        "expires_at": yesterday.isoformat(),
    }
    mock_keyring.get_password.return_value = json.dumps(token_info)

    auth_strategy = DeviceFlowAuth(
        "test_provider",
        "test_client",
        "https://device.url",
        "https://token.url",
        "read:user",
    )

    # Act
    credentials = auth_strategy.get_credentials()

    # Assert
    assert credentials is None
