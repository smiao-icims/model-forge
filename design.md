# Model-Forge Enhancement Design

## 1. Overview

This design document outlines the technical approach for enhancing model-forge to expose model metadata and configuration capabilities required by Browser Pilot. The design prioritizes backward compatibility while adding new functionality through a wrapper pattern.

## 2. Architecture Overview

### 2.1 Current Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Browser Pilot   │────▶│ ModelForgeRegistry│────▶│ LangChain Models│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │ ModelsDevClient  │
                        └──────────────────┘
```

### 2.2 Enhanced Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Browser Pilot   │────▶│ ModelForgeRegistry│────▶│ EnhancedLLM     │
└─────────────────┘     └──────────────────┘     │ (Wrapper)       │
                                │                 └─────────────────┘
                                │                          │
                                ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ ModelsDevClient  │     │ LangChain Models│
                        └──────────────────┘     └─────────────────┘
```

## 3. Detailed Design

### 3.1 EnhancedLLM Wrapper Class

```python
from typing import Any, Dict, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

class EnhancedLLM(BaseChatModel):
    """
    Wrapper class that adds metadata and configuration capabilities
    to standard LangChain models while maintaining full compatibility.
    """

    def __init__(
        self,
        wrapped_llm: BaseChatModel,
        model_metadata: Dict[str, Any],
        provider: str,
        model_alias: str
    ):
        super().__init__()
        self._wrapped_llm = wrapped_llm
        self._metadata = model_metadata
        self._provider = provider
        self._model_alias = model_alias
        self._custom_params = {}

    # Metadata Properties
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
    def model_info(self) -> Dict[str, Any]:
        """Full model metadata from models.dev."""
        return self._metadata.copy()

    @property
    def pricing_info(self) -> Dict[str, Any]:
        """Pricing information per 1M tokens."""
        pricing = self._metadata.get("pricing", {})
        return {
            "input_per_1m": pricing.get("input_per_1m_tokens", 0.0),
            "output_per_1m": pricing.get("output_per_1m_tokens", 0.0),
            "currency": "USD"
        }

    # Parameter Configuration
    @property
    def temperature(self) -> Optional[float]:
        return self._custom_params.get("temperature",
                                      getattr(self._wrapped_llm, "temperature", None))

    @temperature.setter
    def temperature(self, value: float) -> None:
        self.validate_parameters({"temperature": value})
        self._custom_params["temperature"] = value
        if hasattr(self._wrapped_llm, "temperature"):
            self._wrapped_llm.temperature = value

    # Validation and Cost Estimation
    def validate_parameters(self, params: Dict[str, Any]) -> None:
        """Validate parameters against model capabilities."""
        if "max_tokens" in params:
            if params["max_tokens"] > self.max_output_tokens:
                raise ValueError(
                    f"max_tokens ({params['max_tokens']}) exceeds model limit "
                    f"({self.max_output_tokens})"
                )

        if "temperature" in params:
            if not 0 <= params["temperature"] <= 2:
                raise ValueError("temperature must be between 0 and 2")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for given token counts."""
        pricing = self.pricing_info
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
        return input_cost + output_cost

    # Delegate all LangChain methods to wrapped model
    def _generate(self, messages, stop=None, **kwargs):
        # Apply custom parameters
        merged_kwargs = {**self._custom_params, **kwargs}
        return self._wrapped_llm._generate(messages, stop=stop, **merged_kwargs)

    # ... delegate other required methods ...
```

### 3.2 Registry Enhancement

```python
class ModelForgeRegistry:
    def get_llm(
        self,
        provider_name: str | None = None,
        model_alias: str | None = None,
        callbacks: list[Any] | None = None,
        enhanced: bool = None  # New parameter, defaults to None for gradual rollout
    ) -> BaseChatModel:
        """
        Get a fully authenticated and configured LLM instance.

        Args:
            enhanced: If True, returns EnhancedLLM with metadata.
                     If False, returns raw LangChain model (backward compat).
        """
        # ... existing code to get provider/model config ...

        # Handle enhanced parameter with gradual rollout
        if enhanced is None:
            enhanced = os.getenv("MODELFORGE_ENHANCED", "false").lower() == "true"
            if not enhanced:
                warnings.warn(
                    "Starting in model-forge v2.3.0, get_llm() will return "
                    "EnhancedLLM by default. Set enhanced=False to keep current "
                    "behavior or set MODELFORGE_ENHANCED=true to opt-in early.",
                    FutureWarning
                )

        # Create base LLM as before
        base_llm = self._create_llm_instance(
            provider_name, model_alias, provider_data, model_data, callbacks
        )

        if not enhanced:
            return base_llm

        # Fetch metadata from models.dev
        metadata = self._fetch_model_metadata(provider_name, model_alias)

        # Wrap in EnhancedLLM
        return EnhancedLLM(
            wrapped_llm=base_llm,
            model_metadata=metadata,
            provider=provider_name,
            model_alias=model_alias
        )

    def _fetch_model_metadata(self, provider: str, model: str) -> Dict[str, Any]:
        """Fetch and cache model metadata from models.dev."""
        try:
            client = ModelsDevClient()
            model_info = client.get_model_info(provider, model)

            # Transform to our metadata format
            return {
                "context_length": model_info.get("limit", {}).get("context", 0),
                "max_tokens": model_info.get("limit", {}).get("output", 0),
                "capabilities": client._extract_capabilities(model_info),
                "pricing": client._extract_pricing(model_info),
                "knowledge_cutoff": model_info.get("knowledge_cutoff"),
                "raw_info": model_info  # Keep raw data for model_info property
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metadata for {provider}/{model}: {e}")
            # Return safe defaults
            return {
                "context_length": 0,
                "max_tokens": 0,
                "capabilities": [],
                "pricing": {},
                "raw_info": {}
            }
```

### 3.3 Parameter Handling Strategy

Each provider handles parameters differently. Our design accommodates this:

1. **OpenAI/OpenAI-compatible**: Direct parameter support via constructor
2. **Google GenAI**: Parameters via `generation_config`
3. **Ollama**: Limited parameter support
4. **GitHub Copilot**: Uses underlying OpenAI interface

The EnhancedLLM wrapper handles these differences transparently.

### 3.4 Metadata Caching Strategy

- Leverage existing ModelsDevClient caching (7-day TTL for model info)
- Store metadata in EnhancedLLM instance for fast access
- Refresh metadata on explicit request or cache expiry

## 4. Implementation Phases

### Phase 1: Core Wrapper Implementation
- Create EnhancedLLM class with metadata properties
- Implement delegation pattern for LangChain compatibility
- Add basic parameter setters/getters

### Phase 2: Registry Integration
- Modify ModelForgeRegistry.get_llm() to return EnhancedLLM
- Add metadata fetching logic
- Ensure backward compatibility with `enhanced=False` parameter

### Phase 3: Advanced Features
- Implement parameter validation
- Add cost estimation methods
- Create model discovery/filtering utilities

### Phase 4: Testing and Documentation
- Comprehensive unit tests for all new features
- Integration tests with each provider
- Update documentation and examples

## 5. Error Handling

All errors follow model-forge conventions:

```python
class MetadataNotAvailableError(ModelForgeError):
    def __init__(self, provider: str, model: str):
        super().__init__(
            f"Metadata not available for {provider}/{model}",
            context="models.dev may be unavailable or model not found",
            suggestion="Check network connection or try with enhanced=False",
            error_code="METADATA_UNAVAILABLE"
        )
```

## 6. Testing Strategy

### Unit Tests
- Test EnhancedLLM wrapper with mock LangChain models
- Test metadata property access
- Test parameter validation logic
- Test cost calculation accuracy

### Integration Tests
- Test with real providers (OpenAI, Google, etc.)
- Test metadata retrieval from models.dev
- Test parameter application in actual API calls
- Test backward compatibility

### Performance Tests
- Measure overhead of wrapper pattern
- Verify caching effectiveness
- Ensure <100ms additional latency

## 7. Migration Strategy

1. **Default to Enhanced**: New get_llm() calls return EnhancedLLM by default
2. **Opt-out Available**: Users can set `enhanced=False` for raw models
3. **Gradual Adoption**: Browser Pilot can adopt features incrementally
4. **No Breaking Changes**: All existing code continues to work

## 8. Future Enhancements

- **Streaming Support**: Extend metadata to streaming responses
- **Token Counting**: Built-in token counting utilities
- **Model Recommendations**: Suggest models based on requirements
- **Cost Budgets**: Track cumulative costs against budgets
- **Custom Providers**: Allow metadata for custom providers

## 9. Security Considerations

- No sensitive data in cached metadata
- API keys remain in secure storage
- Metadata requests use existing auth mechanisms
- No new security surface area introduced
