# Bug Fix: Token Counting and Cost Tracking - Requirements

## Problem Statement

The current implementation displays token pricing using "per 1K tokens" as the unit, which may be inconsistent with industry standards where pricing is typically shown "per 1M tokens". Additionally, the system lacks comprehensive token usage tracking and telemetry for cost calculation.

## Root Cause Analysis

1. **Unit Inconsistency**: The models.dev API returns pricing data, and our implementation displays it as "per 1K tokens" without converting to the more standard "per 1M tokens" format.

2. **Missing Telemetry**: The current implementation does not track:
   - Input token count
   - Output token count
   - Cache hit tokens (for providers that support caching)
   - Total cost calculation based on actual usage

## Requirements

- **REQ-001**: Clarify and standardize token pricing display unit (1K vs 1M tokens)
- **REQ-002**: Implement token usage tracking for input tokens
- **REQ-003**: Implement token usage tracking for output tokens
- **REQ-004**: Implement cache hit token tracking (where applicable)
- **REQ-005**: Calculate and display total cost based on actual token usage
- **REQ-006**: Store token usage telemetry for analysis and reporting
- **REQ-007**: Maintain backward compatibility with existing pricing display

## Expected Behavior

1. **Pricing Display**:
   - Show pricing in industry-standard format (per 1M tokens) when appropriate
   - Or clearly indicate "per 1K tokens" if that's the intended unit

2. **Token Tracking**:
   - Track input tokens for each LLM call
   - Track output tokens for each LLM call
   - Track cache hit tokens when supported by provider
   - Calculate total cost: (input_tokens * input_price + output_tokens * output_price + cache_tokens * cache_price)

3. **Telemetry Storage**:
   - Store usage data for reporting and analysis
   - Enable cost monitoring and optimization

## Actual Behavior

- Pricing is displayed as "per 1K tokens" without clarity on whether this is intended
- No token usage tracking exists
- No cost calculation based on actual usage
- No telemetry data collection for token usage

## Success Criteria

- [ ] Token pricing unit is clearly defined and consistently displayed
- [ ] Token usage is tracked for all LLM calls (input, output, cache)
- [ ] Cost is calculated based on actual token usage
- [ ] Telemetry data is stored for analysis
- [ ] No regressions in existing functionality
- [ ] All tests pass with new telemetry features
- [ ] Documentation updated with token tracking information
