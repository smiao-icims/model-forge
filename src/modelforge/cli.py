# Standard library imports
import json
import random
import time
from typing import Any

# Third-party imports
import click
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Local imports
from . import auth, config
from .cli_utils import (
    handle_cli_errors,
    print_info,
    print_success,
    print_warning,
)
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    InvalidInputError,
    ModelNotFoundError,
    ProviderError,
)
from .logging_config import get_logger
from .modelsdev import ModelsDevClient
from .registry import ModelForgeRegistry
from .validation import InputValidator

logger = get_logger(__name__)


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
@handle_cli_errors
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
@handle_cli_errors
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
@handle_cli_errors
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
@handle_cli_errors
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
@click.option("--prompt", required=True, help="The prompt to send to the model.")
@click.option("--verbose", is_flag=True, help="Enable verbose debug output.")
@handle_cli_errors
def test_model(prompt: str, verbose: bool) -> None:
    """Tests the currently selected model with a prompt."""
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

    logger.info("Testing model %s/%s with prompt", provider_name, model_alias)
    print_info(
        f"Sending prompt to the selected model [{provider_name}/{model_alias}]..."
    )

    # Step 1: Instantiate the registry and get the model
    registry = ModelForgeRegistry(verbose=verbose)
    llm = registry.get_llm()  # Gets the currently selected model

    if not llm:
        raise ProviderError(
            f"Failed to instantiate language model for {provider_name}/{model_alias}",
            context="Check your configuration and credentials",
            suggestion=(
                f"Run 'modelforge auth login --provider {provider_name}' "
                "to authenticate"
            ),
        )

    # Step 2: Create the prompt and chain
    prompt_template = ChatPromptTemplate.from_messages([("human", "{input}")])
    chain = prompt_template | llm | StrOutputParser()

    # Step 3: Run the chain with smart retry if the provider is GitHub Copilot
    if provider_name == "github_copilot":
        response = _invoke_with_smart_retry(chain, {"input": prompt}, verbose)
    else:
        response = chain.invoke({"input": prompt})

    click.echo(response)


@cli.group(name="auth")
def auth_group() -> None:
    """Authentication management commands."""


@auth_group.command(name="login")
@click.option("--provider", required=True, help="The provider to authenticate with")
@click.option("--api-key", help="API key for authentication (skips interactive prompt)")
@click.option(
    "--force", is_flag=True, help="Force re-authentication even if credentials exist"
)
@handle_cli_errors
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
@handle_cli_errors
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
@handle_cli_errors
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
def models() -> None:
    """Model discovery and management commands."""


@models.command(name="list")
@click.option("--provider", help="Filter by specific provider")
@click.option("--refresh", is_flag=True, help="Force refresh from models.dev")
@click.option(
    "--format", "output_format", type=click.Choice(["table", "json"]), default="table"
)
@handle_cli_errors
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
@handle_cli_errors
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
            if "input_per_1k_tokens" in pricing:
                click.echo(f"   Price: ${pricing['input_per_1k_tokens']}/1K tokens")

        click.echo()


@models.command(name="info")
@click.option("--provider", required=True, help="The provider name")
@click.option("--model", required=True, help="The model name")
@click.option("--refresh", is_flag=True, help="Force refresh from models.dev")
@handle_cli_errors
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
@handle_cli_errors
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
    from .exceptions import RateLimitError

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
