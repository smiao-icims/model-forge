"""Tests for ModelsDev description generation functionality."""

from typing import Any

from modelforge.modelsdev import ModelsDevClient


class TestModelDescriptionGeneration:
    """Test cases for model description generation."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.client = ModelsDevClient()

    def test_generate_model_description_with_full_data(self) -> None:
        """Test description generation with complete model data."""
        model_data = {
            "name": "GPT-4o",
            "reasoning": False,
            "attachment": True,
            "cost": {"input": 2.5, "output": 10},
            "limit": {"context": 128000, "output": 16384},
        }

        description = self.client._generate_model_description(model_data)

        assert "Multimodal model" in description
        assert "$2.5/1M input" in description
        assert "128K context" in description

    def test_generate_model_description_reasoning_model(self) -> None:
        """Test description generation for reasoning models."""
        model_data = {
            "name": "o1-preview",
            "reasoning": True,
            "attachment": False,
            "cost": {"input": 15, "output": 60},
            "limit": {"context": 128000, "output": 32768},
        }

        description = self.client._generate_model_description(model_data)

        assert "Reasoning model" in description
        assert "$15/1M input" in description
        assert "128K context" in description

    def test_generate_model_description_text_model(self) -> None:
        """Test description generation for text-only models."""
        model_data = {
            "name": "GPT-3.5 Turbo",
            "reasoning": False,
            "attachment": False,
            "cost": {"input": 0.5, "output": 1.5},
            "limit": {"context": 16384, "output": 4096},
        }

        description = self.client._generate_model_description(model_data)

        assert "Text model" in description
        assert "$0.5/1M input" in description
        assert "16K context" in description

    def test_generate_model_description_with_minimal_data(self) -> None:
        """Test description generation with minimal data."""
        model_data = {"name": "Basic Model"}

        description = self.client._generate_model_description(model_data)

        assert description == "Basic Model"

    def test_generate_model_description_with_no_name(self) -> None:
        """Test description generation with no name field."""
        model_data = {
            "reasoning": False,
            "attachment": False,
        }

        description = self.client._generate_model_description(model_data)

        assert description == "Language model"

    def test_generate_model_description_with_large_context(self) -> None:
        """Test description generation with large context windows."""
        model_data = {
            "name": "Long Context Model",
            "reasoning": False,
            "attachment": True,
            "cost": {"input": 1.25, "output": 5},
            "limit": {"context": 2000000, "output": 8192},
        }

        description = self.client._generate_model_description(model_data)

        assert "Multimodal model" in description
        assert "$1.25/1M input" in description
        assert "2000K context" in description

    def test_generate_model_description_handles_exceptions(self) -> None:
        """Test description generation handles exceptions gracefully."""
        # Malformed data that might cause exceptions
        model_data = {
            "name": "Test Model",
            "cost": "invalid",  # Should be dict
            "limit": None,  # Should be dict
        }

        description = self.client._generate_model_description(model_data)

        # Should fallback to name
        assert description == "Test Model"

    def test_extract_capabilities_full_features(self) -> None:
        """Test capability extraction with all features."""
        model_data = {
            "reasoning": True,
            "tool_call": True,
            "attachment": True,
            "modalities": {
                "input": ["text", "image", "audio", "video"],
                "output": ["text"],
            },
        }

        capabilities = self.client._extract_capabilities(model_data)

        expected_capabilities = [
            "reasoning",
            "function_calling",
            "multimodal",
            "vision",
            "audio",
            "video",
        ]
        assert all(cap in capabilities for cap in expected_capabilities)

    def test_extract_capabilities_text_only(self) -> None:
        """Test capability extraction for text-only models."""
        model_data = {
            "reasoning": False,
            "tool_call": True,
            "attachment": False,
            "modalities": {"input": ["text"], "output": ["text"]},
        }

        capabilities = self.client._extract_capabilities(model_data)

        assert "function_calling" in capabilities
        assert "reasoning" not in capabilities
        assert "multimodal" not in capabilities
        assert "vision" not in capabilities

    def test_extract_pricing_complete(self) -> None:
        """Test pricing extraction with complete data."""
        model_data = {
            "cost": {
                "input": 2.5,
                "output": 10,
                "cache_read": 1.25,
                "cache_write": 3.75,
            }
        }

        pricing = self.client._extract_pricing(model_data)

        assert pricing["input_per_1m_tokens"] == 2.5
        assert pricing["output_per_1m_tokens"] == 10
        assert pricing["cache_read_per_1m_tokens"] == 1.25
        assert pricing["cache_write_per_1m_tokens"] == 3.75

    def test_extract_pricing_partial(self) -> None:
        """Test pricing extraction with partial data."""
        model_data = {"cost": {"input": 0.15, "output": 0.6}}

        pricing = self.client._extract_pricing(model_data)

        assert pricing["input_per_1m_tokens"] == 0.15
        assert pricing["output_per_1m_tokens"] == 0.6
        assert pricing["cache_read_per_1m_tokens"] is None
        assert pricing["cache_write_per_1m_tokens"] is None

    def test_extract_pricing_missing(self) -> None:
        """Test pricing extraction with missing cost data."""
        model_data: dict[str, Any] = {}

        pricing = self.client._extract_pricing(model_data)

        assert pricing["input_per_1m_tokens"] is None
        assert pricing["output_per_1m_tokens"] is None
        assert pricing["cache_read_per_1m_tokens"] is None
        assert pricing["cache_write_per_1m_tokens"] is None

    def test_parse_model_data_integration(self) -> None:
        """Test full model data parsing integration."""
        api_response: dict[str, Any] = {
            "openai": {
                "models": {
                    "gpt-4o": {
                        "id": "gpt-4o",
                        "name": "GPT-4o",
                        "attachment": True,
                        "reasoning": False,
                        "tool_call": True,
                        "cost": {"input": 2.5, "output": 10},
                        "limit": {"context": 128000, "output": 16384},
                        "modalities": {"input": ["text", "image"], "output": ["text"]},
                    }
                }
            }
        }

        models = self.client._parse_model_data(api_response)

        assert len(models) == 1
        model = models[0]

        assert model["id"] == "gpt-4o"
        assert model["provider"] == "openai"
        assert model["display_name"] == "GPT-4o"
        assert "Multimodal model" in model["description"]
        assert "$2.5/1M input" in model["description"]
        assert "128K context" in model["description"]
        assert model["context_length"] == 128000
        assert model["max_tokens"] == 16384
        assert "function_calling" in model["capabilities"]
        assert "multimodal" in model["capabilities"]
        assert "vision" in model["capabilities"]
