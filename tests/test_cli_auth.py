"""Tests for CLI authentication commands."""

from unittest.mock import patch

from click.testing import CliRunner

from modelforge.cli import cli


class TestCLIAuthCommands:
    """Test cases for CLI authentication commands."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.runner = CliRunner()

    def test_auth_login_no_provider(self) -> None:
        """Test auth login without provider argument."""
        result = self.runner.invoke(cli, ["auth", "login"])
        assert result.exit_code != 0
        assert "--provider" in result.output

    def test_auth_login_nonexistent_provider(self) -> None:
        """Test auth login with non-existent provider."""
        result = self.runner.invoke(cli, ["auth", "login", "--provider", "nonexistent"])
        assert result.exit_code == 0
        assert "not found in configuration" in result.output

    def test_auth_logout_no_provider(self) -> None:
        """Test auth logout without provider argument."""
        result = self.runner.invoke(cli, ["auth", "logout"])
        assert result.exit_code != 0
        assert "--provider" in result.output

    def test_auth_logout_nonexistent_provider(self) -> None:
        """Test auth logout with non-existent provider."""
        result = self.runner.invoke(
            cli, ["auth", "logout", "--provider", "nonexistent"]
        )
        assert result.exit_code == 0
        assert "not found" in result.output

    def test_auth_status_no_providers(self) -> None:
        """Test auth status with no providers configured."""
        result = self.runner.invoke(cli, ["auth", "status"])
        assert result.exit_code == 0

    def test_auth_status_specific_provider(self) -> None:
        """Test auth status for specific provider."""
        result = self.runner.invoke(
            cli, ["auth", "status", "--provider", "nonexistent"]
        )
        assert result.exit_code == 0
        assert "not found in configuration" in result.output

    def test_auth_logout_all_providers(self) -> None:
        """Test auth logout with --all-providers flag."""
        result = self.runner.invoke(cli, ["auth", "logout", "--all-providers"])
        assert result.exit_code == 0


class TestCLIModelsCommands:
    """Test cases for CLI models commands."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.runner = CliRunner()

    def test_models_list_no_models(self) -> None:
        """Test models list with no models available."""
        with patch("modelforge.cli.ModelsDevClient") as mock_client:
            mock_client.return_value.get_models.return_value = []
            result = self.runner.invoke(cli, ["models", "list"])
            assert result.exit_code == 0
            assert "No models found" in result.output

    def test_models_search_no_results(self) -> None:
        """Test models search with no results."""
        with patch("modelforge.cli.ModelsDevClient") as mock_client:
            mock_client.return_value.search_models.return_value = []
            result = self.runner.invoke(cli, ["models", "search", "nonexistent"])
            assert result.exit_code == 0
            assert "No models found matching criteria" in result.output

    def test_models_info_missing_args(self) -> None:
        """Test models info without required arguments."""
        result = self.runner.invoke(cli, ["models", "info"])
        assert result.exit_code != 0
        assert "--provider" in result.output

    def test_models_list_json_format(self) -> None:
        """Test models list with JSON format."""
        mock_models = [{"name": "test-model", "provider": "test"}]

        with patch("modelforge.cli.ModelsDevClient") as mock_client:
            mock_client.return_value.get_models.return_value = mock_models
            result = self.runner.invoke(cli, ["models", "list", "--format", "json"])
            assert result.exit_code == 0
            assert "test-model" in result.output
            assert "test" in result.output

    def test_models_search_with_filters(self) -> None:
        """Test models search with various filters."""
        mock_results = [{"name": "test"}]

        with patch("modelforge.cli.ModelsDevClient") as mock_client:
            mock_client.return_value.search_models.return_value = mock_results

            # Test with provider filter
            result = self.runner.invoke(
                cli, ["models", "search", "test", "--provider", "openai"]
            )
            assert result.exit_code == 0

            # Test with capability filter
            result = self.runner.invoke(
                cli, ["models", "search", "test", "--capability", "chat"]
            )
            assert result.exit_code == 0

            # Test with price filter
            result = self.runner.invoke(
                cli, ["models", "search", "test", "--max-price", "0.1"]
            )
            assert result.exit_code == 0
