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
        self, provider_name: str | None = None, model_alias: str | None = None
    ) -> BaseChatModel | None:
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
        try:
            if not provider_name or not model_alias:
                current_model = config.get_current_model()
                if not current_model:
                    logger.error("No model selected and no provider/model specified")
                    raise ConfigurationError(
                        "No model selected. Use 'modelforge config use' or provide "
                        "provider and model."
                    )
                provider_name = current_model.get("provider")
                model_alias = current_model.get("model")

            provider_data = self._config.get("providers", {}).get(provider_name)
            if not provider_data:
                logger.error("Provider '%s' not found in configuration", provider_name)
                raise ProviderError(
                    f"Provider '{provider_name}' not found in configuration"
                )

            model_data = provider_data.get("models", {}).get(model_alias)
            if model_data is None:  # Can be an empty dict
                logger.error(
                    "Model '%s' not found for provider '%s'", model_alias, provider_name
                )
                raise ModelNotFoundError(
                    f"Model '{model_alias}' not found for provider '{provider_name}'"
                )

            llm_type = provider_data.get("llm_type")
            auth_strategy_name = provider_data.get("auth_strategy")

            logger.info(
                "Creating LLM instance for provider: %s, model: %s",
                provider_name,
                model_alias,
            )

            if llm_type == "ollama":
                return self._create_ollama_llm(model_alias, provider_data)

            if llm_type == "github_copilot":
                return self._create_github_copilot_llm(
                    provider_name, model_alias, provider_data, 
                    model_data, auth_strategy_name
                )

            if llm_type == "openai_compatible":
                return self._create_openai_compatible_llm(
                    provider_name, model_alias, provider_data, model_data
                )

            if llm_type == "google_genai":
                return self._create_google_genai_llm(
                    provider_name, model_alias, model_data
                )

            logger.error(
                "Unsupported llm_type '%s' for provider '%s'", llm_type, provider_name
            )
            raise ProviderError(
                f"Unsupported llm_type '{llm_type}' for provider '{provider_name}'"
            )

        except Exception:
            logger.exception(
                "Error creating LLM instance for %s/%s",
                provider_name,
                model_alias,
            )
            raise

    def _create_openai_compatible_llm(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
    ) -> ChatOpenAI:
        """
        Create a ChatOpenAI instance for OpenAI-compatible providers.

        Args:
            provider_name: The provider name.
            model_alias: The model alias.
            provider_data: Provider configuration data.
            model_data: Model configuration data.

        Returns:
            A configured ChatOpenAI instance.

        Raises:
            ProviderError: If credentials cannot be retrieved or are invalid.
        """
        credentials = auth.get_credentials(
            provider_name, model_alias, verbose=self.verbose
        )
        if not credentials:
            logger.error(
                "Could not retrieve credentials for provider: %s", provider_name
            )
            raise ProviderError(
                f"Could not retrieve credentials for provider '{provider_name}'"
            )

        api_key = credentials.get("access_token") or credentials.get("api_key")
        if not api_key:
            logger.error("Could not find token or key for provider: %s", provider_name)
            raise ProviderError(f"Could not find token or key for '{provider_name}'")

        # Debug information (only if verbose)
        actual_model_name = model_data.get("api_model_name", model_alias)
        base_url = provider_data.get("base_url")
        auth_strategy_name = provider_data.get("auth_strategy")

        if self.verbose:
            logger.debug("Creating ChatOpenAI instance:")
            logger.debug("   Provider: %s", provider_name)
            logger.debug("   Model alias: %s", model_alias)
            logger.debug("   Actual model name: %s", actual_model_name)
            logger.debug("   Base URL: %s", base_url)
            logger.debug(
                "   API key/token: %s",
                "***" + api_key[-10:] if len(api_key) > 10 else "***",
            )
            logger.debug("   Auth strategy: %s", auth_strategy_name)

        return ChatOpenAI(
            model_name=actual_model_name, api_key=api_key, base_url=base_url
        )

    def _create_ollama_llm(
        self, model_alias: str, provider_data: dict[str, Any]
    ) -> ChatOllama:
        """Create ChatOllama instance."""
        return ChatOllama(
            model=model_alias, base_url=provider_data.get("base_url")
        )

    def _create_github_copilot_llm(
        self,
        provider_name: str,
        model_alias: str,
        provider_data: dict[str, Any],
        model_data: dict[str, Any],
        auth_strategy_name: str | None,
    ) -> BaseChatModel:
        """Create GitHub Copilot LLM instance."""
        # Use dedicated ChatGitHubCopilot if available
        if not GITHUB_COPILOT_AVAILABLE:
            logger.warning(
                "langchain-github-copilot not installed, falling back to "
                "openai_compatible"
            )
            return self._create_openai_compatible_llm(
                provider_name, model_alias, provider_data, model_data
            )

        # Use dedicated ChatGitHubCopilot
        credentials = auth.get_credentials(
            provider_name, model_alias, verbose=self.verbose
        )
        if not credentials:
            logger.error(
                "Could not retrieve credentials for provider: %s", provider_name
            )
            raise ProviderError(
                f"Could not retrieve credentials for provider '{provider_name}'"
            )

        access_token = credentials.get("access_token")
        if not access_token:
            logger.error(
                "Could not find access token for provider: %s", provider_name
            )
            raise ProviderError(
                f"Could not find access token for '{provider_name}'"
            )

        # Debug information (only if verbose)
        actual_model_name = model_data.get("api_model_name", model_alias)
        if self.verbose:
            logger.debug("Creating ChatGitHubCopilot instance:")
            logger.debug("   Provider: %s", provider_name)
            logger.debug("   Model alias: %s", model_alias)
            logger.debug("   Actual model name: %s", actual_model_name)
            logger.debug(
                "   Access token: %s",
                "***" + access_token[-10:] if len(access_token) > 10 else "***",
            )
            logger.debug("   Auth strategy: %s", auth_strategy_name)

        # Set the GitHub token as environment variable for ChatGitHubCopilot
        os.environ["GITHUB_TOKEN"] = access_token

        return ChatGitHubCopilot(model=actual_model_name)

    def _create_google_genai_llm(
        self, provider_name: str, model_alias: str, model_data: dict[str, Any]
    ) -> ChatGoogleGenerativeAI:
        """Create Google GenAI LLM instance."""
        credentials = auth.get_credentials(
            provider_name, model_alias, verbose=self.verbose
        )
        if not credentials:
            logger.error(
                "Could not retrieve credentials for provider: %s", provider_name
            )
            raise ProviderError(
                f"Could not retrieve credentials for provider '{provider_name}'"
            )

        api_key = credentials.get("api_key")
        if not api_key:
            logger.error(
                "Could not find API key for provider: %s", provider_name
            )
            raise ProviderError(f"Could not find API key for '{provider_name}'")

        return ChatGoogleGenerativeAI(
            model=model_data.get("api_model_name", model_alias),
            google_api_key=api_key,
        )
