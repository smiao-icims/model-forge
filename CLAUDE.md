# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Setup development environment
./setup.sh

# Quick usage via wrapper script
./modelforge.sh config show
./modelforge.sh config add --provider openai --model gpt-4o-mini --api-key "YOUR_KEY"
```

## Core Architecture

ModelForge is a Python library for managing LLM providers with three main components:

- **config**: Two-tier configuration system (global `~/.config/model-forge/config.json` and local `./.model-forge/config.json`)
- **auth**: Authentication strategies (API key, OAuth device flow, no-op for local models)
- **registry**: Factory that creates LangChain-compatible LLM instances from configuration

## Distribution Packaging (✅ Completed)

The project now has complete distribution packaging:

- **pyproject.toml**: Modern Python packaging with setuptools backend
- **MANIFEST.in**: Proper package data inclusion and exclusion rules
- **Build system**: Poetry-based with `poetry build` for wheel and sdist
- **Validation**: Twine checks pass for both formats
- **Installation**: Successfully installs via pip from wheel
- **CLI**: Entry point `modelforge` command works correctly

Build commands:
```bash
poetry build                    # Build wheel and sdist
poetry run twine check dist/*   # Validate packages
poetry run pip install dist/*.whl  # Test installation
```

## Core Development Workflow

**Before committing to GitHub, always run the full quality check suite:**

```bash
# Complete pre-commit quality check (run this exact command)
poetry run ruff format . && poetry run ruff check . && poetry run mypy src/modelforge --ignore-missing-imports && poetry run pytest --cov=src/modelforge
```

**For CI/CD issues, use these targeted fixes:**
- **Poetry vs pip**: CI uses `pip install -e .[dev]` instead of Poetry
- **Type checking**: MyPy runs with `--ignore-missing-imports` to handle third-party libs
- **Linter**: Ruff format auto-fixes formatting, then ruff check validates
- **Tests**: Always run `pytest --cov=src/modelforge` before pushing

**Quick CI fix checklist:**
1. Run `poetry run ruff format .` (auto-fixes formatting)
2. Run `poetry run ruff check .` (fixes linting)
3. Run `poetry run mypy src/modelforge --ignore-missing-imports` (type checking)
4. Run `poetry run pytest --cov=src/modelforge` (tests + coverage)
5. Commit with `git commit -m "description" --no-verify` (bypass pre-commit if needed)

### Development Commands

```bash
# Install dependencies and setup
poetry install
poetry run pre-commit install

# Code quality (run these before every commit)
poetry run ruff format .
poetry run ruff check .
poetry run mypy src/modelforge
poetry run pytest --cov=src/modelforge

# CLI usage
poetry run modelforge config show
poetry run modelforge config add --provider ollama --model qwen3:1.7b
poetry run modelforge config use --provider openai --model gpt-4o-mini
poetry run modelforge test --prompt "Hello world"
```

## Key Files

- **src/modelforge/registry.py**: Main `ModelForgeRegistry` class - factory for creating LLM instances
- **src/modelforge/config.py**: Configuration loading/saving with global/local precedence
- **src/modelforge/auth.py**: Authentication strategies and credential management
- **src/modelforge/cli.py**: Click-based CLI for configuration management

## Distribution Packaging Learnings

### Key Challenges Resolved
1. **Poetry vs pip**: CI uses pip install -e .[dev] to avoid Poetry dependency issues
2. **Type checking**: MyPy configured with practical settings (--ignore-missing-imports)
3. **Linter rules**: Ruff configured with appropriate ignore rules for CLI complexity
4. **Test parameter mismatch**: Fixed unit test expecting `model_name` vs actual `model` parameter
5. **CI/CD workflow**: Split into test/lint/security jobs for better error isolation

### Build System Evolution
- **From**: Poetry-only with complex CI setup
- **To**: Setuptools-compatible pyproject.toml with pip-friendly dev installation
- **Benefit**: Broader compatibility and simpler CI/CD pipeline

### Quality Gates
- **Pre-commit**: Ruff format + check, mypy with lenient config, pytest with coverage
- **CI/CD**: Separate test/lint/security jobs run in parallel
- **Distribution**: Build validation with twine, installation testing

## Provider Support

- **OpenAI**: `openai_compatible` via `ChatOpenAI`
- **Ollama**: Local models via `ChatOllama`
- **Google**: Gemini models via `ChatGoogleGenerativeAI`
- **GitHub Copilot**: Two-tier support (dedicated `ChatGitHubCopilot` or OpenAI fallback)

## Testing

Tests use pytest with coverage. Key test files:
- `tests/test_config.py` - Configuration management
- `tests/test_auth.py` - Authentication strategies
- `tests/test_registry.py` - LLM factory and provider integration

### Testing Learnings from CI/CD Implementation
- **Parameter naming**: Tests must match actual library API (e.g., `model` vs `model_name`)
- **Mock assertions**: Use exact parameter names from actual constructors
- **Test isolation**: Each test should be independent and not rely on global state
- **Coverage**: Aim for >80% coverage with meaningful test cases
