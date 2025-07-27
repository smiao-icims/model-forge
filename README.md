# ModelForge

A Python library for managing LLM providers, authentication, and model selection with seamless LangChain integration.

[![PyPI version](https://badge.fury.io/py/model-forge-llm.svg)](https://badge.fury.io/py/model-forge-llm)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**🚀 Version 2.2.0 - Enhanced Model Metadata, Improved Telemetry, and Quiet Mode!**

## Installation

### Recommended: Virtual Environment
```bash
# Create and activate virtual environment
python -m venv model-forge-env
source model-forge-env/bin/activate  # On Windows: model-forge-env\Scripts\activate

# Install package
pip install model-forge-llm

# Verify installation
modelforge --help
```

### Quick Install (System-wide)
```bash
pip install model-forge-llm
```

## Quick Start

### Option 1: GitHub Copilot via Device Authentication Flow
```bash
# Discover GitHub Copilot models
modelforge models list --provider github_copilot

# Set up GitHub Copilot with device authentication
modelforge auth login --provider github_copilot

# Select Claude 3.7 Sonnet via GitHub Copilot
modelforge config use --provider github_copilot --model claude-3.7-sonnet

# Test your setup
modelforge test --prompt "Write a Python function to reverse a string"
```

### Option 2: OpenAI (API Key Required)
```bash
# Add OpenAI with your API key
modelforge auth login --provider openai --api-key YOUR_API_KEY

# Select GPT-4o-mini
modelforge config use --provider openai --model gpt-4o-mini

# Test your setup
modelforge test --prompt "Hello, world!"
```

### Option 3: Local Ollama (No API Key Needed)
```bash
# Make sure Ollama is running locally
# Then add a local model
modelforge config add --provider ollama --model qwen3:1.7b

# Select the local model
modelforge config use --provider ollama --model qwen3:1.7b

# Test your setup
modelforge test --prompt "What is machine learning?"
```

### Common Commands - Complete Lifecycle
```bash
# Installation & Setup
modelforge --help                                   # Verify installation
modelforge config show                             # View current config

# Model Discovery & Selection
modelforge models list                             # List all available models
modelforge models search "claude"                   # Search models by name
modelforge models info --provider openai --model gpt-4o  # Get model details

# Authentication Management
modelforge auth login --provider openai --api-key KEY   # API key auth
modelforge auth login --provider github_copilot         # Device flow auth
modelforge auth status                                 # Check auth status
modelforge auth logout --provider openai               # Remove credentials

# Configuration Management
modelforge config add --provider openai --model gpt-4o-mini --api-key KEY
modelforge config add --provider ollama --model qwen3:1.7b --local
modelforge config use --provider openai --model gpt-4o-mini
modelforge config remove --provider openai --model gpt-4o-mini

# Testing & Usage (NEW in v2.2: Quiet mode for automation)
modelforge test --prompt "Hello, how are you?"        # Test current model
modelforge test --prompt "Explain quantum computing" --verbose  # Debug mode
modelforge test --input-file prompt.txt --output-file response.txt  # File I/O
echo "What is AI?" | modelforge test                 # Stdin input
modelforge test --prompt "Hello" --no-telemetry      # Disable telemetry
modelforge test --prompt "What is 2+2?" --quiet      # Minimal output (v2.2)
echo "Hello" | modelforge test --quiet > output.txt  # Perfect for piping

# Cache & Maintenance
modelforge models list --refresh                     # Force refresh from models.dev

# Telemetry Settings (NEW in v2.0)
modelforge settings telemetry on                      # Enable telemetry display
modelforge settings telemetry off                     # Disable telemetry display
modelforge settings telemetry status                  # Check current setting
```

## What's New

### v2.2.0 Features

#### 🤫 Quiet Mode for Automation
- **`--quiet` flag**: Minimal output showing only the model response
- **Perfect for piping**: Clean output for scripts and automation
- **Automatic telemetry suppression**: No metadata in quiet mode
- **Conflict prevention**: Cannot use with `--verbose` flag

#### 📊 Enhanced Telemetry Display
- **Context window tracking**: See how much of the model's context you're using
- **Token estimation**: Automatic estimation for providers that don't report usage
- **Capability display**: Shows if model supports functions, vision, etc.
- **Improved formatting**: Cleaner, more informative telemetry output

#### 🎯 Enhanced Model Metadata (Opt-in)
- **Model capabilities**: Access context length, max tokens, supported features
- **Cost estimation**: Calculate costs before making API calls
- **Parameter validation**: Automatic validation against model limits
- **Backward compatible**: Opt-in feature with `enhanced=True`

#### 🔧 Developer Experience
- **Logging control**: Suppress logs without `--verbose` flag
- **Better error messages**: More context and helpful suggestions
- **Improved callback handling**: Fixed telemetry in enhanced mode

### v2.1.0 Features

#### 🔐 Environment Variable Authentication
- Zero-touch auth for CI/CD pipelines
- Support for all providers via env vars
- Automatic token handling

#### 🌊 Streaming Support
- Real-time response streaming
- Automatic auth refresh during streams
- CLI and API streaming capabilities

### v2.0 Features

### 🎯 Telemetry & Cost Tracking
- **Token usage monitoring**: See exactly how many tokens each request uses
- **Cost estimation**: Real-time cost calculation for supported providers
  - For GitHub Copilot: Shows reference costs based on equivalent OpenAI models (subscription-based service)
- **Performance metrics**: Request duration and model response times
- **Configurable display**: Enable/disable telemetry output globally or per-command

### 📥 Flexible Input/Output
- **Multiple input sources**: Command line, files, or stdin
- **File output**: Save responses directly to files
- **Streaming support**: Pipe commands together for automation
- **Q&A formatting**: Clean, readable output for interactive use

### 🏗️ Simplified Architecture
- **Cleaner codebase**: Removed complex decorators and factory patterns
- **Direct error handling**: Clear, actionable error messages
- **Improved test coverage**: Comprehensive test suite with 90%+ coverage
- **Better maintainability**: Simplified patterns for easier contribution

### 🔧 Enhanced CLI
- **Settings management**: Global configuration for telemetry and preferences
- **Improved error messages**: Context and suggestions for common issues
- **Better help text**: More descriptive command documentation
- **Consistent output**: Unified formatting across all commands
- **Provider name flexibility**: Both `github-copilot` and `github_copilot` formats supported

## Python API

### Basic Usage

```python
from modelforge.registry import ModelForgeRegistry

# Initialize registry
registry = ModelForgeRegistry()

# Get currently configured model
llm = registry.get_llm()

# Use directly with LangChain
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([("human", "{input}")])
chain = prompt | llm
response = chain.invoke({"input": "Tell me a joke"})
print(response)
```

### Advanced Usage with Telemetry (NEW in v2.0)

```python
from modelforge.registry import ModelForgeRegistry
from modelforge.telemetry import TelemetryCallback

# Initialize with debug logging
registry = ModelForgeRegistry(verbose=True)

# Create telemetry callback
telemetry = TelemetryCallback(provider="openai", model="gpt-4o-mini")

# Get model with telemetry tracking
llm = registry.get_llm(
    provider_name="openai",
    model_alias="gpt-4o-mini",
    callbacks=[telemetry]
)

# Use with full LangChain features
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Create complex chains
prompt = ChatPromptTemplate.from_template("Explain {topic} in simple terms")
chain = prompt | llm | StrOutputParser()

# Use with streaming
for chunk in chain.stream({"topic": "quantum computing"}):
    print(chunk, end="", flush=True)

# Batch processing
questions = [
    "What is machine learning?",
    "Explain neural networks",
    "How does backpropagation work?"
]
responses = chain.batch([{"topic": q} for q in questions])

# Access telemetry data after execution
print(f"Tokens used: {telemetry.metrics.token_usage.total_tokens}")
print(f"Duration: {telemetry.metrics.duration_ms:.0f}ms")
print(f"Estimated cost: ${telemetry.metrics.estimated_cost:.6f}")

# Format telemetry for display
from modelforge.telemetry import format_metrics
print(format_metrics(telemetry.metrics))
```

### Enhanced Model Metadata (v2.2.0 - Opt-in Feature)

```python
from modelforge import ModelForgeRegistry

# Enable enhanced features
registry = ModelForgeRegistry()
llm = registry.get_llm("openai", "gpt-4o", enhanced=True)

# Access model metadata
print(f"Context window: {llm.context_length:,} tokens")
print(f"Max output: {llm.max_output_tokens:,} tokens")
print(f"Supports functions: {llm.supports_function_calling}")
print(f"Supports vision: {llm.supports_vision}")

# Get pricing information
pricing = llm.pricing_info
print(f"Input cost: ${pricing['input_per_1m']}/1M tokens")
print(f"Output cost: ${pricing['output_per_1m']}/1M tokens")

# Estimate costs before making calls
estimated_cost = llm.estimate_cost(input_tokens=5000, output_tokens=1000)
print(f"Estimated cost for this request: ${estimated_cost:.4f}")

# Configure parameters with validation
llm.temperature = 0.7  # Validated against model limits
llm.max_tokens = 2000  # Checked against model's max_output_tokens

# Note: This is opt-in for now. In future versions, enhanced=True may become default
# To maintain current behavior, explicitly use enhanced=False
```

### Configuration Management

```python
from modelforge import config

# Get current model selection
current = config.get_current_model()
print(f"Current: {current.get('provider')}/{current.get('model')}")

# Check if models are configured
if not current:
    print("No model selected. Configure with:")
    print("modelforge config add --provider openai --model gpt-4o-mini")

# Manage settings (NEW in v2.0)
settings = config.get_settings()
print(f"Telemetry enabled: {settings.get('show_telemetry', True)}")

# Update settings
config.update_setting("show_telemetry", False)  # Disable telemetry
```

### Error Handling

```python
from modelforge.registry import ModelForgeRegistry
from modelforge.exceptions import ConfigurationError, ProviderError

try:
    registry = ModelForgeRegistry()
    llm = registry.get_llm()
    response = llm.invoke("Hello world")
except ConfigurationError as e:
    print(f"Configuration issue: {e}")
    print("Run: modelforge config add --provider PROVIDER --model MODEL")
except ProviderError as e:
    print(f"Provider error: {e}")
    print("Check: modelforge auth status")
```

### Streaming Support (v2.1+)

ModelForge provides enhanced streaming capabilities with automatic authentication handling:

```python
from modelforge.registry import ModelForgeRegistry
from modelforge.streaming import stream

# Initialize with your LLM
registry = ModelForgeRegistry()
llm = registry.get_llm()

# Stream responses with auth handling
async for chunk in stream(llm, "Write a story about AI",
                         provider_name="openai",
                         provider_data=registry._config.get("providers", {}).get("openai")):
    print(chunk, end="", flush=True)

# Stream to file with automatic token refresh
from modelforge.streaming import stream_to_file
from pathlib import Path

await stream_to_file(llm, "Explain quantum computing",
                    Path("output.txt"),
                    provider_name="github_copilot",
                    provider_data=provider_data)
```

**CLI Streaming:**
```bash
# Stream responses in real-time
modelforge test --prompt "Write a story" --stream

# Stream to file
modelforge test --prompt "Explain AI" --stream --output-file response.txt
```

**Key Features:**
- Automatic token refresh for OAuth providers during long streams
- Environment variable authentication support
- Retry on authentication errors
- Progress callbacks and buffering options

**Note on Streaming Behavior:**
The actual streaming granularity depends on the provider's API implementation. Some providers (like GitHub Copilot) may return responses in larger chunks rather than token-by-token streaming, while others (like Ollama) support finer-grained streaming.

## Supported Providers

- **OpenAI**: GPT-4, GPT-4o, GPT-3.5-turbo
- **Google**: Gemini Pro, Gemini Flash
- **Ollama**: Local models (Llama, Qwen, Mistral)
- **GitHub Copilot**: Claude, GPT models via GitHub (use `github_copilot` or `github-copilot`)

## Authentication

ModelForge supports multiple authentication methods:

- **API Keys**: Store securely in configuration
- **Device Flow**: Browser-based OAuth for GitHub Copilot
- **No Auth**: For local models like Ollama
- **Environment Variables**: Zero-touch authentication for CI/CD (NEW in v2.1)

### Authentication Methods

```bash
# API Key authentication
modelforge auth login --provider openai --api-key YOUR_KEY

# Device flow (GitHub Copilot)
modelforge auth login --provider github_copilot

# Check auth status
modelforge auth status
```

### Environment Variable Support (v2.1+)

For CI/CD and production deployments, you can use environment variables to provide credentials without storing them in configuration files:

```bash
# API Key providers
export MODELFORGE_OPENAI_API_KEY="sk-..."
export MODELFORGE_ANTHROPIC_API_KEY="sk-ant-..."
export MODELFORGE_GOOGLE_API_KEY="..."

# OAuth providers
export MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN="ghu_..."

# Use models without manual authentication
modelforge test --prompt "Hello"
```

Environment variables take precedence over stored credentials and eliminate the need for interactive authentication.

## Configuration

ModelForge uses a two-tier configuration system:

- **Global**: `~/.config/model-forge/config.json` (user-wide)
- **Local**: `./.model-forge/config.json` (project-specific)

Local config takes precedence over global when both exist.

## Model Discovery

```bash
# List all available models
modelforge models list

# Search models by name or capability
modelforge models search "gpt"

# Get detailed model info
modelforge models info --provider openai --model gpt-4o
```

## Development Setup

For contributors and developers:

```bash
git clone https://github.com/smiao-icims/model-forge.git
cd model-forge

# Quick setup with uv (recommended)
./setup.sh

# Or manual setup
uv sync --extra dev
uv run pytest
```

**Requirements:**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (modern Python package manager)

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development guidelines.

## Documentation

- [Models.dev](https://models.dev) - Comprehensive model reference
- [GitHub Issues](https://github.com/smiao-icims/model-forge/issues) - Support and bug reports

## License

MIT License - see LICENSE file for details.
