# Standard library imports
import os
import warnings
from typing import Any

from langchain_community.chat_models import ChatOllama

# Third-party imports
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Try to import ChatGitHubCopilot, but make it optional
try:
    from langchain_github_copilot import ChatGitHubCopilot

    GITHUB_COPILOT_AVAILABLE = True
except ImportError:
    GITHUB_COPILOT_AVAILABLE = False

# Local imports
from . import auth, config
from .enhanced_llm import EnhancedLLM
from .exceptions import (
    ConfigurationError,
    InvalidApiKeyError,
    ModelNotFoundError,
    ProviderError,
    ProviderNotAvailableError,
)
from .logging_config import get_logger
from .modelsdev import ModelsDevClient
from .validation import InputValidator

logger = get_logger(__name__)


class ModelForgeRegistry:
    """
    Main registry for managing and instantiating LLM models.
    This class serves as the primary entry point for accessing configured
    language models across different providers.
    """

    def __init__(self, verbose: bool = False) -> None:
        """
        Initialize the ModelForgeRegistry.
        Args:
            verbose: Enable verbose debug logging.
        """
        self.verbose = verbose
        self._config, _ = config.get_config()
        self._models_client = ModelsDevClient()
        logger.debug("ModelForgeRegistry initialized with verbose=%s", verbose)

    def get_llm(
        self,
        provider_name: str | None = None,
        model_alias: str | None = None,
        callbacks: list[Any] | None = None,
        enhanced: bool | None = None,
    ) -> BaseChatModel:
        """
        Get a fully authenticated and configured LLM instance.
        Args:
            provider_name: The provider name. If None, uses current selection.
            model_alias: The model alias. If None, uses current selection.
            callbacks: Optional list of callback handlers for telemetry.
            enhanced: If True, returns EnhancedLLM with metadata.
                     If False, returns raw LangChain model.
                     If None (default), checks MODELFORGE_ENHANCED env var,
                     defaults to False. Will default to True in v2.3.0.
        Returns:
            A LangChain-compatible LLM instance ready for use.
        Raises:
            ConfigurationError: If no model is selected or configuration is invalid.
            ProviderError: If the provider is not supported or credentials are missing.
            ModelNotFoundError: If the specified model is not found.
        """
        # Validate inputs if provided
        if provider_name:
            provider_name = InputValidator.validate_provider_name(provider_name)
        if model_alias:
            model_alias = InputValidator.validate_model_name(model_alias)

        # Handle enhanced parameter with gradual rollout
        if enhanced is None:
            env_value = os.getenv("MODELFORGE_ENHANCED", "false")
            enhanced = (env_value or "false").lower() == "true"
            if not enhanced:
                warnings.warn(
                    "Starting in model-forge v2.3.0, get_llm() will return "
                    "EnhancedLLM by default. Set enhanced=False to keep current "
                    "behavior or set MODELFORGE_ENHANCED=true to opt-in early.",
                    FutureWarning,
                    stacklevel=2,
                )

        # Get model configuration
        provider_name, model_alias, provider_data, model_data = self._get_model_config(
            provider_name, model_alias
        )

        llm_type = provider_data.get("llm_type")
        if not llm_type:
            raise ConfigurationError(
                f"Provider '{provider_name}' has no 'llm_type' configured",
                context="Missing required configuration field",
                suggestion="Check provider configuration in config file",
                error_code="MISSING_LLM_TYPE",
            )

        logger.info(
            "Creating LLM instance for provider: %s, model: %s, enhanced: %s",
            provider_name,
            model_alias,
            enhanced,
        )

        # Create base LLM
        base_llm = self._create_base_llm(
            llm_type, provider_name, model_alias, provider_data, model_data, callbacks
        )

        # Return raw LLM if not enhanced
        if not enhanced:
            return base_llm

        # Fetch metadata and wrap in EnhancedLLM
        metadata = self._fetch_model_metadata(provider_name, model_alias)
        return EnhancedLLM(
            wrapped_llm=base_llm,
            model_metadata=metadata,
            provider=provider_name,
            model_alias=model_alias,
        )

    def _create_base_llm(
        self,
        llm_type: str,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> BaseChatModel:
        """Create base LLM instance based on type."""
        # Direct instantiation based on llm_type
        if llm_type == "openai_compatible":
            return self._create_openai_compatible(
                provider_name, model_alias, provider_data, model_data, callbacks
            )
        if llm_type == "ollama":
            return self._create_ollama(
                provider_name, model_alias, provider_data, callbacks
            )
        if llm_type == "github_copilot":
            return self._create_github_copilot(
                provider_name, model_alias, provider_data, model_data, callbacks
            )
        if llm_type == "google_genai":
            return self._create_google_genai(
                provider_name, model_alias, provider_data, model_data, callbacks
            )
        raise ProviderError(
            f"Unsupported llm_type '{llm_type}'",
            context=f"Provider '{provider_name}' uses an unknown LLM type",
            suggestion=(
                "Supported: ollama, google_genai, openai_compatible, github_copilot"
            ),
            error_code="UNSUPPORTED_LLM_TYPE",
        )

    def _get_model_config(
        self, provider_name: str | None, model_alias: str | None
    ) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
        """
        Retrieves and validates provider and model configuration.
        If provider or model are not specified, it falls back to the current selection.
        """
        logger.debug(
            "Attempting to get model config for provider: '%s' and model: '%s'",
            provider_name,
            model_alias,
        )

        if not provider_name or not model_alias:
            logger.debug(
                "Provider or model not specified, falling back to current model."
            )
            current_model = config.get_current_model()
            if not current_model:
                raise ConfigurationError(
                    "No model selected",
                    context="No provider or model specified and no default configured",
                    suggestion="Use 'modelforge config use' to set a default model",
                    error_code="NO_MODEL_SELECTED",
                )
            provider_name = current_model.get("provider")
            model_alias = current_model.get("model")
            logger.debug(
                "Using current model: provider='%s', model='%s'",
                provider_name,
                model_alias,
            )

        if not provider_name or not model_alias:
            raise ConfigurationError(
                "Could not determine provider and model",
                context="Configuration may be corrupted",
                suggestion="Check your configuration file or reconfigure",
                error_code="INVALID_CONFIG",
            )

        provider_data = self._config.get("providers", {}).get(provider_name)
        if not provider_data:
            available_providers = list(self._config.get("providers", {}).keys())
            raise ProviderNotAvailableError(
                provider_name,
                (
                    f"Provider not found in configuration. "
                    f"Available: {', '.join(available_providers)}"
                ),
            )

        model_data = provider_data.get("models", {}).get(model_alias)
        if model_data is None:
            available_models = list(provider_data.get("models", {}).keys())
            raise ModelNotFoundError(
                provider_name,
                model_alias,
                available_models,
            )

        logger.debug(
            "Successfully retrieved config for provider='%s' and model='%s'",
            provider_name,
            model_alias,
        )
        return provider_name, model_alias, provider_data, model_data

    def _create_openai_compatible(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> ChatOpenAI:
        """Create a ChatOpenAI instance for OpenAI-compatible providers."""
        credentials = auth.get_credentials(
            provider_name, model_alias, provider_data, verbose=self.verbose
        )
        if not credentials:
            raise InvalidApiKeyError(provider_name)

        api_key = credentials.get("access_token") or credentials.get("api_key")
        if not api_key:
            raise InvalidApiKeyError(provider_name)

        actual_model_name = model_data.get("api_model_name", model_alias)
        base_url = provider_data.get("base_url")

        if self.verbose:
            logger.debug("Creating ChatOpenAI instance with:")
            logger.debug("   Provider: %s", provider_name)
            logger.debug("   Model alias: %s", model_alias)
            logger.debug("   Actual model name: %s", actual_model_name)
            logger.debug("   Base URL: %s", base_url)

        return ChatOpenAI(
            model=actual_model_name,
            api_key=api_key,
            base_url=base_url,
            callbacks=callbacks,
        )

    def _create_ollama(
        self,
        provider_name: str,  # noqa: ARG002
        model_alias: str,
        provider_data: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> ChatOllama:
        """Create ChatOllama instance."""
        base_url = provider_data.get("base_url", os.getenv("OLLAMA_HOST"))
        if not base_url:
            raise ConfigurationError(
                "Ollama base URL not configured",
                context=(
                    "Neither 'base_url' in config nor OLLAMA_HOST "
                    "environment variable is set"
                ),
                suggestion=(
                    "Set OLLAMA_HOST environment variable or add "
                    "'base_url' to provider config"
                ),
                error_code="OLLAMA_URL_MISSING",
            )
        return ChatOllama(model=model_alias, base_url=base_url, callbacks=callbacks)

    def _create_github_copilot(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> BaseChatModel:
        """Create a ChatGitHubCopilot instance."""
        if not GITHUB_COPILOT_AVAILABLE:
            raise ProviderNotAvailableError(
                provider_name,
                "GitHub Copilot libraries not installed",
            )

        credentials = auth.get_credentials(
            provider_name, model_alias, provider_data, verbose=self.verbose
        )
        if not credentials or "access_token" not in credentials:
            raise InvalidApiKeyError(provider_name)

        copilot_token = credentials["access_token"]
        actual_model_name = model_data.get("api_model_name", model_alias)

        if self.verbose:
            logger.debug("Creating ChatGitHubCopilot instance with:")
            logger.debug("   Provider: %s", provider_name)
            logger.debug("   Model alias: %s", model_alias)
            logger.debug("   Actual model name: %s", actual_model_name)

        return ChatGitHubCopilot(
            api_key=copilot_token, model=actual_model_name, callbacks=callbacks
        )

    def _create_google_genai(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
        callbacks: list[Any] | None = None,
    ) -> ChatGoogleGenerativeAI:
        """Create ChatGoogleGenerativeAI instance."""
        credentials = auth.get_credentials(
            provider_name, model_alias, provider_data, verbose=self.verbose
        )
        if not credentials or "api_key" not in credentials:
            raise InvalidApiKeyError(provider_name)

        api_key = credentials["api_key"]
        actual_model_name = model_data.get("api_model_name", model_alias)

        return ChatGoogleGenerativeAI(
            model=actual_model_name, google_api_key=api_key, callbacks=callbacks
        )

    def _fetch_model_metadata(self, provider: str, model: str) -> dict[str, Any]:
        """Fetch and cache model metadata from models.dev."""
        try:
            client = ModelsDevClient()
            model_info = client.get_model_info(provider, model)

            # Transform to our metadata format
            return {
                "context_length": model_info.get("limit", {}).get("context", 0),
                "max_tokens": model_info.get("limit", {}).get("output", 0),
                "capabilities": client._extract_capabilities(model_info),
                "pricing": client._extract_pricing(model_info),
                "knowledge_cutoff": model_info.get("knowledge_cutoff"),
                "raw_info": model_info,  # Keep raw data for model_info property
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {provider}/{model}: {e}")
            # Return safe defaults
            return {
                "context_length": 0,
                "max_tokens": 0,
                "capabilities": [],
                "pricing": {},
                "raw_info": {},
            }

    # ===== Discovery and Listing APIs =====

    def get_available_providers(
        self, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get list of all available providers from models.dev.

        Args:
            force_refresh: Force refresh from models.dev API

        Returns:
            List of provider dictionaries with keys:
            - name: Provider identifier (e.g., "openai", "anthropic")
            - display_name: Human-readable name (e.g., "OpenAI", "Anthropic")
            - description: Provider description or documentation URL
            - auth_types: List of supported authentication types
            - base_urls: List of API base URLs

        Example:
            >>> registry = ModelForgeRegistry()
            >>> providers = registry.get_available_providers()
            >>> print(f"Found {len(providers)} providers")
            >>> for provider in providers[:3]:
            ...     print(f"- {provider['display_name']}: {provider['description']}")
        """
        return self._models_client.get_providers(force_refresh=force_refresh)

    def get_available_models(
        self, provider: str | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """
        Get list of available models from models.dev.

        Args:
            provider: Filter by specific provider (e.g., "openai", "anthropic")
            force_refresh: Force refresh from models.dev API

        Returns:
            List of model dictionaries with keys:
            - id: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
            - provider: Provider name
            - display_name: Human-readable model name
            - description: Model description
            - capabilities: List of model capabilities
            - context_length: Maximum context window in tokens
            - max_tokens: Maximum output tokens
            - pricing: Cost per 1M tokens (input/output)

        Example:
            >>> registry = ModelForgeRegistry()
            >>> # Get all models
            >>> all_models = registry.get_available_models()
            >>> # Get OpenAI models only
            >>> openai_models = registry.get_available_models(provider="openai")
            >>> print(f"OpenAI has {len(openai_models)} models")
        """
        return self._models_client.get_models(
            provider=provider, force_refresh=force_refresh
        )

    def get_configured_providers(self) -> dict[str, dict[str, Any]]:
        """
        Get list of providers configured by the user.

        Returns:
            Dictionary mapping provider names to their configuration:
            - Provider name as key
            - Configuration dict as value containing:
              - llm_type: Type of LLM implementation
              - base_url: API base URL (if applicable)
              - auth_strategy: Authentication method
              - models: Dict of configured model aliases

        Example:
            >>> registry = ModelForgeRegistry()
            >>> configured = registry.get_configured_providers()
            >>> for provider, config in configured.items():
            ...     models = list(config.get('models', {}).keys())
            ...     print(f"{provider}: {len(models)} models configured")
        """
        # Refresh config in case it changed
        self._config, _ = config.get_config()
        return self._config.get("providers", {})

    def get_configured_models(
        self, provider: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        Get list of models configured by the user.

        Args:
            provider: Filter by specific provider name

        Returns:
            Dictionary mapping model aliases to their configuration.
            If provider is specified, returns models for that provider only.
            If provider is None, returns all configured models across providers.

        Example:
            >>> registry = ModelForgeRegistry()
            >>> # Get all configured models
            >>> all_models = registry.get_configured_models()
            >>> # Get models for specific provider
            >>> openai_models = registry.get_configured_models("openai")
            >>> for alias, config in openai_models.items():
            ...     api_name = config.get('api_model_name', alias)
            ...     print(f"Alias: {alias} -> API: {api_name}")
        """
        configured_providers = self.get_configured_providers()

        if provider:
            # Validate and normalize provider name
            provider = InputValidator.validate_provider_name(provider)
            if provider not in configured_providers:
                return {}
            return configured_providers[provider].get("models", {})

        # Return all models from all providers
        all_models = {}
        for provider_name, provider_config in configured_providers.items():
            models = provider_config.get("models", {})
            for model_alias, model_config in models.items():
                # Prefix with provider to avoid conflicts
                key = f"{provider_name}/{model_alias}"
                all_models[key] = {
                    **model_config,
                    "provider": provider_name,
                    "alias": model_alias,
                }
        return all_models

    def is_provider_configured(self, provider: str) -> bool:
        """
        Check if a provider is configured by the user.

        Args:
            provider: Provider name to check

        Returns:
            True if provider is configured, False otherwise

        Example:
            >>> registry = ModelForgeRegistry()
            >>> if registry.is_provider_configured("openai"):
            ...     print("OpenAI is configured")
        """
        provider = InputValidator.validate_provider_name(provider)
        configured_providers = self.get_configured_providers()
        return provider in configured_providers

    def is_model_configured(self, provider: str, model_alias: str) -> bool:
        """
        Check if a specific model is configured by the user.

        Args:
            provider: Provider name
            model_alias: Model alias to check

        Returns:
            True if model is configured, False otherwise

        Example:
            >>> registry = ModelForgeRegistry()
            >>> if registry.is_model_configured("openai", "gpt-4"):
            ...     print("GPT-4 is configured")
        """
        provider = InputValidator.validate_provider_name(provider)
        model_alias = InputValidator.validate_model_name(model_alias)

        configured_models = self.get_configured_models(provider)
        return model_alias in configured_models
