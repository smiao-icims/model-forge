# Standard library imports
import json
import random
import time
from pathlib import Path
from typing import Any

# Third-party imports
import click
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Local imports
from . import auth, config
from .enhanced_llm import EnhancedLLM
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    InvalidInputError,
    ModelNotFoundError,
    ProviderError,
    RateLimitError,
)
from .logging_config import get_logger
from .modelsdev import ModelsDevClient
from .registry import ModelForgeRegistry
from .telemetry import TelemetryCallback, format_metrics
from .validation import InputValidator

logger = get_logger(__name__)


# CLI Utility Functions (merged from cli_utils.py)
def print_success(message: str) -> None:
    """Print a success message with formatting."""
    click.echo(click.style(f"✅ {message}", fg="green"))


def print_warning(message: str) -> None:
    """Print a warning message with formatting."""
    click.echo(click.style(f"⚠️  {message}", fg="yellow"), err=True)


def print_info(message: str) -> None:
    """Print an info message with formatting."""
    click.echo(click.style(f"ℹ️  {message}", fg="blue"))


def _handle_authentication(
    provider: str, provider_data: dict[str, Any], api_key: str | None, dev_auth: bool
) -> None:
    """Handle authentication for provider configuration."""
    if api_key:
        # Validate API key
        validated_key = InputValidator.validate_api_key(api_key, provider)
        auth_strategy = auth.ApiKeyAuth(provider)
        # Store the provided API key using the new config-based approach
        auth_strategy._save_auth_data({"api_key": validated_key})
        print_success(f"API key stored for provider '{provider}'.")
    elif dev_auth:
        print_info("Starting device authentication flow...")
        try:
            strategy = auth.get_auth_strategy(provider, provider_data)
            credentials = strategy.authenticate()
            if credentials:
                print_success(f"Authentication successful for provider '{provider}'.")
            else:
                raise AuthenticationError(
                    f"Authentication failed for provider '{provider}'",
                    suggestion="Check your credentials and try again",
                )
        except AuthenticationError:
            raise
        except Exception as e:
            logger.exception("Device authentication failed")
            raise AuthenticationError(
                f"Device authentication failed for provider '{provider}'",
                context=str(e),
                suggestion="Check your internet connection and try again",
            ) from e


@click.group()
def cli() -> None:
    """ModelForge CLI for managing LLM configurations."""


@cli.group()
def config_group() -> None:
    """Configuration management commands."""


@config_group.command(name="show")
def show_config() -> None:
    """Shows the current configuration."""
    current_config, config_path = config.get_config()
    scope = "local" if config_path == config.LOCAL_CONFIG_FILE else "global"
    print_info(f"Active ModelForge Config ({scope}): {config_path}")

    if not current_config or not current_config.get("providers"):
        print_warning(
            "Configuration is empty. Add models using 'modelforge config add'."
        )
        return

    click.echo(json.dumps(current_config, indent=4))


@config_group.command(name="migrate")
def migrate_config() -> None:
    """Migrates configuration from old location to new global location."""
    config.migrate_old_config()


@config_group.command(name="add")
@click.option(
    "--provider",
    required=True,
    help=(
        "The name of the provider (e.g., 'openai', 'ollama', "
        "'github_copilot', 'google')."
    ),
)
@click.option(
    "--model",
    required=True,
    help="A local, memorable name for the model (e.g., 'copilot-chat').",
)
@click.option(
    "--api-model-name",
    help="The actual model name the API expects (e.g., 'claude-3.7-sonnet-thought').",
)
@click.option("--api-key", help="The API key for the provider, if applicable.")
@click.option(
    "--dev-auth", is_flag=True, help="Use device authentication flow, if applicable."
)
@click.option(
    "--local",
    is_flag=True,
    help="Save to local project config (./.model-forge/config.json).",
)
def add_model(
    provider: str,
    model: str,
    api_model_name: str | None = None,
    api_key: str | None = None,
    dev_auth: bool = False,
    local: bool = False,
) -> None:
    """Add a new model configuration."""
    # Validate inputs
    provider = InputValidator.validate_provider_name(provider)
    model = InputValidator.validate_model_name(model)
    if api_model_name:
        api_model_name = InputValidator.validate_model_name(api_model_name)

    # Load existing configuration
    target_config_path = config.get_config_path(local=local)
    current_config, _ = config.get_config_from_path(target_config_path)

    # Ensure providers section exists
    if "providers" not in current_config:
        current_config["providers"] = {}

    # Initialize provider if it doesn't exist
    if provider not in current_config["providers"]:
        # Provider configuration defaults
        provider_defaults = {
            "openai": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "auth_strategy": "api_key",
            },
            "openrouter": {
                "llm_type": "openai-compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "auth_strategy": "api_key",
            },
            "google": {
                "llm_type": "google_genai",
                "auth_strategy": "api_key",
            },
            "github_copilot": {
                "llm_type": "github_copilot",
                "base_url": "https://api.githubcopilot.com",
                "auth_strategy": "device_flow",
                "auth_details": {
                    "client_id": "01ab8ac9400c4e429b23",
                    "device_code_url": "https://github.com/login/device/code",
                    "token_url": "https://github.com/login/oauth/access_token",
                    "scope": "read:user",
                },
            },
            "ollama": {"llm_type": "ollama", "base_url": "http://localhost:11434"},
        }

        current_config["providers"][provider] = provider_defaults.get(provider, {})
        current_config["providers"][provider]["models"] = {}

    # Add the model
    if "models" not in current_config["providers"][provider]:
        current_config["providers"][provider]["models"] = {}

    model_config = {}
    if api_model_name:
        model_config["api_model_name"] = api_model_name

    current_config["providers"][provider]["models"][model] = model_config

    # Save the configuration
    config.save_config(current_config, local=local)

    # Handle authentication
    _handle_authentication(
        provider, current_config["providers"][provider], api_key, dev_auth
    )

    # Success message
    scope_msg = "local" if local else "global"
    print_success(
        f"Successfully configured model '{model}' for provider '{provider}' "
        f"in the {scope_msg} config."
    )
    print_info("Run 'modelforge config show' to see the updated configuration.")


@config_group.command(name="use")
@click.option(
    "--provider", "provider_name", required=True, help="The name of the provider."
)
@click.option(
    "--model", "model_alias", required=True, help="The alias of the model to use."
)
@click.option(
    "--local", is_flag=True, help="Set the current model in the local project config."
)
def use_model(provider_name: str, model_alias: str, local: bool) -> None:
    """Set the current model to use."""
    # Validate inputs
    provider_name = InputValidator.validate_provider_name(provider_name)
    model_alias = InputValidator.validate_model_name(model_alias)

    success = config.set_current_model(provider_name, model_alias, local=local)
    if not success:
        raise ModelNotFoundError(provider_name, model_alias)


@config_group.command(name="remove")
@click.option("--provider", required=True, help="The name of the provider.")
@click.option("--model", required=True, help="The alias of the model to remove.")
@click.option(
    "--keep-credentials",
    is_flag=True,
    help="Keep stored credentials (don't remove from config).",
)
@click.option("--local", is_flag=True, help="Remove from the local project config.")
def remove_model(
    provider: str, model: str | None, keep_credentials: bool, local: bool
) -> None:
    """Removes a model configuration and optionally its stored credentials."""
    # Validate inputs
    provider = InputValidator.validate_provider_name(provider)
    model = InputValidator.validate_model_name(model)

    target_config_path = config.get_config_path(local=local)
    current_config, _ = config.get_config_from_path(target_config_path)

    providers = current_config.get("providers", {})

    if provider not in providers:
        raise ConfigurationError(
            f"Provider '{provider}' not found",
            suggestion="Use 'modelforge config show' to see available providers",
        )

    provider_data = providers[provider]
    models = provider_data.get("models", {})

    if model not in models:
        raise ModelNotFoundError(
            provider, model, available_models=list(models.keys()) if models else None
        )

    # Remove the model from configuration
    del models[model]

    # If no models left for this provider, remove the entire provider
    if not models:
        del providers[provider]
        print_info(f"Removed provider '{provider}' (no models remaining).")
    else:
        print_success(f"Removed model '{model}' from provider '{provider}'.")

    # Check if this was the currently selected model
    current_model = current_config.get("current_model", {})
    if (
        current_model.get("provider") == provider
        and current_model.get("model") == model
    ):
        current_config["current_model"] = {}
        print_warning("Cleared current model selection (removed model was selected).")

    # Save the updated configuration
    config.save_config(current_config, local=local)

    # Remove stored credentials unless explicitly kept
    if not keep_credentials:
        try:
            # Clear auth data from config file
            auth_strategy = auth.get_auth_strategy(
                provider, current_config["providers"][provider]
            )
            auth_strategy.clear_credentials()
            print_success(f"Removed stored credentials for {provider}")
        except Exception as e:
            print_warning(f"Could not remove credentials from config: {e}")
    else:
        print_info("Kept stored credentials (--keep-credentials flag used).")


@cli.command(name="test")
@click.option("--prompt", "-p", help="The prompt to send to the model.")
@click.option(
    "--input-file", "-i", type=click.Path(exists=True), help="Read prompt from file."
)
@click.option("--output-file", "-o", type=click.Path(), help="Write response to file.")
@click.option("--verbose", is_flag=True, help="Enable verbose debug output.")
@click.option("--no-telemetry", is_flag=True, help="Disable telemetry output.")
@click.option("--stream", is_flag=True, help="Stream the response in real-time.")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output (response only).")
def test_model(
    prompt: str | None,
    input_file: str | None,
    output_file: str | None,
    verbose: bool,
    no_telemetry: bool,
    stream: bool,
    quiet: bool,
) -> None:
    """Tests the currently selected model with a prompt.

    Prompt can be provided via:
    - --prompt flag
    - --input-file flag
    - stdin (if neither flag is provided)

    Output goes to stdout by default, or to file with --output-file.

    Use --quiet for minimal output suitable for piping (response only).
    """
    import sys

    # Handle conflicting flags
    if quiet and verbose:
        raise click.BadParameter("Cannot use --quiet and --verbose together")

    # Set logging level based on flags
    import logging

    if quiet:
        # Suppress all logs in quiet mode
        logging.getLogger("modelforge").setLevel(logging.CRITICAL)
        # Also disable telemetry in quiet mode
        no_telemetry = True
    elif not verbose:
        # Suppress INFO and below logs when not in verbose mode
        logging.getLogger("modelforge").setLevel(logging.WARNING)

    # Determine input source
    if prompt and input_file:
        raise click.BadParameter("Cannot specify both --prompt and --input-file")

    if input_file:
        # Read from file
        input_path = Path(input_file)
        prompt = input_path.read_text(encoding="utf-8").strip()
        if not prompt:
            raise click.BadParameter(f"Input file '{input_file}' is empty")
    elif not prompt:
        # Read from stdin if no prompt provided
        if sys.stdin.isatty():
            # Interactive terminal - require --prompt
            raise click.BadParameter(
                "No prompt provided. Use --prompt, --input-file, or pipe via stdin"
            )
        # Non-interactive - read from stdin
        prompt = sys.stdin.read().strip()
        if not prompt:
            raise click.BadParameter("No input received from stdin")

    current_model = config.get_current_model()
    if not current_model:
        raise ConfigurationError(
            "No model selected for testing",
            suggestion=(
                "Use 'modelforge config use --provider PROVIDER "
                "--model MODEL' to select a model"
            ),
        )

    provider_name = current_model.get("provider")
    model_alias = current_model.get("model")

    if not provider_name or not model_alias:
        raise ConfigurationError(
            "Invalid model configuration - missing provider or model",
            context=f"Current model config: {current_model}",
            suggestion="Re-select a model using 'modelforge config use'",
        )

    if verbose:
        logger.info("Testing model %s/%s with prompt", provider_name, model_alias)
    if not quiet:
        print_info(
            f"Sending prompt to the selected model [{provider_name}/{model_alias}]..."
        )

    # Step 1: Create telemetry callback
    telemetry = TelemetryCallback(provider=provider_name, model=model_alias)

    # Step 2: Instantiate the registry and get the model with telemetry
    registry = ModelForgeRegistry(verbose=verbose)
    # Get enhanced LLM to access metadata
    llm = registry.get_llm(
        callbacks=[telemetry], enhanced=True
    )  # Gets the currently selected model with metadata

    if not llm:
        raise ProviderError(
            f"Failed to instantiate language model for {provider_name}/{model_alias}",
            context="Check your configuration and credentials",
            suggestion=(
                f"Run 'modelforge auth login --provider {provider_name}' "
                "to authenticate"
            ),
        )

    # Step 3: Create the prompt and chain
    prompt_template = ChatPromptTemplate.from_messages([("human", "{input}")])
    chain = prompt_template | llm | StrOutputParser()

    # Step 4: Run the chain with streaming or regular invoke
    if stream:
        # Streaming mode
        response_chunks = []

        # Get provider config for auth handling during streaming
        config_data, _ = config.get_config()

        # Show prompt first for streaming (unless in quiet mode)
        if not output_file and not quiet:
            max_prompt_display = 80
            if len(prompt) > max_prompt_display:
                display_prompt = prompt[: max_prompt_display - 3] + "..."
            else:
                display_prompt = prompt
            click.echo()
            click.echo(click.style("Q: ", fg="blue", bold=True) + display_prompt)
            click.echo(click.style("A: ", fg="green", bold=True), nl=False)

        # Stream the response
        try:
            # Use direct LLM streaming instead of chain streaming for better control
            import sys

            # For debugging - let's see what stream returns
            if verbose:
                logger.info("Starting streaming response...")

            # Try using the chain's stream method with proper message format
            stream_iter = chain.stream({"input": prompt})

            for i, chunk in enumerate(stream_iter):
                # Extract text content from chunk
                chunk_text = str(chunk) if chunk else ""

                if verbose and i == 0:
                    logger.info(
                        "First chunk type: %s, content: %s...",
                        type(chunk),
                        chunk_text[:50],
                    )

                response_chunks.append(chunk_text)
                if not output_file and chunk_text:
                    # Write chunk immediately
                    sys.stdout.write(chunk_text)
                    sys.stdout.flush()
        except Exception as e:
            # Handle streaming errors
            if "401" in str(e) or "unauthorized" in str(e).lower():
                click.echo(
                    click.style(
                        "\nAuthentication error during streaming. "
                        "Please re-authenticate.",
                        fg="red",
                    )
                )
                raise
            click.echo(click.style(f"\nStreaming error: {e}", fg="red"))
            raise

        # Combine chunks for telemetry and file output
        response = "".join(response_chunks)
        if not output_file and not quiet:
            click.echo()  # New line after streaming
    # Regular invoke mode
    elif provider_name == "github_copilot":
        response = _invoke_with_smart_retry(chain, {"input": prompt}, verbose)
    else:
        response = chain.invoke({"input": prompt})

    # Format output
    if output_file:
        # Write to file (raw response only)
        output_path = Path(output_file)
        output_path.write_text(response, encoding="utf-8")
        print_success(f"Response written to {output_file}")

        # Still show telemetry to console if enabled
        settings = config.get_settings()
        show_telemetry = settings.get("show_telemetry", True) and not no_telemetry

        if show_telemetry and (
            telemetry.metrics.token_usage.total_tokens > 0 or verbose
        ):
            # Add context information if using enhanced LLM
            if isinstance(llm, EnhancedLLM):
                telemetry.metrics.metadata["context_length"] = llm.context_length
                telemetry.metrics.metadata["max_output_tokens"] = llm.max_output_tokens
                telemetry.metrics.metadata["supports_function_calling"] = (
                    llm.supports_function_calling
                )
                telemetry.metrics.metadata["supports_vision"] = llm.supports_vision
            click.echo(format_metrics(telemetry.metrics))
    else:
        # For non-streaming mode, format output based on quiet flag
        if not stream:
            if quiet:
                # In quiet mode, only output the response
                click.echo(response)
            else:
                # Normal Q&A chat style for console output
                max_prompt_display = 80  # Maximum characters to display for the prompt

                if len(prompt) > max_prompt_display:
                    display_prompt = prompt[: max_prompt_display - 3] + "..."
                else:
                    display_prompt = prompt

                click.echo()  # Empty line before Q&A
                click.echo(click.style("Q: ", fg="blue", bold=True) + display_prompt)
                click.echo(click.style("A: ", fg="green", bold=True) + response)

        # Step 5: Display telemetry information (unless disabled)
        settings = config.get_settings()
        show_telemetry = settings.get("show_telemetry", True) and not no_telemetry

        if show_telemetry and (
            telemetry.metrics.token_usage.total_tokens > 0 or verbose
        ):
            # Add context information if using enhanced LLM
            if isinstance(llm, EnhancedLLM):
                telemetry.metrics.metadata["context_length"] = llm.context_length
                telemetry.metrics.metadata["max_output_tokens"] = llm.max_output_tokens
                telemetry.metrics.metadata["supports_function_calling"] = (
                    llm.supports_function_calling
                )
                telemetry.metrics.metadata["supports_vision"] = llm.supports_vision
            click.echo(format_metrics(telemetry.metrics))


@cli.group(name="auth")
def auth_group() -> None:
    """Authentication management commands."""


@auth_group.command(name="login")
@click.option("--provider", required=True, help="The provider to authenticate with")
@click.option("--api-key", help="API key for authentication (skips interactive prompt)")
@click.option(
    "--force", is_flag=True, help="Force re-authentication even if credentials exist"
)
def auth_login(provider: str, api_key: str | None, force: bool) -> None:
    """Authenticate with a provider using API key or device flow."""
    # Validate provider name
    provider = InputValidator.validate_provider_name(provider)

    current_config, _ = config.get_config()
    providers = current_config.get("providers", {})

    if provider not in providers:
        raise ConfigurationError(
            f"Provider '{provider}' not found in configuration",
            suggestion=(
                "Use 'modelforge models list' to discover providers, "
                "then 'modelforge config add' to configure"
            ),
        )

    provider_data = providers[provider]
    auth_strategy = auth.get_auth_strategy(provider, provider_data)

    # Check for existing credentials
    if not force and auth_strategy.get_credentials():
        print_success(f"Already authenticated with '{provider}'")
        print_info("Use --force to re-authenticate")
        return

    # Handle different auth strategies
    if isinstance(auth_strategy, auth.ApiKeyAuth):
        if api_key:
            validated_key = InputValidator.validate_api_key(api_key, provider)
            auth_strategy.store_api_key(validated_key)
            print_success(f"API key stored for provider '{provider}'")
        else:
            credentials = auth_strategy.authenticate()
            if credentials:
                print_success(f"Successfully authenticated with '{provider}'")
            else:
                raise AuthenticationError(
                    f"Authentication failed for '{provider}'",
                    suggestion="Check your API key and try again",
                )
    elif isinstance(auth_strategy, auth.DeviceFlowAuth):
        print_info(f"Starting device flow authentication for '{provider}'...")
        credentials = auth_strategy.authenticate()
        if credentials:
            print_success(f"Successfully authenticated with '{provider}'")
        else:
            raise AuthenticationError(
                f"Authentication failed for '{provider}'",
                suggestion="Check your internet connection and try again",
            )
    else:
        print_success(f"Provider '{provider}' doesn't require authentication")


@auth_group.command(name="logout")
@click.option("--provider", required=False, help="The provider to log out from")
@click.option("--all-providers", is_flag=True, help="Log out from all providers")
def auth_logout(provider: str | None, all_providers: bool) -> None:
    """Clear stored credentials for a provider."""
    if all_providers:
        current_config, _ = config.get_config()
        providers = current_config.get("providers", {})

        for provider_name in providers:
            try:
                provider_data = providers[provider_name]
                auth_strategy = auth.get_auth_strategy(provider_name, provider_data)
                auth_strategy.clear_credentials()
                print_success(f"Cleared credentials for '{provider_name}'")
            except Exception as e:
                print_warning(f"Failed to clear credentials for '{provider_name}': {e}")
    elif provider:
        # Validate provider name
        provider = InputValidator.validate_provider_name(provider)

        current_config, _ = config.get_config()
        providers = current_config.get("providers", {})

        if provider not in providers:
            raise ConfigurationError(
                f"Provider '{provider}' not found",
                suggestion="Use 'modelforge config show' to see available providers",
            )

        provider_data = providers[provider]
        auth_strategy = auth.get_auth_strategy(provider, provider_data)
        auth_strategy.clear_credentials()
        print_success(f"Cleared credentials for '{provider}'")
    else:
        raise InvalidInputError(
            "Either --provider or --all-providers is required",
            suggestion=(
                "Use 'modelforge auth logout --provider PROVIDER' or "
                "'modelforge auth logout --all-providers'"
            ),
        )


@auth_group.command(name="status")
@click.option("--provider", help="Check status for specific provider")
@click.option("--verbose", is_flag=True, help="Show detailed token information")
def auth_status(provider: str | None, verbose: bool) -> None:
    """Check authentication status for providers."""
    current_config, _ = config.get_config()
    providers = current_config.get("providers", {})

    if provider:
        # Validate provider name
        provider = InputValidator.validate_provider_name(provider)

        # Check specific provider
        if provider not in providers:
            raise ConfigurationError(
                f"Provider '{provider}' not found in configuration",
                suggestion="Use 'modelforge config show' to see available providers",
            )
        _check_provider_status(provider, providers[provider], verbose)
    else:
        # Check all providers
        print_info("Authentication Status for All Providers:\n")
        for provider_name, provider_data in providers.items():
            _check_provider_status(provider_name, provider_data, verbose)
            click.echo()  # Empty line between providers


@cli.group()
def settings() -> None:
    """Manage ModelForge settings."""


@settings.command(name="show")
def show_settings() -> None:
    """Show current settings."""
    current_settings = config.get_settings()
    print_info("Current ModelForge Settings:")
    for key, value in current_settings.items():
        click.echo(f"  {key}: {value}")


@settings.command(name="telemetry")
@click.argument("action", type=click.Choice(["on", "off", "status"]))
@click.option("--local", is_flag=True, help="Update local project config.")
def manage_telemetry(action: str, local: bool) -> None:
    """Manage telemetry display settings."""
    if action == "status":
        settings = config.get_settings()
        current_state = (
            "enabled" if settings.get("show_telemetry", True) else "disabled"
        )
        print_info(f"Telemetry display is currently {current_state}")
    elif action == "on":
        config.update_setting("show_telemetry", True, local=local)
        scope = "local" if local else "global"
        print_success(f"Telemetry display enabled in {scope} config")
    elif action == "off":
        config.update_setting("show_telemetry", False, local=local)
        scope = "local" if local else "global"
        print_success(f"Telemetry display disabled in {scope} config")


@cli.group()
def models() -> None:
    """Model discovery and management commands."""


@models.command(name="list")
@click.option("--provider", help="Filter by specific provider")
@click.option("--refresh", is_flag=True, help="Force refresh from models.dev")
@click.option(
    "--format", "output_format", type=click.Choice(["table", "json"]), default="table"
)
def list_models(provider: str | None, refresh: bool, output_format: str) -> None:
    """List available models from models.dev."""
    if provider:
        provider = InputValidator.validate_provider_name(provider)

    client = ModelsDevClient()
    models = client.get_models(provider=provider, force_refresh=refresh)

    if not models:
        print_warning("No models found")
        return

    if output_format == "json":
        click.echo(json.dumps(models, indent=2))
    else:
        # Table format
        print_info(f"Found {len(models)} models:\n")

        # Group by provider
        provider_models: dict[str, list[dict[str, Any]]] = {}
        for model in models:
            prov = model.get("provider", "unknown")
            if prov not in provider_models:
                provider_models[prov] = []
            provider_models[prov].append(model)

        for prov, prov_models in provider_models.items():
            click.echo(f"🤖 {prov.upper()}:")
            for model in prov_models:
                name = model.get("name", "unknown")
                display_name = model.get("display_name", name)
                description = model.get("description", "")
                if len(description) > 50:
                    description = description[:47] + "..."

                click.echo(f"  • {display_name} - {description}")
            click.echo()


@models.command(name="search")
@click.argument("query")
@click.option("--provider", help="Filter by specific provider")
@click.option("--capability", multiple=True, help="Filter by capabilities")
@click.option("--max-price", type=float, help="Maximum price per 1K tokens")
@click.option("--refresh", is_flag=True, help="Force refresh from models.dev")
def search_models(
    query: str,
    provider: str | None,
    capability: tuple[str, ...],
    max_price: float | None,
    refresh: bool,
) -> None:
    """Search models by name, description, or capabilities."""
    if provider:
        provider = InputValidator.validate_provider_name(provider)

    # max_price is already a float from click.option type=float

    client = ModelsDevClient()
    models = client.search_models(
        query=query,
        provider=provider,
        capabilities=list(capability) if capability else None,
        max_price=max_price,
        force_refresh=refresh,
    )

    if not models:
        print_warning("No models found matching criteria")
        return

    print_info(f"Found {len(models)} matching models:\n")
    for model in models:
        name = model.get("name", "unknown")
        display_name = model.get("display_name", name)
        provider_name = model.get("provider", "unknown")
        description = model.get("description", "")

        click.echo(f"🤖 {display_name} ({provider_name})")
        click.echo(f"   {description}")

        if model.get("capabilities"):
            caps = ", ".join(model["capabilities"])
            click.echo(f"   Capabilities: {caps}")

        if model.get("pricing"):
            pricing = model["pricing"]
            input_price = pricing.get("input_per_1m_tokens")
            if input_price is not None:
                click.echo(f"   Price: ${input_price}/1M tokens")

        click.echo()


@models.command(name="info")
@click.option("--provider", required=True, help="The provider name")
@click.option("--model", required=True, help="The model name")
@click.option("--refresh", is_flag=True, help="Force refresh from models.dev")
def model_info(provider: str, model: str, refresh: bool) -> None:
    """Get detailed information about a specific model."""
    # Validate inputs
    provider = InputValidator.validate_provider_name(provider)
    model = InputValidator.validate_model_name(model)

    client = ModelsDevClient()
    info = client.get_model_info(provider=provider, model=model, force_refresh=refresh)

    click.echo(json.dumps(info, indent=2))


@cli.command(name="status")
@click.option("--provider", help="Check status for specific provider")
@click.option("--verbose", is_flag=True, help="Show detailed token information")
def status(provider: str | None, verbose: bool) -> None:
    """Check authentication status for providers (deprecated, use 'auth status')."""
    print_warning("This command is deprecated. Use 'modelforge auth status' instead.")
    auth_status(provider, verbose)


def _check_provider_status(
    provider_name: str, provider_data: dict[str, Any], verbose: bool
) -> None:
    """Check status for a specific provider."""
    auth_strategy_name = provider_data.get("auth_strategy", "unknown")

    click.echo(f"📋 Provider: {provider_name}")
    click.echo(f"   Auth Strategy: {auth_strategy_name}")

    if auth_strategy_name == "local":
        print_success("   Status: Local provider (no authentication needed)")
        return

    try:
        auth_strategy = auth.get_auth_strategy(provider_name, provider_data)
        credentials = auth_strategy.get_credentials()

        if credentials:
            print_success("   Status: Valid credentials found")

            # Show detailed token info for device flow
            if auth_strategy_name == "device_flow" and hasattr(
                auth_strategy, "get_token_info"
            ):
                token_info = auth_strategy.get_token_info()
                if token_info and verbose:
                    click.echo("   Token Details:")
                    if "time_remaining" in token_info:
                        click.echo(
                            f"      Time Remaining: {token_info['time_remaining']}"
                        )
                    if "expiry_time" in token_info:
                        click.echo(f"      Expires At: {token_info['expiry_time']}")
                    if "scope" in token_info:
                        click.echo(f"      Scope: {token_info['scope']}")
                elif token_info and not verbose:
                    if "time_remaining" in token_info:
                        remaining = str(token_info["time_remaining"]).split(".")[
                            0
                        ]  # Remove microseconds
                        click.echo(f"   Time Remaining: {remaining}")
        else:
            print_warning("   Status: No valid credentials found")
            click.echo(
                f"   Action: Run 'modelforge auth login --provider {provider_name}'"
            )

    except Exception as e:
        print_warning(f"   Status: Error checking credentials: {e}")


def _invoke_with_smart_retry(
    chain: Any,  # noqa: ANN401
    input_data: dict[str, Any],
    verbose: bool = False,
    max_retries: int = 3,
) -> str:
    """
    Invokes a LangChain model with smart retry logic for GitHub Copilot rate limits.

    Args:
        chain: The LangChain model to invoke
        input_data: The input data to pass to the model
        verbose: Whether to show verbose output
        max_retries: Maximum number of retry attempts

    Returns:
        The model response

    Raises:
        RateLimitError: If max retries are reached for rate limiting
        ProviderError: For non-rate-limit errors
    """
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info(
                    "Retry attempt %d/%d for GitHub Copilot", attempt + 1, max_retries
                )
                if verbose:
                    print_info(
                        f"Retry attempt {attempt + 1}/{max_retries} "
                        f"for GitHub Copilot..."
                    )

            result = chain.invoke(input_data)
            if isinstance(result, BaseMessage):
                return str(result.content)
            return str(result)

        except Exception as e:
            error_msg = str(e).lower()

            # Check if this is a rate limiting error that we should retry
            if any(
                phrase in error_msg
                for phrase in ["forbidden", "rate limit", "too many requests"]
            ):
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    # Exponential backoff with jitter: 1s, 2s, 4s + random(0-1)
                    # Note: Using random for non-cryptographic backoff delay
                    delay = (2**attempt) + random.uniform(0, 1)  # noqa: S311

                    logger.warning(
                        "Rate limited by GitHub Copilot. Waiting %.1fs before retry",
                        delay,
                    )
                    if verbose:
                        print_warning(
                            f"Rate limited by GitHub Copilot. "
                            f"Waiting {delay:.1f}s before retry..."
                        )

                    time.sleep(delay)
                    continue
                logger.exception(
                    "Max retries (%d) reached for GitHub Copilot rate limiting",
                    max_retries,
                )
                raise RateLimitError("github_copilot", retry_after=None) from e
            # Non-rate-limit error, don't retry
            logger.exception("Non-rate-limit error in GitHub Copilot call")
            raise ProviderError(
                f"GitHub Copilot API error: {str(e)}",
                context="Error occurred during model invocation",
                suggestion="Check your configuration and try again",
            ) from e

    # If we get here, all retries failed
    logger.error("All retry attempts failed for GitHub Copilot")
    raise RateLimitError("github_copilot")


if __name__ == "__main__":
    cli()
