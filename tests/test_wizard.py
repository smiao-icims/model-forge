"""Tests for the interactive configuration wizard."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from modelforge.exceptions import AuthenticationError
from modelforge.wizard import ConfigWizard


class TestConfigWizard:
    """Test ConfigWizard functionality."""

    def test_wizard_initialization(self) -> None:
        """Test wizard initializes correctly."""
        wizard = ConfigWizard()
        assert wizard.registry is not None
        assert wizard.current_config is not None
        assert isinstance(wizard.is_local, bool)

    def test_get_ollama_models_success(self) -> None:
        """Test successful Ollama model discovery."""
        wizard = ConfigWizard()

        # Mock subprocess.run to return ollama list output
        mock_result = MagicMock()
        mock_result.stdout = """NAME                            ID              SIZE      MODIFIED
llama3.2:latest                 a80c4f17acd5    2.0 GB    3 days ago
qwen3:latest                    45b456ec6c6a    4.7 GB    2 weeks ago
mixtral:8x7b                    7bdf52dc5b01    26 GB     3 weeks ago
"""
        mock_result.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", return_value=mock_result),
        ):
            models = wizard._get_ollama_models()

        assert len(models) == 3
        assert "llama3.2" in models
        assert "qwen3" in models
        assert "mixtral" in models

    def test_get_ollama_models_not_installed(self) -> None:
        """Test Ollama model discovery when Ollama is not installed."""
        wizard = ConfigWizard()

        with patch("shutil.which", return_value=None):
            models = wizard._get_ollama_models()

        assert models == []

    def test_get_ollama_models_empty(self) -> None:
        """Test Ollama model discovery with no models."""
        wizard = ConfigWizard()

        mock_result = MagicMock()
        mock_result.stdout = "NAME    ID    SIZE    MODIFIED\n"  # Header only
        mock_result.returncode = 0

        with (
            patch("shutil.which", return_value="/usr/bin/ollama"),
            patch("subprocess.run", return_value=mock_result),
        ):
            models = wizard._get_ollama_models()

        assert models == []

    def test_get_or_create_provider_config_existing(self) -> None:
        """Test getting existing provider config."""
        wizard = ConfigWizard()
        wizard.current_config = {
            "providers": {
                "openai": {
                    "llm_type": "custom",
                    "auth_strategy": "custom_auth",
                }
            }
        }

        config = wizard._get_or_create_provider_config("openai")
        assert config["llm_type"] == "custom"
        assert config["auth_strategy"] == "custom_auth"

    def test_get_or_create_provider_config_default(self) -> None:
        """Test creating default provider configs."""
        wizard = ConfigWizard()
        wizard.current_config = {"providers": {}}

        # Test known providers
        openai_config = wizard._get_or_create_provider_config("openai")
        assert openai_config["llm_type"] == "openai_compatible"
        assert openai_config["auth_strategy"] == "api_key"

        github_config = wizard._get_or_create_provider_config("github_copilot")
        assert github_config["llm_type"] == "github_copilot"
        assert github_config["auth_strategy"] == "device_flow"
        assert "auth_details" in github_config

        # Test hyphenated version
        github_hyphen_config = wizard._get_or_create_provider_config("github-copilot")
        assert github_hyphen_config["llm_type"] == "github_copilot"
        assert github_hyphen_config["auth_strategy"] == "device_flow"
        assert "auth_details" in github_hyphen_config

        ollama_config = wizard._get_or_create_provider_config("ollama")
        assert ollama_config["llm_type"] == "ollama"
        assert ollama_config["auth_strategy"] == "none"

    def test_get_or_create_provider_config_unknown(self) -> None:
        """Test creating config for unknown provider."""
        wizard = ConfigWizard()
        wizard.current_config = {"providers": {}}

        config = wizard._get_or_create_provider_config("unknown_provider")
        assert config["llm_type"] == "openai_compatible"
        assert config["auth_strategy"] == "api_key"

    @patch("modelforge.wizard.questionary")
    def test_run_terminal_check(self, mock_questionary: MagicMock) -> None:
        """Test wizard exits gracefully when not in terminal."""
        wizard = ConfigWizard()

        with (
            patch("sys.stdin.isatty", return_value=False),
            pytest.raises(SystemExit) as exc_info,
        ):
            wizard.run()

        assert exc_info.value.code == 1
        mock_questionary.print.assert_not_called()

    def test_save_configuration(self) -> None:
        """Test configuration saving."""
        wizard = ConfigWizard()

        with (
            patch("modelforge.config.save_config") as mock_save,
            patch("modelforge.config.get_config_path") as mock_path,
            patch("modelforge.config.get_config_from_path") as mock_get,
        ):
            mock_path.return_value = "/test/path"
            mock_get.return_value = ({"providers": {}}, "/test/path")

            wizard._save_configuration("test_provider", "test_model", local=False)

            mock_save.assert_called_once()
            saved_config = mock_save.call_args[0][0]

            assert "providers" in saved_config
            assert "test_provider" in saved_config["providers"]
            assert "models" in saved_config["providers"]["test_provider"]
            assert "test_model" in saved_config["providers"]["test_provider"]["models"]

    @patch("modelforge.wizard.questionary")
    def test_choose_scope_global(self, mock_questionary: MagicMock) -> None:
        """Test choosing global scope."""
        wizard = ConfigWizard()
        wizard.is_local = False  # Currently global

        mock_questionary.select.return_value.ask.return_value = "global"

        result = wizard._choose_scope()

        assert result == "global"
        mock_questionary.select.assert_called_once()
        call_args = mock_questionary.select.call_args
        assert "Where should the configuration be saved?" in call_args[0]
        assert len(call_args[1]["choices"]) == 2

    @patch("modelforge.wizard.questionary")
    def test_choose_scope_local(self, mock_questionary: MagicMock) -> None:
        """Test choosing local scope."""
        wizard = ConfigWizard()
        wizard.is_local = True  # Currently local

        mock_questionary.select.return_value.ask.return_value = "local"

        result = wizard._choose_scope()

        assert result == "local"

    @patch("modelforge.wizard.questionary")
    def test_select_provider_success(self, mock_questionary: MagicMock) -> None:
        """Test successful provider selection."""
        wizard = ConfigWizard()

        # Mock registry methods
        wizard.registry.get_available_providers = MagicMock(
            return_value=[
                {
                    "name": "openai",
                    "display_name": "OpenAI",
                    "auth_types": ["api_key"],
                },
                {
                    "name": "github-copilot",
                    "display_name": "GitHub Copilot",
                    "auth_types": ["device_flow"],
                },
            ]
        )
        wizard.registry.get_configured_providers = MagicMock(return_value={})
        wizard.current_model = {"provider": "openai"}

        mock_questionary.print = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "openai"

        result = wizard._select_provider()

        assert result == "openai"
        wizard.registry.get_available_providers.assert_called_once()
        wizard.registry.get_configured_providers.assert_called_once()

    @patch("modelforge.wizard.questionary")
    def test_select_provider_with_configured(self, mock_questionary: MagicMock) -> None:
        """Test provider selection with configured providers."""
        wizard = ConfigWizard()

        wizard.registry.get_available_providers = MagicMock(
            return_value=[
                {
                    "name": "openai",
                    "display_name": "OpenAI",
                    "auth_types": ["api_key"],
                }
            ]
        )
        wizard.registry.get_configured_providers = MagicMock(
            return_value={"openai": {"models": {"gpt-4": {}}}}
        )
        wizard.current_model = {}

        mock_questionary.print = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "openai"

        result = wizard._select_provider()

        assert result == "openai"

    @patch("modelforge.wizard.questionary")
    def test_select_provider_exception_fallback(
        self, mock_questionary: MagicMock
    ) -> None:
        """Test provider selection fallback on exception."""
        wizard = ConfigWizard()

        wizard.registry.get_available_providers = MagicMock(
            side_effect=Exception("API error")
        )

        mock_questionary.print = MagicMock()
        mock_questionary.text.return_value.ask.return_value = "custom_provider"

        result = wizard._select_provider()

        assert result == "custom_provider"
        mock_questionary.print.assert_called()
        mock_questionary.text.assert_called_once()

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.auth.get_credentials")
    def test_configure_authentication_existing_creds(
        self, mock_get_creds: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test authentication with existing credentials."""
        wizard = ConfigWizard()

        mock_get_creds.return_value = {"api_key": "test-key"}
        mock_questionary.print = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "use_existing"

        result = wizard._configure_authentication("openai")

        assert result is True
        mock_questionary.select.assert_called_once()

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.auth.get_credentials")
    def test_configure_authentication_github_copilot(
        self, mock_get_creds: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test GitHub Copilot authentication flow."""
        wizard = ConfigWizard()

        mock_get_creds.side_effect = Exception("No credentials")
        mock_questionary.print = MagicMock()

        with patch.object(
            wizard, "_configure_github_copilot_auth", return_value=True
        ) as mock_gh_auth:
            result = wizard._configure_authentication("github-copilot")

        assert result is True
        mock_gh_auth.assert_called_once()

    @patch("modelforge.wizard.questionary")
    def test_configure_authentication_ollama(self, mock_questionary: MagicMock) -> None:
        """Test Ollama authentication (no auth needed)."""
        wizard = ConfigWizard()

        mock_questionary.print = MagicMock()

        result = wizard._configure_authentication("ollama")

        assert result is True
        mock_questionary.print.assert_called()

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.auth.get_credentials")
    def test_configure_authentication_api_key(
        self, mock_get_creds: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test API key authentication flow."""
        wizard = ConfigWizard()

        mock_get_creds.side_effect = Exception("No credentials")
        mock_questionary.print = MagicMock()

        with patch.object(
            wizard, "_configure_api_key_auth", return_value=True
        ) as mock_api_auth:
            result = wizard._configure_authentication("openai")

        assert result is True
        mock_api_auth.assert_called_once()

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.auth.DeviceFlowAuth")
    def test_configure_github_copilot_auth_success(
        self, mock_device_flow: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test successful GitHub Copilot authentication."""
        wizard = ConfigWizard()

        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate.return_value = {"access_token": "test-token"}
        mock_device_flow.return_value = mock_auth_instance

        provider_config: dict[str, Any] = {"auth_details": {"client_id": "test-id"}}

        mock_questionary.print = MagicMock()

        result = wizard._configure_github_copilot_auth(provider_config)

        assert result is True
        mock_device_flow.assert_called_once()
        mock_auth_instance.authenticate.assert_called_once()

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.auth.DeviceFlowAuth")
    def test_configure_github_copilot_auth_failure(
        self, mock_device_flow: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test failed GitHub Copilot authentication."""
        wizard = ConfigWizard()

        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate.return_value = None
        mock_device_flow.return_value = mock_auth_instance

        provider_config: dict[str, Any] = {"auth_details": {}}

        mock_questionary.print = MagicMock()

        result = wizard._configure_github_copilot_auth(provider_config)

        assert result is False

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.auth.DeviceFlowAuth")
    def test_configure_github_copilot_auth_exception(
        self, mock_device_flow: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test GitHub Copilot authentication with exception."""
        wizard = ConfigWizard()

        mock_device_flow.side_effect = Exception("Auth error")

        provider_config: dict[str, Any] = {"auth_details": {}}

        mock_questionary.print = MagicMock()

        result = wizard._configure_github_copilot_auth(provider_config)

        assert result is False

    @patch("modelforge.wizard.questionary")
    @patch("os.getenv")
    def test_configure_api_key_auth_env_var(
        self, mock_getenv: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test API key auth with environment variable."""
        wizard = ConfigWizard()

        mock_getenv.return_value = "test-api-key"
        mock_questionary.print = MagicMock()

        result = wizard._configure_api_key_auth("openai", {})

        assert result is True
        mock_questionary.print.assert_called()

    @patch("modelforge.wizard.questionary")
    @patch("os.getenv")
    @patch("modelforge.validation.InputValidator.validate_api_key")
    @patch("modelforge.auth.ApiKeyAuth")
    def test_configure_api_key_auth_prompt(
        self,
        mock_api_key_auth: MagicMock,
        mock_validate: MagicMock,
        mock_getenv: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test API key auth with user prompt."""
        wizard = ConfigWizard()

        mock_getenv.return_value = None
        mock_validate.return_value = "validated-key"
        mock_auth_instance = MagicMock()
        mock_api_key_auth.return_value = mock_auth_instance

        mock_questionary.password.return_value.ask.return_value = "user-key"
        mock_questionary.print = MagicMock()

        result = wizard._configure_api_key_auth("openai", {})

        assert result is True
        mock_validate.assert_called_with("user-key", "openai")
        mock_auth_instance._save_auth_data.assert_called_with(
            {"api_key": "validated-key"}
        )

    @patch("modelforge.wizard.questionary")
    @patch("os.getenv")
    def test_configure_api_key_auth_empty(
        self, mock_getenv: MagicMock, mock_questionary: MagicMock
    ) -> None:
        """Test API key auth with empty input."""
        wizard = ConfigWizard()

        mock_getenv.return_value = None
        mock_questionary.password.return_value.ask.return_value = ""

        result = wizard._configure_api_key_auth("openai", {})

        assert result is False

    @patch("modelforge.wizard.questionary")
    @patch("os.getenv")
    @patch("modelforge.validation.InputValidator.validate_api_key")
    def test_configure_api_key_auth_invalid(
        self,
        mock_validate: MagicMock,
        mock_getenv: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test API key auth with invalid key."""
        wizard = ConfigWizard()

        mock_getenv.return_value = None
        mock_validate.side_effect = Exception("Invalid key")

        mock_questionary.password.return_value.ask.return_value = "invalid-key"
        mock_questionary.print = MagicMock()

        result = wizard._configure_api_key_auth("openai", {})

        assert result is False

    @patch("modelforge.wizard.questionary")
    def test_select_model_success(self, mock_questionary: MagicMock) -> None:
        """Test successful model selection."""
        wizard = ConfigWizard()
        wizard.current_model = {"provider": "openai", "model": "gpt-4"}

        wizard.registry.get_available_models = MagicMock(
            return_value=[
                {
                    "id": "gpt-4",
                    "display_name": "GPT-4",
                    "context_length": 8192,
                    "pricing": {"input_per_1m_tokens": 30.0},
                }
            ]
        )
        wizard.registry.get_configured_models = MagicMock(return_value=["gpt-4"])

        mock_questionary.print = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "gpt-4"

        result = wizard._select_model("openai")

        assert result == "gpt-4"

    @patch("modelforge.wizard.questionary")
    def test_select_model_ollama(self, mock_questionary: MagicMock) -> None:
        """Test model selection for Ollama."""
        wizard = ConfigWizard()
        wizard.current_model = {}

        with patch.object(wizard, "_get_ollama_models", return_value=["llama3.2"]):
            wizard.registry.get_configured_models = MagicMock(return_value=[])

            mock_questionary.print = MagicMock()
            mock_questionary.select.return_value.ask.return_value = "llama3.2"

            result = wizard._select_model("ollama")

        assert result == "llama3.2"

    @patch("modelforge.wizard.questionary")
    def test_select_model_no_models(self, mock_questionary: MagicMock) -> None:
        """Test model selection when no models found."""
        wizard = ConfigWizard()

        wizard.registry.get_available_models = MagicMock(return_value=[])

        mock_questionary.print = MagicMock()
        mock_questionary.text.return_value.ask.return_value = "custom-model"

        result = wizard._select_model("custom")

        assert result == "custom-model"

    @patch("modelforge.wizard.questionary")
    def test_select_model_exception(self, mock_questionary: MagicMock) -> None:
        """Test model selection with exception."""
        wizard = ConfigWizard()

        wizard.registry.get_available_models = MagicMock(
            side_effect=Exception("API error")
        )

        mock_questionary.print = MagicMock()
        mock_questionary.text.return_value.ask.return_value = "fallback-model"

        result = wizard._select_model("provider")

        assert result == "fallback-model"

    @patch("modelforge.wizard.questionary")
    @patch("modelforge.telemetry.TelemetryCallback")
    @patch("langchain_core.messages.HumanMessage")
    def test_test_configuration_success(
        self,
        mock_human_message: MagicMock,
        mock_telemetry: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test successful configuration testing."""
        wizard = ConfigWizard()

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Test successful!")
        wizard.registry.get_llm = MagicMock(return_value=mock_llm)

        # Mock telemetry
        mock_telemetry_instance = MagicMock()
        mock_telemetry_instance.metrics.token_usage.total_tokens = 10
        mock_telemetry_instance.metrics.metadata = {}
        mock_telemetry.return_value = mock_telemetry_instance

        mock_questionary.print = MagicMock()

        result = wizard._test_configuration("openai", "gpt-4")

        assert result is True
        wizard.registry.get_llm.assert_called_once()
        mock_llm.invoke.assert_called_once()

    @patch("modelforge.wizard.questionary")
    def test_test_configuration_auth_error(self, mock_questionary: MagicMock) -> None:
        """Test configuration testing with auth error."""
        wizard = ConfigWizard()

        wizard.registry.get_llm = MagicMock(
            side_effect=AuthenticationError("Auth failed", suggestion="Check API key")
        )

        mock_questionary.print = MagicMock()

        result = wizard._test_configuration("openai", "gpt-4")

        assert result is False

    @patch("modelforge.wizard.questionary")
    def test_test_configuration_quota_exceeded(
        self, mock_questionary: MagicMock
    ) -> None:
        """Test configuration testing with quota exceeded."""
        wizard = ConfigWizard()

        wizard.registry.get_llm = MagicMock(
            side_effect=Exception("quota exceeded for this model")
        )

        mock_questionary.print = MagicMock()

        result = wizard._test_configuration("openai", "gpt-4")

        assert result is True  # Should still return True for quota errors

    @patch("modelforge.wizard.questionary")
    def test_test_configuration_other_error(self, mock_questionary: MagicMock) -> None:
        """Test configuration testing with other error."""
        wizard = ConfigWizard()

        wizard.registry.get_llm = MagicMock(side_effect=Exception("Some other error"))

        mock_questionary.print = MagicMock()

        result = wizard._test_configuration("openai", "gpt-4")

        assert result is False

    @patch("modelforge.config.save_config")
    @patch("modelforge.config.get_config_path")
    @patch("modelforge.config.get_config_from_path")
    @patch("modelforge.config.get_config")
    @patch("modelforge.wizard.questionary")
    def test_save_configuration_github_copilot_normalization(
        self,
        mock_questionary: MagicMock,
        mock_get_config: MagicMock,
        mock_get_config_from_path: MagicMock,
        mock_get_config_path: MagicMock,
        mock_save_config: MagicMock,
    ) -> None:
        """Test configuration saving with GitHub Copilot name normalization."""
        # Mock the config.get_config() call in ConfigWizard.__init__
        mock_get_config.return_value = ({"providers": {}}, "/test/global")

        wizard = ConfigWizard()

        mock_get_config_path.return_value = "/test/path"
        mock_get_config_from_path.return_value = ({"providers": {}}, "/test/path")
        mock_questionary.print = MagicMock()

        wizard._save_configuration("github-copilot", "gpt-4", local=False)

        # Should normalize to github_copilot
        saved_config = mock_save_config.call_args[0][0]
        assert "github_copilot" in saved_config["providers"]
