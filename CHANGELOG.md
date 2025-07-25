# Changelog

All notable changes to ModelForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
