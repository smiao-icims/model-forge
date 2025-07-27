#!/usr/bin/env python3
"""
Demonstration of EnhancedLLM metadata and configuration features.

This example shows how to use the new metadata properties and
parameter configuration capabilities in model-forge v2.2.0.
"""

import os

from modelforge import ModelForgeRegistry


def demo_metadata_features() -> None:
    """Demonstrate metadata access and cost estimation."""
    print("=" * 60)
    print("Model-Forge Enhanced Metadata Demo")
    print("=" * 60)

    # Create registry
    registry = ModelForgeRegistry()

    # Get an enhanced LLM (explicitly opt-in for now)
    print("\n1. Creating enhanced LLM with metadata...")
    llm = registry.get_llm("openai", "gpt-4o", enhanced=True)

    # Display metadata
    print("\n2. Model Metadata:")
    print(f"   Context Length: {llm.context_length:,} tokens")
    print(f"   Max Output Tokens: {llm.max_output_tokens:,} tokens")
    print(f"   Supports Function Calling: {llm.supports_function_calling}")
    print(f"   Supports Vision: {llm.supports_vision}")

    # Pricing information
    pricing = llm.pricing_info
    print("\n3. Pricing Information:")
    print(f"   Input: ${pricing['input_per_1m']:.2f} per 1M tokens")
    print(f"   Output: ${pricing['output_per_1m']:.2f} per 1M tokens")
    print(f"   Currency: {pricing['currency']}")

    # Cost estimation
    print("\n4. Cost Estimation Example:")
    input_tokens = 5000
    output_tokens = 1000
    cost = llm.estimate_cost(input_tokens, output_tokens)
    print(f"   For {input_tokens:,} input + {output_tokens:,} output tokens:")
    print(f"   Estimated cost: ${cost:.4f}")

    # Full model info
    print("\n5. Raw Model Info Keys:")
    model_info = llm.model_info
    print(f"   Available fields: {', '.join(model_info.keys())}")


def demo_parameter_configuration() -> None:
    """Demonstrate parameter configuration."""
    print("\n" + "=" * 60)
    print("Parameter Configuration Demo")
    print("=" * 60)

    registry = ModelForgeRegistry()
    llm = registry.get_llm("openai", "gpt-4o", enhanced=True)

    print("\n1. Setting Parameters:")
    print(f"   Original temperature: {llm.temperature}")

    # Set new temperature
    llm.temperature = 0.7
    print(f"   New temperature: {llm.temperature}")

    # Set other parameters
    llm.top_p = 0.9
    llm.max_tokens = 2000

    print(f"   Top P: {llm.top_p}")
    print(f"   Max tokens: {llm.max_tokens}")

    # Demonstrate validation
    print("\n2. Parameter Validation:")
    try:
        llm.temperature = 2.5  # Invalid - too high
    except ValueError as e:
        print(f"   ✓ Temperature validation works: {e}")

    try:
        llm.max_tokens = 10000  # Exceeds model limit
    except ValueError as e:
        print(f"   ✓ Max tokens validation works: {e}")


def demo_browser_pilot_use_case() -> None:
    """Demonstrate Browser Pilot use case."""
    print("\n" + "=" * 60)
    print("Browser Pilot Use Case Demo")
    print("=" * 60)

    registry = ModelForgeRegistry()

    # Browser Pilot wants to check context limits
    print("\n1. Context Length Awareness:")
    llm = registry.get_llm("openai", "gpt-4o", enhanced=True)

    prompt_tokens = 100000
    context_limit = llm.context_length
    usage_percentage = (prompt_tokens / context_limit) * 100

    print(f"   Model context limit: {context_limit:,} tokens")
    print(f"   Current prompt size: {prompt_tokens:,} tokens")
    print(f"   Usage: {usage_percentage:.1f}%")

    if usage_percentage > 80:
        print("   ⚠️  WARNING: Approaching context limit!")
        print("   Suggestion: Split test or use a model with larger context")

    # Dynamic parameter adjustment
    print("\n2. Dynamic Parameter Adjustment:")
    test_type = "deterministic"  # or "exploratory"

    if test_type == "exploratory":
        llm.temperature = 0.7
        print("   Set temperature to 0.7 for exploratory testing")
    else:
        llm.temperature = 0.1
        print("   Set temperature to 0.1 for deterministic testing")

    # Cost awareness
    print("\n3. Cost-Aware Testing:")
    estimated_input = 50000
    estimated_output = 10000
    cost = llm.estimate_cost(estimated_input, estimated_output)

    print(f"   Estimated tokens: {estimated_input:,} in, {estimated_output:,} out")
    print(f"   Estimated cost: ${cost:.2f}")

    cost_threshold = 1.00  # $1 threshold
    if cost > cost_threshold:
        print(f"   ⚠️  WARNING: Exceeds ${cost_threshold:.2f} threshold!")
        print("   Consider using a cheaper model or reducing test scope")


def demo_backward_compatibility() -> None:
    """Demonstrate backward compatibility."""
    print("\n" + "=" * 60)
    print("Backward Compatibility Demo")
    print("=" * 60)

    registry = ModelForgeRegistry()

    # Old code still works (with a FutureWarning)
    print("\n1. Legacy code (enhanced=False by default):")
    llm = registry.get_llm("openai", "gpt-4o")  # No enhanced parameter
    print(f"   Type: {type(llm).__name__}")
    print("   ✓ Returns raw LangChain model as before")

    # Explicit opt-out
    print("\n2. Explicit opt-out:")
    llm = registry.get_llm("openai", "gpt-4o", enhanced=False)
    print(f"   Type: {type(llm).__name__}")
    print("   ✓ No enhanced features, no warnings")

    # Opt-in via environment variable
    print("\n3. Environment variable opt-in:")
    os.environ["MODELFORGE_ENHANCED"] = "true"
    llm = registry.get_llm("openai", "gpt-4o")
    print(f"   Type: {type(llm).__name__}")
    print("   ✓ Returns EnhancedLLM when env var is set")

    # Clean up
    del os.environ["MODELFORGE_ENHANCED"]


def main() -> None:
    """Run all demonstrations."""
    try:
        demo_metadata_features()
        demo_parameter_configuration()
        demo_browser_pilot_use_case()
        demo_backward_compatibility()

        print("\n" + "=" * 60)
        print("✅ All demonstrations completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have configured a provider (e.g., OpenAI)")
        print("Run: modelforge config add --provider openai")


if __name__ == "__main__":
    main()
