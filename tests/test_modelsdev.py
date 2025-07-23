"""Tests for models.dev integration."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from requests_mock import Mocker

from modelforge.modelsdev import ModelsDevClient


class TestModelsDevClient:
    """Test cases for ModelsDevClient."""

    def test_init(self) -> None:
        """Test client initialization."""
        client = ModelsDevClient()
        assert client.api_key is None
        assert client.BASE_URL == "https://models.dev"

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
        mock_data = {
            "openai": {
                "name": "OpenAI",
                "doc": "OpenAI API",
                "api": "https://api.openai.com/v1",
            },
            "anthropic": {
                "name": "Anthropic",
                "doc": "Anthropic API",
                "api": "https://api.anthropic.com",
            },
        }
        requests_mock.get("https://models.dev/api.json", json=mock_data)

        client = ModelsDevClient()
        providers = client.get_providers(force_refresh=True)

        assert len(providers) == 2
        assert providers[0]["name"] == "openai"
        assert providers[0]["display_name"] == "OpenAI"
        assert providers[1]["name"] == "anthropic"
        assert providers[1]["display_name"] == "Anthropic"

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
        mock_data = {
            "openai": {
                "models": {
                    "gpt-4": {
                        "name": "GPT-4",
                        "attachment": True,
                        "reasoning": False,
                        "tool_call": True,
                        "cost": {"input": 0.03, "output": 0.06},
                        "limit": {"context": 8192, "output": 4096},
                        "modalities": {"input": ["text", "image"], "output": ["text"]},
                    },
                    "gpt-3.5-turbo": {
                        "name": "GPT-3.5 Turbo",
                        "attachment": False,
                        "reasoning": False,
                        "tool_call": True,
                        "cost": {"input": 0.0015, "output": 0.002},
                        "limit": {"context": 4096, "output": 4096},
                        "modalities": {"input": ["text"], "output": ["text"]},
                    },
                }
            }
        }
        requests_mock.get("https://models.dev/api.json", json=mock_data)

        client = ModelsDevClient()
        models = client.get_models(force_refresh=True)

        assert len(models) == 2
        assert models[0]["id"] == "gpt-4"
        assert models[0]["provider"] == "openai"
        assert models[0]["display_name"] == "GPT-4"
        # Check that description is now populated with meaningful content
        assert models[0]["description"] != ""
        assert "model" in models[0]["description"].lower()
        # Check that capabilities are extracted
        assert isinstance(models[0]["capabilities"], list)
        # Check that pricing is extracted
        assert models[0]["pricing"]["input_per_1k_tokens"] == 0.03

    def test_get_models_with_provider_filter(self, requests_mock: Mocker) -> None:
        """Test models retrieval with provider filter."""
        mock_data = {
            "openai": {
                "models": {
                    "gpt-4": {
                        "display_name": "GPT-4",
                        "description": "GPT-4 model",
                        "capabilities": ["chat"],
                    }
                }
            }
        }
        requests_mock.get("https://models.dev/api.json", json=mock_data)

        client = ModelsDevClient()
        models = client.get_models(provider="openai", force_refresh=True)

        assert len(models) == 1
        assert models[0]["id"] == "gpt-4"
        assert models[0]["provider"] == "openai"

    def test_get_model_info_success(self, requests_mock: Mocker) -> None:
        """Test successful model info retrieval."""
        # Mock the full API response structure
        mock_api_response = {
            "openai": {
                "models": {
                    "gpt-4": {
                        "name": "gpt-4",
                        "description": "GPT-4 model",
                        "attachment": True,
                        "reasoning": False,
                    }
                }
            }
        }
        requests_mock.get(
            "https://models.dev/api.json",
            json=mock_api_response,
            headers={"Content-Type": "application/json"},
        )

        client = ModelsDevClient()
        info = client.get_model_info("openai", "gpt-4")

        # The returned info should include the model data plus provider and id fields
        expected_info = {
            "name": "gpt-4",
            "description": "GPT-4 model",
            "attachment": True,
            "reasoning": False,
            "provider": "openai",
            "id": "gpt-4",
        }
        assert info == expected_info

    def test_search_models(self, requests_mock: Mocker) -> None:
        """Test model search functionality."""
        mock_data = {
            "openai": {
                "models": {
                    "gpt-4": {
                        "name": "GPT-4",
                        "attachment": True,
                        "reasoning": False,
                        "tool_call": True,
                        "cost": {"input": 0.03},
                        "limit": {"context": 8192, "output": 4096},
                        "modalities": {"input": ["text", "image"], "output": ["text"]},
                    }
                }
            },
            "anthropic": {
                "models": {
                    "claude-3": {
                        "name": "Claude 3",
                        "attachment": True,
                        "reasoning": False,
                        "tool_call": True,
                        "cost": {"input": 0.08},
                        "limit": {"context": 200000, "output": 4096},
                        "modalities": {"input": ["text", "image"], "output": ["text"]},
                    }
                }
            },
        }
        requests_mock.get("https://models.dev/api.json", json=mock_data)

        # Mock the CACHE_DIR to prevent real cache usage
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)

            with patch.object(ModelsDevClient, "CACHE_DIR", cache_dir):
                client = ModelsDevClient()

                # Test basic search
                results = client.search_models("gpt", force_refresh=True)
                assert len(results) == 1
                assert results[0]["id"] == "gpt-4"

                # Test capability filter - use a search term that matches descriptions
                results = client.search_models(
                    "multimodal", capabilities=["function_calling"], force_refresh=True
                )
                assert len(results) == 2  # Both models have function_calling capability

                # Test price filter - search for models with "gpt" or use display name
                results = client.search_models(
                    "gpt", max_price=0.05, force_refresh=True
                )
                assert len(results) == 1
                assert results[0]["id"] == "gpt-4"

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
        requests_mock.get("https://models.dev/api.json", status_code=500)

        # Mock the CACHE_DIR to use a temp directory with no cache
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / ".cache" / "model-forge" / "modelsdev"
            cache_dir.mkdir(parents=True, exist_ok=True)

            with patch.object(ModelsDevClient, "CACHE_DIR", cache_dir):
                client = ModelsDevClient()

                # Should return empty list when no cache available
                providers = client.get_providers()
                assert providers == []

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

    def test_get_model_info_provider_not_found(self, requests_mock: Mocker) -> None:
        """Test error handling when provider is not found."""
        # Mock API response without the requested provider
        mock_api_response = {
            "openai": {"models": {"gpt-4": {"name": "GPT-4"}}},
            "anthropic": {"models": {"claude-3": {"name": "Claude 3"}}},
        }
        requests_mock.get(
            "https://models.dev/api.json",
            json=mock_api_response,
            headers={"Content-Type": "application/json"},
        )

        # Mock get_providers for suggestions
        requests_mock.get(
            "https://models.dev/api.json",
            json=mock_api_response,
            headers={"Content-Type": "application/json"},
        )

        client = ModelsDevClient()

        from modelforge.exceptions import ProviderError

        with pytest.raises(ProviderError, match="Provider.*not found") as exc_info:
            client.get_model_info("nonexistent", "gpt-4", force_refresh=True)

        error_msg = str(exc_info.value)
        assert "Provider 'nonexistent' not found" in error_msg

    def test_get_model_info_model_not_found(self, requests_mock: Mocker) -> None:
        """Test error handling when model is not found for provider."""
        # Mock API response with provider but without the requested model
        mock_api_response = {
            "openai": {
                "models": {
                    "gpt-4": {"name": "GPT-4"},
                    "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo"},
                }
            }
        }
        requests_mock.get(
            "https://models.dev/api.json",
            json=mock_api_response,
            headers={"Content-Type": "application/json"},
        )

        client = ModelsDevClient()

        from modelforge.exceptions import ModelNotFoundError

        with pytest.raises(ModelNotFoundError, match="Model.*not found") as exc_info:
            client.get_model_info("openai", "nonexistent", force_refresh=True)

        error_msg = str(exc_info.value)
        assert "Model 'nonexistent' not found for provider 'openai'" in error_msg

    def test_get_model_info_provider_normalization(self, requests_mock: Mocker) -> None:
        """Test provider name normalization (underscores to hyphens)."""
        mock_api_response = {
            "github-copilot": {
                "models": {
                    "gpt-4o": {
                        "name": "GPT-4o",
                        "attachment": True,
                    }
                }
            }
        }
        requests_mock.get(
            "https://models.dev/api.json",
            json=mock_api_response,
            headers={"Content-Type": "application/json"},
        )

        client = ModelsDevClient()

        # Test with underscore - should be normalized to hyphen
        info = client.get_model_info("github_copilot", "gpt-4o", force_refresh=True)

        expected_info = {
            "name": "GPT-4o",
            "attachment": True,
            "provider": "github-copilot",
            "id": "gpt-4o",
        }
        assert info == expected_info

    def test_get_model_info_input_validation(self) -> None:
        """Test input validation for provider and model names."""
        client = ModelsDevClient()

        from modelforge.exceptions import InvalidInputError

        # Test empty provider
        with pytest.raises(InvalidInputError, match="Provider name cannot be empty"):
            client.get_model_info("", "gpt-4")

        # Test empty model - now validates model name
        with pytest.raises(InvalidInputError):
            client.get_model_info("openai", "")

    def test_get_model_info_invalid_content_type(self, requests_mock: Mocker) -> None:
        """Test error handling when API returns non-JSON content."""
        requests_mock.get(
            "https://models.dev/api.json",
            text="<html>404 Not Found</html>",
            headers={"Content-Type": "text/html"},
        )

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("pathlib.Path.home", return_value=Path(temp_dir)),
        ):
            client = ModelsDevClient()

            # Clear any existing cache
            client.clear_cache()

            from modelforge.exceptions import ProviderError

            with pytest.raises(
                ProviderError, match="Expected JSON response, got text/html"
            ):
                client.get_model_info("openai", "gpt-4", force_refresh=True)
