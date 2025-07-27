# Browser Pilot Integration Guide for ModelForge v2.2.0+

## Issue Summary

Browser Pilot is getting this error with ModelForge v2.2.0:
```
ValueError: "ChatGitHubCopilot" object has no field "model_info"
```

## Root Cause

ModelForge v2.2.0 introduced an **opt-in** enhanced LLM wrapper that adds metadata properties like `model_info`. Browser Pilot is getting the raw `ChatGitHubCopilot` object because it's not requesting the enhanced version.

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

- **v2.2.0 (current)**: Enhanced features are opt-in via `enhanced=True`
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

### Issue 3: Missing `bind_tools` Method ✅ RESOLVED
**Root Cause**: `EnhancedLLM` wrapper was missing `bind_tools` delegation
**Solution**: Added explicit `bind_tools`, `bind`, and `with_structured_output` methods to `EnhancedLLM`

## Recommendation

**Use Option 1** (pass `enhanced=True`) for immediate compatibility and access to new features. This provides the cleanest integration and prepares Browser Pilot for v2.3.0 when enhanced mode becomes the default.

All Browser Pilot compatibility issues have been resolved in ModelForge v2.2.0.
