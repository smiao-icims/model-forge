# Model Forge Library

A reusable library for managing LLM providers, authentication, and model selection.

This library is intended to be used by various Python-based AI projects to provide a consistent way to handle LLM interactions.

## High-Level Design

The library is composed of three core modules:

-   **`config`**: Manages configuration files with a two-tier system - global (`~/.model-forge/config.json`) and local (`./.model-forge/config.json`) - where all provider and model settings are stored.
-   **`auth`**: Provides a suite of authentication strategies (API Key, OAuth 2.0 Device Flow, and a No-Op for local models) and handles secure credential storage using the system's native keyring.
-   **`registry`**: Acts as the main entry point and factory. It reads the configuration, invokes the appropriate authentication strategy, and instantiates ready-to-use, LangChain-compatible LLM objects.

## 🛠️ **Quick Start**

## **Option 1: Traditional Development Setup (Recommended)**
Best for developers who will use ModelForge frequently:

```bash
# 1. Run setup script
./setup.sh

# 2. Use Poetry directly (faster for repeated use)
poetry run modelforge config show
poetry run modelforge config add --provider openai --model gpt-4
```

## **Option 2: Wrapper Script (Quick Usage)**
Best for occasional use, CI/CD, or Docker environments:

```bash
# Single command that handles setup + execution
./modelforge.sh config show
./modelforge.sh config add --provider openai --model gpt-4
```

**Performance Comparison:**
- **Traditional**: ~0.9s per command
- **Wrapper**: ~1.6s per command (includes setup overhead)

## Local Development & Testing

To test the library locally, you can use the built-in Command-Line Interface (CLI).

**Option 1: Using the setup script (recommended)**
```bash
./setup.sh
```

**Option 2: Manual setup**
1.  **Set up a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

2.  **Install the library in editable mode:**
    This allows you to use the CLI and reflects any code changes immediately without reinstalling.
    ```bash
    pip install -e .
    ```

3.  **Use the CLI to manage your models:**
    ```bash
    # Show the current configuration
    modelforge config show

    # Add a local Ollama model
    modelforge config add --provider ollama --model qwen3:1.7b

    # Add OpenAI models with API key
    modelforge config add --provider openai --model gpt-4o-mini --api-key "YOUR_API_KEY_HERE"
    modelforge config add --provider openai --model gpt-4o --api-model-name "gpt-4o" --api-key "YOUR_API_KEY_HERE"

    # Add a provider requiring an API key (Google Gemini)
    modelforge config add --provider google --model gemini-pro --api-model-name "gemini-1.5-pro" --api-key "YOUR_API_KEY_HERE"

    # Add GitHub Copilot and trigger the device authentication flow
    modelforge config add --provider github_copilot --model claude-3.7-sonnet --dev-auth

    # Set a model to be the default
    modelforge config use --provider ollama --model qwen3:1.7b
    ```

## Available Models and Providers

**📚 Model Reference:**
For a comprehensive list of available providers and models, visit **[models.dev](https://models.dev)** - your go-to resource for:

- **Provider Documentation**: Detailed information about each LLM provider
- **Model Specifications**: Complete model listings with capabilities and pricing
- **API References**: Authentication methods and integration guides
- **Model Comparisons**: Performance metrics and use case recommendations

**Supported Providers:**
- **OpenAI**: GPT-4, GPT-4o, GPT-3.5-turbo, and more
- **Ollama**: Local models like Llama, Qwen, Mistral, and others
- **GitHub Copilot**: Claude, GPT-4, and other models via GitHub *(Enhanced Support)*
- **Google Gemini**: Gemini Pro, Gemini Flash, and other Google models

### 🚀 **Enhanced GitHub Copilot Support**

ModelForge provides **two-tier GitHub Copilot integration** for optimal performance:

#### **🎯 Tier 1: Dedicated ChatGitHubCopilot (Recommended)**
When `langchain-github-copilot` is installed, ModelForge uses the specialized GitHub Copilot class:

```bash
# Install the enhanced GitHub Copilot support
poetry add langchain-github-copilot

# Add GitHub Copilot with device authentication
./modelforge.sh config add --provider github_copilot --model claude-3.7-sonnet --dev-auth
```

**Benefits:**
- ✅ **Optimized for 25-minute token lifecycle**
- ✅ **GitHub-specific rate limiting**
- ✅ **Enhanced error handling**
- ✅ **Built-in token refresh**

#### **🔄 Tier 2: OpenAI-Compatible Fallback**
If `langchain-github-copilot` is not available, ModelForge automatically falls back to OpenAI-compatible mode:

```bash
# Works even without langchain-github-copilot installed
./modelforge.sh config add --provider github_copilot --model claude-3.7-sonnet --dev-auth
```

**Characteristics:**
- ⚡ **Universal compatibility**
- 🛠️ **Manual token management**
- 📊 **Standard OpenAI interface**

#### **🔍 Installation Options**

```bash
# Option 1: Full installation with GitHub Copilot enhancement
git clone <repo>
cd model-forge
./setup.sh
poetry add langchain-github-copilot

# Option 2: Basic installation (fallback mode)
git clone <repo>
cd model-forge
./setup.sh
# Uses OpenAI-compatible fallback automatically
```

Use [models.dev](https://models.dev) to explore the full ecosystem and find the perfect model for your use case!

## Configuration System

ModelForge uses a **two-tier configuration system** that provides flexibility for both personal and project-specific setups:

### 🌍 **Global Configuration** (`~/.model-forge/config.json`)
- **Location**: User's home directory
- **Purpose**: System-wide model configurations shared across all projects
- **Use case**: Personal API keys, frequently used models, default settings

### 📁 **Local Configuration** (`./.model-forge/config.json`)
- **Location**: Current working directory (project-specific)
- **Purpose**: Project-specific model configurations
- **Use case**: Team projects, specific model requirements, environment-specific settings

### 🔄 **Precedence Rules**
1. **Local First**: If a local config exists, it takes precedence
2. **Global Fallback**: If no local config, the global config is used
3. **Auto-Creation**: If neither exists, a new global config is created

### 💡 **Managing Configurations**
```bash
# View current configuration (shows which config is active)
modelforge config show

# Add to global configuration (default)
modelforge config add --provider openai --model gpt-4o --api-key "YOUR_KEY"

# Add to local configuration (project-specific)
modelforge config add --provider openai --model gpt-4o --api-key "YOUR_KEY" --local
```

Both configuration files use the same JSON structure and are fully compatible with all ModelForge features.

## Code Quality & Development

ModelForge maintains high code quality standards with automated tooling:

### 🔧 **Quality Tools**
- **Ruff**: Fast linting and formatting
- **MyPy**: Type checking for reliability
- **Pre-commit**: Automated quality checks
- **GitHub Actions**: CI/CD pipeline
- **Pytest**: Comprehensive testing with coverage

### 📋 **Code Review Guidelines**
We provide comprehensive code review guidelines for consistent quality:
- **[Detailed Guidelines](CODE_REVIEW_GUIDELINES.md)**: Complete review criteria and examples
- **[LLM Prompt](PROMPT_CODE_REVIEW.md)**: Quick prompt for AI-assisted code reviews

### 🚀 **Development Commands**
```bash
# Format and check code
poetry run ruff format .
poetry run ruff check .

# Type checking
poetry run mypy src/modelforge

# Run tests with coverage
poetry run pytest --cov=src/modelforge

# Run all quality checks
poetry run pre-commit run --all-files
```

## Integration Guide

To use this library in a host application (e.g., RAG-Forge):

1.  **Install the library:**
    ```bash
    # Quick setup (recommended for development)
    cd /path/to/model-forge && ./setup.sh

    # Or install manually from a local path
    pip install -e /path/to/model-forge

    # In the future, you would install from a package registry like PyPI
    # pip install model-forge
    ```

2.  **Use the `ModelForgeRegistry` in your application:**
    ```python
    from modelforge.registry import ModelForgeRegistry

    # 1. Initialize the registry
    registry = ModelForgeRegistry()

    # 2. See which models the user has configured
    available_models = registry.list_models()
    print(f"Available models: {available_models}")
    # Example output: ['ollama/qwen3:1.7b', 'github_copilot/claude-3.7-sonnet']

    # 3. Get a fully authenticated model instance
    if available_models:
        model_id = available_models[0]
        llm = registry.get_model_instance(model_id)

        if llm:
            # Now you have a LangChain-compatible LLM object to use
            response = llm.invoke("Tell me a joke.")
            print(response)
    ```

## Features

- **Multi-Provider Support**: OpenAI, Ollama, GitHub Copilot, Google Gemini
- **Flexible Authentication**: API Key, OAuth 2.0 Device Flow, Local (no auth)
- **Secure Credential Storage**: Uses system keyring for API keys and tokens
- **LangChain Integration**: Provides ready-to-use LangChain-compatible model instances
- **Centralized Configuration**: Single configuration file managing all providers and models
