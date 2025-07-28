"""Interactive configuration wizard for ModelForge."""

import logging
import shutil
import subprocess
import sys
from typing import Any

import questionary
from questionary import Choice

from . import auth, config
from .enhanced_llm import EnhancedLLM
from .exceptions import AuthenticationError
from .logging_config import get_logger
from .registry import ModelForgeRegistry
from .telemetry import TelemetryCallback, format_metrics
from .validation import InputValidator

logger = get_logger(__name__)


class ConfigWizard:
    """Interactive configuration wizard for ModelForge."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the configuration wizard."""
        self.verbose = verbose

        # Suppress logs unless verbose
        if not verbose:
            # Suppress all modelforge logs and submodules
            logging.getLogger("modelforge").setLevel(logging.ERROR)
            # Also suppress the doubly-prefixed loggers created by get_logger
            logging.getLogger("modelforge.modelforge").setLevel(logging.ERROR)

        self.registry = ModelForgeRegistry()
        self.current_config, self.config_path = config.get_config()
        self.is_local = self.config_path == config.LOCAL_CONFIG_FILE
        # Get current model selection for defaults
        self.current_model = config.get_current_model() or {}

    def run(self) -> None:
        """Run the interactive configuration wizard."""
        # Check if we're in an interactive terminal

        if not sys.stdin.isatty():
            print(
                "❌ Error: The configuration wizard requires an interactive terminal."
            )
            print("Please run this command directly in your terminal.")
            sys.exit(1)

        questionary.print(
            "🧙 Welcome to ModelForge Configuration Wizard!",
            style="bold fg:cyan",
        )
        questionary.print(
            "This wizard will help you configure LLM providers step by step.",
            style="italic",
        )
        questionary.print(
            "(Press Ctrl+C at any time to exit)\n",
            style="fg:#666666",
        )

        try:
            # Step 1: Choose configuration scope
            scope = self._choose_scope()

            # Step 2: Select provider
            provider = self._select_provider()
            if not provider:
                return

            # Step 3: Configure provider authentication
            if not self._configure_authentication(provider):
                return

            # Step 4: Select model
            model = self._select_model(provider)
            if not model:
                return

            # Step 5: Test configuration
            questionary.print("\n🧪 Testing configuration...", style="bold")
            if not self._test_configuration(
                provider, model
            ) and not questionary.confirm(
                "Configuration test failed. Save anyway?",
                default=False,
            ):
                questionary.print("❌ Configuration cancelled.", style="bold fg:red")
                return

            # Step 6: Save configuration
            self._save_configuration(provider, model, scope == "local")

            # Step 7: Set as current model?
            if questionary.confirm(
                f"\nSet {provider}/{model} as the current model?",
                default=True,
            ):
                # Normalize provider name for config
                normalized_provider = (
                    "github_copilot" if provider == "github-copilot" else provider
                )
                config.set_current_model(
                    normalized_provider,
                    model,
                    local=(scope == "local"),
                    quiet=not self.verbose,
                )
                questionary.print("✅ Set as current model!", style="bold fg:green")

            questionary.print(
                "\n🎉 Configuration complete! You can now use:",
                style="bold fg:green",
            )
            questionary.print("   modelforge test --prompt 'Hello, world!'")
            questionary.print(f"   modelforge test  # (uses {provider}/{model})")

        except KeyboardInterrupt:
            questionary.print("\n❌ Configuration cancelled.", style="bold fg:red")
            sys.exit(1)
        except Exception as e:
            questionary.print(f"\n❌ Error: {e}", style="bold fg:red")
            sys.exit(1)

    def _choose_scope(self) -> str:
        """Choose between global and local configuration."""
        current_scope = "local" if self.is_local else "global"

        # Build titles with current indicator
        global_title = "🌍 Global configuration (user-wide)"
        local_title = "📁 Local configuration (project-specific)"

        if current_scope == "global":
            global_title += " [current]"
        else:
            local_title += " [current]"

        choices = [
            Choice(title=global_title, value="global"),
            Choice(title=local_title, value="local"),
        ]

        return questionary.select(
            "Where should the configuration be saved?",
            choices=choices,
        ).ask()

    def _select_provider(self) -> str | None:
        """Select a provider from available options."""
        questionary.print("\n📦 Fetching available providers...", style="italic")

        try:
            # Get available providers
            available_providers = self.registry.get_available_providers()

            # Check which ones are already configured
            configured = self.registry.get_configured_providers()
            # Normalize configured provider names for display
            configured_normalized = {}
            for provider_name, provider_config in configured.items():
                if provider_name == "github_copilot":
                    configured_normalized["github-copilot"] = provider_config
                else:
                    configured_normalized[provider_name] = provider_config

            # Build choices with helpful annotations
            choices = []

            # Group by configuration status
            # ⭐ = Recommended providers (popular, well-tested)
            # ✅ = Already configured providers
            recommended = [
                "openai",
                "anthropic",
                "github-copilot",
                "google",
                "ollama",
                "openrouter",
            ]

            for provider in available_providers:
                name = provider["name"]
                display = provider["display_name"]
                auth_types = provider.get("auth_types", [])

                # Build title with status (check normalized configured)
                if name in configured_normalized:
                    models_count = len(configured_normalized[name].get("models", {}))
                    title = f"✅ {display} ({models_count} models configured)"
                else:
                    # Special handling for known providers with specific auth
                    if name in ["github_copilot", "github-copilot"]:
                        auth_str = "device_flow"
                    elif name == "ollama":
                        auth_str = "none"
                    else:
                        auth_str = ", ".join(auth_types) if auth_types else "unknown"
                    title = f"   {display} (auth: {auth_str})"

                # Add recommendation badge
                if name in recommended:
                    title = "⭐ " + title

                choices.append(Choice(title=title, value=name))

            # Sort: recommended first, then configured, then others
            choices.sort(
                key=lambda c: (
                    c.value not in recommended,
                    c.value not in configured_normalized,
                    c.value,
                )
            )

            # Get current provider to set as default
            current_provider = self.current_model.get("provider")
            # Normalize provider name for comparison
            if current_provider == "github_copilot":
                current_provider = "github-copilot"

            # Find the index of current provider in choices
            default_index = 0
            if current_provider:
                for i, choice in enumerate(choices):
                    if choice.value == current_provider:
                        default_index = i
                        break

            return questionary.select(
                "Select a provider:",
                choices=choices,
                default=choices[default_index].value if choices else None,
                instruction="(Use ↑↓ arrows, Enter to select)",
            ).ask()

        except Exception as e:
            questionary.print(f"Failed to fetch providers: {e}", style="bold fg:red")
            # Fallback to manual entry
            return questionary.text(
                "Enter provider name manually (e.g., openai, anthropic):"
            ).ask()

    def _configure_authentication(self, provider: str) -> bool:
        """Configure authentication for the selected provider."""
        # Normalize provider name for consistent handling
        normalized_provider = (
            "github_copilot" if provider == "github-copilot" else provider
        )

        # Get provider configuration (use normalized name for consistency)
        provider_config = self._get_or_create_provider_config(normalized_provider)
        auth_strategy = provider_config.get("auth_strategy", "api_key")

        logger.debug(
            "Provider: %s, Normalized: %s, Auth strategy: %s",
            provider,
            normalized_provider,
            auth_strategy,
        )

        questionary.print(
            f"\n🔐 Configuring authentication for {provider}...",
            style="bold",
        )

        # Check existing authentication
        try:
            existing_creds = auth.get_credentials(
                normalized_provider, "", provider_config, verbose=False
            )
            if existing_creds:
                questionary.print("✅ Valid credentials found!", style="fg:green")

                # Build choice based on auth type
                if (
                    provider in ["github_copilot", "github-copilot"]
                    and auth_strategy == "device_flow"
                ):
                    use_existing_text = "Use existing device authentication token"
                    re_auth_text = "Re-authenticate with GitHub (new device flow)"
                elif provider == "ollama":
                    # Ollama doesn't need auth, skip this
                    return True
                else:
                    use_existing_text = "Use existing API key"
                    re_auth_text = "Enter new API key"

                choice = questionary.select(
                    "What would you like to do?",
                    choices=[
                        Choice(title=use_existing_text, value="use_existing"),
                        Choice(title=re_auth_text, value="re_authenticate"),
                    ],
                ).ask()

                if choice == "use_existing":
                    return True
                # Otherwise fall through to re-authentication
        except Exception as e:
            logger.debug("Error checking existing credentials: %s", e)

        # Provider-specific authentication
        if (
            provider in ["github_copilot", "github-copilot"]
            and auth_strategy == "device_flow"
        ):
            return self._configure_github_copilot_auth(provider_config)
        if provider == "ollama":
            # Ollama doesn't need authentication
            questionary.print(
                "ℹ️  Ollama doesn't require authentication.", style="fg:blue"
            )
            return True
        # API key authentication
        return self._configure_api_key_auth(normalized_provider, provider_config)

    def _configure_github_copilot_auth(self, provider_config: dict[str, Any]) -> bool:
        """Configure GitHub Copilot device flow authentication."""
        # This method is only called if user chose to re-authenticate
        # or if no valid credentials exist
        questionary.print(
            "Starting GitHub device flow authentication...",
            style="italic",
        )

        # Start authentication directly without additional confirmation
        # since user already chose to authenticate
        try:
            # Always use underscore version for auth, extract auth details
            auth_details = provider_config.get("auth_details", {})
            if not auth_details:
                questionary.print(
                    "⚠️  Missing auth details in configuration. Using defaults.",
                    style="fg:yellow",
                )
            auth_strategy = auth.DeviceFlowAuth(
                provider_name="github_copilot",
                client_id=auth_details.get("client_id", "01ab8ac9400c4e429b23"),
                device_code_url=auth_details.get(
                    "device_code_url", "https://github.com/login/device/code"
                ),
                token_url=auth_details.get(
                    "token_url", "https://github.com/login/oauth/access_token"
                ),
                scope=auth_details.get("scope", "read:user"),
            )
            questionary.print(
                "\n🌐 Opening browser for authentication...",
                style="bold",
            )

            credentials = auth_strategy.authenticate()
            if credentials:
                questionary.print(
                    "✅ Authentication successful!", style="bold fg:green"
                )
                return True
            questionary.print("❌ Authentication failed.", style="bold fg:red")
            return False  # noqa: TRY300
        except Exception as e:
            questionary.print(f"❌ Authentication error: {e}", style="bold fg:red")
            logger.exception("GitHub Copilot device flow auth failed")
            return False

    def _configure_api_key_auth(
        self, provider: str, provider_config: dict[str, Any]
    ) -> bool:
        """Configure API key authentication."""
        # Check environment variable first
        env_var = f"{provider.upper()}_API_KEY"
        import os

        if os.getenv(env_var):
            questionary.print(
                f"ℹ️  Found API key in environment variable {env_var}",
                style="fg:blue",
            )
            return True

        # Prompt for API key
        api_key = questionary.password(
            f"Enter API key for {provider}:",
            instruction="(Input hidden)",
        ).ask()

        if api_key:
            try:
                # Validate and store
                validated_key = InputValidator.validate_api_key(api_key, provider)
                auth_strategy = auth.ApiKeyAuth(provider)
                auth_strategy._save_auth_data({"api_key": validated_key})
                questionary.print("✅ API key saved!", style="bold fg:green")
            except Exception as e:
                questionary.print(f"❌ Invalid API key: {e}", style="bold fg:red")
                return False
            else:
                return True  # noqa: TRY300
        else:
            return False

    def _select_model(self, provider: str) -> str | None:
        """Select a model for the provider."""
        questionary.print(
            f"\n🤖 Fetching available models for {provider}...",
            style="italic",
        )

        try:
            # Special handling for Ollama - use ollama list
            models: list[str] | list[dict[str, Any]]
            if provider == "ollama":
                models = self._get_ollama_models()
            else:
                # Get models from models.dev
                models = self.registry.get_available_models(provider=provider)

            if not models:
                questionary.print(f"No models found for {provider}.", style="fg:yellow")
                return questionary.text("Enter model name manually:").ask()

            # Get configured models to show status
            # Normalize provider name for registry lookup
            registry_provider = (
                "github_copilot" if provider == "github-copilot" else provider
            )
            configured_models = self.registry.get_configured_models(registry_provider)

            # Build choices
            choices = []
            for model in models:
                if isinstance(model, str):
                    # Ollama returns simple strings
                    title = f"   {model}"
                    if model in configured_models:
                        title = f"✅ {model}"
                    choices.append(Choice(title=title, value=model))
                else:
                    # models.dev returns dicts
                    model_id = model["id"]
                    display_name = model.get("display_name", model_id)
                    context = model.get("context_length", 0)

                    # Build informative title
                    title = f"   {display_name}"
                    if context:
                        title += f" ({context:,} tokens)"

                    # Check if configured
                    if model_id in configured_models:
                        title = "✅" + title[2:]

                    # Add pricing info if available
                    pricing = model.get("pricing", {})
                    if pricing and pricing.get("input_per_1m_tokens"):
                        price = pricing["input_per_1m_tokens"]
                        title += f" - ${price}/1M"

                    choices.append(Choice(title=title, value=model_id))

            # Sort by configuration status
            choices.sort(
                key=lambda c: (
                    "✅" not in getattr(c, "title", ""),
                    getattr(c, "value", ""),
                )
            )

            # Get current model to set as default
            current_model_alias = None
            if self.current_model.get("provider") == provider or (
                self.current_model.get("provider") == "github_copilot"
                and provider == "github-copilot"
            ):
                current_model_alias = self.current_model.get("model")

            # Find the index of current model in choices
            default_index = 0
            if current_model_alias:
                for i, choice in enumerate(choices[:20]):
                    if hasattr(choice, "value") and choice.value == current_model_alias:
                        default_index = i
                        break

            return questionary.select(
                f"Select a model for {provider}:",
                choices=choices[:20],  # Limit to 20 for usability
                default=choices[default_index].value
                if default_index < len(choices[:20])
                else None,
                instruction="(Showing top 20 models)",
            ).ask()

        except Exception as e:
            questionary.print(f"Failed to fetch models: {e}", style="bold fg:red")
            return questionary.text("Enter model name manually:").ask()

    def _get_ollama_models(self) -> list[str]:
        """Get locally available Ollama models."""
        try:
            # Find ollama executable for security
            ollama_path = shutil.which("ollama")
            if not ollama_path:
                raise FileNotFoundError("Ollama not found in PATH")

            result = subprocess.run(  # noqa: S603
                [ollama_path, "list"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse output
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    # Extract model name (first column)
                    model_name = line.split()[0]
                    # Remove tag if present
                    model_name = model_name.split(":")[0]
                    if model_name not in models:
                        models.append(model_name)

        except (subprocess.CalledProcessError, FileNotFoundError):
            questionary.print(
                "⚠️  Could not get Ollama models. Is Ollama installed?",
                style="fg:yellow",
            )
            return []
        else:
            return models  # noqa: TRY300

    def _test_configuration(self, provider: str, model: str) -> bool:
        """Test the configuration with a simple prompt."""
        # Normalize provider name for registry
        normalized_provider = (
            "github_copilot" if provider == "github-copilot" else provider
        )

        try:
            # Create LLM instance
            llm = self.registry.get_llm(
                provider_name=normalized_provider,
                model_alias=model,
                enhanced=True,
            )

            # Test with telemetry
            telemetry = TelemetryCallback(provider=normalized_provider, model=model)

            from langchain_core.messages import HumanMessage

            test_prompt = "Say 'Configuration test successful!' in 5 words or less."
            response = llm.invoke(
                [HumanMessage(content=test_prompt)],
                config={"callbacks": [telemetry]},
            )

            # Show response
            questionary.print(f"\n📝 Model response: {response.content}")

            # Show telemetry if available
            if telemetry.metrics.token_usage.total_tokens > 0:
                # Add context info if enhanced
                if isinstance(llm, EnhancedLLM):
                    telemetry.metrics.metadata["context_length"] = llm.context_length
                questionary.print(format_metrics(telemetry.metrics))

            questionary.print(
                "✅ Configuration test successful!", style="bold fg:green"
            )
        except AuthenticationError as e:
            questionary.print(f"❌ Authentication failed: {e}", style="bold fg:red")
            if e.suggestion:
                questionary.print(f"   💡 {e.suggestion}", style="italic")
            return False
        except Exception as e:
            error_msg = str(e).lower()

            # Check for quota exceeded
            if "quota" in error_msg and "exceeded" in error_msg:
                questionary.print(
                    f"⚠️  Quota exceeded for {provider}", style="bold fg:yellow"
                )
                questionary.print(
                    "   Your usage limit has been reached for this model.",
                    style="italic",
                )
                questionary.print(
                    "   💡 Configuration will still be saved, but you may need to:",
                    style="italic",
                )
                questionary.print(
                    "      - Wait for your quota to reset", style="italic"
                )
                questionary.print("      - Upgrade your plan", style="italic")
                questionary.print("      - Use a different model", style="italic")
                # Return True since the configuration is valid, just quota limited
                return True

            # Other errors
            questionary.print(f"❌ Test failed: {e}", style="bold fg:red")
            return False
        else:
            return True  # noqa: TRY300

    def _get_or_create_provider_config(self, provider: str) -> dict[str, Any]:
        """Get existing provider config or create default."""
        providers = self.current_config.get("providers", {})

        if provider in providers:
            existing_config = providers[provider]
            # For github_copilot, ensure auth_details are present
            if provider == "github_copilot" and "auth_details" not in existing_config:
                existing_config["auth_details"] = {
                    "client_id": "01ab8ac9400c4e429b23",
                    "device_code_url": "https://github.com/login/device/code",
                    "token_url": "https://github.com/login/oauth/access_token",
                    "scope": "read:user",
                }
            return existing_config

        # Default configurations
        defaults = {
            "openai": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "auth_strategy": "api_key",
            },
            "anthropic": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.anthropic.com/v1",
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
            "github-copilot": {  # Handle hyphenated version
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
            "google": {
                "llm_type": "google_genai",
                "auth_strategy": "api_key",
            },
            "ollama": {
                "llm_type": "ollama",
                "base_url": "http://localhost:11434",
                "auth_strategy": "none",
            },
        }

        result = defaults.get(
            provider,
            {
                "llm_type": "openai_compatible",
                "auth_strategy": "api_key",
            },
        )
        # Ensure we return a dict, not an object
        return result if isinstance(result, dict) else {}

    def _save_configuration(
        self, provider: str, model: str, local: bool = False
    ) -> None:
        """Save the configuration."""
        # Normalize provider name for backward compatibility
        # Always save as github_copilot (underscore) regardless of input
        if provider == "github-copilot":
            provider = "github_copilot"

        # Load target config
        target_path = config.get_config_path(local=local)
        target_config, _ = config.get_config_from_path(target_path)

        # Ensure structure exists
        if "providers" not in target_config:
            target_config["providers"] = {}

        # Add/update provider
        if provider not in target_config["providers"]:
            target_config["providers"][provider] = self._get_or_create_provider_config(
                provider
            )
            target_config["providers"][provider]["models"] = {}

        # Add model with api_model_name for proper mapping
        # For most providers, the model ID from models.dev is the API model name
        target_config["providers"][provider]["models"][model] = {
            "api_model_name": model
        }

        # Save
        config.save_config(target_config, local=local)

        scope = "local" if local else "global"
        questionary.print(
            f"✅ Configuration saved to {scope} config!",
            style="bold fg:green",
        )


def run_wizard(verbose: bool = False) -> None:
    """Entry point for the configuration wizard."""
    wizard = ConfigWizard(verbose=verbose)
    wizard.run()
