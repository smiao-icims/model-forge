# CLI Refactor - Design

## Architecture Overview

### Command Structure Redesign
```
src/modelforge/cli/
├── __init__.py
├── commands/              # Command implementations
│   ├── __init__.py
│   ├── config_commands.py
│   ├── auth_commands.py
│   ├── models_commands.py
│   └── test_commands.py
├── formatters/           # Output formatting
│   ├── __init__.py
│   ├── table_formatter.py
│   ├── json_formatter.py
│   └── text_formatter.py
├── validators/          # Input validation
│   ├── __init__.py
│   └── cli_validators.py
└── utils/              # CLI utilities
    ├── __init__.py
    ├── output_utils.py
    └── progress_utils.py
```

## Core Command Architecture

### Base Command Structure
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import click

class BaseCommand(ABC):
    """Base class for all CLI commands."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the command and return result data."""
        pass

    @abstractmethod
    def format_output(self, result: Dict[str, Any], format_type: str) -> str:
        """Format the output based on requested format."""
        pass

class CLICommandExecutor:
    """Execute CLI commands with proper error handling and formatting."""

    def __init__(self, command: BaseCommand):
        self.command = command

    def run(self, **kwargs) -> None:
        """Run command with error handling and output formatting."""
        try:
            result = self.command.execute(**kwargs)
            output = self.command.format_output(result, kwargs.get('format', 'text'))
            click.echo(output)
        except Exception as e:
            self._handle_error(e, kwargs.get('verbose', False))

    def _handle_error(self, error: Exception, verbose: bool) -> None:
        """Handle and display errors appropriately."""
        if verbose:
            click.echo(f"Error: {str(error)}", err=True)
            import traceback
            traceback.print_exc()
        else:
            click.echo(f"Error: {str(error)}", err=True)
```

## Command Implementations

### Config Commands (`commands/config_commands.py`)
```python
import click
from typing import Dict, Any, Optional
from modelforge import config

class ConfigShowCommand(BaseCommand):
    """Show current configuration."""

    def execute(self) -> Dict[str, Any]:
        """Get current configuration."""
        config_data, _ = config.get_config()
        current_model = config.get_current_model()

        return {
            "config": config_data,
            "current_model": current_model,
            "success": True
        }

    def format_output(self, result: Dict[str, Any], format_type: str) -> str:
        """Format configuration output."""
        if format_type == "json":
            import json
            return json.dumps(result, indent=2)

        # Text format
        output = []
        current = result["current_model"]

        if current:
            output.append(f"Current Model: {current['provider']}/{current['model']}")
        else:
            output.append("No model currently selected")

        if result["config"]["providers"]:
            output.append("")
            output.append("Available Providers:")
            for provider_name, provider_data in result["config"]["providers"].items():
                output.append(f"  {provider_name}:")
                for model_name in provider_data["models"].keys():
                    current_marker = " (current)" if current and current["provider"] == provider_name and current["model"] == model_name else ""
                    output.append(f"    - {model_name}{current_marker}")

        return "\n".join(output)

class ConfigAddCommand(BaseCommand):
    """Add model configuration."""

    def execute(self, provider: str, model: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Add model configuration."""
        from modelforge.registry import ModelForgeRegistry

        registry = ModelForgeRegistry()

        # Validate provider and model
        if not self._validate_provider_model(provider, model):
            raise click.BadParameter(f"Invalid provider or model: {provider}/{model}")

        # Add configuration
        config.add_model_config(provider, model, api_key=api_key)

        return {
            "provider": provider,
            "model": model,
            "action": "added",
            "success": True
        }

    def _validate_provider_model(self, provider: str, model: str) -> bool:
        """Validate provider and model combination."""
        # Implementation would check against models.dev or registry
        return True
```

### Auth Commands (`commands/auth_commands.py`)
```python
import click
from typing import Dict, Any
from modelforge import auth

class AuthLoginCommand(BaseCommand):
    """Handle authentication login."""

    def execute(self, provider: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Execute authentication login."""
        from modelforge.registry import ModelForgeRegistry

        strategy = auth.get_auth_strategy(provider)

        if not strategy:
            raise click.BadParameter(f"Unsupported provider: {provider}")

        try:
            if api_key:
                credentials = strategy.authenticate_with_api_key(api_key)
            else:
                credentials = strategy.authenticate()

            return {
                "provider": provider,
                "status": "authenticated",
                "method": "api_key" if api_key else "device_flow",
                "success": True
            }
        except Exception as e:
            return {
                "provider": provider,
                "status": "failed",
                "error": str(e),
                "success": False
            }

class AuthStatusCommand(BaseCommand):
    """Show authentication status."""

    def execute(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get authentication status."""
        from modelforge.registry import ModelForgeRegistry

        if provider:
            strategy = auth.get_auth_strategy(provider)
            status = strategy.get_status() if strategy else None
            return {
                "provider": provider,
                "status": status or "not_configured",
                "success": True
            }
        else:
            # Get all provider statuses
            all_statuses = {}
            for provider_name in ["openai", "google", "github_copilot"]:
                strategy = auth.get_auth_strategy(provider_name)
                if strategy:
                    all_statuses[provider_name] = strategy.get_status()

            return {
                "providers": all_statuses,
                "success": True
            }
```

## Output Formatting System

### Base Formatter (`formatters/base_formatter.py`)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseFormatter(ABC):
    """Base class for output formatters."""

    @abstractmethod
    def format(self, data: Dict[str, Any]) -> str:
        """Format the data into string output."""
        pass
```

### Table Formatter (`formatters/table_formatter.py`)
```python
import click
from typing import Dict, Any, List
from tabulate import tabulate

class TableFormatter(BaseFormatter):
    """Format data as tables."""

    def format(self, data: Dict[str, Any]) -> str:
        """Format data as a table."""
        if "models" in data:
            return self._format_models_table(data["models"])
        elif "providers" in data:
            return self._format_providers_table(data["providers"])
        else:
            return str(data)

    def _format_models_table(self, models: List[Dict[str, Any]]) -> str:
        """Format models as table."""
        headers = ["ID", "Provider", "Display Name", "Capabilities", "Context Length"]
        rows = []

        for model in models:
            rows.append([
                model.get("id", ""),
                model.get("provider", ""),
                model.get("display_name", ""),
                ", ".join(model.get("capabilities", [])),
                str(model.get("context_length", "N/A"))
            ])

        return tabulate(rows, headers=headers, tablefmt="grid")
```

### JSON Formatter (`formatters/json_formatter.py`)
```python
import json
from typing import Dict, Any

class JSONFormatter(BaseFormatter):
    """Format data as JSON."""

    def format(self, data: Dict[str, Any]) -> str:
        """Format data as pretty JSON."""
        return json.dumps(data, indent=2, sort_keys=True)
```

### Text Formatter (`formatters/text_formatter.py`)
```python
import click
from typing import Dict, Any

class TextFormatter(BaseFormatter):
    """Format data as human-readable text."""

    def format(self, data: Dict[str, Any]) -> str:
        """Format data as readable text."""
        lines = []

        if "success" in data and not data["success"]:
            lines.append(f"❌ Error: {data.get('error', 'Unknown error')}")
            return "\n".join(lines)

        if "provider" in data and "model" in data:
            lines.append(f"Provider: {data['provider']}")
            lines.append(f"Model: {data['model']}")

            if data.get("status") == "ready":
                lines.append("Status: ✅ Ready")
            elif data.get("status") == "authenticated":
                lines.append("Status: ✅ Authenticated")
            else:
                lines.append(f"Status: {data.get('status', 'Unknown')}")

        return "\n".join(lines)
```

## Progress Indicators

### Progress Utils (`utils/progress_utils.py`)
```python
import click
from typing import Iterator, Any
import time

class ProgressIndicator:
    """Display progress indicators for long operations."""

    @staticmethod
    def spinner(text: str, func, *args, **kwargs) -> Any:
        """Show spinner while executing function."""
        with click_spinner.spinner():
            return func(*args, **kwargs)

    @staticmethod
    def progress_bar(iterable, label: str = "Processing"):
        """Show progress bar for iterable operations."""
        return click.progressbar(iterable, label=label)

class StatusReporter:
    """Report status updates during operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def info(self, message: str) -> None:
        """Report informational message."""
        if self.verbose:
            click.echo(f"ℹ️  {message}")

    def success(self, message: str) -> None:
        """Report success message."""
        click.echo(f"✅ {message}")

    def warning(self, message: str) -> None:
        """Report warning message."""
        click.echo(f"⚠️  {message}")

    def error(self, message: str) -> None:
        """Report error message."""
        click.echo(f"❌ {message}", err=True)
```

## Input Validation

### CLI Validators (`validators/cli_validators.py`)
```python
import click
from typing import Optional

class CLIValidators:
    """Input validation for CLI commands."""

    @staticmethod
    def validate_provider(ctx, param, value: Optional[str]) -> str:
        """Validate provider name."""
        if not value:
            return value

        from modelforge.modelsdev import ModelsDevClient

        try:
            client = ModelsDevClient()
            providers = client.get_providers()
            valid_providers = [p["name"] for p in providers]

            if value not in valid_providers:
                raise click.BadParameter(
                    f"Invalid provider '{value}'. Valid providers: {', '.join(valid_providers)}"
                )
        except Exception:
            # Allow validation to pass if models.dev unavailable
            pass

        return value

    @staticmethod
    def validate_model(ctx, param, value: Optional[str]) -> str:
        """Validate model name for given provider."""
        if not value:
            return value

        provider = ctx.params.get('provider')
        if not provider:
            return value

        from modelforge.modelsdev import ModelsDevClient

        try:
            client = ModelsDevClient()
            models = client.get_models()
            valid_models = [m["id"] for m in models if m["provider"] == provider]

            if value not in valid_models:
                raise click.BadParameter(
                    f"Invalid model '{value}' for provider '{provider}'. "
                    f"Valid models: {', '.join(valid_models)}"
                )
        except Exception:
            # Allow validation to pass if models.dev unavailable
            pass

        return value
```

## Updated CLI Structure

### Main CLI (`cli.py`)
```python
import click
from typing import Optional
from .commands import (
    ConfigShowCommand, ConfigAddCommand, ConfigUseCommand,
    AuthLoginCommand, AuthStatusCommand, AuthLogoutCommand,
    ModelsListCommand, ModelsSearchCommand, ModelsInfoCommand,
    TestCommand
)
from .formatters import TextFormatter, JSONFormatter, TableFormatter

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'table']),
              default='text', help='Output format')
@click.pass_context
def cli(ctx, verbose, format):
    """ModelForge CLI - Manage LLM providers and models."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['format'] = format

@cli.group()
@click.pass_context
def config(ctx):
    """Manage configuration."""
    pass

@config.command('show')
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    command = ConfigShowCommand(verbose=ctx.obj['verbose'])
    executor = CLICommandExecutor(command)
    executor.run(format=ctx.obj['format'])

@config.command('add')
@click.option('--provider', required=True, help='Provider name')
@click.option('--model', required=True, help='Model name')
@click.option('--api-key', help='API key for authentication')
@click.pass_context
def config_add(ctx, provider, model, api_key):
    """Add model configuration."""
    command = ConfigAddCommand(verbose=ctx.obj['verbose'])
    executor = CLICommandExecutor(command)
    executor.run(provider=provider, model=model, api_key=api_key, format=ctx.obj['format'])

@cli.group()
@click.pass_context
def auth(ctx):
    """Manage authentication."""
    pass

@auth.command('login')
@click.option('--provider', required=True,
              callback=CLIValidators.validate_provider,
              help='Provider name')
@click.option('--api-key', help='API key (optional for device flow)')
@click.pass_context
def auth_login(ctx, provider, api_key):
    """Authenticate with a provider."""
    command = AuthLoginCommand(verbose=ctx.obj['verbose'])
    executor = CLICommandExecutor(command)
    executor.run(provider=provider, api_key=api_key, format=ctx.obj['format'])

@cli.command('test')
@click.option('--prompt', default='Hello, world!', help='Test prompt')
@click.option('--provider', help='Specific provider to test')
@click.option('--model', help='Specific model to test')
@click.pass_context
def test_model(ctx, prompt, provider, model):
    """Test current model or specified model."""
    command = TestCommand(verbose=ctx.obj['verbose'])
    executor = CLICommandExecutor(command)
    executor.run(prompt=prompt, provider=provider, model=model, format=ctx.obj['format'])
```

## Error Handling System

### Error Categories
```python
from typing import Dict, Any

class CLIError:
    """Structured CLI error information."""

    def __init__(self, code: str, message: str, suggestion: str = None, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.details = details or {}

class ErrorHandler:
    """Centralized CLI error handling."""

    ERROR_MESSAGES = {
        "INVALID_PROVIDER": CLIError(
            code="INVALID_PROVIDER",
            message="Invalid provider '{provider}'",
            suggestion="Run 'modelforge models list' to see available providers"
        ),
        "INVALID_MODEL": CLIError(
            code="INVALID_MODEL",
            message="Invalid model '{model}' for provider '{provider}'",
            suggestion="Run 'modelforge models list --provider {provider}' to see available models"
        ),
        "AUTH_FAILED": CLIError(
            code="AUTH_FAILED",
            message="Authentication failed for {provider}",
            suggestion="Check your API key or run 'modelforge auth login --provider {provider}'"
        )
    }

    @classmethod
    def handle(cls, error_code: str, **kwargs) -> None:
        """Handle and display error with suggestion."""
        error = cls.ERROR_MESSAGES.get(error_code)
        if error:
            message = error.message.format(**kwargs)
            click.echo(f"❌ Error: {message}", err=True)
            if error.suggestion:
                suggestion = error.suggestion.format(**kwargs)
                click.echo(f"💡 Suggestion: {suggestion}", err=True)
```

## Migration Strategy

### Phase 1: Command Extraction (Week 1)
1. Extract business logic from CLI commands
2. Create command classes for each operation
3. Implement formatters for output
4. Add basic error handling

### Phase 2: Validation & UX (Week 2)
1. Add comprehensive input validation
2. Implement progress indicators
3. Add helpful error messages
4. Improve output formatting

### Phase 3: Testing & Polish (Week 3)
1. Add comprehensive CLI tests
2. Add tab completion support
3. Add interactive help
4. Final polish and documentation

### Phase 4: Release (Week 4)
1. Update documentation
2. Add migration guide
3. Final testing
4. Release preparation
