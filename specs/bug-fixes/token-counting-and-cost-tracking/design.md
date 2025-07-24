# Bug Fix: Token Counting and Cost Tracking - Design

## Technical Analysis

### Current State
1. **Pricing Display**: The system shows pricing as "per 1K tokens" based on models.dev API data
2. **No Token Tracking**: LangChain models return token usage, but we don't capture or store it
3. **No Cost Calculation**: No mechanism to calculate actual costs based on usage

### Industry Standards
- Most providers (OpenAI, Anthropic, Google) display pricing per 1M tokens
- The models.dev API appears to return pricing per 1K tokens
- LangChain provides token usage data in response metadata

## Solution Design

### 1. Token Pricing Unit Standardization

**Option A: Convert to 1M tokens (Recommended)**
- Convert models.dev pricing from 1K to 1M tokens for display
- Maintain internal calculations in the original unit
- Benefits: Aligns with industry standards
- Drawback: May confuse users familiar with models.dev pricing

**Option B: Keep 1K tokens with clear labeling**
- Keep current unit but ensure clear labeling everywhere
- Benefits: Matches models.dev API directly
- Drawback: Different from industry standard

**Decision**: Use Option B - Keep 1K tokens to match models.dev API, but ensure clear and consistent labeling.

### 2. Token Usage Tracking Architecture

```python
# New telemetry module structure
src/modelforge/telemetry.py

class TokenUsage:
    """Track token usage for a single LLM call."""
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    model: str
    provider: str
    timestamp: datetime

class CostCalculator:
    """Calculate costs based on token usage and pricing."""
    def calculate_cost(usage: TokenUsage, pricing: dict) -> float:
        # Calculate total cost based on token counts and pricing

class TelemetryCollector:
    """Collect and store telemetry data."""
    def record_usage(usage: TokenUsage) -> None:
        # Store usage data for analysis
```

### 3. Integration Points

**Registry Integration**:
- Wrap LangChain model responses to extract token usage
- Create a response wrapper that captures metadata
- Store telemetry data after each call

**CLI Integration**:
- Add `--show-usage` flag to display token counts and costs
- Add `modelforge usage` command to show usage statistics

### 4. Storage Strategy

**Local JSON Storage** (Initial Implementation):
```json
{
  "usage_records": [
    {
      "timestamp": "2025-01-24T10:30:00Z",
      "provider": "openai",
      "model": "gpt-4",
      "input_tokens": 150,
      "output_tokens": 250,
      "cache_read_tokens": 0,
      "cost": 0.012
    }
  ]
}
```

Location: `~/.config/model-forge/telemetry.json`

## Implementation Strategy

### Phase 1: Token Tracking Infrastructure
1. Create telemetry module with core classes
2. Implement token usage extraction from LangChain responses
3. Add response wrapper in registry.py

### Phase 2: Cost Calculation
1. Implement cost calculator using pricing data
2. Ensure pricing unit consistency (1K tokens)
3. Add cost display to CLI commands

### Phase 3: Storage and Reporting
1. Implement local JSON storage
2. Add usage reporting commands
3. Create usage summary displays

## Testing Strategy

1. **Unit Tests**:
   - Test token usage extraction from various LangChain responses
   - Test cost calculation with different pricing models
   - Test telemetry storage and retrieval

2. **Integration Tests**:
   - Test end-to-end token tracking with real API calls
   - Test CLI commands with usage display
   - Test backward compatibility

3. **Mock Tests**:
   - Mock LangChain responses with token usage data
   - Test edge cases (missing usage data, malformed responses)

## Backward Compatibility

1. **Pricing Display**: Keep existing format, just ensure clear labeling
2. **Optional Telemetry**: Make telemetry opt-in initially
3. **Graceful Degradation**: Handle providers that don't report token usage
4. **Migration Path**: Provide clear documentation for new features

## Security Considerations

1. **Sensitive Data**: Don't store prompt/response content, only metadata
2. **Local Storage**: Keep telemetry data in user's config directory
3. **Privacy**: Allow users to disable telemetry collection
4. **Data Retention**: Implement configurable retention policies

## Future Enhancements

1. **Provider-Specific Features**:
   - Support Anthropic's cache tokens
   - Support OpenAI's reasoning tokens
   - Handle provider-specific pricing models

2. **Advanced Analytics**:
   - Cost trends over time
   - Usage patterns by model/provider
   - Budget alerts and limits

3. **Export Options**:
   - CSV export for analysis
   - Integration with monitoring tools
   - API for programmatic access
