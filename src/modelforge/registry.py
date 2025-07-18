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
from .exceptions import ConfigurationError, ModelNotFoundError, ProviderError
from .logging_config import get_logger


def _raise_provider_error(message: str) -> None:
    """Raise a ProviderError with the given message."""
    raise ProviderError(message)


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
                msg = (
                    "No model selected. Use 'modelforge config use' "
                    "or provide provider and model."
                )
                raise ConfigurationError(msg)
            provider_name = current_model.get("provider")
            model_alias = current_model.get("model")
            logger.debug(
                "Using current model: provider='%s', model='%s'",
                provider_name,
                model_alias,
            )

        if not provider_name or not model_alias:
            msg = "Could not determine provider and model to use."
            raise ConfigurationError(msg)

        provider_data = self._config.get("providers", {}).get(provider_name)
        if not provider_data:
            msg = f"Provider '{provider_name}' not found in configuration"
            raise ProviderError(msg)

        model_data = provider_data.get("models", {}).get(model_alias)
        if model_data is None:
            msg = f"Model '{model_alias}' not found for provider '{provider_name}'"
            raise ModelNotFoundError(msg)

        logger.debug(
            "Successfully retrieved config for provider='%s' and model='%s'",
            provider_name,
            model_alias,
        )
        return provider_name, model_alias, provider_data, model_data

    def get_llm(
        self, provider_name: str | None = None, model_alias: str | None = None
    ) -> BaseChatModel:
        """
        Get a fully authenticated and configured LLM instance.
        Args:
            provider_name: The provider name. If None, uses current selection.
            model_alias: The model alias. If None, uses current selection.
        Returns:
            A LangChain-compatible LLM instance ready for use.
        Raises:
            ConfigurationError: If no model is selected or configuration is invalid.
            ProviderError: If the provider is not supported or credentials are missing.
            ModelNotFoundError: If the specified model is not found.
        """
        resolved_provider = provider_name
        resolved_model = model_alias
        try:
            (
                resolved_provider,
                resolved_model,
                provider_data,
                model_data,
            ) = self._get_model_config(resolved_provider, resolved_model)

            llm_type = provider_data.get("llm_type")
            if not llm_type:
                _raise_provider_error(
                    f"Provider '{resolved_provider}' has no 'llm_type' configured."
                )

            logger.info(
                "Creating LLM instance for provider: %s, model: %s",
                resolved_provider,
                resolved_model,
            )

            # Factory mapping for LLM creation
            creator_map = {
                "ollama": self._create_ollama_llm,
                "google_genai": self._create_google_genai_llm,
                "openai_compatible": self._create_openai_compatible_llm,
                "github_copilot": self._create_github_copilot_llm,
            }

            creator = creator_map.get(llm_type)
            if not creator:
                _raise_provider_error(
                    f"Unsupported llm_type '{llm_type}' for provider "
                    f"'{resolved_provider}'"
                )

            return creator(resolved_provider, resolved_model, provider_data, model_data)

        except (ConfigurationError, ProviderError, ModelNotFoundError):
            logger.exception("Failed to create LLM")
            raise
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while creating LLM instance for %s/%s",
                resolved_provider,
                resolved_model,
            )
            msg = "An unexpected error occurred during LLM creation."
            raise ProviderError(msg) from e

    def _create_openai_compatible_llm(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
    ) -> ChatOpenAI:
        """
        Create a ChatOpenAI instance for OpenAI-compatible providers.
        """
        credentials = auth.get_credentials(
            provider_name, model_alias, provider_data, verbose=self.verbose
        )
        if not credentials:
            msg = f"Could not retrieve credentials for provider: {provider_name}"
            raise ProviderError(msg)

        api_key = credentials.get("access_token") or credentials.get("api_key")
        if not api_key:
            msg = f"Could not find token or key for provider: {provider_name}"
            raise ProviderError(msg)

        actual_model_name = model_data.get("api_model_name", model_alias)
        base_url = provider_data.get("base_url")

        if self.verbose:
            logger.debug("Creating ChatOpenAI instance with:")
            logger.debug("   Provider: %s", provider_name)
            logger.debug("   Model alias: %s", model_alias)
            logger.debug("   Actual model name: %s", actual_model_name)
            logger.debug("   Base URL: %s", base_url)

        return ChatOpenAI(
            model_name=actual_model_name, api_key=api_key, base_url=base_url
        )

    def _create_ollama_llm(
        self,
        provider_name: str,  # noqa: ARG002
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],  # noqa: ARG002
    ) -> ChatOllama:
        """Create ChatOllama instance."""
        base_url = provider_data.get("base_url", os.getenv("OLLAMA_HOST"))
        if not base_url:
            msg = (
                "Ollama 'base_url' not set in config and "
                "OLLAMA_HOST env var is not set."
            )
            raise ConfigurationError(msg)
        return ChatOllama(model=model_alias, base_url=base_url)

    def _create_github_copilot_llm(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
    ) -> BaseChatModel:
        """Create a ChatGitHubCopilot instance."""
        if not GITHUB_COPILOT_AVAILABLE:
            msg = (
                "GitHub Copilot libraries not installed. "
                "Please run 'poetry install --extras github-copilot'"
            )
            raise ProviderError(msg)

        credentials = auth.get_credentials(
            provider_name, model_alias, provider_data, verbose=self.verbose
        )
        if not credentials or "access_token" not in credentials:
            msg = f"Could not get valid credentials for {provider_name}"
            raise ProviderError(msg)

        copilot_token = credentials["access_token"]
        actual_model_name = model_data.get("api_model_name", model_alias)

        if self.verbose:
            logger.debug("Creating ChatGitHubCopilot instance with:")
            logger.debug("   Provider: %s", provider_name)
            logger.debug("   Model alias: %s", model_alias)
            logger.debug("   Actual model name: %s", actual_model_name)

        return ChatGitHubCopilot(api_key=copilot_token, model=actual_model_name)  # type: ignore

    def _create_google_genai_llm(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
    ) -> ChatGoogleGenerativeAI:
        """Create ChatGoogleGenerativeAI instance."""
        credentials = auth.get_credentials(
            provider_name, model_alias, provider_data, verbose=self.verbose
        )
        if not credentials or "api_key" not in credentials:
            msg = f"API key not found for {provider_name}"
            raise ProviderError(msg)

        api_key = credentials["api_key"]
        actual_model_name = model_data.get("api_model_name", model_alias)

        return ChatGoogleGenerativeAI(model=actual_model_name, google_api_key=api_key)
