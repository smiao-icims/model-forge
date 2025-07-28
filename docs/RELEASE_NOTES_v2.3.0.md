# ModelForge v2.3.0 Release Notes

## 🧙 Interactive Configuration Wizard

We're excited to introduce the **Interactive Configuration Wizard** - the easiest way to set up ModelForge!

### Quick Start
```bash
modelforge config
```

That's it! The wizard will guide you through everything.

### Key Features

#### 🎯 Smart Provider Selection
- **Visual indicators** make it easy to see what's configured:
  - ⭐ = Recommended providers (OpenAI, Anthropic, GitHub Copilot, etc.)
  - ✅ = Already configured providers
- **Authentication info** shown for unconfigured providers
- **Intelligent sorting** - recommended and configured providers appear first

#### 🔐 Flexible Authentication
When you already have valid credentials, the wizard asks:
```
✅ Valid credentials found!
? What would you like to do?
  > Use existing device authentication token
    Re-authenticate with GitHub (new device flow)
```

No more forced re-authentication!

#### 🎨 Enhanced User Experience
- **Arrow key navigation** through all options
- **Current selections as defaults** - the wizard remembers your current provider/model
- **Quiet by default** - no verbose logs unless you use `--verbose`
- **Graceful error handling** - quota exceeded? The wizard still saves your config

#### 🧪 Live Configuration Testing
The wizard tests your configuration with a sample prompt and shows:
- Model response
- Token usage and costs
- Context window utilization
- Any warnings (like quota limits)

### Provider Name Compatibility

The wizard handles both naming conventions seamlessly:
- `github-copilot` (hyphenated) - used in models.dev
- `github_copilot` (underscore) - used internally

Your existing configurations work without any changes!

### Developer APIs

For tool builders, we've added comprehensive discovery APIs:

```python
from modelforge.registry import ModelForgeRegistry

registry = ModelForgeRegistry()

# Discover available providers
providers = registry.get_available_providers()

# Check what's configured
if registry.is_provider_configured("openai"):
    models = registry.get_configured_models("openai")
```

Perfect for building tools like Browser Pilot that need to discover and present LLM options!

## Installation

```bash
pip install --upgrade model-forge-llm
```

## What's Next?

In v2.3.0, we're planning to make enhanced mode the default, bringing even more metadata and capabilities to all LLM instances.

## Acknowledgments

Special thanks to our users who provided feedback on the configuration experience, especially around GitHub Copilot authentication and provider discovery needs.

---

**Full Changelog**: https://github.com/smiao/model-forge/blob/main/CHANGELOG.md

**Documentation**: https://github.com/smiao/model-forge#readme
