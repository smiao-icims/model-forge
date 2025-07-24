# LLM Usage Tracking & Cost Estimation - Tasks

## Implementation Tasks

### Phase 1: Core Telemetry Infrastructure with LangChain Callbacks

- [ ] **TASK-001**: Create `ModelForgeTelemetry` class with configuration support
- [ ] **TASK-002**: Integrate LangChain's `UsageMetadataCallbackHandler` for token tracking
- [ ] **TASK-003**: Implement `CostCalculator` class with 2025 pricing data
- [ ] **TASK-004**: Create `TelemetryConfig` and `SessionConfig` dataclasses
- [ ] **TASK-005**: Update `ModelForgeRegistry.__init__` to accept telemetry configuration
- [ ] **TASK-006**: Modify `ModelForgeRegistry.get_llm()` to attach telemetry callbacks
- [ ] **TASK-007**: Add `get_telemetry()` method to registry for accessing usage data
- [ ] **TASK-008**: Write unit tests for telemetry components

### Phase 2: OpenTelemetry Integration

- [ ] **TASK-009**: Implement `OTelCallbackHandler` extending `BaseCallbackHandler`
- [ ] **TASK-010**: Add OpenTelemetry span creation in `on_llm_start`
- [ ] **TASK-011**: Implement token usage extraction in `on_llm_end`
- [ ] **TASK-012**: Add error handling in `on_llm_error` with span recording
- [ ] **TASK-013**: Follow OpenTelemetry semantic conventions for LLM attributes
- [ ] **TASK-014**: Add configuration for OTel endpoint and exporter
- [ ] **TASK-015**: Create integration tests with OpenTelemetry Collector
- [ ] **TASK-016**: Document OTel span attributes and metrics

### Phase 3: Cost Calculation and Pricing

- [ ] **TASK-017**: Implement comprehensive pricing data for all providers
- [ ] **TASK-018**: Add support for loading custom pricing from JSON file
- [ ] **TASK-019**: Create `add_costs()` method to enhance usage metadata
- [ ] **TASK-020**: Handle model name variations and aliases for pricing
- [ ] **TASK-021**: Add support for cached token pricing (if applicable)
- [ ] **TASK-022**: Write tests for cost calculation accuracy

### Phase 4: Session Management

- [ ] **TASK-023**: Implement `SessionManager` class for tracking aggregated metrics
- [ ] **TASK-024**: Create in-memory storage backend for sessions
- [ ] **TASK-025**: Add file-based persistence for session data
- [ ] **TASK-026**: Implement session TTL and automatic cleanup
- [ ] **TASK-027**: Add session export/import functionality
- [ ] **TASK-028**: Create tests for session management

### Phase 5: CLI Integration

- [ ] **TASK-029**: Create `cli_telemetry.py` module with usage command group
- [ ] **TASK-030**: Implement `usage show` command for viewing statistics
- [ ] **TASK-031**: Add `usage list` command for historical sessions
- [ ] **TASK-032**: Implement `usage export` command with JSON/OTLP formats
- [ ] **TASK-033**: Add `usage clear` command for data cleanup
- [ ] **TASK-034**: Create `usage config` command for telemetry settings
- [ ] **TASK-035**: Add CLI tests and help documentation

### Phase 6: Streaming Support

- [ ] **TASK-036**: Test streaming token usage with `stream_usage=True`
- [ ] **TASK-037**: Ensure callbacks work correctly with streaming responses
- [ ] **TASK-038**: Add streaming-specific attributes to OTel spans
- [ ] **TASK-039**: Document streaming telemetry behavior

### Phase 7: Provider-Specific Enhancements

- [ ] **TASK-040**: Test telemetry with OpenAI models and callbacks
- [ ] **TASK-041**: Verify Anthropic model token tracking
- [ ] **TASK-042**: Test Google Gemini usage metadata
- [ ] **TASK-043**: Handle Ollama local model telemetry
- [ ] **TASK-044**: Add provider-specific cost calculation rules

### Phase 8: Configuration and Setup

- [ ] **TASK-045**: Add telemetry configuration to global config schema
- [ ] **TASK-046**: Create environment variable support for telemetry settings
- [ ] **TASK-047**: Add telemetry configuration to `.model-forge/config.json`
- [ ] **TASK-048**: Document configuration options in README

### Phase 9: Documentation and Examples

- [ ] **TASK-049**: Write telemetry overview documentation
- [ ] **TASK-050**: Create example scripts showing telemetry usage
- [ ] **TASK-051**: Document OpenTelemetry integration guide
- [ ] **TASK-052**: Add troubleshooting guide for telemetry issues
- [ ] **TASK-053**: Update CLAUDE.md with telemetry patterns

## Testing Tasks

- [ ] **TASK-054**: Create mock fixtures for LangChain callbacks
- [ ] **TASK-055**: Write unit tests for all telemetry components
- [ ] **TASK-056**: Add integration tests with real LLM providers
- [ ] **TASK-057**: Create performance benchmarks for callback overhead
- [ ] **TASK-058**: Test telemetry with high-concurrency scenarios
- [ ] **TASK-059**: Verify zero overhead when telemetry is disabled

## Validation Tasks

- [ ] **TASK-060**: Manual testing with each supported provider
- [ ] **TASK-061**: Verify cost calculations match provider billing
- [ ] **TASK-062**: Test OpenTelemetry export to various collectors
- [ ] **TASK-063**: Validate CLI output formatting and usability
- [ ] **TASK-064**: Performance profiling and optimization
- [ ] **TASK-065**: Security review of telemetry data handling

## Migration and Compatibility

- [ ] **TASK-066**: Ensure backward compatibility with existing code
- [ ] **TASK-067**: Create migration guide for users
- [ ] **TASK-068**: Test with existing ModelForge applications
- [ ] **TASK-069**: Verify no breaking changes to public API

## Future Enhancements (Post-Initial Release)

- [ ] **FUTURE-001**: Add Prometheus metrics exporter
- [ ] **FUTURE-002**: Create Grafana dashboard templates
- [ ] **FUTURE-003**: Add budget alerts and notifications
- [ ] **FUTURE-004**: Implement usage prediction models
- [ ] **FUTURE-005**: Add multi-user/team support
- [ ] **FUTURE-006**: Create web UI for usage visualization
- [ ] **FUTURE-007**: Add integration with cloud cost management tools
