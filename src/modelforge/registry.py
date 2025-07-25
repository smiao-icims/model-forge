# Standard library imports
import os
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
from .exceptions import (
    ConfigurationError,
    InvalidApiKeyError,
    ModelNotFoundError,
    ProviderError,
    ProviderNotAvailableError,
)
from .logging_config import get_logger
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
        logger.debug("ModelForgeRegistry initialized with verbose=%s", verbose)

    def get_llm(
        self,
        provider_name: str | None = None,
        model_alias: str | None = None,
        callbacks: list[Any] | None = None,
    ) -> BaseChatModel:
        """
        Get a fully authenticated and configured LLM instance.
        Args:
            provider_name: The provider name. If None, uses current selection.
            model_alias: The model alias. If None, uses current selection.
            callbacks: Optional list of callback handlers for telemetry.
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
            "Creating LLM instance for provider: %s, model: %s",
            provider_name,
            model_alias,
        )

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
