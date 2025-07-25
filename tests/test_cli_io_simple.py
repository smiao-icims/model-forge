"""Simple tests for CLI I/O enhancements - focused on the key functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from modelforge import cli
from modelforge.exceptions import ConfigurationError


class TestCLIIOEnhancements:
    """Test the CLI I/O enhancements."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    def test_test_command_error_both_prompt_and_file(self, runner: CliRunner) -> None:
        """Test that --prompt and --input-file cannot be used together."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("File content")
            temp_file = f.name

        try:
            result = runner.invoke(
                cli.test_model, ["--prompt", "Prompt", "--input-file", temp_file]
            )

            assert result.exit_code != 0
            assert "Cannot specify both --prompt and --input-file" in result.output
        finally:
            Path(temp_file).unlink()

    @patch("modelforge.cli.config.get_current_model")
    def test_test_command_no_model_selected(
        self, mock_get_current_model: MagicMock, runner: CliRunner
    ) -> None:
        """Test error when no model is selected."""
        mock_get_current_model.return_value = None

        # Let Click handle the exception normally
        result = runner.invoke(cli.test_model, ["--prompt", "Test"])

        # Check error output
        assert result.exit_code != 0
        # Exception details might be in stderr or just show the exception type
        assert result.exception is not None
        assert isinstance(result.exception, ConfigurationError)

    def test_test_command_empty_input_file(self, runner: CliRunner) -> None:
        """Test error with empty input file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")  # Empty file
            temp_file = f.name

        try:
            result = runner.invoke(cli.test_model, ["--input-file", temp_file])

            assert result.exit_code != 0
            assert "is empty" in result.output
        finally:
            Path(temp_file).unlink()

    @patch("modelforge.cli.config.get_current_model")
    @patch("modelforge.cli.ModelForgeRegistry")
    @patch("modelforge.cli.ChatPromptTemplate")
    @patch("modelforge.cli.StrOutputParser")
    @patch("modelforge.cli.config.get_settings")
    def test_input_output_file_functionality(
        self,
        mock_get_settings: MagicMock,
        mock_parser: MagicMock,
        mock_prompt_template: MagicMock,
        mock_registry_class: MagicMock,
        mock_get_current_model: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test basic file I/O functionality."""
        # Setup mocks
        mock_get_current_model.return_value = {
            "provider": "test",
            "model": "test-model",
        }
        mock_get_settings.return_value = {"show_telemetry": False}

        # Mock the chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "File response content"

        mock_prompt = MagicMock()
        mock_prompt.__or__.return_value.__or__.return_value = mock_chain
        mock_prompt_template.from_messages.return_value = mock_prompt

        # Mock registry
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = MagicMock()
        mock_registry_class.return_value = mock_registry

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create input file
            input_file = Path(tmpdir) / "input.txt"
            input_file.write_text("Input from file")

            # Define output file
            output_file = Path(tmpdir) / "output.txt"

            result = runner.invoke(
                cli.test_model,
                ["--input-file", str(input_file), "--output-file", str(output_file)],
            )

            assert result.exit_code == 0
            assert f"Response written to {output_file}" in result.output

            # Check output file was created
            assert output_file.exists()
            assert output_file.read_text() == "File response content"

    @patch("modelforge.cli.config.get_current_model")
    @patch("modelforge.cli.ModelForgeRegistry")
    @patch("modelforge.cli.ChatPromptTemplate")
    @patch("modelforge.cli.StrOutputParser")
    @patch("modelforge.cli.config.get_settings")
    def test_prompt_truncation(
        self,
        mock_get_settings: MagicMock,
        mock_parser: MagicMock,
        mock_prompt_template: MagicMock,
        mock_registry_class: MagicMock,
        mock_get_current_model: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test that long prompts are truncated in display."""
        # Setup mocks
        mock_get_current_model.return_value = {
            "provider": "test",
            "model": "test-model",
        }
        mock_get_settings.return_value = {"show_telemetry": False}

        # Mock the chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Response to long prompt"

        mock_prompt = MagicMock()
        mock_prompt.__or__.return_value.__or__.return_value = mock_chain
        mock_prompt_template.from_messages.return_value = mock_prompt

        # Mock registry
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = MagicMock()
        mock_registry_class.return_value = mock_registry

        # Test with a very long prompt
        long_prompt = "x" * 100  # 100 characters
        result = runner.invoke(cli.test_model, ["--prompt", long_prompt])

        assert result.exit_code == 0
        # Check that the prompt was truncated to 80 chars with ellipsis
        assert "Q: " + "x" * 77 + "..." in result.output
        assert "A: Response to long prompt" in result.output

    @patch("modelforge.cli.config.get_current_model")
    @patch("modelforge.cli.ModelForgeRegistry")
    @patch("modelforge.cli.ChatPromptTemplate")
    @patch("modelforge.cli.StrOutputParser")
    @patch("modelforge.cli.config.get_settings")
    def test_no_telemetry_flag(
        self,
        mock_get_settings: MagicMock,
        mock_parser: MagicMock,
        mock_prompt_template: MagicMock,
        mock_registry_class: MagicMock,
        mock_get_current_model: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test --no-telemetry flag suppresses telemetry output."""
        # Setup mocks
        mock_get_current_model.return_value = {
            "provider": "test",
            "model": "test-model",
        }
        mock_get_settings.return_value = {
            "show_telemetry": True
        }  # Telemetry enabled by default

        # Mock the chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Test response"

        mock_prompt = MagicMock()
        mock_prompt.__or__.return_value.__or__.return_value = mock_chain
        mock_prompt_template.from_messages.return_value = mock_prompt

        # Mock registry with telemetry callback
        mock_registry = MagicMock()
        mock_llm = MagicMock()

        # Setup telemetry callback to have metrics
        def get_llm_side_effect(callbacks=None):
            if callbacks and len(callbacks) > 0:
                # Set some token usage on the callback
                callbacks[0].metrics.token_usage.total_tokens = 100
            return mock_llm

        mock_registry.get_llm.side_effect = get_llm_side_effect
        mock_registry_class.return_value = mock_registry

        result = runner.invoke(cli.test_model, ["--prompt", "Test", "--no-telemetry"])

        assert result.exit_code == 0
        assert "Q: Test" in result.output
        assert "A: Test response" in result.output
        # Telemetry should not be shown
        assert "Telemetry Information" not in result.output

    @patch("modelforge.cli.config.get_current_model")
    @patch("modelforge.cli.ModelForgeRegistry")
    @patch("modelforge.cli.ChatPromptTemplate")
    @patch("modelforge.cli.StrOutputParser")
    @patch("modelforge.cli.config.get_settings")
    def test_stdin_input(
        self,
        mock_get_settings: MagicMock,
        mock_parser: MagicMock,
        mock_prompt_template: MagicMock,
        mock_registry_class: MagicMock,
        mock_get_current_model: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test reading prompt from stdin."""
        # Setup mocks
        mock_get_current_model.return_value = {
            "provider": "test",
            "model": "test-model",
        }
        mock_get_settings.return_value = {"show_telemetry": False}

        # Mock the chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Response from stdin"

        mock_prompt = MagicMock()
        mock_prompt.__or__.return_value.__or__.return_value = mock_chain
        mock_prompt_template.from_messages.return_value = mock_prompt

        # Mock registry
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = MagicMock()
        mock_registry_class.return_value = mock_registry

        # Provide input via stdin
        result = runner.invoke(cli.test_model, input="Hello from stdin\n")

        assert result.exit_code == 0
        assert "Q: Hello from stdin" in result.output
        assert "A: Response from stdin" in result.output
