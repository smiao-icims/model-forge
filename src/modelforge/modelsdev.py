"""Models.dev API integration for ModelForge."""

import json
import time
from pathlib import Path
from typing import Any

import requests

from .logging_config import get_logger

logger = get_logger(__name__)


class ModelsDevClient:
    """Client for interacting with models.dev API."""

    BASE_URL = "https://models.dev/api/v1"
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

    def get_providers(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Get list of supported providers from models.dev.

        Args:
            force_refresh: Force refresh from API even if cache is valid

        Returns:
            List of provider information dictionaries
        """
        cache_path = self._get_cache_path("providers")

        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["providers"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                data = cached_data["data"]
                if isinstance(data, list):
                    return data
                return [data]

        try:
            response = self.session.get(f"{self.BASE_URL}/providers")
            response.raise_for_status()
            providers_data = response.json()
            providers: list[dict[str, Any]] = (
                [providers_data]
                if isinstance(providers_data, dict)
                else providers_data
                if isinstance(providers_data, list)
                else [providers_data]
            )
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error while fetching providers")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached providers data")
                return cached_data["data"]
            raise
        except requests.exceptions.HTTPError:
            logger.exception("HTTP error while fetching providers")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached providers data")
                return cached_data["data"]
            raise
        except requests.exceptions.Timeout:
            logger.exception("Timeout while fetching providers")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached providers data")
                return cached_data["data"]
            raise
        else:
            self._save_to_cache(cache_path, {"data": providers})
            return providers

    def get_models(
        self, provider: str | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Get list of models from models.dev.

        Args:
            provider: Optional provider filter
            force_refresh: Force refresh from API even if cache is valid

        Returns:
            List of model information dictionaries
        """
        cache_path = self._get_cache_path("models", provider or "all")

        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["models"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                data = cached_data["data"]
                if isinstance(data, list):
                    return data
                return [data]

        try:
            url = f"{self.BASE_URL}/models"
            params = {}
            if provider:
                params["provider"] = provider

            response = self.session.get(url, params=params)
            response.raise_for_status()
            models_data = response.json()
            models: list[dict[str, Any]] = (
                models_data if isinstance(models_data, list) else [models_data]
            )
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error while fetching models")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached models data")
                return cached_data["data"]
            raise
        except requests.exceptions.HTTPError:
            logger.exception("HTTP error while fetching models")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached models data")
                return cached_data["data"]
            raise
        except requests.exceptions.Timeout:
            logger.exception("Timeout while fetching models")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict) and "data" in cached_data:
                logger.info("Using stale cached models data")
                return cached_data["data"]
            raise
        else:
            self._save_to_cache(cache_path, {"data": models})
            return models

    def get_model_info(
        self, provider: str, model: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        """Get detailed information about a specific model.

        Args:
            provider: Provider name
            model: Model identifier
            force_refresh: Force refresh from API even if cache is valid

        Returns:
            Model information dictionary
        """
        cache_path = self._get_cache_path("model_info", provider, model)

        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["model_info"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                return cached_data

        try:
            url = f"{self.BASE_URL}/models/{provider}/{model}"
            response = self.session.get(url)
            response.raise_for_status()
            model_info = response.json()
            if not isinstance(model_info, dict):
                model_info = {"model": model_info}
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error while fetching model info")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached model info")
                return cached_data
            raise
        except requests.exceptions.HTTPError:
            logger.exception("HTTP error while fetching model info")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached model info")
                return cached_data
            raise
        except requests.exceptions.Timeout:
            logger.exception("Timeout while fetching model info")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached model info")
                return cached_data
            raise
        else:
            self._save_to_cache(cache_path, model_info)
            return model_info

    def get_provider_config(
        self, provider: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        """Get configuration template for a provider.

        Args:
            provider: Provider name
            force_refresh: Force refresh from API even if cache is valid

        Returns:
            Provider configuration template
        """
        cache_path = self._get_cache_path("provider_config", provider)

        if not force_refresh and self._is_cache_valid(
            cache_path, self.CACHE_TTL["provider_config"]
        ):
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                return cached_data

        try:
            url = f"{self.BASE_URL}/providers/{provider}/config"
            response = self.session.get(url)
            response.raise_for_status()
            provider_config = response.json()
            if not isinstance(provider_config, dict):
                provider_config = {"config": provider_config}
            return provider_config
        except requests.exceptions.ConnectionError:
            logger.exception("Connection error while fetching provider config")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached provider config")
                return cached_data
            raise
        except requests.exceptions.HTTPError:
            logger.exception("HTTP error while fetching provider config")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached provider config")
                return cached_data
            raise
        except requests.exceptions.Timeout:
            logger.exception("Timeout while fetching provider config")
            cached_data = self._load_from_cache(cache_path)
            if cached_data and isinstance(cached_data, dict):
                logger.info("Using stale cached provider config")
                return cached_data
            raise
        else:
            self._save_to_cache(cache_path, provider_config)
            return provider_config

    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            for cache_file in self.CACHE_DIR.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared models.dev cache")
        except OSError:
            logger.exception("Failed to clear cache")

    def search_models(
        self,
        query: str,
        provider: str | None = None,
        capabilities: list[str] | None = None,
        max_price: float | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Search models based on criteria.

        Args:
            query: Search query string
            provider: Optional provider filter
            capabilities: Optional list of required capabilities
            max_price: Optional maximum price filter
            force_refresh: Force refresh from API

        Returns:
            List of matching models
        """
        models = self.get_models(provider=provider, force_refresh=force_refresh)

        results = []
        for model in models:
            # Text search in name and description
            model_text = (
                f"{model.get('name', '')} {model.get('description', '')}".lower()
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
                price = model.get("pricing", {}).get("input_per_1k_tokens")
                if price is not None and price > max_price:
                    continue

            results.append(model)

        return results
