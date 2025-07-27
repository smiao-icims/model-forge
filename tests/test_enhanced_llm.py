"""Tests for EnhancedLLM wrapper functionality."""

import pickle
from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from modelforge.enhanced_llm import EnhancedLLM


class MockLLM(BaseChatModel):
    """Mock LLM for testing."""

    temperature: float = 0.7

    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "mock"

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Mock generation."""
        from langchain_core.messages import AIMessage

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="Mock response"))]
        )

    async def _agenerate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Mock async generation."""
        from langchain_core.messages import AIMessage

        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content="Mock async response"))
            ]
        )

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"temperature": self.temperature}

    def _stream(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        """Mock streaming."""
        yield "Mock"
        yield " streaming"
        yield " response"

    async def _astream(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        """Mock async streaming."""
        yield "Mock"
        yield " async"
        yield " streaming"


@pytest.fixture
def mock_llm() -> MockLLM:
    """Create a mock LLM instance."""
    return MockLLM()


@pytest.fixture
def mock_metadata() -> dict[str, Any]:
    """Create mock metadata."""
    return {
        "context_length": 128000,
        "max_tokens": 4096,
        "capabilities": ["function_calling", "vision"],
        "pricing": {
            "input_per_1m_tokens": 5.0,
            "output_per_1m_tokens": 15.0,
        },
        "knowledge_cutoff": "2024-04",
        "raw_info": {
            "id": "gpt-4",
            "name": "GPT-4",
            "limit": {"context": 128000, "output": 4096},
        },
    }


@pytest.fixture
def enhanced_llm(mock_llm: MockLLM, mock_metadata: dict[str, Any]) -> EnhancedLLM:
    """Create an EnhancedLLM instance."""
    return EnhancedLLM(
        wrapped_llm=mock_llm,
        model_metadata=mock_metadata,
        provider="openai",
        model_alias="gpt-4",
    )


class TestMetadataProperties:
    """Test metadata property access."""

    def test_context_length(self, enhanced_llm: EnhancedLLM) -> None:
        """Test context_length property."""
        assert enhanced_llm.context_length == 128000

    def test_max_output_tokens(self, enhanced_llm: EnhancedLLM) -> None:
        """Test max_output_tokens property."""
        assert enhanced_llm.max_output_tokens == 4096

    def test_supports_function_calling(self, enhanced_llm: EnhancedLLM) -> None:
        """Test supports_function_calling property."""
        assert enhanced_llm.supports_function_calling is True

    def test_supports_vision(self, enhanced_llm: EnhancedLLM) -> None:
        """Test supports_vision property."""
        assert enhanced_llm.supports_vision is True

    def test_model_info(self, enhanced_llm: EnhancedLLM) -> None:
        """Test model_info property returns copy."""
        info = enhanced_llm.model_info
        assert info["id"] == "gpt-4"
        # Verify it's a copy
        info["modified"] = True
        assert "modified" not in enhanced_llm.model_info

    def test_pricing_info(self, enhanced_llm: EnhancedLLM) -> None:
        """Test pricing_info property."""
        pricing = enhanced_llm.pricing_info
        assert pricing["input_per_1m"] == 5.0
        assert pricing["output_per_1m"] == 15.0
        assert pricing["currency"] == "USD"

    def test_missing_metadata_defaults(self) -> None:
        """Test defaults when metadata is missing."""
        llm = EnhancedLLM(
            wrapped_llm=MockLLM(),
            model_metadata={},
            provider="test",
            model_alias="test",
        )
        assert llm.context_length == 0
        assert llm.max_output_tokens == 0
        assert llm.supports_function_calling is False
        assert llm.supports_vision is False


class TestParameterConfiguration:
    """Test parameter configuration."""

    def test_temperature_get_set(self, enhanced_llm: EnhancedLLM) -> None:
        """Test temperature getter and setter."""
        # Default from wrapped model
        assert enhanced_llm.temperature == 0.7

        # Set new value
        enhanced_llm.temperature = 1.2
        assert enhanced_llm.temperature == 1.2
        # Should also update wrapped model
        assert enhanced_llm._wrapped_llm.temperature == 1.2

    def test_temperature_validation(self, enhanced_llm: EnhancedLLM) -> None:
        """Test temperature validation."""
        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            enhanced_llm.temperature = 2.5

        with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
            enhanced_llm.temperature = -0.1

    def test_top_p_get_set(self, enhanced_llm: EnhancedLLM) -> None:
        """Test top_p parameter."""
        enhanced_llm.top_p = 0.9
        assert enhanced_llm.top_p == 0.9

    def test_top_p_validation(self, enhanced_llm: EnhancedLLM) -> None:
        """Test top_p validation."""
        with pytest.raises(ValueError, match="top_p must be between 0 and 1"):
            enhanced_llm.top_p = 1.5

    def test_max_tokens_validation(self, enhanced_llm: EnhancedLLM) -> None:
        """Test max_tokens validation against model limit."""
        enhanced_llm.max_tokens = 2000  # Should work
        assert enhanced_llm.max_tokens == 2000

        with pytest.raises(ValueError, match="exceeds model limit"):
            enhanced_llm.max_tokens = 5000  # Exceeds 4096 limit


class TestCostEstimation:
    """Test cost estimation functionality."""

    def test_estimate_cost(self, enhanced_llm: EnhancedLLM) -> None:
        """Test cost estimation calculation."""
        # 1000 input tokens, 500 output tokens
        cost = enhanced_llm.estimate_cost(1000, 500)

        # Cost calculation: Input=0.005, Output=0.0075, Total=0.0125
        assert cost == pytest.approx(0.0125)

    def test_estimate_cost_large_values(self, enhanced_llm: EnhancedLLM) -> None:
        """Test cost estimation with large token counts."""
        cost = enhanced_llm.estimate_cost(1_000_000, 500_000)

        # Cost calculation: Input=5.0, Output=7.5, Total=12.5
        assert cost == pytest.approx(12.5)


class TestDelegation:
    """Test method delegation to wrapped model."""

    def test_generate_delegation(self, enhanced_llm: EnhancedLLM) -> None:
        """Test _generate delegates to wrapped model."""
        messages = [HumanMessage(content="Hello")]
        result = enhanced_llm._generate(messages)

        assert isinstance(result, ChatResult)
        assert result.generations[0].message.content == "Mock response"

    def test_custom_params_in_generate(self, enhanced_llm: EnhancedLLM) -> None:
        """Test custom parameters are passed to generation."""
        enhanced_llm.temperature = 0.5
        enhanced_llm._custom_params["custom_param"] = "value"

        with patch.object(enhanced_llm._wrapped_llm, "_generate") as mock_gen:
            mock_gen.return_value = ChatResult(generations=[])

            enhanced_llm._generate([HumanMessage(content="Hi")], extra_param="extra")

            # Verify merged kwargs
            args, kwargs = mock_gen.call_args
            assert kwargs["temperature"] == 0.5
            assert kwargs["custom_param"] == "value"
            assert kwargs["extra_param"] == "extra"

    def test_attribute_delegation(self, enhanced_llm: EnhancedLLM) -> None:
        """Test unknown attributes delegate to wrapped model."""
        # Access wrapped model's _llm_type
        assert enhanced_llm._llm_type == "mock"

        # Test attribute that doesn't exist raises AttributeError
        with pytest.raises(AttributeError):
            _ = enhanced_llm.nonexistent_attr


class TestCallbackIntegration:
    """Test callback integration with wrapped model."""

    def test_callback_propagation(self) -> None:
        """Test callbacks from wrapped model are accessible."""
        from modelforge.telemetry import TelemetryCallback

        # Create wrapped LLM with callbacks
        telemetry_callback = TelemetryCallback(provider="test", model="test-model")
        wrapped_llm = MockLLM()
        wrapped_llm.callbacks = [telemetry_callback]

        # Create EnhancedLLM
        enhanced_llm = EnhancedLLM(
            wrapped_llm=wrapped_llm,
            model_metadata={"context_length": 1000},
            provider="test",
            model_alias="test-model",
        )

        # Should be accessible through delegation
        assert enhanced_llm.callbacks == [telemetry_callback]

    def test_callback_initialization(self) -> None:
        """Test EnhancedLLM inherits callbacks from wrapped model."""
        from modelforge.telemetry import TelemetryCallback

        # Create wrapped LLM with multiple callbacks
        telemetry1 = TelemetryCallback(provider="test", model="test-model-1")
        telemetry2 = TelemetryCallback(provider="test", model="test-model-2")
        wrapped_llm = MockLLM()
        wrapped_llm.callbacks = [telemetry1, telemetry2]

        # Create EnhancedLLM
        enhanced_llm = EnhancedLLM(
            wrapped_llm=wrapped_llm,
            model_metadata={"context_length": 1000},
            provider="test",
            model_alias="test-model",
        )

        # Callbacks should be inherited
        assert hasattr(enhanced_llm, "callbacks")
        assert enhanced_llm.callbacks == [telemetry1, telemetry2]


class TestSerialization:
    """Test pickling support."""

    def test_pickle_unpickle(self, enhanced_llm: EnhancedLLM) -> None:
        """Test EnhancedLLM can be pickled and unpickled."""
        # Set some custom state
        enhanced_llm.temperature = 0.8
        enhanced_llm._custom_params["test"] = "value"

        # Pickle and unpickle
        pickled = pickle.dumps(enhanced_llm)
        unpickled = pickle.loads(pickled)  # noqa: S301

        # Verify state is preserved
        assert unpickled.temperature == 0.8
        assert unpickled._custom_params["test"] == "value"
        assert unpickled.context_length == 128000
        assert unpickled._provider == "openai"
        assert unpickled._model_alias == "gpt-4"


class TestStringRepresentation:
    """Test string representation."""

    def test_repr(self, enhanced_llm: EnhancedLLM) -> None:
        """Test __repr__ method."""
        repr_str = repr(enhanced_llm)
        assert "EnhancedLLM" in repr_str
        assert "provider=openai" in repr_str
        assert "model=gpt-4" in repr_str
        assert "context_length=128000" in repr_str
