"""Telemetry and metrics tracking for ModelForge."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ModelMetrics:
    """Metrics for a model invocation."""

    provider: str
    model: str
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float = 0.0
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    estimated_cost: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TelemetryCallback(BaseCallbackHandler):
    """Callback handler for collecting telemetry data."""

    def __init__(self, provider: str, model: str) -> None:
        """Initialize telemetry callback.

        Args:
            provider: Provider name (e.g., "openai", "ollama")
            model: Model name (e.g., "gpt-4", "llama2")
        """
        super().__init__()
        self.metrics = ModelMetrics(provider=provider, model=model)
        self._start_time: float | None = None
        self._prompts: list[str] = []

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts processing."""
        self._start_time = time.time()
        self.metrics.start_time = datetime.now(UTC)
        self._prompts = prompts  # Save prompts for token estimation
        logger.debug(f"LLM started: {self.metrics.provider}/{self.metrics.model}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes processing."""
        if self._start_time:
            self.metrics.duration_ms = (time.time() - self._start_time) * 1000

        self.metrics.end_time = datetime.now(UTC)

        # Extract token usage from response
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            self.metrics.token_usage.prompt_tokens = usage.get("prompt_tokens", 0)
            self.metrics.token_usage.completion_tokens = usage.get(
                "completion_tokens", 0
            )
            self.metrics.token_usage.total_tokens = usage.get("total_tokens", 0)

            # Store model name from response if available
            if "model_name" in response.llm_output:
                self.metrics.metadata["actual_model"] = response.llm_output[
                    "model_name"
                ]

        # If no token usage reported (common with GitHub Copilot), estimate it
        if self.metrics.token_usage.total_tokens == 0 and response.generations:
            # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
            prompt_text = " ".join(self._prompts) if self._prompts else ""
            completion_text = ""
            for generation_list in response.generations:
                for generation in generation_list:
                    if hasattr(generation, "text"):
                        completion_text += generation.text
                    elif hasattr(generation, "message"):
                        completion_text += str(generation.message.content)
                    else:
                        # Fallback for other generation types
                        completion_text += str(generation)

            # Very rough token estimation
            estimated_prompt_tokens = len(prompt_text) // 4 if prompt_text else 10
            estimated_completion_tokens = (
                len(completion_text) // 4 if completion_text else 10
            )

            if estimated_prompt_tokens > 0 or estimated_completion_tokens > 0:
                self.metrics.token_usage.prompt_tokens = estimated_prompt_tokens
                self.metrics.token_usage.completion_tokens = estimated_completion_tokens
                self.metrics.token_usage.total_tokens = (
                    estimated_prompt_tokens + estimated_completion_tokens
                )
                self.metrics.metadata["token_estimation"] = True

        # Calculate estimated cost
        self.metrics.estimated_cost = calculate_cost(
            self.metrics.provider, self.metrics.model, self.metrics.token_usage
        )

        logger.debug(
            f"LLM completed: {self.metrics.provider}/{self.metrics.model} "
            f"- {self.metrics.token_usage.total_tokens} tokens "
            f"in {self.metrics.duration_ms:.0f}ms"
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when LLM encounters an error."""
        self.metrics.error = str(error)
        if self._start_time:
            self.metrics.duration_ms = (time.time() - self._start_time) * 1000
        logger.error(f"LLM error: {error}")


# Cost calculation based on public pricing (as of 2024)
# Prices are per 1K tokens
PRICING = {
    "openai": {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    },
    "anthropic": {
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    },
    "google": {
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
        "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
        "gemini-pro": {"input": 0.0005, "output": 0.0015},
    },
    "github_copilot": {
        # GitHub Copilot is subscription-based, not per-token
        # Using reference values based on OpenAI pricing for the same models
        # These are for estimation purposes only
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4.1": {"input": 0.03, "output": 0.06},  # Same as gpt-4
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    },
}


def calculate_cost(provider: str, model: str, usage: TokenUsage) -> float:
    """Calculate estimated cost based on token usage.

    Args:
        provider: Provider name
        model: Model name
        usage: Token usage statistics

    Returns:
        Estimated cost in USD
    """
    # Get pricing for provider/model
    provider_pricing = PRICING.get(provider.lower(), {})
    model_pricing = provider_pricing.get(model.lower())

    if not model_pricing:
        # Try to find a partial match (e.g., "gpt-4-0125-preview" matches "gpt-4")
        for model_key, pricing in provider_pricing.items():
            if model_key in model.lower():
                model_pricing = pricing
                break

    if not model_pricing:
        logger.debug(f"No pricing data for {provider}/{model}")
        return 0.0

    # Calculate cost (prices are per 1K tokens)
    input_cost = (usage.prompt_tokens / 1000) * model_pricing["input"]
    output_cost = (usage.completion_tokens / 1000) * model_pricing["output"]

    return input_cost + output_cost


def format_metrics(metrics: ModelMetrics) -> str:
    """Format metrics for display.

    Args:
        metrics: Model metrics to format

    Returns:
        Formatted string for display
    """
    lines = [
        "\n" + "=" * 50,
        "📊 Telemetry Information",
        "=" * 50,
        f"Provider: {metrics.provider}",
        f"Model: {metrics.model}",
    ]

    if metrics.metadata.get("actual_model"):
        lines.append(f"Actual Model: {metrics.metadata['actual_model']}")

    lines.extend(
        [
            f"Duration: {metrics.duration_ms:.0f}ms",
            "",
            "📝 Token Usage:"
            + (" (estimated)" if metrics.metadata.get("token_estimation") else ""),
            f"  Prompt tokens: {metrics.token_usage.prompt_tokens:,}",
            f"  Completion tokens: {metrics.token_usage.completion_tokens:,}",
            f"  Total tokens: {metrics.token_usage.total_tokens:,}",
        ]
    )

    # Add context information if available (from enhanced LLM)
    if metrics.metadata.get("context_length"):
        context_length = metrics.metadata["context_length"]
        used_tokens = metrics.token_usage.prompt_tokens
        remaining = context_length - used_tokens
        usage_percent = (
            (used_tokens / context_length * 100) if context_length > 0 else 0
        )

        lines.extend(
            [
                "",
                "📊 Context Window:",
                f"  Model limit: {context_length:,} tokens",
                f"  Used: {used_tokens:,} tokens ({usage_percent:.1f}%)",
                f"  Remaining: {remaining:,} tokens",
            ]
        )

        # Add capabilities info if available
        if metrics.metadata.get("max_output_tokens"):
            lines.append(
                f"  Max output: {metrics.metadata['max_output_tokens']:,} tokens"
            )

        # Add model capabilities
        capabilities = []
        if metrics.metadata.get("supports_function_calling"):
            capabilities.append("✓ Functions")
        if metrics.metadata.get("supports_vision"):
            capabilities.append("✓ Vision")

        if capabilities:
            lines.append(f"  Capabilities: {', '.join(capabilities)}")

    if metrics.estimated_cost > 0:
        lines.extend(
            [
                "",
                f"💰 Estimated Cost: ${metrics.estimated_cost:.6f}",
            ]
        )

        # Add note for GitHub Copilot
        if metrics.provider.lower() == "github_copilot":
            lines.append(
                "   Note: GitHub Copilot is subscription-based. "
                "Cost shown is for reference only."
            )

    if metrics.error:
        lines.extend(
            [
                "",
                f"❌ Error: {metrics.error}",
            ]
        )

    lines.append("=" * 50)

    return "\n".join(lines)
