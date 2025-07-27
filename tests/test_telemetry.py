"""Test telemetry functionality."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from langchain_core.outputs import LLMResult

from modelforge.telemetry import (
    ModelMetrics,
    TelemetryCallback,
    TokenUsage,
    calculate_cost,
    format_metrics,
)


class TestTokenUsage:
    """Test TokenUsage dataclass."""

    def test_default_values(self) -> None:
        """Test default values for TokenUsage."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self) -> None:
        """Test TokenUsage with custom values."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestModelMetrics:
    """Test ModelMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default values for ModelMetrics."""
        metrics = ModelMetrics(provider="openai", model="gpt-4")
        assert metrics.provider == "openai"
        assert metrics.model == "gpt-4"
        assert isinstance(metrics.start_time, datetime)
        assert metrics.end_time is None
        assert metrics.duration_ms == 0.0
        assert isinstance(metrics.token_usage, TokenUsage)
        assert metrics.estimated_cost == 0.0
        assert metrics.error is None
        assert metrics.metadata == {}

    def test_custom_values(self) -> None:
        """Test ModelMetrics with custom values."""
        now = datetime.now(UTC)
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        metrics = ModelMetrics(
            provider="anthropic",
            model="claude-3-opus",
            start_time=now,
            end_time=now,
            duration_ms=123.45,
            token_usage=usage,
            estimated_cost=0.01125,
            error="Test error",
            metadata={"key": "value"},
        )
        assert metrics.provider == "anthropic"
        assert metrics.model == "claude-3-opus"
        assert metrics.start_time == now
        assert metrics.end_time == now
        assert metrics.duration_ms == 123.45
        assert metrics.token_usage == usage
        assert metrics.estimated_cost == 0.01125
        assert metrics.error == "Test error"
        assert metrics.metadata == {"key": "value"}


class TestTelemetryCallback:
    """Test TelemetryCallback class."""

    def test_initialization(self) -> None:
        """Test callback initialization."""
        callback = TelemetryCallback(provider="openai", model="gpt-4")
        assert callback.metrics.provider == "openai"
        assert callback.metrics.model == "gpt-4"
        assert callback._start_time is None

    @patch("time.time")
    def test_on_llm_start(self, mock_time: MagicMock) -> None:
        """Test on_llm_start callback."""
        mock_time.return_value = 1234567890.0
        callback = TelemetryCallback(provider="openai", model="gpt-4")

        callback.on_llm_start({}, ["test prompt"])

        assert callback._start_time == 1234567890.0
        assert isinstance(callback.metrics.start_time, datetime)

    @patch("time.time")
    def test_on_llm_end_with_token_usage(self, mock_time: MagicMock) -> None:
        """Test on_llm_end callback with token usage."""
        # Setup time mock
        mock_time.side_effect = [1234567890.0, 1234567891.5]  # start and end times

        callback = TelemetryCallback(provider="openai", model="gpt-4")
        callback.on_llm_start({}, ["test prompt"])

        # Create mock LLM result with token usage
        llm_result = LLMResult(
            generations=[],
            llm_output={
                "token_usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                },
                "model_name": "gpt-4-0613",
            },
        )

        callback.on_llm_end(llm_result)

        assert callback.metrics.duration_ms == 1500.0  # 1.5 seconds
        assert callback.metrics.token_usage.prompt_tokens == 100
        assert callback.metrics.token_usage.completion_tokens == 50
        assert callback.metrics.token_usage.total_tokens == 150
        assert callback.metrics.metadata["actual_model"] == "gpt-4-0613"
        assert callback.metrics.estimated_cost > 0

    def test_on_llm_end_without_token_usage(self) -> None:
        """Test on_llm_end callback without token usage."""
        callback = TelemetryCallback(provider="ollama", model="llama2")

        # Create mock LLM result without token usage
        llm_result = LLMResult(generations=[], llm_output={})

        callback.on_llm_end(llm_result)

        assert callback.metrics.token_usage.total_tokens == 0
        assert callback.metrics.estimated_cost == 0.0

    @patch("modelforge.telemetry.logger")
    @patch("time.time")
    def test_on_llm_error(self, mock_time: MagicMock, mock_logger: MagicMock) -> None:
        """Test on_llm_error callback."""
        mock_time.side_effect = [1234567890.0, 1234567891.0]

        callback = TelemetryCallback(provider="openai", model="gpt-4")
        callback.on_llm_start({}, ["test prompt"])

        error = ValueError("Test error message")
        callback.on_llm_error(error)

        assert callback.metrics.error == "Test error message"
        assert callback.metrics.duration_ms == 1000.0
        mock_logger.error.assert_called_once_with("LLM error: Test error message")


class TestCalculateCost:
    """Test cost calculation function."""

    def test_openai_gpt4_cost(self) -> None:
        """Test cost calculation for OpenAI GPT-4."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "gpt-4", usage)

        # GPT-4: $0.03/1K input, $0.06/1K output
        expected_cost = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        assert cost == expected_cost

    def test_anthropic_claude_cost(self) -> None:
        """Test cost calculation for Anthropic Claude."""
        usage = TokenUsage(
            prompt_tokens=2000, completion_tokens=1000, total_tokens=3000
        )
        cost = calculate_cost("anthropic", "claude-3-sonnet", usage)

        # Claude-3-sonnet: $0.003/1K input, $0.015/1K output
        expected_cost = (2000 / 1000) * 0.003 + (1000 / 1000) * 0.015
        assert cost == expected_cost

    def test_partial_model_match(self) -> None:
        """Test cost calculation with partial model name match."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "gpt-4-0125-preview", usage)

        # Should match "gpt-4" pricing
        expected_cost = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        assert cost == expected_cost

    def test_unknown_provider(self) -> None:
        """Test cost calculation for unknown provider."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("unknown_provider", "some-model", usage)
        assert cost == 0.0

    def test_unknown_model(self) -> None:
        """Test cost calculation for unknown model."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        cost = calculate_cost("openai", "unknown-model", usage)
        assert cost == 0.0

    def test_zero_tokens(self) -> None:
        """Test cost calculation with zero tokens."""
        usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        cost = calculate_cost("openai", "gpt-4", usage)
        assert cost == 0.0

    def test_case_insensitive_matching(self) -> None:
        """Test case-insensitive provider and model matching."""
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

        # Test uppercase provider
        cost1 = calculate_cost("OPENAI", "gpt-4", usage)
        expected_cost = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        assert cost1 == expected_cost

        # Test uppercase model
        cost2 = calculate_cost("openai", "GPT-4", usage)
        assert cost2 == expected_cost


class TestFormatMetrics:
    """Test metrics formatting function."""

    def test_basic_formatting(self) -> None:
        """Test basic metrics formatting."""
        metrics = ModelMetrics(
            provider="openai",
            model="gpt-4",
            duration_ms=1234.5,
            token_usage=TokenUsage(
                prompt_tokens=100, completion_tokens=50, total_tokens=150
            ),
            estimated_cost=0.0075,
        )

        result = format_metrics(metrics)

        assert "📊 Telemetry Information" in result
        assert "Provider: openai" in result
        assert "Model: gpt-4" in result
        assert (
            "Duration: 1234ms" in result
        )  # format_metrics uses f"{metrics.duration_ms:.0f}ms"
        assert "Prompt tokens: 100" in result
        assert "Completion tokens: 50" in result
        assert "Total tokens: 150" in result
        assert "💰 Estimated Cost: $0.007500" in result

    def test_formatting_with_actual_model(self) -> None:
        """Test formatting with actual model metadata."""
        metrics = ModelMetrics(
            provider="openai",
            model="gpt-4",
            duration_ms=1000.0,
            metadata={"actual_model": "gpt-4-0613"},
        )

        result = format_metrics(metrics)

        assert "Actual Model: gpt-4-0613" in result

    def test_formatting_with_error(self) -> None:
        """Test formatting with error."""
        metrics = ModelMetrics(
            provider="openai",
            model="gpt-4",
            duration_ms=500.0,
            error="Connection timeout",
        )

        result = format_metrics(metrics)

        assert "❌ Error: Connection timeout" in result

    def test_formatting_without_cost(self) -> None:
        """Test formatting without estimated cost."""
        metrics = ModelMetrics(
            provider="ollama",
            model="llama2",
            duration_ms=1000.0,
            token_usage=TokenUsage(
                prompt_tokens=100, completion_tokens=50, total_tokens=150
            ),
            estimated_cost=0.0,
        )

        result = format_metrics(metrics)

        assert "💰 Estimated Cost" not in result

    def test_formatting_with_large_numbers(self) -> None:
        """Test formatting with large token counts."""
        metrics = ModelMetrics(
            provider="openai",
            model="gpt-3.5-turbo",
            duration_ms=5000.0,
            token_usage=TokenUsage(
                prompt_tokens=10000, completion_tokens=5000, total_tokens=15000
            ),
            estimated_cost=0.0125,
        )

        result = format_metrics(metrics)

        assert "Prompt tokens: 10,000" in result
        assert "Completion tokens: 5,000" in result
        assert "Total tokens: 15,000" in result

    def test_formatting_with_context_info(self) -> None:
        """Test formatting with context window information from enhanced LLM."""
        metrics = ModelMetrics(
            provider="openai",
            model="gpt-4",
            duration_ms=2000.0,
            token_usage=TokenUsage(
                prompt_tokens=1000, completion_tokens=500, total_tokens=1500
            ),
            estimated_cost=0.045,
            metadata={
                "context_length": 128000,
                "max_output_tokens": 4096,
                "supports_function_calling": True,
                "supports_vision": True,
            },
        )

        result = format_metrics(metrics)

        # Check basic info
        assert "📊 Telemetry Information" in result
        assert "Provider: openai" in result
        assert "Model: gpt-4" in result

        # Check context window information
        assert "📊 Context Window:" in result
        assert "Model limit: 128,000 tokens" in result
        assert "Used: 1,000 tokens (0.8%)" in result
        assert "Remaining: 127,000 tokens" in result
        assert "Max output: 4,096 tokens" in result
        assert "Capabilities: ✓ Functions, ✓ Vision" in result

    def test_formatting_with_partial_context_info(self) -> None:
        """Test formatting with partial context information."""
        metrics = ModelMetrics(
            provider="openai",
            model="gpt-3.5-turbo",
            duration_ms=1000.0,
            token_usage=TokenUsage(
                prompt_tokens=500, completion_tokens=250, total_tokens=750
            ),
            estimated_cost=0.001,
            metadata={
                "context_length": 16000,
                "max_output_tokens": 4096,
                "supports_function_calling": True,
                "supports_vision": False,
            },
        )

        result = format_metrics(metrics)

        # Check context window information
        assert "📊 Context Window:" in result
        assert "Model limit: 16,000 tokens" in result
        assert "Used: 500 tokens (3.1%)" in result
        assert "Remaining: 15,500 tokens" in result
        assert "Max output: 4,096 tokens" in result
        assert "Capabilities: ✓ Functions" in result
        assert "✓ Vision" not in result


class TestIntegration:
    """Integration tests for telemetry components."""

    @patch("time.time")
    def test_full_telemetry_flow(self, mock_time: MagicMock) -> None:
        """Test complete telemetry flow from start to formatted output."""
        # Setup time mock
        mock_time.side_effect = [1234567890.0, 1234567892.5]

        # Create callback
        callback = TelemetryCallback(provider="openai", model="gpt-4o-mini")

        # Simulate LLM lifecycle
        callback.on_llm_start({}, ["Test prompt"])

        llm_result = LLMResult(
            generations=[],
            llm_output={
                "token_usage": {
                    "prompt_tokens": 250,
                    "completion_tokens": 100,
                    "total_tokens": 350,
                },
                "model_name": "gpt-4o-mini-2024-07-18",
            },
        )

        callback.on_llm_end(llm_result)

        # Format and verify output
        output = format_metrics(callback.metrics)

        assert "Provider: openai" in output
        assert "Model: gpt-4o-mini" in output
        assert "Actual Model: gpt-4o-mini-2024-07-18" in output
        assert "Duration: 2500ms" in output
        assert "Prompt tokens: 250" in output
        assert "Completion tokens: 100" in output
        assert "Total tokens: 350" in output

        # Check cost calculation (gpt-4o-mini: $0.00015/1K input, $0.0006/1K output)
        expected_cost = (250 / 1000) * 0.00015 + (100 / 1000) * 0.0006
        assert f"💰 Estimated Cost: ${expected_cost:.6f}" in output


class TestGitHubCopilotFormatting:
    """Test GitHub Copilot specific formatting."""

    def test_github_copilot_cost_note(self) -> None:
        """Test that GitHub Copilot shows cost disclaimer."""
        metrics = ModelMetrics(
            provider="github_copilot",
            model="gpt-4o",
            duration_ms=1500,
            token_usage=TokenUsage(
                prompt_tokens=100, completion_tokens=50, total_tokens=150
            ),
            estimated_cost=0.00075,
        )

        output = format_metrics(metrics)

        assert "📊 Telemetry Information" in output
        assert "Provider: github_copilot" in output
        assert "Model: gpt-4o" in output
        assert "💰 Estimated Cost: $0.000750" in output
        assert (
            "Note: GitHub Copilot is subscription-based. Cost shown is for reference only."
            in output
        )

    def test_github_copilot_no_cost_no_note(self) -> None:
        """Test that note doesn't appear when there's no cost."""
        metrics = ModelMetrics(
            provider="github_copilot",
            model="gpt-4o",
            duration_ms=1500,
            token_usage=TokenUsage(
                prompt_tokens=0, completion_tokens=0, total_tokens=0
            ),
            estimated_cost=0.0,
        )

        output = format_metrics(metrics)

        assert "📊 Telemetry Information" in output
        assert "Provider: github_copilot" in output
        assert "💰 Estimated Cost" not in output
        assert "Note: GitHub Copilot is subscription-based" not in output
