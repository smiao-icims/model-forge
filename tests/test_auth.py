"""Tests for the authentication module."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from modelforge.auth import ApiKeyAuth, DeviceFlowAuth


@pytest.fixture
def mock_config(mocker: MockerFixture) -> Mock:
    """Mocks the config module functions."""
    mock_get_config = mocker.patch("modelforge.auth.get_config")
    mock_save_config = mocker.patch("modelforge.auth.save_config")

    # Setup default config structure
    mock_get_config.return_value = ({"providers": {}}, None)

    return Mock(get_config=mock_get_config, save_config=mock_save_config)


@pytest.fixture
def mock_getpass(mocker: MockerFixture) -> Any:
    """Mocks the getpass.getpass function."""
    return mocker.patch("modelforge.auth.getpass.getpass", return_value="test-api-key")


@pytest.fixture
def mock_requests(mocker: MockerFixture) -> Any:
    """Mocks the requests module."""
    return mocker.patch("modelforge.auth.requests", autospec=True)


@pytest.fixture
def mock_webbrowser(mocker: MockerFixture) -> Any:
    """Mocks the webbrowser module."""
    return mocker.patch("webbrowser.open", autospec=True)


def test_api_key_auth_authenticate(mock_config: Mock, mock_getpass: Mock) -> None:
    """Test that ApiKeyAuth prompts for a key and saves it."""
    auth_strategy = ApiKeyAuth("test_provider")

    credentials = auth_strategy.authenticate()

    mock_getpass.assert_called_once_with("Enter API key for test_provider: ")
    mock_config.save_config.assert_called_once()
    assert credentials == {"api_key": "test-api-key"}


def test_api_key_auth_get_credentials_found(mock_config: Mock) -> None:
    """Test retrieving a stored API key."""
    # Setup config with stored credentials
    mock_config.get_config.return_value = (
        {"providers": {"test_provider": {"auth_data": {"api_key": "stored-api-key"}}}},
        None,
    )

    auth_strategy = ApiKeyAuth("test_provider")

    credentials = auth_strategy.get_credentials()

    assert credentials == {"api_key": "stored-api-key"}


def test_api_key_auth_get_credentials_not_found(mock_config: Mock) -> None:
    """Test retrieving a non-existent API key."""
    # Setup config without stored credentials
    mock_config.get_config.return_value = ({"providers": {}}, None)

    auth_strategy = ApiKeyAuth("test_provider")

    credentials = auth_strategy.get_credentials()

    assert credentials is None


def test_device_flow_auth_success(
    mock_config: Mock, mock_requests: Mock, mock_webbrowser: Mock
) -> None:
    """Test the successful device flow authentication."""
    # Ensure mock_webbrowser is used
    _ = mock_webbrowser
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
                return_value={"access_token": "mock-access-token", "expires_in": 3600}
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
    mock_config.save_config.assert_called()
    assert credentials is not None
    assert credentials["access_token"] == "mock-access-token"  # noqa: S105
    assert "expires_at" in credentials
    assert "expires_in" in credentials


def test_device_flow_get_credentials_valid_token(mock_config: Mock) -> None:
    """Test retrieving a valid, non-expired device flow token."""
    # Arrange
    now = datetime.now(UTC)
    token_info = {
        "access_token": "valid-token",
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }

    mock_config.get_config.return_value = (
        {"providers": {"test_provider": {"auth_data": token_info}}},
        None,
    )

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
    assert credentials["access_token"] == "valid-token"  # noqa: S105
    assert "expires_at" in credentials


def test_device_flow_get_token_info_with_calculated_fields(mock_config: Mock) -> None:
    """Test that get_token_info returns calculated time_remaining and expiry_time."""
    # Arrange
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=2, minutes=30)
    token_info = {
        "access_token": "test-token",
        "expires_at": expires_at.isoformat(),
        "scope": "read:user",
    }

    mock_config.get_config.return_value = (
        {"providers": {"test_provider": {"auth_data": token_info}}},
        None,
    )

    auth_strategy = DeviceFlowAuth(
        "test_provider",
        "test_client",
        "https://device.url",
        "https://token.url",
        "read:user",
    )

    # Act
    result = auth_strategy.get_token_info()

    # Assert
    assert result is not None
    assert result["access_token"] == "test-token"  # noqa: S105
    assert result["scope"] == "read:user"
    assert "time_remaining" in result
    assert "expiry_time" in result

    # Check that time_remaining is approximately 2.5 hours
    time_remaining_str = result["time_remaining"]
    assert "2:" in time_remaining_str  # Should contain "2:" for 2 hours

    # Check that expiry_time is formatted correctly
    expiry_time = result["expiry_time"]
    assert expiry_time.endswith(" UTC")
    assert len(expiry_time) == 23  # "YYYY-MM-DD HH:MM:SS UTC"


def test_device_flow_get_token_info_expired_token(mock_config: Mock) -> None:
    """Test that get_token_info shows 'expired' for expired tokens."""
    # Arrange
    yesterday = datetime.now(UTC) - timedelta(days=1)
    token_info = {
        "access_token": "expired-token",
        "expires_at": yesterday.isoformat(),
    }

    mock_config.get_config.return_value = (
        {"providers": {"test_provider": {"auth_data": token_info}}},
        None,
    )

    auth_strategy = DeviceFlowAuth(
        "test_provider",
        "test_client",
        "https://device.url",
        "https://token.url",
        "read:user",
    )

    # Act
    result = auth_strategy.get_token_info()

    # Assert
    assert result is not None
    assert result["access_token"] == "expired-token"  # noqa: S105
    assert result["time_remaining"] == "expired"
    assert "expiry_time" in result


def test_device_flow_get_token_info_no_expiration(mock_config: Mock) -> None:
    """Test that get_token_info works with tokens that have no expiration info."""
    # Arrange
    token_info = {"access_token": "permanent-token", "scope": "read:user"}

    mock_config.get_config.return_value = (
        {"providers": {"test_provider": {"auth_data": token_info}}},
        None,
    )

    auth_strategy = DeviceFlowAuth(
        "test_provider",
        "test_client",
        "https://device.url",
        "https://token.url",
        "read:user",
    )

    # Act
    result = auth_strategy.get_token_info()

    # Assert
    assert result is not None
    assert result["access_token"] == "permanent-token"  # noqa: S105
    assert result["scope"] == "read:user"
    # No time_remaining or expiry_time should be added if expires_at is missing
    assert "time_remaining" not in result
    assert "expiry_time" not in result


def test_device_flow_get_credentials_expired_token(mock_config: Mock) -> None:
    """Test that an expired token is not returned."""
    # Arrange
    yesterday = datetime.now(UTC) - timedelta(days=1)
    token_info = {
        "access_token": "mock-expired-token",
        "expires_at": yesterday.isoformat(),
    }

    mock_config.get_config.return_value = (
        {"providers": {"test_provider": {"auth_data": token_info}}},
        None,
    )

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
