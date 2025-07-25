# OpenTelemetry Integration - Requirements

## Problem Statement

ModelForge currently provides telemetry through LangChain callbacks, capturing token usage, costs, and duration. However, it lacks integration with distributed tracing systems, making it difficult to:

- Track LLM calls within larger distributed systems
- Correlate LLM operations with upstream/downstream services
- Visualize LLM latency in APM tools (Datadog, New Relic, Jaeger)
- Propagate trace context through the entire request lifecycle

## Requirements

### Functional Requirements

- **REQ-001**: Automatic span creation for LLM operations when OpenTelemetry is active
- **REQ-002**: Preserve existing trace context from parent spans
- **REQ-003**: Add relevant attributes to spans (provider, model, token counts, cost)
- **REQ-004**: Support both automatic and manual instrumentation
- **REQ-005**: Work seamlessly when OpenTelemetry is not installed (optional dependency)
- **REQ-006**: Integrate with existing TelemetryCallback without duplication

### Non-Functional Requirements

- **REQ-007**: Zero performance impact when OpenTelemetry is disabled
- **REQ-008**: Minimal overhead when enabled (<1ms per operation)
- **REQ-009**: Follow OpenTelemetry semantic conventions for AI/ML
- **REQ-010**: Support all major OpenTelemetry exporters (OTLP, Jaeger, Zipkin)

## User Stories

### Story 1: Automatic Instrumentation
```python
# User just needs to configure OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())

# ModelForge automatically creates spans
registry = ModelForgeRegistry()
llm = registry.get_llm()  # Span created: "modelforge.get_llm"
response = llm.invoke("Hello")  # Span created: "langchain.llm.invoke"
```

### Story 2: Custom Attributes
```python
# User can add custom attributes
registry = ModelForgeRegistry(
    otel_attributes={
        "environment": "production",
        "team": "ml-platform"
    }
)
```

### Story 3: Trace Context Propagation
```python
# In a FastAPI app
@app.post("/chat")
async def chat(request: ChatRequest):
    # Trace context from HTTP headers is preserved
    llm = registry.get_llm()
    # LLM span is child of the HTTP request span
    response = llm.invoke(request.message)
    return response
```

## Success Criteria

- [ ] LLM operations appear in distributed traces
- [ ] Trace context propagates correctly
- [ ] No breaking changes to existing code
- [ ] Performance overhead < 1ms
- [ ] Works with major APM vendors
- [ ] Clear documentation and examples

## Out of Scope

- Custom OpenTelemetry configuration (users configure their own)
- Metrics and logs (focus on tracing only)
- Automatic HTTP header propagation (handled by HTTP clients)
