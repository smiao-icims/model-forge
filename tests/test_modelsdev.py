"""Tests for models.dev integration."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from requests_mock import Mocker

from modelforge.modelsdev import ModelsDevClient


class TestModelsDevClient:
    """Test cases for ModelsDevClient."""

    def test_init(self) -> None:
        """Test client initialization."""
        client = ModelsDevClient()
        assert client.api_key is None
        assert client.BASE_URL == "https://models.dev/api/v1"

    def test_init_with_api_key(self) -> None:
        """Test client initialization with API key."""
        client = ModelsDevClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert "Authorization" in client.session.headers

    def test_cache_directory_creation(self) -> None:
        """Test that cache directory is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            with patch.object(ModelsDevClient, "CACHE_DIR", cache_path):
                client = ModelsDevClient()
                assert client.CACHE_DIR.exists()

    def test_get_providers_success(self, requests_mock: Mocker) -> None:
        """Test successful providers retrieval."""
        mock_providers = [
            {"name": "openai", "display_name": "OpenAI"},
            {"name": "anthropic", "display_name": "Anthropic"},
        ]
        requests_mock.get("https://models.dev/api/v1/providers", json=mock_providers)

        client = ModelsDevClient()
        providers = client.get_providers()

        assert providers == mock_providers

    def test_get_providers_cached(self) -> None:
        """Test providers retrieval from cache."""
        mock_providers = [{"name": "cached", "display_name": "Cached"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "providers.json"

            with cache_file.open("w") as f:
                json.dump(mock_providers, f)

            # Mock the CACHE_DIR and force cache to be valid by making file recent
            with patch.object(ModelsDevClient, "CACHE_DIR", cache_dir):
                # Make sure the cache file is recent enough to be valid
                os.utime(cache_file, (time.time(), time.time()))

                client = ModelsDevClient()

                # Mock the _is_cache_valid method to return True for this test
                with patch.object(client, "_is_cache_valid", return_value=True):
                    providers = client.get_providers()
                    assert providers == mock_providers

    def test_get_models_success(self, requests_mock: Mocker) -> None:
        """Test successful models retrieval."""
        mock_models = [
            {"name": "gpt-4", "provider": "openai"},
            {"name": "claude-3", "provider": "anthropic"},
        ]
        requests_mock.get("https://models.dev/api/v1/models", json=mock_models)

        client = ModelsDevClient()
        models = client.get_models()

        assert models == mock_models

    def test_get_models_with_provider_filter(self, requests_mock: Mocker) -> None:
        """Test models retrieval with provider filter."""
        mock_models = [{"name": "gpt-4", "provider": "openai"}]
        requests_mock.get(
            "https://models.dev/api/v1/models?provider=openai", json=mock_models
        )

        client = ModelsDevClient()
        models = client.get_models(provider="openai")

        assert models == mock_models

    def test_get_model_info_success(self, requests_mock: Mocker) -> None:
        """Test successful model info retrieval."""
        mock_info = {
            "name": "gpt-4",
            "provider": "openai",
            "description": "GPT-4 model",
        }
        requests_mock.get(
            "https://models.dev/api/v1/models/openai/gpt-4", json=mock_info
        )

        client = ModelsDevClient()
        info = client.get_model_info("openai", "gpt-4")

        assert info == mock_info

    def test_search_models(self, requests_mock: Mocker) -> None:
        """Test model search functionality."""
        mock_models = [
            {
                "name": "gpt-4",
                "provider": "openai",
                "description": "Advanced language model",
                "capabilities": ["chat", "code"],
                "pricing": {"input_per_1k_tokens": 0.03},
            },
            {
                "name": "claude-3",
                "provider": "anthropic",
                "description": "Claude model",
                "capabilities": ["chat"],
                "pricing": {"input_per_1k_tokens": 0.08},
            },
        ]
        requests_mock.get("https://models.dev/api/v1/models", json=mock_models)

        # Mock the CACHE_DIR to prevent real cache usage
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)

            with patch.object(ModelsDevClient, "CACHE_DIR", cache_dir):
                client = ModelsDevClient()

                # Test basic search
                results = client.search_models("gpt")
                assert len(results) == 1
                assert results[0]["name"] == "gpt-4"

                # Test capability filter
                results = client.search_models("", capabilities=["code"])
                assert len(results) == 1
                assert results[0]["name"] == "gpt-4"

                # Test price filter
                results = client.search_models("", max_price=0.05)
                assert len(results) == 1
                assert results[0]["name"] == "gpt-4"

    def test_clear_cache(self) -> None:
        """Test cache clearing functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Create some cache files with .json extension as expected by clear_cache
            (cache_dir / "test1.json").write_text('{"test": 1}')
            (cache_dir / "test2.json").write_text('{"test": 2}')

            # Mock the CACHE_DIR to use our temp directory
            with patch.object(ModelsDevClient, "CACHE_DIR", cache_dir):
                client = ModelsDevClient()
                client.clear_cache()

                assert not (cache_dir / "test1.json").exists()
                assert not (cache_dir / "test2.json").exists()

    def test_network_error_handling(self, requests_mock: Mocker) -> None:
        """Test handling of network errors."""
        requests_mock.get("https://models.dev/api/v1/providers", status_code=500)

        # Mock the CACHE_DIR to use a temp directory with no cache
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)

            with patch.object(ModelsDevClient, "CACHE_DIR", cache_dir):
                client = ModelsDevClient()

                # Should raise exception when no cache available
                with pytest.raises(requests.exceptions.HTTPError):
                    client.get_providers()

    def test_cache_validation(self) -> None:
        """Test cache TTL validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "providers.json"

            # Create expired cache
            with cache_file.open("w") as f:
                json.dump([{"name": "old"}], f)

            # Make file old enough to be expired
            os.utime(cache_file, (time.time() - 3600 * 25, time.time() - 3600 * 25))

            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                client = ModelsDevClient()
                assert not client._is_cache_valid(cache_file, 3600)
