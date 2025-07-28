# Browser Pilot Integration Guide for ModelForge v2.2.1+

## Issue Summary

Browser Pilot was experiencing compatibility issues with ModelForge v2.2.0+:

1. **Missing `model_info` Property**: `ValueError: "ChatGitHubCopilot" object has no field "model_info"`
2. **Callback Validation Error**: `LangChainVerboseCallback` not recognized as `BaseCallbackHandler`
3. **Missing `bind_tools` Method**: `NotImplementedError` when calling `bind_tools()`

## Root Cause

ModelForge v2.2.0+ introduced an **opt-in** enhanced LLM wrapper that adds metadata properties and LangChain compatibility methods. Browser Pilot was getting the raw `ChatGitHubCopilot` object because it wasn't requesting the enhanced version, and some LangChain methods were missing from the wrapper.

## Solution Options

### Option 1: Pass `enhanced=True` (RECOMMENDED)

**Update Browser Pilot code to explicitly request enhanced features:**

```python
# OLD (returns raw ChatGitHubCopilot)
llm = registry.get_llm()

# NEW (returns EnhancedLLM with model_info)
llm = registry.get_llm(enhanced=True)
```

### Option 2: Set Environment Variable

**Set the environment variable to opt into enhanced mode globally:**

```python
import os
os.environ['MODELFORGE_ENHANCED'] = 'true'

# Now get_llm() returns EnhancedLLM by default
llm = registry.get_llm()
```

### Option 3: Graceful Feature Detection (BACKWARD COMPATIBLE)

**Check for enhanced features without requiring them:**

```python
llm = registry.get_llm()  # Keep existing call

# Check if enhanced features are available
if hasattr(llm, 'model_info'):
    # Use enhanced features
    context_length = llm.context_length
    model_info = llm.model_info
    supports_vision = llm.supports_vision
else:
    # Fallback to basic usage
    print("Enhanced features not available, using basic LLM")
```

## Enhanced Features Available

When using `enhanced=True`, you get access to:

- `llm.model_info` - Full model metadata from models.dev
- `llm.context_length` - Maximum context window in tokens
- `llm.max_output_tokens` - Maximum output tokens
- `llm.supports_vision` - Whether model supports image inputs
- `llm.supports_function_calling` - Whether model supports function calls
- `llm.pricing_info` - Cost per 1M tokens
- `llm.estimate_cost(input_tokens, output_tokens)` - Cost estimation

## Migration Timeline

- **v2.2.0**: Enhanced features introduced as opt-in via `enhanced=True`
- **v2.2.1 (current)**: Added missing LangChain compatibility methods (`bind_tools`, `bind`, `with_structured_output`)
- **v2.3.0 (planned)**: Enhanced features will be default (`enhanced=True` by default)

## Example Code

```python
from modelforge.registry import ModelForgeRegistry
from modelforge.enhanced_llm import EnhancedLLM

registry = ModelForgeRegistry()

# Get enhanced LLM
llm = registry.get_llm(enhanced=True)

# Type check for safety
if isinstance(llm, EnhancedLLM):
    print(f"Model: {llm.model_info['name']}")
    print(f"Context: {llm.context_length:,} tokens")
    print(f"Vision: {llm.supports_vision}")

    # Estimate cost for 1000 input + 500 output tokens
    cost = llm.estimate_cost(1000, 500)
    print(f"Estimated cost: ${cost:.6f}")
```

## Fixed Issues

### Issue 1: Missing `model_info` Property ✅ RESOLVED
**Root Cause**: Browser Pilot wasn't requesting enhanced LLM wrapper
**Solution**: Pass `enhanced=True` parameter

### Issue 2: Callback Validation Error ✅ RESOLVED
**Root Cause**: `LangChainVerboseCallback` didn't inherit from `BaseCallbackHandler`
**Solution**: Updated Browser Pilot's callback class to properly inherit from `BaseCallbackHandler`

### Issue 3: Missing `bind_tools` Method ✅ RESOLVED (v2.2.1)
**Root Cause**: `EnhancedLLM` wrapper was missing `bind_tools` delegation
**Solution**: Added explicit `bind_tools`, `bind`, and `with_structured_output` methods to `EnhancedLLM`

## Recommendation

**Use Option 1** (pass `enhanced=True`) for immediate compatibility and access to new features. This provides the cleanest integration and prepares Browser Pilot for v2.3.0 when enhanced mode becomes the default.

All Browser Pilot compatibility issues have been resolved in ModelForge v2.2.1.

## Upgrade Instructions

### For ModelForge v2.2.1+

1. **Update ModelForge**: `pip install --upgrade model-forge-llm>=2.2.1`
2. **Use Enhanced Mode**: Pass `enhanced=True` when getting LLM instances
3. **Update Callbacks**: Ensure custom callbacks inherit from `BaseCallbackHandler`

### Verification

Test that Browser Pilot works correctly:

```bash
# Install/upgrade ModelForge
pip install --upgrade model-forge-llm>=2.2.1

# Run Browser Pilot with enhanced mode
uv run browser-pilot examples/test.md --provider github_copilot --model gpt-4o --verbose
```

The integration should now work without any errors.

## Provider and Model Discovery APIs

ModelForge v2.2.1+ includes comprehensive APIs for Browser Pilot to discover and list providers and models:

### Available Provider Discovery

```python
from modelforge.registry import ModelForgeRegistry

registry = ModelForgeRegistry()

# Get all available providers from models.dev
providers = registry.get_available_providers()
for provider in providers:
    print(f"{provider['display_name']}: {provider['description']}")
    print(f"  Auth types: {provider['auth_types']}")
```

### Available Model Discovery

```python
# Get all available models
all_models = registry.get_available_models()

# Get models for specific provider
openai_models = registry.get_available_models(provider="openai")
for model in openai_models:
    print(f"{model['display_name']}: {model['context_length']:,} tokens")
    if model.get('pricing'):
        price = model['pricing'].get('input_per_1m_tokens', 0)
        print(f"  Cost: ${price}/1M tokens")
```

### User Configuration Discovery

```python
# Check what providers user has configured
configured_providers = registry.get_configured_providers()
for provider_name, config in configured_providers.items():
    models = config.get('models', {})
    print(f"{provider_name}: {len(models)} models, auth: {config.get('auth_strategy')}")

# Get configured models for a provider
openai_models = registry.get_configured_models("openai")
for alias, config in openai_models.items():
    api_name = config.get('api_model_name', alias)
    print(f"Alias: {alias} -> API: {api_name}")

# Check if provider/model is configured
if registry.is_provider_configured("openai"):
    if registry.is_model_configured("openai", "gpt-4"):
        print("GPT-4 is ready to use!")
```

### Complete Browser Pilot Integration Example

```python
from modelforge.registry import ModelForgeRegistry

def setup_browser_pilot_llm():
    """Smart LLM selection for Browser Pilot."""
    registry = ModelForgeRegistry()

    # Find best configured provider for Browser Pilot
    for provider in ["openai", "anthropic", "github_copilot"]:
        if registry.is_provider_configured(provider):
            models = registry.get_configured_models(provider)
            if models:
                # Use first available model
                model_alias = list(models.keys())[0]

                # Get enhanced LLM with metadata
                llm = registry.get_llm(
                    provider_name=provider,
                    model_alias=model_alias,
                    enhanced=True  # Required for model_info property
                )

                print(f"Using {provider}/{model_alias}")
                print(f"Context: {llm.context_length:,} tokens")
                print(f"Vision: {llm.supports_vision}")

                return llm

    raise Exception("No suitable LLM provider configured")

# Usage in Browser Pilot
llm = setup_browser_pilot_llm()
```

### API Reference Summary

| Method | Description | Returns |
|--------|-------------|---------|
| `get_available_providers()` | All providers from models.dev | `list[dict]` |
| `get_available_models(provider=None)` | All/filtered models from models.dev | `list[dict]` |
| `get_configured_providers()` | User's configured providers | `dict[str, dict]` |
| `get_configured_models(provider=None)` | User's configured models | `dict[str, dict]` |
| `is_provider_configured(provider)` | Check if provider configured | `bool` |
| `is_model_configured(provider, model)` | Check if model configured | `bool` |

These APIs enable Browser Pilot to:
1. **Discover** what providers and models are available
2. **Check** what the user has configured
3. **Select** the best option automatically
4. **Present** configuration options to users
5. **Get** enhanced LLM instances ready for use
