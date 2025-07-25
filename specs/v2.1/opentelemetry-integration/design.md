# OpenTelemetry Integration - Design

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User App with  │────▶│   ModelForge     │────▶│  LangChain LLM  │
│  OTel Tracer    │     │  (Instrumented)  │     │   (Callbacks)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                        │                         │
         └────────────────────────┴─────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   OTel Collector   │
                    │  or APM Backend    │
                    └────────────────────┘
```

## Design Decisions

### 1. Optional Dependency
- OpenTelemetry will be an optional dependency
- Use dynamic imports to avoid breaking non-OTel users
- Gracefully degrade when OTel is not available

### 2. Instrumentation Points

#### Registry Level
```python
# In ModelForgeRegistry.get_llm()
with tracer.start_as_current_span("modelforge.get_llm") as span:
    span.set_attribute("provider", provider_name)
    span.set_attribute("model", model_alias)
    span.set_attribute("llm_type", llm_type)
```

#### Enhanced Telemetry Callback
```python
class TelemetryCallback(BaseCallbackHandler):
    def __init__(self, provider: str, model: str, otel_enabled: bool = None):
        # Auto-detect if not specified
        self.otel_enabled = otel_enabled or is_otel_available()
        self.span = None

    def on_llm_start(self, ...):
        if self.otel_enabled:
            self.span = tracer.start_span("langchain.llm.invoke")
            self.span.set_attribute("llm.vendor", self.provider)
            self.span.set_attribute("llm.request.model", self.model)

    def on_llm_end(self, response: LLMResult, ...):
        if self.span:
            # Add token usage and cost
            self.span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
            self.span.set_attribute("llm.usage.completion_tokens", completion_tokens)
            self.span.set_attribute("llm.usage.total_tokens", total_tokens)
            self.span.set_attribute("llm.usage.cost_usd", cost)
            self.span.end()
```

### 3. Semantic Conventions

Follow emerging OpenTelemetry semantic conventions for LLM:
- `llm.vendor` - Provider name (openai, anthropic, etc.)
- `llm.request.model` - Model identifier
- `llm.request.max_tokens` - Token limit
- `llm.response.model` - Actual model used
- `llm.usage.prompt_tokens` - Input token count
- `llm.usage.completion_tokens` - Output token count
- `llm.usage.total_tokens` - Total tokens
- Custom: `llm.usage.cost_usd` - Estimated cost

### 4. Configuration

```python
# In config.py
{
    "telemetry": {
        "show_metrics": true,
        "opentelemetry": {
            "enabled": true,  # Auto-detect by default
            "service_name": "modelforge",
            "attributes": {
                "environment": "production"
            }
        }
    }
}
```

## Implementation Strategy

### Phase 1: Core Integration
1. Add OpenTelemetry as optional dependency
2. Create `otel_utils.py` with helper functions
3. Instrument `ModelForgeRegistry.get_llm()`
4. Enhance `TelemetryCallback` with OTel support

### Phase 2: Advanced Features
1. Streaming support (span events for chunks)
2. Error handling (record exceptions in spans)
3. Sampling configuration
4. Custom span processors

### Phase 3: Testing & Documentation
1. Unit tests with OTel enabled/disabled
2. Integration tests with mock collectors
3. Documentation and examples
4. Performance benchmarks

## Error Handling

- If OTel initialization fails, log warning and continue
- Never let OTel errors break LLM functionality
- Use try/except around all OTel operations

## Performance Considerations

- Lazy import OpenTelemetry modules
- Cache tracer instances
- Use sampling for high-volume applications
- Batch span exports
