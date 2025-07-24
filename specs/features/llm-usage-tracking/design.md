# LLM Usage Tracking & Cost Estimation - Design

## Technical Analysis

ModelForge creates LangChain-compatible LLM instances through a registry pattern. Our research reveals that LangChain already provides comprehensive telemetry support through:

1. **Native Callbacks**: `UsageMetadataCallbackHandler` for token tracking
2. **Provider Callbacks**: `get_openai_callback()` includes cost calculation
3. **Streaming Support**: `stream_usage=True` for real-time token counting
4. **Extensible System**: Custom callbacks can bridge to any telemetry backend

The industry has converged on OpenTelemetry as the standard for observability, with major platforms (LangSmith, Langfuse) adopting OTel in 2025.

### Key Design Decisions

1. **Leverage Native Support**: Use LangChain's built-in callbacks rather than wrapping LLMs
2. **OpenTelemetry Bridge**: Create a callback handler that exports to OTel
3. **Minimal Overhead**: Callbacks only active when telemetry is enabled
4. **Provider Agnostic**: Works with any LangChain-compatible model

## Solution Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        User Code                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   ModelForgeRegistry                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            get_llm() + telemetry callbacks           │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │                                     │
│  ┌─────────────────────▼───────────────────────────────┐    │
│  │              ModelForgeTelemetry                     │    │
│  │  - UsageMetadataCallbackHandler (native)           │    │
│  │  - OTelCallbackHandler (bridge)                    │    │
│  │  - CostCalculator                                  │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │                                     │
│  ┌─────────────────────▼───────────────────────────────┐    │
│  │          LangChain Model (with callbacks)            │    │
│  │  - Automatic token tracking via callbacks           │    │
│  │  - Native streaming support                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              OpenTelemetry Collector (Optional)              │
└─────────────────────────────────────────────────────────────┘
```

### Component Design

#### 1. ModelForgeTelemetry Class

```python
class ModelForgeTelemetry:
    """Unified telemetry for ModelForge using LangChain callbacks."""

    def __init__(self, config: TelemetryConfig):
        self.config = config
        self.callbacks = []

        if config.enabled:
            # Always use native token tracking
            self.usage_callback = UsageMetadataCallbackHandler()
            self.callbacks.append(self.usage_callback)

            # Add OpenTelemetry if configured
            if config.backend == "opentelemetry":
                self.otel_callback = OTelCallbackHandler(config.otel_endpoint)
                self.callbacks.append(self.otel_callback)

            # Add cost tracking
            self.cost_calculator = CostCalculator()

            # Session management
            self.session = SessionManager(config.session_config)

    def get_callbacks(self) -> List[BaseCallbackHandler]:
        """Return callbacks to attach to LLM."""
        return self.callbacks

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get aggregated usage with costs."""
        usage = self.usage_callback.usage_metadata
        return self.cost_calculator.add_costs(usage)
```

#### 2. OTelCallbackHandler

```python
class OTelCallbackHandler(BaseCallbackHandler):
    """Bridge LangChain callbacks to OpenTelemetry."""

    def __init__(self, endpoint: str):
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer("modelforge")
        self.spans = {}

    def on_llm_start(self, serialized: Dict, prompts: List[str], **kwargs):
        """Start a new span when LLM is invoked."""
        span = self.tracer.start_span("llm.invoke")
        span.set_attributes({
            "llm.system": "modelforge",
            "llm.request.model": serialized.get("name", "unknown"),
            "llm.request.max_tokens": serialized.get("max_tokens"),
            "llm.request.temperature": serialized.get("temperature"),
        })
        self.spans[kwargs["run_id"]] = span

    def on_llm_end(self, response: LLMResult, **kwargs):
        """End span and record token usage."""
        run_id = kwargs["run_id"]
        if run_id in self.spans:
            span = self.spans[run_id]

            # Extract token usage from response
            if hasattr(response, 'llm_output') and response.llm_output:
                usage = response.llm_output.get('token_usage', {})
                span.set_attributes({
                    "llm.usage.prompt_tokens": usage.get('prompt_tokens', 0),
                    "llm.usage.completion_tokens": usage.get('completion_tokens', 0),
                    "llm.usage.total_tokens": usage.get('total_tokens', 0),
                })

            span.set_status(Status(StatusCode.OK))
            span.end()
            del self.spans[run_id]

    def on_llm_error(self, error: Exception, **kwargs):
        """Record errors in span."""
        run_id = kwargs.get("run_id")
        if run_id in self.spans:
            span = self.spans[run_id]
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.end()
            del self.spans[run_id]
```

#### 3. Cost Calculator

```python
class CostCalculator:
    """Calculate costs based on token usage and provider pricing."""

    # Pricing per 1M tokens in USD (2025 rates)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    }

    def calculate_cost(self, model: str, usage: Dict[str, int]) -> Decimal:
        """Calculate cost for given token usage."""
        if model not in self.PRICING:
            return Decimal("0.00")

        pricing = self.PRICING[model]
        input_cost = (usage.get("input_tokens", 0) / 1_000_000) * pricing["input"]
        output_cost = (usage.get("output_tokens", 0) / 1_000_000) * pricing["output"]

        return Decimal(str(input_cost + output_cost)).quantize(Decimal("0.000001"))

    def add_costs(self, usage_metadata: Dict[str, Dict]) -> Dict[str, Any]:
        """Add cost calculations to usage metadata."""
        result = {"models": {}, "total_cost": Decimal("0.00")}

        for model, usage in usage_metadata.items():
            cost = self.calculate_cost(model, usage)
            result["models"][model] = {
                **usage,
                "cost_usd": str(cost)
            }
            result["total_cost"] += cost

        result["total_cost"] = str(result["total_cost"])
        return result
```

#### 4. Integration with Registry

```python
class ModelForgeRegistry:
    """Updated to support telemetry."""

    def __init__(self, config_manager=None, enable_telemetry=False,
                 telemetry_config=None):
        self.config_manager = config_manager or ConfigManager()

        # Initialize telemetry
        if enable_telemetry:
            telemetry_config = telemetry_config or TelemetryConfig()
            self.telemetry = ModelForgeTelemetry(telemetry_config)
        else:
            self.telemetry = None

    def get_llm(self, provider_name=None, model_alias=None, **kwargs):
        """Get LLM with telemetry callbacks attached."""
        # ... existing logic ...

        # Merge telemetry callbacks with any user-provided callbacks
        if self.telemetry:
            callbacks = kwargs.get("callbacks", [])
            callbacks.extend(self.telemetry.get_callbacks())
            kwargs["callbacks"] = callbacks

        # Create LLM with callbacks
        llm = self._create_llm(provider_config, **kwargs)
        return llm

    def get_telemetry(self) -> Optional[ModelForgeTelemetry]:
        """Access telemetry instance for usage data."""
        return self.telemetry
```

### Configuration Schema

```python
@dataclass
class TelemetryConfig:
    """Configuration for telemetry features."""
    enabled: bool = False
    backend: str = "native"  # "native", "opentelemetry"
    otel_endpoint: Optional[str] = None
    pricing_config: Optional[str] = None  # Path to custom pricing JSON
    session_config: SessionConfig = field(default_factory=SessionConfig)

@dataclass
class SessionConfig:
    """Configuration for session management."""
    storage_backend: str = "memory"  # "memory", "file"
    storage_path: Optional[str] = None
    auto_save: bool = True
    ttl_seconds: int = 3600
```

### CLI Integration

```python
# src/modelforge/cli_telemetry.py
@click.group("usage")
def usage_group():
    """Manage and view LLM usage statistics."""
    pass

@usage_group.command("show")
@click.option("--session", default="current", help="Session ID or 'current'")
def show_usage(session):
    """Show usage statistics for a session."""
    registry = ModelForgeRegistry(enable_telemetry=True)
    telemetry = registry.get_telemetry()

    if not telemetry:
        click.echo("Telemetry is not enabled")
        return

    summary = telemetry.get_usage_summary()

    # Display formatted output
    for model, data in summary["models"].items():
        click.echo(f"\n{model}:")
        click.echo(f"  Input tokens: {data['input_tokens']:,}")
        click.echo(f"  Output tokens: {data['output_tokens']:,}")
        click.echo(f"  Total tokens: {data['total_tokens']:,}")
        click.echo(f"  Cost: ${data['cost_usd']}")

    click.echo(f"\nTotal cost: ${summary['total_cost']}")

@usage_group.command("export")
@click.option("--format", type=click.Choice(["json", "otlp"]), default="json")
@click.option("--output", help="Output file or endpoint")
def export_usage(format, output):
    """Export usage data in specified format."""
    # Implementation for exporting telemetry data
```

## Implementation Strategy

### Phase 1: Core Telemetry Infrastructure
1. Implement `ModelForgeTelemetry` class with native callbacks
2. Integrate `UsageMetadataCallbackHandler` for token tracking
3. Add basic cost calculation with hardcoded pricing
4. Update `ModelForgeRegistry` to attach callbacks

### Phase 2: OpenTelemetry Integration
1. Implement `OTelCallbackHandler` following semantic conventions
2. Add configuration for OTel endpoint
3. Test with OpenTelemetry Collector
4. Document span attributes and metrics

### Phase 3: Session Management
1. Implement session tracking for aggregated metrics
2. Add in-memory storage backend
3. Create file-based persistence option
4. Add session TTL and cleanup

### Phase 4: CLI and User Experience
1. Implement CLI commands for usage viewing
2. Add export functionality
3. Create configuration commands
4. Write user documentation

## Testing Strategy

### Unit Tests
- Test callback handlers with mock LLM responses
- Verify cost calculations with known inputs
- Test OTel span creation and attributes
- Mock LangChain callback system

### Integration Tests
- Test with real LangChain models
- Verify token counting accuracy
- Test OTel export to collector
- Validate streaming token tracking

### Performance Tests
- Measure overhead with telemetry enabled/disabled
- Test callback performance with high throughput
- Memory usage profiling
- Verify zero overhead when disabled

## Backward Compatibility

- Telemetry is disabled by default
- Existing API remains unchanged
- Callbacks are additive, not replacing existing functionality
- Configuration follows existing ModelForge patterns
- All changes are backward compatible
