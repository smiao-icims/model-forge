"""Tests for environment variable authentication support."""

import os
from unittest.mock import Mock, patch

import pytest
from pytest_mock import MockerFixture

from modelforge.auth import (
    ApiKeyAuth,
    DeviceFlowAuth,
    _get_env_var_for_provider,
    _normalize_provider_name_for_env,
)


class TestEnvironmentVariableHelpers:
    """Test helper functions for environment variable support."""

    def test_normalize_provider_name_for_env(self) -> None:
        """Test provider name normalization for env vars."""
        assert _normalize_provider_name_for_env("openai") == "OPENAI"
        assert _normalize_provider_name_for_env("github-copilot") == "GITHUB_COPILOT"
        assert _normalize_provider_name_for_env("github_copilot") == "GITHUB_COPILOT"
        assert _normalize_provider_name_for_env("anthropic") == "ANTHROPIC"

    def test_get_env_var_for_provider_api_key(self) -> None:
        """Test getting API key from environment."""
        with patch.dict(os.environ, {"MODELFORGE_OPENAI_API_KEY": "test-key"}):
            assert _get_env_var_for_provider("openai", "API_KEY") == "test-key"

        # Test with hyphenated provider name
        with patch.dict(os.environ, {"MODELFORGE_GITHUB_COPILOT_API_KEY": "gh-key"}):
            assert _get_env_var_for_provider("github-copilot", "API_KEY") == "gh-key"
            assert _get_env_var_for_provider("github_copilot", "API_KEY") == "gh-key"

    def test_get_env_var_for_provider_access_token(self) -> None:
        """Test getting access token from environment."""
        with patch.dict(
            os.environ, {"MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN": "test-token"}
        ):
            assert (
                _get_env_var_for_provider("github-copilot", "ACCESS_TOKEN")
                == "test-token"
            )
            assert (
                _get_env_var_for_provider("github_copilot", "ACCESS_TOKEN")
                == "test-token"
            )

    def test_get_env_var_not_set(self) -> None:
        """Test when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_env_var_for_provider("openai", "API_KEY") is None
            assert _get_env_var_for_provider("github-copilot", "ACCESS_TOKEN") is None


class TestApiKeyAuthEnvironment:
    """Test API key authentication with environment variables."""

    @pytest.fixture
    def mock_config(self, mocker: MockerFixture) -> Mock:
        """Mock config functions."""
        mock_get_config = mocker.patch("modelforge.auth.get_config")
        mock_save_config = mocker.patch("modelforge.auth.save_config")

        # Setup default config structure
        mock_get_config.return_value = ({"providers": {}}, None)

        return Mock(get_config=mock_get_config, save_config=mock_save_config)

    def test_get_credentials_from_env_var(self, mock_config: Mock) -> None:
        """Test retrieving API key from environment variable."""
        with patch.dict(os.environ, {"MODELFORGE_OPENAI_API_KEY": "env-api-key"}):
            auth = ApiKeyAuth("openai")
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["api_key"] == "env-api-key"
            # Should not call config functions when env var is present
            mock_config.get_config.assert_not_called()

    def test_get_credentials_from_env_var_with_validation(
        self, mock_config: Mock
    ) -> None:
        """Test API key validation when retrieved from environment."""
        # OpenAI keys start with sk-
        with patch.dict(os.environ, {"MODELFORGE_OPENAI_API_KEY": "sk-test123"}):
            auth = ApiKeyAuth("openai")
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["api_key"] == "sk-test123"

    def test_get_credentials_fallback_to_config(self, mock_config: Mock) -> None:
        """Test falling back to config when no env var."""
        with patch.dict(os.environ, {}, clear=True):
            # Setup config to return stored key
            mock_config.get_config.return_value = (
                {"providers": {"openai": {"auth_data": {"api_key": "config-api-key"}}}},
                None,
            )

            auth = ApiKeyAuth("openai")
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["api_key"] == "config-api-key"
            mock_config.get_config.assert_called()

    def test_env_var_takes_precedence_over_config(self, mock_config: Mock) -> None:
        """Test that environment variable takes precedence over config."""
        with patch.dict(os.environ, {"MODELFORGE_OPENAI_API_KEY": "env-api-key"}):
            # Setup config with different key
            mock_config.get_config.return_value = (
                {"providers": {"openai": {"auth_data": {"api_key": "config-api-key"}}}},
                None,
            )

            auth = ApiKeyAuth("openai")
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["api_key"] == "env-api-key"  # Should use env var
            # Should not even check config when env var is present
            mock_config.get_config.assert_not_called()


class TestDeviceFlowAuthEnvironment:
    """Test device flow authentication with environment variables."""

    @pytest.fixture
    def mock_config(self, mocker: MockerFixture) -> Mock:
        """Mock config functions."""
        mock_get_config = mocker.patch("modelforge.auth.get_config")
        mock_save_config = mocker.patch("modelforge.auth.save_config")

        # Setup default config structure
        mock_get_config.return_value = ({"providers": {}}, None)

        return Mock(get_config=mock_get_config, save_config=mock_save_config)

    def test_get_credentials_from_env_var(self, mock_config: Mock) -> None:
        """Test retrieving access token from environment variable."""
        with patch.dict(
            os.environ, {"MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN": "env-token"}
        ):
            auth = DeviceFlowAuth(
                "github-copilot",
                "client-id",
                "https://device.url",
                "https://token.url",
                "scope",
            )
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["access_token"] == "env-token"
            # Should not have expiry info for env tokens
            assert "expires_at" not in creds

    def test_get_credentials_fallback_to_stored_token(self, mock_config: Mock) -> None:
        """Test falling back to stored token when no env var."""
        from datetime import UTC, datetime, timedelta

        with patch.dict(os.environ, {}, clear=True):
            # Setup config with valid token
            future_expiry = datetime.now(UTC) + timedelta(hours=1)
            mock_config.get_config.return_value = (
                {
                    "providers": {
                        "github-copilot": {
                            "auth_data": {
                                "access_token": "stored-token",
                                "refresh_token": "refresh-token",
                                "expires_at": future_expiry.isoformat(),
                            }
                        }
                    }
                },
                None,
            )

            auth = DeviceFlowAuth(
                "github-copilot",
                "client-id",
                "https://device.url",
                "https://token.url",
                "scope",
            )
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["access_token"] == "stored-token"
            mock_config.get_config.assert_called()

    def test_env_var_bypasses_token_refresh(self, mock_config: Mock) -> None:
        """Test that env var tokens don't trigger refresh logic."""
        from datetime import UTC, datetime, timedelta

        with patch.dict(
            os.environ, {"MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN": "env-token"}
        ):
            # Setup config with expired token
            past_expiry = datetime.now(UTC) - timedelta(hours=1)
            mock_config.get_config.return_value = (
                {
                    "providers": {
                        "github-copilot": {
                            "auth_data": {
                                "access_token": "expired-token",
                                "refresh_token": "refresh-token",
                                "expires_at": past_expiry.isoformat(),
                            }
                        }
                    }
                },
                None,
            )

            auth = DeviceFlowAuth(
                "github-copilot",
                "client-id",
                "https://device.url",
                "https://token.url",
                "scope",
            )
            creds = auth.get_credentials()

            assert creds is not None
            assert creds["access_token"] == "env-token"  # Should use env var
            # Should not check config or attempt refresh
            mock_config.get_config.assert_not_called()


class TestEnvironmentVariableIntegration:
    """Integration tests for environment variable support."""

    def test_multiple_providers_with_env_vars(self, mocker: MockerFixture) -> None:
        """Test multiple providers using environment variables."""
        mocker.patch(
            "modelforge.auth.get_config", return_value=({"providers": {}}, None)
        )

        env_vars = {
            "MODELFORGE_OPENAI_API_KEY": "openai-key",
            "MODELFORGE_ANTHROPIC_API_KEY": "anthropic-key",
            "MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN": "github-token",
        }

        with patch.dict(os.environ, env_vars):
            # Test OpenAI
            openai_auth = ApiKeyAuth("openai")
            openai_creds = openai_auth.get_credentials()
            assert openai_creds["api_key"] == "openai-key"

            # Test Anthropic
            anthropic_auth = ApiKeyAuth("anthropic")
            anthropic_creds = anthropic_auth.get_credentials()
            assert anthropic_creds["api_key"] == "anthropic-key"

            # Test GitHub Copilot
            github_auth = DeviceFlowAuth(
                "github-copilot",
                "client-id",
                "https://device.url",
                "https://token.url",
                "scope",
            )
            github_creds = github_auth.get_credentials()
            assert github_creds["access_token"] == "github-token"
