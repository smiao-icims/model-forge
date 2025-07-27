"""Enhanced LLM wrapper that adds metadata and configuration capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

if TYPE_CHECKING:
    pass


class EnhancedLLM(BaseChatModel):
    """
    Enhanced LLM wrapper that adds metadata and configuration capabilities
    to standard LangChain models while maintaining full compatibility.

    This class wraps any LangChain chat model and adds:
    - Model metadata properties (context length, capabilities, etc.)
    - Parameter configuration and validation
    - Cost estimation utilities
    - Full delegation to maintain compatibility

    Example:
        >>> llm = registry.get_llm("openai", "gpt-4", enhanced=True)
        >>> print(f"Context length: {llm.context_length}")
        >>> print(f"Supports vision: {llm.supports_vision}")
        >>> llm.temperature = 0.7  # Set parameters
        >>> cost = llm.estimate_cost(1000, 500)  # Estimate costs
    """

    # Pydantic fields
    _wrapped_llm: BaseChatModel
    _metadata: dict[str, Any]
    _provider: str
    _model_alias: str
    _custom_params: dict[str, Any]

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
        extra = "forbid"

    def __init__(
        self,
        wrapped_llm: BaseChatModel,
        model_metadata: dict[str, Any],
        provider: str,
        model_alias: str,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Enhanced LLM wrapper.

        Args:
            wrapped_llm: The base LangChain model to wrap
            model_metadata: Metadata from models.dev including capabilities
            provider: Provider name (e.g., "openai", "google")
            model_alias: Model alias (e.g., "gpt-4", "gemini-pro")
            **kwargs: Additional keyword arguments for parent class
        """
        # Extract callbacks from wrapped model if present
        if hasattr(wrapped_llm, "callbacks") and wrapped_llm.callbacks:
            kwargs["callbacks"] = wrapped_llm.callbacks

        # Initialize parent without the wrapped model as a field
        super().__init__(**kwargs)

        # Set our private attributes
        object.__setattr__(self, "_wrapped_llm", wrapped_llm)
        object.__setattr__(self, "_metadata", model_metadata)
        object.__setattr__(self, "_provider", provider)
        object.__setattr__(self, "_model_alias", model_alias)
        object.__setattr__(self, "_custom_params", {})

    # ===== Metadata Properties =====

    @property
    def context_length(self) -> int:
        """Maximum context window in tokens."""
        return self._metadata.get("context_length", 0)

    @property
    def max_output_tokens(self) -> int:
        """Maximum output tokens the model can generate."""
        return self._metadata.get("max_tokens", 0)

    @property
    def supports_function_calling(self) -> bool:
        """Whether the model supports function/tool calling."""
        capabilities = self._metadata.get("capabilities", [])
        return "function_calling" in capabilities

    @property
    def supports_vision(self) -> bool:
        """Whether the model supports image inputs."""
        capabilities = self._metadata.get("capabilities", [])
        return "vision" in capabilities

    @property
    def model_info(self) -> dict[str, Any]:
        """Full model metadata from models.dev."""
        return self._metadata.get("raw_info", self._metadata).copy()

    @property
    def pricing_info(self) -> dict[str, Any]:
        """
        Pricing information per 1M tokens.

        Returns:
            Dict with keys:
            - input_per_1m: Cost per 1M input tokens
            - output_per_1m: Cost per 1M output tokens
            - currency: Currency code (default "USD")
        """
        pricing = self._metadata.get("pricing", {})
        return {
            "input_per_1m": pricing.get("input_per_1m_tokens", 0.0),
            "output_per_1m": pricing.get("output_per_1m_tokens", 0.0),
            "currency": "USD",
        }

    # ===== Parameter Configuration =====

    @property
    def temperature(self) -> float | None:
        """Model temperature for randomness (0.0-2.0)."""
        return self._custom_params.get(
            "temperature", getattr(self._wrapped_llm, "temperature", None)
        )

    @temperature.setter
    def temperature(self, value: float) -> None:
        """Set model temperature with validation."""
        self.validate_parameters({"temperature": value})
        self._custom_params["temperature"] = value
        if hasattr(self._wrapped_llm, "temperature"):
            self._wrapped_llm.temperature = value

    @property
    def top_p(self) -> float | None:
        """Nucleus sampling parameter (0.0-1.0)."""
        return self._custom_params.get(
            "top_p", getattr(self._wrapped_llm, "top_p", None)
        )

    @top_p.setter
    def top_p(self, value: float) -> None:
        """Set top_p parameter with validation."""
        self.validate_parameters({"top_p": value})
        self._custom_params["top_p"] = value
        if hasattr(self._wrapped_llm, "top_p"):
            self._wrapped_llm.top_p = value

    @property
    def top_k(self) -> int | None:
        """Top K sampling parameter."""
        return self._custom_params.get(
            "top_k", getattr(self._wrapped_llm, "top_k", None)
        )

    @top_k.setter
    def top_k(self, value: int) -> None:
        """Set top_k parameter."""
        self._custom_params["top_k"] = value
        if hasattr(self._wrapped_llm, "top_k"):
            self._wrapped_llm.top_k = value

    @property
    def max_tokens(self) -> int | None:
        """Maximum tokens to generate."""
        return self._custom_params.get(
            "max_tokens", getattr(self._wrapped_llm, "max_tokens", None)
        )

    @max_tokens.setter
    def max_tokens(self, value: int) -> None:
        """Set max_tokens with validation."""
        self.validate_parameters({"max_tokens": value})
        self._custom_params["max_tokens"] = value
        if hasattr(self._wrapped_llm, "max_tokens"):
            self._wrapped_llm.max_tokens = value

    # ===== Validation and Cost Estimation =====

    def validate_parameters(self, params: dict[str, Any]) -> None:
        """
        Validate parameters against model capabilities.

        Args:
            params: Parameters to validate

        Raises:
            ValueError: If parameters are invalid
        """
        if (
            "max_tokens" in params
            and self.max_output_tokens > 0
            and params["max_tokens"] > self.max_output_tokens
        ):
            raise ValueError(
                f"max_tokens ({params['max_tokens']}) exceeds model limit "
                f"({self.max_output_tokens})"
            )

        if "temperature" in params and not 0 <= params["temperature"] <= 2:
            raise ValueError("temperature must be between 0 and 2")

        if "top_p" in params and not 0 <= params["top_p"] <= 1:
            raise ValueError("top_p must be between 0 and 1")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for given token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = self.pricing_info
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
        return input_cost + output_cost

    # ===== LangChain Method Delegation =====

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Generate a chat response by delegating to wrapped model.

        This method applies custom parameters before delegating.
        """
        # Merge custom parameters with provided kwargs
        merged_kwargs = {**self._custom_params, **kwargs}

        # Delegate to wrapped model
        return self._wrapped_llm._generate(
            messages, stop=stop, run_manager=run_manager, **merged_kwargs
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generation by delegating to wrapped model."""
        merged_kwargs = {**self._custom_params, **kwargs}
        return await self._wrapped_llm._agenerate(
            messages, stop=stop, run_manager=run_manager, **merged_kwargs
        )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Any:
        """Stream responses by delegating to wrapped model."""
        merged_kwargs = {**self._custom_params, **kwargs}
        return self._wrapped_llm._stream(
            messages, stop=stop, run_manager=run_manager, **merged_kwargs
        )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Async stream responses by delegating to wrapped model."""
        merged_kwargs = {**self._custom_params, **kwargs}
        async for chunk in self._wrapped_llm._astream(
            messages, stop=stop, run_manager=run_manager, **merged_kwargs
        ):
            yield chunk

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[
        PromptValue
        | str
        | Sequence[BaseMessage | list[str] | tuple[str, str] | str | dict[str, Any]],
        BaseMessage,
    ]:
        """Bind tools by delegating to wrapped model."""
        return self._wrapped_llm.bind_tools(tools, tool_choice=tool_choice, **kwargs)

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        """Bind structured output schema by delegating to wrapped model."""
        return self._wrapped_llm.with_structured_output(schema, **kwargs)

    def bind(self, **kwargs: Any) -> Any:
        """Bind parameters by delegating to wrapped model."""
        return self._wrapped_llm.bind(**kwargs)

    @property
    def _llm_type(self) -> str:
        """Return the LLM type from wrapped model."""
        return getattr(self._wrapped_llm, "_llm_type", "enhanced")

    @property
    def _identifying_params(self) -> dict[str, Any]:
        """Return identifying parameters."""
        base_params = getattr(self._wrapped_llm, "_identifying_params", {})
        return {
            **base_params,
            "enhanced": True,
            "provider": self._provider,
            "model_alias": self._model_alias,
        }

    # ===== Attribute Delegation =====

    def __getattr__(self, name: str) -> Any:
        """
        Delegate unknown attributes to wrapped model.

        This ensures compatibility with provider-specific attributes.
        """
        return getattr(self._wrapped_llm, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Handle attribute setting with delegation.

        Enhanced attributes are handled by this class,
        others are delegated to the wrapped model.
        """
        # List of attributes handled by EnhancedLLM
        enhanced_attrs = {
            "_wrapped_llm",
            "_metadata",
            "_provider",
            "_model_alias",
            "_custom_params",
            "temperature",
            "top_p",
            "top_k",
            "max_tokens",
        }

        if name in enhanced_attrs or name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            # Delegate to wrapped model
            setattr(self._wrapped_llm, name, value)

    # ===== Serialization Support =====

    def __getstate__(self) -> dict[str, Any]:
        """Support pickling of the enhanced LLM."""
        return {
            "wrapped_llm": self._wrapped_llm,
            "metadata": self._metadata,
            "provider": self._provider,
            "model_alias": self._model_alias,
            "custom_params": self._custom_params,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Support unpickling of the enhanced LLM."""
        object.__setattr__(self, "_wrapped_llm", state["wrapped_llm"])
        object.__setattr__(self, "_metadata", state["metadata"])
        object.__setattr__(self, "_provider", state["provider"])
        object.__setattr__(self, "_model_alias", state["model_alias"])
        object.__setattr__(self, "_custom_params", state["custom_params"])

    def __repr__(self) -> str:
        """String representation of the enhanced LLM."""
        return (
            f"EnhancedLLM(provider={self._provider}, "
            f"model={self._model_alias}, "
            f"context_length={self.context_length})"
        )
