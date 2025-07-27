# Changelog

All notable changes to ModelForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Enhanced Model Metadata and Configuration** (opt-in feature)
  - New `EnhancedLLM` wrapper class that adds metadata properties to any LangChain model
  - Model capabilities exposed: `context_length`, `max_output_tokens`, `supports_function_calling`, `supports_vision`
  - Full model information from models.dev accessible via `model_info` property
  - Pricing information with `pricing_info` property (cost per 1M tokens)
  - Cost estimation via `estimate_cost(input_tokens, output_tokens)` method
  - Parameter configuration with validation: `temperature`, `top_p`, `top_k`, `max_tokens`
  - Parameters validated against model limits (e.g., max_tokens cannot exceed model's limit)

### Changed
- **Gradual Feature Rollout**
  - `get_llm()` now accepts optional `enhanced` parameter (defaults to `False` for compatibility)
  - When `enhanced=None`, checks `MODELFORGE_ENHANCED` environment variable
  - FutureWarning alerts users that `enhanced=True` will become default in v2.3.0
  - Full backward compatibility maintained - existing code works without changes

### Migration Notes
- **No action required** - all existing code continues to work
- To opt-in to new features: `registry.get_llm(enhanced=True)` or set `MODELFORGE_ENHANCED=true`
- In v2.3.0, enhanced features will be enabled by default (use `enhanced=False` for legacy behavior)

### Technical Details
- EnhancedLLM uses delegation pattern to wrap any BaseChatModel
- Metadata fetched from models.dev API with 7-day cache
- <100ms overhead for enhanced features
- Full serialization/pickle support maintained
- All 227 existing tests pass without modification

## [2.1.0] - 2025-01-25

### Added
- **Environment Variable Authentication**
  - Zero-touch authentication for CI/CD pipelines
  - Support for `MODELFORGE_<PROVIDER>_API_KEY` and `MODELFORGE_<PROVIDER>_ACCESS_TOKEN`
  - Provider name normalization (github-copilot → GITHUB_COPILOT)
  - Environment variables take precedence over stored credentials
  - No configuration file changes required for deployment

- **Streaming Support with Authentication**
  - Real-time streaming responses with `--stream` flag in CLI
  - `StreamingAuthHandler` for token monitoring during long responses
  - `StreamWrapper` class for auth-aware streaming in Python API
  - Automatic OAuth token refresh during streaming sessions
  - Authentication error handling and retry logic during streams
  - Async streaming API with timeout and progress callbacks

- **Enhanced Development Experience**
  - Comprehensive test coverage for environment variables and streaming
  - 227 total tests with new auth and streaming test suites
  - Provider-specific streaming behavior documentation
  - Types for aiofiles support for async file operations

### Changed
- **CLI Streaming Interface**
  - Added `--stream` flag to `modelforge test` command
  - Visual feedback shows real-time token generation
  - Provider-dependent streaming granularity (Ollama: token-by-token, GitHub Copilot: buffered)
  - Improved error messages for streaming authentication issues

- **Authentication Priority**
  - Environment variables now take precedence over stored credentials
  - Streamlined authentication flow for automated environments
  - Backward compatibility maintained for existing configurations

### Fixed
- Long line formatting issues in CLI error messages
- Type annotations for all test methods
- Exception handling in streaming modules (proper chaining and logging)
- Pre-commit hook compliance for all new code

### Technical Details
- **New Files**
  - `src/modelforge/streaming.py` - Streaming support with auth handling
  - `tests/test_auth_env_vars.py` - Environment variable authentication tests
  - `tests/test_streaming_simple.py` - Basic streaming functionality tests
  - `specs/v2.1/` - Complete specification documents for v2.1 features

- **Updated Dependencies**
  - Added `types-aiofiles` for async file operation type support
  - All existing dependencies maintained at current versions

## [2.0.0] - 2025-01-25

### Added
- **Telemetry & Cost Tracking**
  - Real-time token usage monitoring (prompt, completion, total)
  - Cost estimation for all supported providers
  - Performance metrics (request duration, response times)
  - Special handling for GitHub Copilot subscription-based pricing
  - Configurable telemetry display (global settings or per-command)
  - LangChain callback integration for metrics collection

- **Flexible Input/Output**
  - Multiple input sources: command-line, files, or stdin
  - File output support with `--output-file` flag
  - Full streaming support for piping commands
  - Clean Q&A formatting for interactive use

- **Settings Management**
  - New `settings` command group for managing preferences
  - Global telemetry control (`modelforge settings telemetry on/off`)
  - Local project-specific settings support
  - Settings stored in configuration files

- **Enhanced CLI Features**
  - `--no-telemetry` flag for disabling telemetry per command
  - Better error messages with context and suggestions
  - Provider name flexibility (both `github-copilot` and `github_copilot` supported)
  - Improved help text and command documentation

- **Developer Experience**
  - Comprehensive test suite (227 tests, 77% coverage)
  - Simplified architecture for easier contribution
  - Direct error handling without complex decorators
  - TDD approach with spec-driven development

### Changed
- **Architecture Simplification**
  - Removed decorator-based error handling (`@handle_errors`, `@handle_cli_errors`)
  - Simplified registry pattern (removed factory abstraction)
  - Merged CLI utilities directly into cli.py
  - Removed abstract base classes in auth.py
  - Direct exception raising with context and suggestions

- **Error Handling**
  - All exceptions now include context and actionable suggestions
  - Consistent error format across the codebase
  - No silent failures or hidden error swallowing
  - Clear error codes for programmatic handling

### Fixed
- Provider name normalization (hyphens to underscores)
- Models.dev API response parsing for descriptions
- Token counting accuracy for cost calculations
- Auth token expiration handling
- Various test failures and edge cases

### Technical Details
- **Removed Files**
  - `error_handler.py` - Decorator-based error handling
  - `cli_utils.py` - Utilities merged into cli.py

- **New Files**
  - `telemetry.py` - Token usage and cost tracking
  - Comprehensive test files for all new features

- **Updated Dependencies**
  - Added `uv` as the recommended package manager
  - Updated to latest LangChain versions
  - Python 3.11+ requirement

## [1.0.0] - 2024-12-20

### Added
- Initial release of ModelForge
- Multi-provider support (OpenAI, Google, Ollama, GitHub Copilot)
- Two-tier configuration system (global and local)
- Authentication management (API keys and device flow)
- Model discovery via models.dev integration
- LangChain integration
- CLI interface for all operations
- Basic error handling and logging

### Provider Support
- OpenAI (GPT-4, GPT-4o, GPT-3.5-turbo)
- Google (Gemini Pro, Gemini Flash)
- Ollama (local models)
- GitHub Copilot (Claude, GPT models)

### Authentication Methods
- API key authentication
- OAuth device flow (GitHub Copilot)
- No-auth support (local models)

## [0.2.5] - 2024-12-15

### Added
- PyPI distribution as `model-forge-llm`
- GitHub Actions CI/CD pipeline
- Automated testing and deployment

## [0.1.0] - 2024-12-01

### Added
- Initial prototype
- Basic provider management
- Simple CLI interface
- Configuration file support

---

## Upgrade Guide

### From 2.0 to 2.1

ModelForge 2.1 is fully backward compatible with 2.0. To upgrade:

```bash
pip install --upgrade model-forge-llm
```

**New Features to Try:**

1. **Environment Variable Authentication** (great for CI/CD):
   ```bash
   export MODELFORGE_OPENAI_API_KEY="sk-..."
   export MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN="ghu_..."
   # No need for modelforge auth login anymore!
   ```

2. **Streaming Responses**:
   ```bash
   modelforge test --prompt "Write a story" --stream
   ```

3. **Async Python API**:
   ```python
   from modelforge.streaming import stream
   async for chunk in stream(llm, "Hello world"):
       print(chunk, end="", flush=True)
   ```

**CI/CD Integration**: Replace interactive auth with environment variables for zero-touch deployment.

### From 1.x to 2.0

ModelForge 2.0 maintains full backward compatibility for all public APIs. To upgrade:

```bash
pip install --upgrade model-forge-llm
```

**New Features to Try:**

1. **Enable Telemetry**:
   ```bash
   modelforge settings telemetry on
   ```

2. **Use Flexible I/O**:
   ```bash
   echo "What is AI?" | modelforge test
   modelforge test --input-file prompt.txt --output-file response.txt
   ```

3. **Add Telemetry to Your Code**:
   ```python
   from modelforge.telemetry import TelemetryCallback
   telemetry = TelemetryCallback(provider="openai", model="gpt-4")
   llm = registry.get_llm(callbacks=[telemetry])
   ```

No changes required to existing code - all v1.0 code continues to work as before.
