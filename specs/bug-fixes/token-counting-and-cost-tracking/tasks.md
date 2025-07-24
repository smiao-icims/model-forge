# Bug Fix: Token Counting and Cost Tracking - Tasks

## Implementation Tasks

### Phase 1: Token Tracking Infrastructure

- [ ] **TASK-001**: Create telemetry module with core data structures
  - Create `src/modelforge/telemetry.py`
  - Define `TokenUsage` dataclass
  - Define `UsageRecord` for storage
  - Estimated effort: 2 hours

- [ ] **TASK-002**: Implement token usage extraction from LangChain responses
  - Create `extract_token_usage()` function
  - Handle different response formats from various providers
  - Add error handling for missing usage data
  - Estimated effort: 3 hours

- [ ] **TASK-003**: Create response wrapper in registry.py
  - Wrap LLM responses to capture token usage
  - Maintain backward compatibility
  - Pass through all original response data
  - Estimated effort: 3 hours

### Phase 2: Cost Calculation

- [ ] **TASK-004**: Implement cost calculator
  - Create `CostCalculator` class
  - Use pricing data from models.dev
  - Ensure calculations use 1K token units consistently
  - Estimated effort: 2 hours

- [ ] **TASK-005**: Update pricing display for clarity
  - Ensure all pricing displays show "per 1K tokens" explicitly
  - Update CLI output formatting
  - Update any documentation references
  - Estimated effort: 1 hour

### Phase 3: Storage and Reporting

- [ ] **TASK-006**: Implement telemetry storage
  - Create `TelemetryCollector` class
  - Implement JSON file storage in `~/.config/model-forge/telemetry.json`
  - Add configuration for enabling/disabling telemetry
  - Estimated effort: 3 hours

- [ ] **TASK-007**: Add CLI commands for usage reporting
  - Add `--show-usage` flag to existing commands
  - Create `modelforge usage` command for statistics
  - Display token counts and costs in output
  - Estimated effort: 4 hours

### Testing Tasks

- [ ] **TASK-008**: Write unit tests for telemetry module
  - Test `TokenUsage` creation and validation
  - Test cost calculation with various pricing models
  - Test storage and retrieval operations
  - Estimated effort: 3 hours

- [ ] **TASK-009**: Write integration tests
  - Test token tracking with mocked LangChain responses
  - Test CLI commands with usage display
  - Test backward compatibility scenarios
  - Estimated effort: 3 hours

- [ ] **TASK-010**: Test with real providers
  - Manual testing with OpenAI, Anthropic, Google
  - Verify token counts match provider dashboards
  - Test providers without token usage data
  - Estimated effort: 2 hours

### Documentation Tasks

- [ ] **TASK-011**: Update user documentation
  - Document new telemetry features in README
  - Add usage tracking section to CLAUDE.md
  - Create examples of cost calculation
  - Estimated effort: 2 hours

- [ ] **TASK-012**: Add configuration documentation
  - Document telemetry configuration options
  - Explain privacy considerations
  - Show how to export/analyze usage data
  - Estimated effort: 1 hour

### Validation Tasks

- [ ] **TASK-013**: Validate pricing unit consistency
  - Ensure all displays show "per 1K tokens"
  - Verify calculations use consistent units
  - Check models.dev API alignment
  - Estimated effort: 1 hour

- [ ] **TASK-014**: Performance testing
  - Ensure telemetry doesn't slow down API calls
  - Test with high-volume usage
  - Verify storage doesn't grow unbounded
  - Estimated effort: 2 hours

- [ ] **TASK-015**: Security review
  - Ensure no sensitive data is stored
  - Verify file permissions on telemetry storage
  - Review data retention policies
  - Estimated effort: 1 hour

## Total Estimated Effort: ~32 hours

## Implementation Order

1. Start with TASK-001 through TASK-003 (core infrastructure)
2. Implement TASK-008 (tests) alongside infrastructure
3. Move to TASK-004 and TASK-005 (cost calculation)
4. Complete TASK-006 and TASK-007 (storage and CLI)
5. Finish with remaining testing and documentation tasks

## Definition of Done

- All tasks marked as completed
- All tests passing with >90% coverage on new code
- Documentation updated and reviewed
- Manual testing completed with major providers
- No performance regressions observed
- Code reviewed and approved
