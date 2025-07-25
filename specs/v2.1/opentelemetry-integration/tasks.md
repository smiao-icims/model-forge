# OpenTelemetry Integration - Tasks

## Implementation Tasks

### Core Infrastructure (Priority: High)

- [ ] **TASK-001**: Add OpenTelemetry as optional dependency in pyproject.toml
  - Add to extras: `otel = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]`
  - Update installation docs

- [ ] **TASK-002**: Create `otel_utils.py` module
  - Implement `is_otel_available()` function
  - Create `get_tracer()` with caching
  - Add span creation helpers with error handling

- [ ] **TASK-003**: Add OTel configuration to config schema
  - Extend settings with `opentelemetry` section
  - Support enabled/disabled flag
  - Allow custom attributes

### Registry Instrumentation (Priority: High)

- [ ] **TASK-004**: Instrument `ModelForgeRegistry.__init__()`
  - Check if OTel is available
  - Initialize tracer if enabled
  - Store OTel config

- [ ] **TASK-005**: Instrument `ModelForgeRegistry.get_llm()`
  - Create span "modelforge.get_llm"
  - Add attributes: provider, model, llm_type
  - Handle errors gracefully

- [ ] **TASK-006**: Pass OTel context to TelemetryCallback
  - Detect if OTel is enabled
  - Pass flag to callback constructor

### Telemetry Callback Enhancement (Priority: High)

- [ ] **TASK-007**: Update TelemetryCallback constructor
  - Add `otel_enabled` parameter
  - Store tracer reference
  - Initialize span storage

- [ ] **TASK-008**: Instrument `on_llm_start()`
  - Create span "langchain.llm.invoke"
  - Set initial attributes
  - Link to parent span if exists

- [ ] **TASK-009**: Instrument `on_llm_end()`
  - Add token usage attributes
  - Add cost estimation
  - Record duration
  - End span

- [ ] **TASK-010**: Instrument `on_llm_error()`
  - Record exception in span
  - Set error status
  - End span

### Testing (Priority: Medium)

- [ ] **TASK-011**: Unit tests for otel_utils
  - Test availability detection
  - Test tracer creation
  - Test error handling

- [ ] **TASK-012**: Integration tests with OTel enabled
  - Test span creation
  - Test attribute propagation
  - Test parent-child relationships

- [ ] **TASK-013**: Integration tests with OTel disabled
  - Ensure no errors
  - Verify no performance impact
  - Check graceful degradation

- [ ] **TASK-014**: Performance benchmarks
  - Measure overhead with OTel
  - Compare with/without instrumentation
  - Document results

### Documentation (Priority: Medium)

- [ ] **TASK-015**: Create OTel integration guide
  - Installation instructions
  - Basic configuration
  - Example with FastAPI
  - Example with Celery

- [ ] **TASK-016**: Update README
  - Add OTel to feature list
  - Show installation with extras
  - Link to integration guide

- [ ] **TASK-017**: Add OTel examples
  - Standalone script with Jaeger
  - Web app with distributed tracing
  - Export to different backends

### Advanced Features (Priority: Low)

- [ ] **TASK-018**: Streaming support
  - Add span events for chunks
  - Track streaming metrics
  - Handle long-running streams

- [ ] **TASK-019**: Baggage propagation
  - Support OTel baggage
  - Pass user context
  - Document use cases

- [ ] **TASK-020**: Metrics integration (future)
  - Export token counts as metrics
  - Track request rates
  - Monitor costs

## Testing Checklist

- [ ] Manual test with Jaeger locally
- [ ] Test with FastAPI app
- [ ] Test with Celery workers
- [ ] Verify in Datadog APM
- [ ] Verify in New Relic APM
- [ ] Load test for performance

## Acceptance Criteria

- [ ] OTel integration works when enabled
- [ ] No errors when OTel not installed
- [ ] Spans appear in tracing backends
- [ ] Parent-child relationships correct
- [ ] Performance overhead < 1ms
- [ ] All tests pass
- [ ] Documentation complete
