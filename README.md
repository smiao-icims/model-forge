# ModelForge

A Python library for managing LLM providers, authentication, and model selection with seamless LangChain integration.

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

# Testing & Usage
modelforge test --prompt "Hello, how are you?"        # Test current model
modelforge test --prompt "Explain quantum computing" --verbose  # Debug mode

# Cache & Maintenance
modelforge models list --refresh                     # Force refresh from models.dev
```

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

### Advanced Usage

```python
from modelforge.registry import ModelForgeRegistry

# Initialize with debug logging
registry = ModelForgeRegistry(verbose=True)

# Get specific model by provider and name
llm = registry.get_llm(provider_name="openai", model_alias="gpt-4o-mini")

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

## Supported Providers

- **OpenAI**: GPT-4, GPT-4o, GPT-3.5-turbo
- **Google**: Gemini Pro, Gemini Flash
- **Ollama**: Local models (Llama, Qwen, Mistral)
- **GitHub Copilot**: Claude, GPT models via GitHub

## Authentication

ModelForge supports multiple authentication methods:

- **API Keys**: Store securely in configuration
- **Device Flow**: Browser-based OAuth for GitHub Copilot
- **No Auth**: For local models like Ollama

```bash
# API Key authentication
modelforge auth login --provider openai --api-key YOUR_KEY

# Device flow (GitHub Copilot)
modelforge auth login --provider github_copilot

# Check auth status
modelforge auth status
```

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
poetry install
poetry run pytest
```

## Documentation

- [Models.dev](https://models.dev) - Comprehensive model reference
- [GitHub Issues](https://github.com/smiao-icims/model-forge/issues) - Support and bug reports

## License

MIT License - see LICENSE file for details.
