"""CLI utilities for ModelForge."""

from __future__ import annotations

import functools
import inspect
import sys
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

import click

from modelforge.exceptions import ModelForgeError
from modelforge.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ErrorFormatter:
    """Formats errors for CLI display."""

    def __init__(self, verbose: bool = False, debug: bool = False) -> None:
        """Initialize error formatter.

        Args:
            verbose: Show additional context like error codes
            debug: Show full stack traces
        """
        self.verbose = verbose
        self.debug = debug

    def format_error(self, error: Exception) -> str:
        """Format an exception for CLI display.

        Args:
            error: Exception to format

        Returns:
            Formatted error message with colors and styling
        """
        if isinstance(error, ModelForgeError):
            return self._format_modelforge_error(error)
        return self._format_generic_error(error)

    def _format_modelforge_error(self, error: ModelForgeError) -> str:
        """Format ModelForgeError with context and suggestions."""
        parts = []

        # Main error message
        parts.append(click.style(f"❌ Error: {error.message}", fg="red", bold=True))

        # Context information
        if error.context:
            parts.append(click.style(f"   Context: {error.context}", fg="yellow"))

        # Suggestion for resolution
        if error.suggestion:
            parts.append(
                click.style(f"   💡 Suggestion: {error.suggestion}", fg="green")
            )

        # Error code (verbose mode)
        if self.verbose and error.error_code:
            parts.append(click.style(f"   Code: {error.error_code}", fg="bright_black"))

        # Additional details (debug mode)
        if self.debug and error.details:
            parts.append(click.style(f"   Details: {error.details}", fg="bright_black"))

        # Stack trace (debug mode)
        if self.debug:
            parts.append("")  # Empty line before traceback
            parts.append(click.style("Traceback:", fg="bright_black"))
            tb_lines = traceback.format_tb(sys.exc_info()[2])
            for line in tb_lines:
                parts.append(click.style(line.rstrip(), fg="bright_black"))

        return "\n".join(parts)

    def _format_generic_error(self, error: Exception) -> str:
        """Format generic exceptions."""
        # Basic error message
        error_type = type(error).__name__
        message = str(error) or "An unexpected error occurred"

        parts = [
            click.style(f"❌ Error ({error_type}): {message}", fg="red", bold=True)
        ]

        # In verbose mode, suggest reporting the error
        if self.verbose:
            parts.append(
                click.style(
                    "   💡 Suggestion: This might be a bug. "
                    "Please report it with the error details",
                    fg="green",
                )
            )

        # Full traceback in debug mode
        if self.debug:
            parts.append("")  # Empty line
            parts.append(click.style("Full Traceback:", fg="bright_black"))
            parts.append(click.style(traceback.format_exc(), fg="bright_black"))

        return "\n".join(parts)


def handle_cli_errors(func: F) -> F:
    """Decorator for consistent CLI error handling.

    This decorator should be applied to Click command functions to provide
    consistent error formatting and exit codes.

    Args:
        func: Click command function to decorate

    Returns:
        Decorated function with error handling
    """
    # Check if the original function expects a context parameter
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    expects_context = len(params) > 0 and (params[0] in {"ctx", "_ctx", "context"})

    @functools.wraps(func)
    @click.pass_context
    def wrapper(ctx: click.Context, *args: object, **kwargs: object) -> object:
        # Get formatter options from context
        verbose = ctx.obj.get("verbose", False) if ctx.obj else False
        debug = ctx.obj.get("debug", False) if ctx.obj else False
        formatter = ErrorFormatter(verbose=verbose, debug=debug)

        try:
            # Call the function with or without context based on its signature
            if expects_context:
                return func(ctx, *args, **kwargs)
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            click.echo("\n⚠️  Operation cancelled by user", err=True)
            ctx.exit(130)  # Standard exit code for SIGINT
        except click.ClickException:
            # Let Click handle its own exceptions (like --help)
            raise
        except Exception as e:
            # Format and display the error
            error_message = formatter.format_error(e)
            click.echo(error_message, err=True)

            # Log structured error for debugging
            if isinstance(e, ModelForgeError):
                logger.exception("CLI error", extra=e.to_dict())
            else:
                logger.exception("Unexpected CLI error")

            # Exit with error code
            ctx.exit(1)

    return wrapper  # type: ignore


def print_success(message: str) -> None:
    """Print a success message with formatting.

    Args:
        message: Success message to display
    """
    click.echo(click.style(f"✅ {message}", fg="green"))


def print_warning(message: str) -> None:
    """Print a warning message with formatting.

    Args:
        message: Warning message to display
    """
    click.echo(click.style(f"⚠️  {message}", fg="yellow"), err=True)


def print_info(message: str) -> None:
    """Print an info message with formatting.

    Args:
        message: Info message to display
    """
    click.echo(click.style(f"ℹ️  {message}", fg="blue"))


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation with formatting.

    Args:
        message: Confirmation message
        default: Default answer if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    return bool(click.confirm(click.style(f"❓ {message}", fg="cyan"), default=default))


def format_table(
    headers: list[str], rows: list[list[str]], max_width: int | None = None
) -> str:
    """Format data as a simple ASCII table.

    Args:
        headers: Column headers
        rows: Data rows
        max_width: Maximum width for each column (optional)

    Returns:
        Formatted table as string
    """
    if not rows:
        return "No data to display"

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # Apply max width if specified
    if max_width:
        widths = [min(w, max_width) for w in widths]

    # Format header with truncation
    header_cells = []
    for header, width in zip(headers, widths, strict=False):
        truncated_header = header
        if len(header) > width:
            truncated_header = header[: width - 3] + "..."
        header_cells.append(truncated_header.ljust(width))
    header_line = " | ".join(header_cells)
    separator = "-+-".join("-" * w for w in widths)

    # Format rows
    formatted_rows = []
    for row in rows:
        cells = []
        for cell, width in zip(row, widths, strict=False):
            cell_str = str(cell)
            if len(cell_str) > width:
                cell_str = cell_str[: width - 3] + "..."
            cells.append(cell_str.ljust(width))
        formatted_rows.append(" | ".join(cells))

    # Combine all parts
    return "\n".join([header_line, separator] + formatted_rows)
