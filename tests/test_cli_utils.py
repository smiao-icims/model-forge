"""Tests for CLI utilities."""

from unittest.mock import patch

import click

from modelforge.cli_utils import (
    ErrorFormatter,
    confirm_action,
    format_table,
    handle_cli_errors,
    print_info,
    print_success,
    print_warning,
)
from modelforge.exceptions import (
    ConfigurationNotFoundError,
    InvalidInputError,
    ModelForgeError,
    NetworkTimeoutError,
)


class TestErrorFormatter:
    """Test ErrorFormatter class."""

    def test_format_modelforge_error_basic(self):
        """Test formatting basic ModelForgeError."""
        formatter = ErrorFormatter()
        error = ModelForgeError("Something went wrong")
        result = formatter.format_error(error)

        assert "❌ Error: Something went wrong" in result
        assert "Context:" not in result
        assert "Suggestion:" not in result

    def test_format_modelforge_error_with_context(self):
        """Test formatting error with context."""
        formatter = ErrorFormatter()
        error = ModelForgeError(
            "Operation failed",
            context="File not found",
            suggestion="Check the file path",
        )
        result = formatter.format_error(error)

        assert "❌ Error: Operation failed" in result
        assert "Context: File not found" in result
        assert "💡 Suggestion: Check the file path" in result

    def test_format_modelforge_error_verbose(self):
        """Test verbose formatting with error code."""
        formatter = ErrorFormatter(verbose=True)
        error = ModelForgeError(
            "Test error",
            error_code="TEST_ERROR",
        )
        result = formatter.format_error(error)

        assert "Code: TEST_ERROR" in result

    def test_format_modelforge_error_debug(self):
        """Test debug formatting with details."""
        formatter = ErrorFormatter(debug=True)
        error = ModelForgeError(
            "Test error",
            details={"key": "value"},
        )
        result = formatter.format_error(error)

        assert "Details: {'key': 'value'}" in result
        assert "Traceback:" in result

    def test_format_specific_errors(self):
        """Test formatting specific error types."""
        formatter = ErrorFormatter()

        # ConfigurationNotFoundError
        error = ConfigurationNotFoundError("openai", "gpt-4")
        result = formatter.format_error(error)
        assert "No configuration found for provider 'openai'" in result
        assert "Attempting to use model 'gpt-4'" in result
        assert "modelforge config add --provider openai" in result

        # NetworkTimeoutError
        error = NetworkTimeoutError("API call", timeout=30)
        result = formatter.format_error(error)
        assert "Network timeout during API call" in result
        assert "Request timed out after 30 seconds" in result

    def test_format_generic_error(self):
        """Test formatting generic Python exceptions."""
        formatter = ErrorFormatter()
        error = ValueError("Invalid value")
        result = formatter.format_error(error)

        assert "❌ Error (ValueError): Invalid value" in result
        assert "Suggestion:" not in result  # No suggestion in non-verbose mode

    def test_format_generic_error_verbose(self):
        """Test verbose formatting of generic errors."""
        formatter = ErrorFormatter(verbose=True)
        error = KeyError("missing_key")
        result = formatter.format_error(error)

        assert "❌ Error (KeyError):" in result
        assert "This might be a bug" in result

    def test_format_generic_error_debug(self):
        """Test debug formatting with full traceback."""
        formatter = ErrorFormatter(debug=True)

        try:
            raise RuntimeError("Test error")
        except RuntimeError as e:
            result = formatter.format_error(e)

        assert "Full Traceback:" in result
        assert "RuntimeError: Test error" in result
        assert "test_format_generic_error_debug" in result  # Function name in traceback


class TestHandleCliErrors:
    """Test handle_cli_errors decorator."""

    def test_handle_cli_errors_integration(self):
        """Test handle_cli_errors with a real Click command."""
        from click.testing import CliRunner

        @click.command()
        @handle_cli_errors
        def test_command(ctx):
            if ctx.obj.get("raise_error"):
                raise InvalidInputError("Test error", suggestion="Fix it")
            return ctx.obj.get("value", "success")

        runner = CliRunner()

        # Test successful execution
        result = runner.invoke(test_command, obj={"value": "test"})
        assert result.exit_code == 0

        # Test error handling
        result = runner.invoke(test_command, obj={"raise_error": True})
        assert result.exit_code == 1
        assert "❌ Error: Test error" in result.output
        assert "💡 Suggestion: Fix it" in result.output

    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt."""
        from click.testing import CliRunner

        @click.command()
        @handle_cli_errors
        def test_command(ctx):
            raise KeyboardInterrupt

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        assert result.exit_code == 130
        assert "⚠️  Operation cancelled by user" in result.output

    def test_click_exception_passthrough(self):
        """Test that Click exceptions pass through properly."""
        from click.testing import CliRunner

        @click.command()
        @handle_cli_errors
        def test_command(ctx):
            raise click.ClickException("Click error")

        runner = CliRunner()
        result = runner.invoke(test_command, obj={})

        # Click exceptions should be handled by Click itself
        assert result.exit_code != 0
        assert "Click error" in result.output

    def test_verbose_and_debug_modes(self):
        """Test verbose and debug mode error formatting."""
        from click.testing import CliRunner

        @click.command()
        @handle_cli_errors
        def test_command(ctx):
            raise NetworkTimeoutError("API call", timeout=30)

        runner = CliRunner()

        # Test verbose mode
        result = runner.invoke(test_command, obj={"verbose": True})
        assert "Code: NETWORK_TIMEOUT" in result.output

        # Test debug mode
        result = runner.invoke(test_command, obj={"debug": True})
        assert "Traceback:" in result.output
        assert "Details:" in result.output


class TestPrintFunctions:
    """Test print utility functions."""

    @patch("click.echo")
    def test_print_success(self, mock_echo):
        """Test print_success."""
        print_success("Operation completed")
        mock_echo.assert_called_once()
        call_args = mock_echo.call_args[0][0]
        assert "✅ Operation completed" in call_args

    @patch("click.echo")
    def test_print_warning(self, mock_echo):
        """Test print_warning."""
        print_warning("Something might be wrong")
        mock_echo.assert_called_once_with(
            click.style("⚠️  Something might be wrong", fg="yellow"),
            err=True,
        )

    @patch("click.echo")
    def test_print_info(self, mock_echo):
        """Test print_info."""
        print_info("Here's some information")
        mock_echo.assert_called_once()
        call_args = mock_echo.call_args[0][0]
        assert "ℹ️  Here's some information" in call_args

    @patch("click.confirm")
    def test_confirm_action(self, mock_confirm):
        """Test confirm_action."""
        mock_confirm.return_value = True
        result = confirm_action("Continue?", default=False)

        assert result is True
        mock_confirm.assert_called_once()
        call_args = mock_confirm.call_args[0][0]
        assert "❓ Continue?" in call_args


class TestFormatTable:
    """Test format_table function."""

    def test_basic_table(self):
        """Test basic table formatting."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["Alice", "25", "New York"],
            ["Bob", "30", "San Francisco"],
        ]

        result = format_table(headers, rows)

        assert "Name  | Age | City" in result
        assert "------+-----+-------------" in result
        assert "Alice | 25  | New York" in result
        assert "Bob   | 30  | San Francisco" in result

    def test_empty_table(self):
        """Test empty table."""
        result = format_table(["Col1", "Col2"], [])
        assert result == "No data to display"

    def test_table_with_max_width(self):
        """Test table with maximum column width."""
        headers = ["Short", "Very Long Header"]
        rows = [["OK", "This is a very long cell content that should be truncated"]]

        result = format_table(headers, rows, max_width=10)

        assert "Very Lo..." in result  # Header truncated
        assert "This is..." in result  # Cell truncated

    def test_table_with_varying_widths(self):
        """Test table with varying column widths."""
        headers = ["ID", "Description"]
        rows = [
            ["1", "Short"],
            ["123", "A longer description here"],
            ["45", "Medium length"],
        ]

        result = format_table(headers, rows)

        # Check alignment
        lines = result.split("\n")
        assert all(
            len(line) == len(lines[0]) for line in lines[1:]
        )  # All lines same width
