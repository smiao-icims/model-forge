# LLM Usage Tracking & Cost Estimation - Requirements

## Problem Statement

ModelForge users need visibility into their LLM usage patterns, including execution time, token consumption, context length, and associated costs. Currently, there's no built-in mechanism to track these metrics, making it difficult to:
- Monitor and optimize LLM usage
- Estimate and control costs
- Debug performance issues
- Analyze usage patterns across sessions
- Export telemetry to observability platforms

## Context

Research shows that LangChain (the underlying framework for ModelForge) already provides:
- Native token tracking via `UsageMetadataCallbackHandler`
- Provider-specific callbacks (e.g., `get_openai_callback`) with cost tracking
- Built-in callback system for extensibility
- Support for streaming with token usage (`stream_usage=True`)

The industry standard for observability is OpenTelemetry (OTel), with major platforms like LangSmith and Langfuse having migrated to OTel-based architectures in 2025.

## Requirements

### Functional Requirements

- **REQ-001**: Leverage LangChain's native `UsageMetadataCallbackHandler` for token tracking
- **REQ-002**: Integrate OpenTelemetry for standards-based telemetry export
- **REQ-003**: Calculate and track cost estimates using provider-specific pricing models
- **REQ-004**: Support session-based tracking to aggregate metrics across multiple requests
- **REQ-005**: Provide both programmatic API and CLI access to usage data
- **REQ-006**: Support configurable telemetry backends (native callbacks, OpenTelemetry, custom)
- **REQ-007**: Allow telemetry to be enabled/disabled via configuration
- **REQ-008**: Bridge LangChain callbacks to OpenTelemetry spans for unified observability
- **REQ-009**: Track streaming token usage when supported by the provider

### Non-Functional Requirements

- **REQ-010**: Zero performance overhead when telemetry is disabled
- **REQ-011**: Minimal overhead (<2% latency) when using native LangChain callbacks
- **REQ-012**: No breaking changes to existing ModelForge API
- **REQ-013**: Telemetry failures should not affect LLM operations
- **REQ-014**: Support for all LangChain-compatible models
- **REQ-015**: Follow OpenTelemetry semantic conventions for LLM observability

## Success Criteria

- [ ] Users can enable telemetry with a simple configuration flag
- [ ] Token usage is captured via native LangChain callbacks
- [ ] OpenTelemetry spans include LLM-specific attributes
- [ ] Cost estimates match provider billing within 5%
- [ ] Session aggregation works across different providers
- [ ] CLI commands display usage statistics clearly
- [ ] Telemetry can export to any OTel-compatible backend
- [ ] All existing tests continue to pass

## User Stories

1. **As a developer**, I want to track token usage per request using LangChain's native support
2. **As a team lead**, I want to monitor total LLM costs across sessions to stay within budget
3. **As a DevOps engineer**, I want to export telemetry to our existing OpenTelemetry infrastructure
4. **As a developer**, I want to see real-time token usage during streaming responses
5. **As a user**, I want telemetry to be optional with zero impact when disabled
6. **As an ops engineer**, I want spans to follow OTel semantic conventions for easy querying

## Example Usage

```python
# Enable telemetry with native callbacks
from modelforge import ModelForgeRegistry

registry = ModelForgeRegistry(enable_telemetry=True)
llm = registry.get_llm()

# Use LLM normally - telemetry happens automatically
response = llm.invoke("What is the capital of France?")

# Access usage data
telemetry = registry.get_telemetry()
print(f"Total tokens: {telemetry.get_usage_summary()}")
print(f"Estimated cost: ${telemetry.get_total_cost()}")

# Or with OpenTelemetry export
registry = ModelForgeRegistry(
    enable_telemetry=True,
    telemetry_backend="opentelemetry",
    otel_endpoint="http://localhost:4317"
)

# CLI usage
$ modelforge usage show --session latest
$ modelforge usage export --format otlp --endpoint http://collector:4317
```

## Out of Scope

- Custom telemetry backends beyond OTel
- Real-time streaming dashboards
- Direct integration with specific APM vendors
- Retroactive tracking of past usage
- Modifying LangChain's callback behavior
