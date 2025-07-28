"""Tests for the interactive configuration wizard."""

from unittest.mock import MagicMock, patch

import pytest

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
