#!/usr/bin/env python3
"""
Example showing how Browser Pilot can use ModelForge's provider/model discovery APIs.

This demonstrates the complete workflow for an agentic application to:
1. Discover available providers and models
2. Check what's configured by the user
3. Present options to the user
4. Get LLM instances for interaction
"""

from typing import Any

from modelforge.registry import ModelForgeRegistry


def demo_browser_pilot_integration() -> None:
    """Demonstrate Browser Pilot integration with ModelForge discovery APIs."""

    print("🚀 Browser Pilot + ModelForge Integration Demo")
    print("=" * 50)

    # Initialize ModelForge registry
    registry = ModelForgeRegistry()

    # === 1. DISCOVER AVAILABLE PROVIDERS ===
    print("\n📋 Step 1: Discover Available Providers")
    print("-" * 40)

    available_providers = registry.get_available_providers()
    print(f"Found {len(available_providers)} providers from models.dev:")

    for provider in available_providers[:5]:  # Show first 5
        auth_types = ", ".join(provider.get("auth_types", []))
        print(f"  • {provider['display_name']}")
        print(f"    - ID: {provider['name']}")
        print(f"    - Auth: {auth_types}")
        print(f"    - Info: {provider['description']}")
        print()

    # === 2. CHECK CONFIGURED PROVIDERS ===
    print("🔧 Step 2: Check User's Configured Providers")
    print("-" * 45)

    configured_providers = registry.get_configured_providers()
    if configured_providers:
        print(f"User has {len(configured_providers)} configured providers:")
        for provider_name, config in configured_providers.items():
            models = config.get("models", {})
            auth = config.get("auth_strategy", "none")
            print(f"  ✅ {provider_name}")
            print(f"     - {len(models)} models configured")
            print(f"     - Auth: {auth}")
    else:
        print("❌ No providers configured yet")
        print("   User needs to run:")
        print("   modelforge config add --provider <name> --model <model>")

    # === 3. DISCOVER MODELS FOR CONFIGURED PROVIDERS ===
    print("\n🤖 Step 3: Available Models for Configured Providers")
    print("-" * 52)

    for provider_name in configured_providers:
        if provider_name == "invalid":  # Skip test entries
            continue

        print(f"\n📦 {provider_name.upper()} Models:")

        # Get available models from models.dev for this provider
        try:
            available_models = registry.get_available_models(provider=provider_name)
            print(f"   Available from models.dev: {len(available_models)} models")

            # Show some examples
            for model in available_models[:3]:
                context = (
                    f"{model['context_length']:,}"
                    if model["context_length"]
                    else "Unknown"
                )
                pricing = ""
                if model.get("pricing") and model["pricing"].get("input_per_1m_tokens"):
                    price = model["pricing"]["input_per_1m_tokens"]
                    pricing = f", ${price}/1M tokens"

                print(f"   • {model['display_name']}")
                print(f"     - ID: {model['id']}")
                print(f"     - Context: {context} tokens{pricing}")

        except Exception as e:
            print(f"   ⚠️  Could not fetch models from models.dev: {e}")

        # Get user's configured models for this provider
        configured_models = registry.get_configured_models(provider_name)
        print(f"   User configured: {len(configured_models)} models")
        for model_alias in list(configured_models.keys())[:3]:
            print(f"   ✓ {model_alias}")

    # === 4. SMART PROVIDER/MODEL SELECTION ===
    print("\n🎯 Step 4: Smart Selection for Browser Pilot")
    print("-" * 44)

    # Recommend best configured providers for Browser Pilot
    recommended_providers: list[dict[str, Any]] = []

    for provider_name in ["openai", "anthropic", "github_copilot", "google"]:
        if registry.is_provider_configured(provider_name):
            models = registry.get_configured_models(provider_name)
            if models:
                recommended_providers.append(
                    {
                        "name": provider_name,
                        "models": list(models.keys()),
                        "count": len(models),
                    }
                )

    if recommended_providers:
        print("🌟 Recommended providers for Browser Pilot:")
        for provider in recommended_providers:
            print(f"  • {provider['name']}: {provider['count']} models")
            print(f"    Models: {', '.join(provider['models'][:3])}")

            # Test if we can get an LLM instance
            first_model = provider["models"][0]
            provider_name_str = str(provider["name"])
            try:
                if registry.is_model_configured(provider_name_str, first_model):
                    print(f"    ✅ Ready to use: {provider_name_str}/{first_model}")
                else:
                    print(f"    ❌ Not configured: {provider_name_str}/{first_model}")
            except Exception as e:
                print(f"    ⚠️  Configuration issue: {e}")
            print()
    else:
        print("❌ No suitable providers configured for Browser Pilot")
        print("   Please configure at least one provider:")
        print("   modelforge config add --provider openai --model gpt-4")

    # === 5. GET LLM INSTANCE ===
    print("🔗 Step 5: Get LLM Instance for Browser Pilot")
    print("-" * 42)

    if recommended_providers:
        # Try to get an enhanced LLM instance
        provider = recommended_providers[0]
        provider_name = str(provider["name"])
        model_alias = str(provider["models"][0])

        try:
            print(f"Getting enhanced LLM: {provider_name}/{model_alias}")
            llm = registry.get_llm(
                provider_name=provider_name,
                model_alias=model_alias,
                enhanced=True,  # Get enhanced version with metadata
            )

            print("✅ Successfully created LLM instance:")
            print(f"   Type: {type(llm).__name__}")

            # Show enhanced features if available
            if hasattr(llm, "model_info"):
                print(f"   Context Length: {llm.context_length:,} tokens")
                print(f"   Supports Vision: {llm.supports_vision}")
                print(f"   Supports Functions: {llm.supports_function_calling}")

                # Test browser pilot integration
                print("\n🔧 Testing Browser Pilot compatibility:")

                # Test bind_tools (required for Browser Pilot)
                bound_llm = llm.bind_tools([])
                print(f"   ✅ bind_tools() works: {type(bound_llm).__name__}")

                # Test other methods
                bound_params = llm.bind(temperature=0.7)
                print(f"   ✅ bind() works: {type(bound_params).__name__}")

                print("\n🎉 Browser Pilot integration ready!")
                cmd = f"registry.get_llm('{provider_name}', '{model_alias}'"
                print(f"   Use: {cmd}, enhanced=True)")

        except Exception as e:
            print(f"❌ Failed to create LLM: {e}")
    else:
        print("❌ Cannot create LLM - no providers configured")

    print("\n" + "=" * 50)
    print("✨ Integration demo complete!")


if __name__ == "__main__":
    demo_browser_pilot_integration()
