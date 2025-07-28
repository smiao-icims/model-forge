"""Models.dev API integration for ModelForge."""

import json
import time
from pathlib import Path
from typing import Any

import requests

from .exceptions import (
    InvalidInputError,
    JsonDecodeError,
    ModelNotFoundError,
    NetworkError,
    ProviderError,
)
from .logging_config import get_logger
from .retry import retry_on_error
from .validation import InputValidator

logger = get_logger(__name__)


class ModelsDevClient:
    """Client for interacting with models.dev API."""

    BASE_URL = "https://models.dev"
    CACHE_DIR = Path.home() / ".cache" / "model-forge" / "modelsdev"

    # Cache TTL in seconds
    CACHE_TTL = {
        "providers": 24 * 3600,  # 24 hours
        "models": 24 * 3600,  # 24 hours
        "model_info": 7 * 24 * 3600,  # 7 days
        "provider_config": 7 * 24 * 3600,  # 7 days
    }

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the models.dev client.

        Args:
            api_key: Optional API key for authenticated requests
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        # Ensure cache directory exists
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, endpoint: str, *args: str) -> Path:
        """Get cache file path for an endpoint."""
        filename = f"{endpoint}_{'_'.join(args)}.json" if args else f"{endpoint}.json"
        return self.CACHE_DIR / filename

    def _is_cache_valid(self, cache_path: Path, ttl: int) -> bool:
        """Check if cached data is still valid."""
        if not cache_path.exists():
            return False

        try:
            cache_time = cache_path.stat().st_mtime
            return time.time() - cache_time < ttl
        except OSError:
            return False

    def _load_from_cache(self, cache_path: Path) -> dict[str, Any] | None:
        """Load data from cache."""
        try:
            with cache_path.open() as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    return {"data": data}
                return {"data": data}
        except OSError:
            logger.warning("Failed to read cache file: %s", cache_path)
            return None
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in cache file %s: %s", cache_path, e)
            return None

    def _save_to_cache(self, cache_path: Path, data: dict[str, Any]) -> None:
        """Save data to cache."""
        try:
            with cache_path.open("w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning("Failed to write cache file %s: %s", cache_path, e)

    def _raise_content_type_error(self, content_type: str) -> None:
        """Raise error for invalid content type."""
        raise ProviderError(
            f"Expected JSON response, got {content_type}",
            context="models.dev API returned unexpected content type",
            suggestion="Check if the API endpoint is correct or try again later",
            error_code="INVALID_CONTENT_TYPE",
        )

    def _raise_provider_not_found_error(self, provider: str) -> None:
        """Raise error when provider is not found."""
        raise ProviderError(
            f"Provider '{provider}' not found in models.dev API",
            context="Available providers can be listed with 'modelforge models list'",
            suggestion="Check provider name spelling or refresh with --refresh",
            error_code="PROVIDER_NOT_FOUND",
        )

    def _raise_invalid_provider_structure_error(self, provider: str) -> None:
        """Raise error for invalid provider data structure."""
        raise ProviderError(
            f"Invalid provider data structure for '{provider}'",
            context="models.dev API returned malformed provider data",
            suggestion="This may be a temporary API issue, try again later",
            error_code="INVALID_PROVIDER_STRUCTURE",
        )

    def _raise_model_not_found_error(self, model: str, provider: str) -> None:
        """Raise error when model is not found for provider."""
        raise ModelNotFoundError(provider, model)

    def _raise_enhanced_provider_error(
        self, original_error: Exception, suggestions: str
    ) -> None:
        """Raise enhanced error with provider suggestions."""
        raise ProviderError(
            f"{original_error}",
            context=f"Available providers include: {suggestions}",
            suggestion="Use 'modelforge models list' to see all available providers",
            error_code="PROVIDER_SUGGESTION",
        ) from original_error

    def _raise_enhanced_model_error(
        self, original_error: Exception, suggestions: str
    ) -> None:
        """Raise enhanced error with model suggestions."""
        # Extract provider and model from original error if possible
        if isinstance(original_error, ModelNotFoundError):
            raise ModelNotFoundError(
                original_error.details["provider"],
                original_error.details["model"],
                suggestions.split(", "),
            ) from original_error
        # Fallback for other error types
        raise ModelNotFoundError("unknown", "unknown") from original_error

    def _parse_provider_data(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse provider data from models.dev API response."""
        providers = []
        for provider_key, provider_data in data.items():
            if not isinstance(provider_data, dict):
                continue

            provider_info = {
                "name": provider_key,
                "display_name": provider_data.get("name", provider_key.title()),
                "description": provider_data.get("doc", f"{provider_key.title()} AI"),
                "auth_types": ["api_key"],  # Default
                "base_urls": [provider_data.get("api", "")]
                if provider_data.get("api")
                else [],
            }

            # Determine auth type
            if provider_key == "ollama":
                provider_info["auth_types"] = ["none"]
            elif provider_key in ["github", "github_copilot", "github-copilot"]:
                provider_info["auth_types"] = ["device_flow"]
            elif "env" in provider_data:
                env_vars = provider_data["env"]
                if env_vars and isinstance(env_vars, list) and env_vars:
                    has_api_key = any("API_KEY" in str(env) for env in env_vars)
                    if has_api_key:
                        provider_info["auth_types"] = ["api_key"]

            providers.append(provider_info)
        return providers

    def _handle_network_error(self, cache_path: Path) -> list[dict[str, Any]]:
        """Handle network errors by using cached data if available."""
        try:
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached data due to network error")
                cached_result = cached_data["data"]
                if isinstance(cached_result, list):
                    return cached_result
        except Exception as e:
            logger.warning(
                "Failed to load cached data during network error fallback: %s", e
            )

        # Return empty list if no cached data available
        logger.warning("No cached data available, returning empty results")
        return []

    @retry_on_error(max_retries=3)
    def _fetch_providers(
        self, cache_path: Path, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch providers from API or cache."""
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["providers"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                data = cached_data["data"]
                return data if isinstance(data, list) else [data]

        # Fetch from API
        response = self.session.get(f"{self.BASE_URL}/api.json", timeout=30)
        response.raise_for_status()

        if not response.content.strip():
            logger.warning("Empty response from providers API")
            return []

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise JsonDecodeError(
                "Invalid JSON response from models.dev providers API"
            ) from e

        if not isinstance(data, dict):
            raise ProviderError(
                f"Expected JSON object from providers API, got {type(data).__name__}"
            )

        providers = self._parse_provider_data(data)
        self._save_to_cache(cache_path, {"data": providers})

        return providers

    def get_providers(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Get list of supported providers from models.dev."""
        cache_path = self._get_cache_path("providers")

        try:
            return self._fetch_providers(cache_path, force_refresh)
        except NetworkError:
            # Fallback to cached data on network error
            logger.info("Network error occurred, attempting to use cached data")
            return self._handle_network_error(cache_path)

    def _parse_model_data(
        self, data: dict[str, Any], provider_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Parse model data from models.dev API response."""
        models = []
        for provider_key, provider_data in data.items():
            if not isinstance(provider_data, dict) or "models" not in provider_data:
                continue

            provider_models = provider_data["models"]
            if not isinstance(provider_models, dict):
                continue

            for model_key, model_info in provider_models.items():
                # Filter by provider if specified
                if provider_filter and provider_key != provider_filter:
                    continue

                # Generate rich description from metadata
                description = self._generate_model_description(model_info)

                # Normalize model data
                normalized_model = {
                    "id": model_key,
                    "provider": provider_key,
                    "display_name": model_info.get("name", model_key),
                    "description": description,
                    "capabilities": self._extract_capabilities(model_info),
                    "context_length": model_info.get("limit", {}).get("context"),
                    "max_tokens": model_info.get("limit", {}).get("output"),
                    "pricing": self._extract_pricing(model_info),
                }
                models.append(normalized_model)
        return models

    def _generate_model_description(self, model_info: dict[str, Any]) -> str:
        """Generate a descriptive string from model metadata."""
        try:
            parts = []

            # Add model type/capabilities
            if model_info.get("reasoning"):
                parts.append("Reasoning model")
            elif model_info.get("attachment"):
                parts.append("Multimodal model")
            else:
                parts.append("Text model")

            # Add pricing info (per 1M tokens)
            cost = model_info.get("cost", {})
            if cost.get("input"):
                parts.append(f"${cost['input']}/1M input")

            # Add context length
            limit = model_info.get("limit", {})
            if limit.get("context"):
                context_k = limit["context"] // 1000
                parts.append(f"{context_k}K context")

            description = ", ".join(parts)

            # Fallback to model name if no meaningful description generated
            return str(
                model_info.get("name", "Language model")
                if not description or description == "Text model"
                else description
            )

        except Exception as e:
            logger.warning("Failed to generate model description: %s", e)
            return str(model_info.get("name", "Language model"))

    def _extract_capabilities(self, model_info: dict[str, Any]) -> list[str]:
        """Extract model capabilities from API response."""
        capabilities = []

        if model_info.get("reasoning"):
            capabilities.append("reasoning")
        if model_info.get("tool_call"):
            capabilities.append("function_calling")
        if model_info.get("attachment"):
            capabilities.append("multimodal")

        modalities = model_info.get("modalities", {})
        input_types = modalities.get("input", [])
        if "image" in input_types:
            capabilities.append("vision")
        if "audio" in input_types:
            capabilities.append("audio")
        if "video" in input_types:
            capabilities.append("video")

        return capabilities

    def _extract_pricing(self, model_info: dict[str, Any]) -> dict[str, Any]:
        """Extract pricing information from API response.

        Note: models.dev returns prices in dollars per 1M tokens.
        """
        cost = model_info.get("cost", {})
        return {
            "input_per_1m_tokens": cost.get("input"),
            "output_per_1m_tokens": cost.get("output"),
            "cache_read_per_1m_tokens": cost.get("cache_read"),
            "cache_write_per_1m_tokens": cost.get("cache_write"),
        }

    @retry_on_error(max_retries=3)
    def _fetch_models(
        self, cache_path: Path, provider: str | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch models from API or cache."""
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["models"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                data = cached_data["data"]
                return data if isinstance(data, list) else [data]

        # Fetch from API
        response = self.session.get(f"{self.BASE_URL}/api.json", timeout=30)
        response.raise_for_status()

        if not response.content.strip():
            logger.warning("Empty response from models API")
            return []

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise JsonDecodeError(
                "Invalid JSON response from models.dev models API"
            ) from e

        if not isinstance(data, dict):
            raise ProviderError(
                f"Expected JSON object from models API, got {type(data).__name__}"
            )

        models = self._parse_model_data(data, provider)
        self._save_to_cache(cache_path, {"data": models})

        return models

    def get_models(
        self, provider: str | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Get list of models from models.dev."""
        # Validate provider name if provided
        if provider:
            InputValidator.validate_provider_name(provider)

        # Normalize provider name if provided (replace underscores with hyphens)
        normalized_provider = provider.replace("_", "-") if provider else None
        cache_path = self._get_cache_path("models", normalized_provider or "all")

        try:
            return self._fetch_models(cache_path, normalized_provider, force_refresh)
        except NetworkError:
            # Fallback to cached data on network error
            logger.info("Network error occurred, attempting to use cached data")
            return self._handle_network_error(cache_path)

    @retry_on_error(max_retries=2)
    def _fetch_model_info(
        self, cache_path: Path, provider: str, model: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        """Fetch model info from models.dev API."""
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["model_info"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                return cached_data

        # Normalize provider name (replace underscores with hyphens)
        normalized_provider = provider.replace("_", "-")

        try:
            # Fetch from API
            response = self.session.get(f"{self.BASE_URL}/api.json", timeout=30)
            response.raise_for_status()

            # Check if response is JSON
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type.lower():
                self._raise_content_type_error(content_type)

            api_response = response.json()

            # Extract the specific model data
            if normalized_provider not in api_response:
                self._raise_provider_not_found_error(provider)

            provider_data = api_response[normalized_provider]
            if "models" not in provider_data or not isinstance(
                provider_data["models"], dict
            ):
                self._raise_invalid_provider_structure_error(provider)

            models = provider_data["models"]
            if model not in models:
                self._raise_model_not_found_error(model, provider)

            model_info = models[model]

            # Add provider and id fields if not present
            model_info["provider"] = normalized_provider
            model_info["id"] = model

            # Cache the response
            self._save_to_cache(cache_path, model_info)

        except requests.exceptions.JSONDecodeError as e:
            # Try to use cached data as fallback
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached model info due to JSON error")
                return cached_data
            raise JsonDecodeError(
                "Failed to parse model info from models.dev API"
            ) from e
        except NetworkError:
            # Try to use cached data as fallback
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached model info due to network error")
                return cached_data
            raise
        else:
            return model_info

    def get_model_info(
        self, provider: str, model: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        """Get detailed information about a specific model."""
        # Validate input parameters
        InputValidator.validate_provider_name(provider)
        InputValidator.validate_model_name(model)

        # Normalize provider name for cache path consistency
        normalized_provider = provider.replace("_", "-")
        cache_path = self._get_cache_path("model_info", normalized_provider, model)

        try:
            return self._fetch_model_info(cache_path, provider, model, force_refresh)
        except (ProviderError, ModelNotFoundError) as e:
            # Provide helpful suggestions for common errors
            if isinstance(e, ProviderError):
                try:
                    providers = self.get_providers(force_refresh=False)
                    provider_names = [p.get("name", "") for p in providers[:5]]
                    suggestions = ", ".join(filter(None, provider_names))
                    if suggestions:
                        self._raise_enhanced_provider_error(e, suggestions)
                except Exception:  # noqa: S110
                    # Ignore errors from get_providers() and re-raise original
                    pass
            elif isinstance(e, ModelNotFoundError):
                try:
                    models = self.get_models(
                        provider=normalized_provider, force_refresh=False
                    )
                    model_ids = [m.get("id", "") for m in models[:5]]
                    suggestions = ", ".join(filter(None, model_ids))
                    if suggestions:
                        self._raise_enhanced_model_error(e, suggestions)
                except Exception:  # noqa: S110
                    # Ignore errors from get_models() and re-raise original
                    pass
            raise

    @retry_on_error(max_retries=2)
    def _fetch_provider_config(
        self, cache_path: Path, provider: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        """Fetch provider config from API or cache."""
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["provider_config"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                return cached_data

        # Fetch from API
        url = f"{self.BASE_URL}/providers/{provider}/config"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        try:
            api_response = response.json()
        except requests.exceptions.JSONDecodeError as e:
            # Try to use cached data as fallback
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached provider config due to JSON error")
                return cached_data
            raise JsonDecodeError(
                f"Invalid JSON response from provider config API for '{provider}'"
            ) from e

        provider_config = (
            api_response if isinstance(api_response, dict) else {"config": api_response}
        )
        self._save_to_cache(cache_path, provider_config)

        return provider_config

    def get_provider_config(
        self, provider: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        """Get configuration template for a provider."""
        # Validate provider name
        InputValidator.validate_provider_name(provider)

        # Normalize provider name (replace underscores with hyphens)
        normalized_provider = provider.replace("_", "-")
        cache_path = self._get_cache_path("provider_config", normalized_provider)
        return self._fetch_provider_config(
            cache_path, normalized_provider, force_refresh
        )

    def clear_cache(self) -> None:
        """Clear all cached data."""
        for cache_file in self.CACHE_DIR.glob("*.json"):
            cache_file.unlink()
        logger.info("Cleared models.dev cache")

    def search_models(
        self,
        query: str,
        provider: str | None = None,
        capabilities: list[str] | None = None,
        max_price: float | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Search models based on criteria."""
        # Validate input parameters
        if not query or not query.strip():
            raise InvalidInputError("Search query cannot be empty")
        if provider:
            InputValidator.validate_provider_name(provider)
        if max_price is not None and max_price <= 0:
            raise InvalidInputError("Maximum price must be positive")

        models = self.get_models(provider=provider, force_refresh=force_refresh)

        results = []
        for model in models:
            # Text search in id, display_name and description
            model_text = (
                f"{model.get('id', '')} {model.get('display_name', '')} "
                f"{model.get('description', '')}".lower()
            )
            if query.lower() not in model_text:
                continue

            # Capabilities filter
            if capabilities:
                model_caps = set(model.get("capabilities", []))
                if not set(capabilities).issubset(model_caps):
                    continue

            # Price filter
            if max_price is not None:
                pricing = model.get("pricing", {})
                price = pricing.get("input_per_1m_tokens")
                if price is not None and price > max_price:
                    continue

            results.append(model)

        return results
