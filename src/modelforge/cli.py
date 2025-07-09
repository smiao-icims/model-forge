# Standard library imports
import json
import random
import time
from typing import Any

# Third-party imports
import click
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Local imports
from . import auth, config
from .logging_config import get_logger
from .registry import ModelForgeRegistry

logger = get_logger(__name__)


def _handle_authentication(
    provider: str, provider_data: dict[str, Any], api_key: str | None, dev_auth: bool
) -> None:
    """Handle authentication for provider configuration."""
    if api_key:
        auth_strategy = auth.ApiKeyAuth(provider)
        # Store the provided API key using the new config-based approach
        auth_strategy._save_auth_data({"api_key": api_key})
        click.echo(f"API key stored for provider '{provider}'.")
    elif dev_auth:
        click.echo("Starting device authentication flow...")
        try:
            auth_strategy = auth.get_auth_strategy(provider, provider_data)
            credentials = auth_strategy.authenticate()
            if credentials:
                click.echo(f"Authentication successful for provider '{provider}'.")
            else:
                click.echo("Authentication failed.", err=True)
                return
        except Exception as e:
            logger.exception("Device authentication failed")
            click.echo(f"Device authentication failed: {e}", err=True)
            return


@click.group()
def cli() -> None:
    """ModelForge CLI for managing LLM configurations."""


@cli.group(name="config")
def config_group() -> None:
    """Configuration management commands."""


@config_group.command(name="show")
def show_config() -> None:
    """Shows the current configuration."""
    try:
        current_config, config_path = config.get_config()
        scope = "local" if config_path == config.LOCAL_CONFIG_FILE else "global"
        click.echo(f"Active ModelForge Config ({scope}): {config_path}")

        if not current_config or not current_config.get("providers"):
            click.echo(
                "Configuration is empty. Add models using 'modelforge config add'."
            )
            return

        click.echo(json.dumps(current_config, indent=4))
    except Exception as e:
        logger.exception("Failed to show configuration")
        click.echo(f"Error: Failed to show configuration: {e}", err=True)


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
    *,
    local: bool = False,
) -> None:
    """Add a new model configuration."""
    try:
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
        click.echo(
            f"Successfully configured model '{model}' for provider '{provider}' "
            f"in the {scope_msg} config."
        )
        click.echo("Run 'modelforge config show' to see the updated configuration.")

    except Exception as e:
        logger.exception("Failed to add model configuration")
        click.echo(f"Error: {e}", err=True)


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
    success = config.set_current_model(provider_name, model_alias, local=local)
    if not success:
        raise click.ClickException


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
    target_config_path = config.get_config_path(local=local)
    current_config, _ = config.get_config_from_path(target_config_path)

    providers = current_config.get("providers", {})

    if provider not in providers:
        click.echo(f"Error: Provider '{provider}' not found.")
        return

    provider_data = providers[provider]
    models = provider_data.get("models", {})

    if model not in models:
        click.echo(f"Error: Model '{model}' not found for provider '{provider}'.")
        return

    # Remove the model from configuration
    del models[model]

    # If no models left for this provider, remove the entire provider
    if not models:
        del providers[provider]
        click.echo(f"Removed provider '{provider}' (no models remaining).")
    else:
        click.echo(f"Removed model '{model}' from provider '{provider}'.")

    # Check if this was the currently selected model
    current_model = current_config.get("current_model", {})
    if (
        current_model.get("provider") == provider
        and current_model.get("model") == model
    ):
        current_config["current_model"] = {}
        click.echo("Cleared current model selection (removed model was selected).")

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
            click.echo(f"Removed stored credentials for {provider}")
        except Exception as e:
            click.echo(f"Warning: Could not remove credentials from config: {e}")
    else:
        click.echo("Kept stored credentials (--keep-credentials flag used).")


@cli.command(name="test")
@click.option("--prompt", required=True, help="The prompt to send to the model.")
@click.option("--verbose", is_flag=True, help="Enable verbose debug output.")
def test_model(prompt: str, verbose: bool) -> None:
    """Tests the currently selected model with a prompt."""
    try:
        current_model = config.get_current_model()
        if not current_model:
            logger.error("No model selected for testing")
            click.echo(
                "Error: No model selected. Use 'modelforge config use'.", err=True
            )
            return

        provider_name = current_model.get("provider")
        model_alias = current_model.get("model")

        logger.info("Testing model %s/%s with prompt", provider_name, model_alias)
        click.echo(
            f"Sending prompt to the selected model [{provider_name}/{model_alias}]..."
        )

        # Step 1: Instantiate the registry and get the model
        registry = ModelForgeRegistry(verbose=verbose)
        llm = registry.get_llm()  # Gets the currently selected model

        if not llm:
            logger.error(
                "Failed to instantiate language model for %s/%s",
                provider_name,
                model_alias,
            )
            click.echo(
                "Failed to instantiate the language model. Check logs for details.",
                err=True,
            )
            return

        # Step 2: Create the prompt and chain
        prompt_template = ChatPromptTemplate.from_messages([("human", "{input}")])
        chain = prompt_template | llm | StrOutputParser()

        # Step 3: Run the chain with smart retry if the provider is GitHub Copilot
        if provider_name == "github_copilot":
            response = _invoke_with_smart_retry(chain, {"input": prompt}, verbose)
        else:
            response = chain.invoke({"input": prompt})

        click.echo(response)

    except Exception as e:
        logger.exception("Error occurred while running model test")
        click.echo(f"\nAn error occurred while running the model: {e}", err=True)


@cli.command(name="status")
@click.option("--provider", help="Check status for specific provider")
@click.option("--verbose", is_flag=True, help="Show detailed token information")
def status(provider: str | None, verbose: bool) -> None:
    """Check authentication status for providers."""
    try:
        current_config, _ = config.get_config()
        providers = current_config.get("providers", {})

        if provider:
            # Check specific provider
            if provider not in providers:
                click.echo(f"❌ Provider '{provider}' not found in configuration")
                return
            _check_provider_status(provider, providers[provider], verbose)
        else:
            # Check all providers
            click.echo("🔍 Authentication Status for All Providers:\n")
            for provider_name, provider_data in providers.items():
                _check_provider_status(provider_name, provider_data, verbose)
                click.echo()  # Empty line between providers

    except Exception as e:
        logger.exception("Failed to check authentication status")
        click.echo(f"❌ Error checking status: {e}", err=True)


def _check_provider_status(
    provider_name: str, provider_data: dict[str, Any], verbose: bool
) -> None:
    """Check status for a specific provider."""
    auth_strategy_name = provider_data.get("auth_strategy", "unknown")

    click.echo(f"📋 Provider: {provider_name}")
    click.echo(f"   Auth Strategy: {auth_strategy_name}")

    if auth_strategy_name == "local":
        click.echo("   Status: ✅ Local provider (no authentication needed)")
        return

    try:
        auth_strategy = auth.get_auth_strategy(provider_name, provider_data)
        credentials = auth_strategy.get_credentials()

        if credentials:
            click.echo("   Status: ✅ Valid credentials found")

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
            click.echo("   Status: ❌ No valid credentials found")
            click.echo(f"   Action: Run authentication for {provider_name}")

    except Exception as e:
        click.echo(f"   Status: ❌ Error checking credentials: {e}")


def _invoke_with_smart_retry(
    chain: BaseChatModel,
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
        ProviderError: If max retries are reached for rate limiting
        Exception: For non-rate-limit errors
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info(
                    "Retry attempt %d/%d for GitHub Copilot", attempt + 1, max_retries
                )
                if verbose:
                    click.echo(
                        f"🔄 Retry attempt {attempt + 1}/{max_retries} "
                        f"for GitHub Copilot..."
                    )

            return chain.invoke(input_data)

        except Exception as e:
            last_exception = e
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
                        click.echo(
                            f"⏳ Rate limited by GitHub Copilot. "
                            f"Waiting {delay:.1f}s before retry..."
                        )

                    time.sleep(delay)
                    continue
                logger.exception(
                    "Max retries (%d) reached for GitHub Copilot rate limiting",
                    max_retries,
                )
                if verbose:
                    click.echo(
                        f"❌ Max retries ({max_retries}) reached "
                        f"for GitHub Copilot rate limiting"
                    )
            else:
                # Non-rate-limit error, don't retry
                logger.exception("Non-rate-limit error in GitHub Copilot call")
                raise

    # If we get here, all retries failed
    logger.error("All retry attempts failed for GitHub Copilot")
    raise last_exception


if __name__ == "__main__":
    cli()
