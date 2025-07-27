# Model-Forge Enhancement Requirements for Browser Pilot

## Overview
Browser Pilot requires enhanced model metadata and configuration capabilities from model-forge to provide better insights and control for QA engineers using LLM-powered test automation.

## Functional Requirements

### FR1: Model Metadata Exposure
The system SHALL expose model capabilities and limits that are already fetched from models.dev through the LLM object interface.

#### FR1.1: Core Metadata Properties
The LLM object SHALL provide the following read-only properties:
- `context_length`: Maximum context window in tokens (integer)
- `max_output_tokens`: Maximum output tokens the model can generate (integer)
- `supports_function_calling`: Whether the model supports function/tool calling (boolean)
- `supports_vision`: Whether the model supports image inputs (boolean)
- `model_info`: Full model metadata dictionary from models.dev

#### FR1.2: Metadata Availability
- Metadata SHALL be available immediately after LLM instantiation
- Metadata SHALL be cached to avoid repeated API calls to models.dev
- Missing metadata fields SHALL return sensible defaults (e.g., False for capability flags, 0 for limits)

### FR2: Model Configuration Parameters
The system SHALL allow setting and retrieving model parameters consistently across all providers.

#### FR2.1: Parameter Setting
Users SHALL be able to set common parameters on LLM objects:
- `temperature` (float, 0.0-2.0)
- `top_p` (float, 0.0-1.0)
- `top_k` (integer, provider-specific range)
- `max_tokens` (integer, up to model's max_output_tokens)

#### FR2.2: Parameter Retrieval
Users SHALL be able to retrieve current parameter values from LLM objects.

#### FR2.3: Parameter Persistence
Set parameters SHALL be applied to all subsequent LLM invocations until changed.

### FR3: Provider-Agnostic Parameter Validation
The system SHALL validate parameters based on model capabilities before sending requests.

#### FR3.1: Validation Rules
- Parameters SHALL be validated against model-specific limits
- Invalid parameters SHALL raise clear, actionable errors
- Validation SHALL occur before API calls to prevent wasted requests

### FR4: Enhanced Cost Estimation
The system SHALL expose pricing information and provide cost calculation utilities.

#### FR4.1: Pricing Information Property
LLM objects SHALL expose a `pricing_info` property containing:
- `input_per_1m`: Cost per 1 million input tokens (float)
- `output_per_1m`: Cost per 1 million output tokens (float)
- `currency`: Currency code (string, default "USD")

#### FR4.2: Cost Estimation Method
LLM objects SHALL provide an `estimate_cost(input_tokens, output_tokens)` method that returns estimated cost in the specified currency.

## Non-Functional Requirements

### NFR1: Backward Compatibility
- All new features SHALL be backward compatible with existing model-forge APIs
- Existing code using model-forge SHALL continue to work without modifications
- New properties SHALL have sensible defaults when metadata is unavailable

### NFR2: Performance
- Metadata retrieval SHALL add no more than 100ms to LLM instantiation time
- Metadata SHALL be cached with appropriate TTL (7 days for model info)
- Parameter validation SHALL add negligible overhead (<10ms)

### NFR3: Error Handling
- All errors SHALL follow model-forge's existing error pattern with context and suggestions
- Missing metadata SHALL not cause LLM instantiation to fail
- Network errors when fetching metadata SHALL fall back to cached data

### NFR4: Provider Support
- Core features SHALL work with all existing providers (OpenAI, Google, Ollama, GitHub Copilot)
- Provider-specific limitations SHALL be documented
- Unsupported features SHALL degrade gracefully with appropriate warnings

## Use Cases

### UC1: Context Length Awareness
**Actor**: Browser Pilot Test Automation
**Precondition**: LLM instance created
**Flow**:
1. Browser Pilot gets LLM's context_length property
2. Browser Pilot calculates prompt token count
3. If prompt exceeds 80% of context limit, Browser Pilot warns user
4. Browser Pilot suggests splitting the test or using a different model

### UC2: Dynamic Model Selection
**Actor**: Browser Pilot Test Automation
**Precondition**: Multiple models configured
**Flow**:
1. Browser Pilot queries available models with specific capabilities
2. Model-forge returns models matching criteria (context length, function calling, cost)
3. Browser Pilot selects optimal model for the test scenario
4. Browser Pilot creates LLM instance with selected model

### UC3: Cost-Aware Testing
**Actor**: QA Engineer
**Precondition**: LLM with pricing information available
**Flow**:
1. Engineer configures cost threshold for test suite
2. Browser Pilot estimates cost before each test using LLM's estimate_cost method
3. If estimated cost exceeds threshold, Browser Pilot warns and asks for confirmation
4. After test, actual cost is compared with estimate for accuracy tracking

## Constraints

### Technical Constraints
- Must integrate with existing LangChain model classes
- Must work with model-forge's two-tier configuration system
- Must handle providers that don't expose certain metadata

### Business Constraints
- Implementation must be completed without breaking existing model-forge users
- Solution must not require changes to Browser Pilot's existing model-forge integration

## Acceptance Criteria

### AC1: Metadata Exposure
- [ ] All LLM objects expose required metadata properties
- [ ] Metadata is accurately retrieved from models.dev
- [ ] Missing metadata returns appropriate defaults
- [ ] Metadata is cached and refreshed appropriately

### AC2: Parameter Configuration
- [ ] Parameters can be set and retrieved on all LLM types
- [ ] Parameters persist across LLM invocations
- [ ] Parameter changes are reflected in actual API calls

### AC3: Cost Estimation
- [ ] Pricing information is available for all supported models
- [ ] Cost estimation is accurate within 5% of actual costs
- [ ] GitHub Copilot shows appropriate disclaimer about subscription pricing

### AC4: Backward Compatibility
- [ ] All existing model-forge tests pass without modification
- [ ] Existing Browser Pilot integration continues to work
- [ ] New features are optional and don't break existing usage
