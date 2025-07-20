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

### 🔄 Developer Workflow (New Python Developers)

**Before every commit, run this exact sequence:**

```bash
# 1. Format code (fixes 90% of issues automatically)
poetry run ruff format .

# 2. Check for linting issues
poetry run ruff check .

# 3. Type checking (catches subtle bugs)
poetry run mypy src/modelforge --ignore-missing-imports

# 4. Run all tests with coverage
poetry run pytest --cov=src/modelforge

# 5. If all pass, you're ready to commit!
git add .
git commit -m "your message"
```

**What these tools do:**
- **ruff format**: Auto-fixes code formatting (like Black)
- **ruff check**: Finds code smells and style issues
- **mypy**: Type checking - catches bugs before runtime
- **pytest**: Runs all tests and shows coverage

### 🚨 Common Developer Mistakes & Fixes

**Problem: CI fails with "line too long"**
```bash
# Fix: ruff format will auto-wrap lines
poetry run ruff format .
```

**Problem: CI fails with "undefined variable"**
```bash
# Fix: mypy catches these - check the error message
poetry run mypy src/modelforge --ignore-missing-imports
```

**Problem: Test fails with "assertion error"**
```bash
# Fix: Run tests locally to see detailed failure
poetry run pytest tests/test_specific_file.py -v
```

### 🎯 Quick Fix Commands

```bash
# Fix everything in one go
poetry run ruff format . && poetry run ruff check --fix . && poetry run mypy src/modelforge --ignore-missing-imports

# Run specific test file
poetry run pytest tests/test_registry.py -v

# See coverage report
poetry run pytest --cov=src/modelforge --cov-report=html
open htmlcov/index.html  # View in browser (macOS)
```

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

## PyPI Distribution & Version Management (✅ Completed)

### 🚀 Proper Release Workflow (Step-by-Step)

**For new Python developers - follow this exact sequence:**

```bash
# 1. Ensure all tests pass locally
poetry run ruff format . && poetry run ruff check . && poetry run mypy src/modelforge --ignore-missing-imports && poetry run pytest --cov=src/modelforge

# 2. Update version in BOTH files:
#    - src/modelforge/__init__.py (change __version__)
#    - pyproject.toml (change version field)

# 3. Commit version bump
git add src/modelforge/__init__.py pyproject.toml
git commit -m "chore: bump version to 0.2.5"

# 4. Create and push tag (triggers GitHub Actions)
git tag v0.2.5              # MUST match version above
git push origin v0.2.5      # Triggers PyPI release

# 5. Monitor release at: https://github.com/your-org/model-forge/actions
```

### ⚠️ Critical Version Rules
- **PyPI versions are IMMUTABLE** - once published, cannot be changed
- **Version MUST match** between `__init__.py` and `pyproject.toml`
- **Tag MUST match** version exactly (v0.2.5 tag → 0.2.5 version)
- **Never re-use version numbers** - always increment

### 📦 PyPI Package Details
- **Package name**: `model-forge-llm` (avoided conflict with 2018 `modelforge` package)
- **PyPI URL**: https://pypi.org/project/model-forge-llm/
- **Installation**: `pip install model-forge-llm`

### 🔧 Version Bumping Commands
```bash
# Automatic version bump (updates pyproject.toml)
poetry version patch        # 0.2.4 → 0.2.5 (recommended)
poetry version minor        # 0.2.4 → 0.3.0 (new features)
poetry version major        # 0.2.4 → 1.0.0 (breaking changes)

# Manual version update (when automatic doesn't work)
# Edit both __init__.py and pyproject.toml manually
```

### 🐛 Common Release Issues

**Problem: PyPI upload fails with "File already exists"**
```bash
# You're trying to re-use a version - bump instead
poetry version patch
git tag v0.2.5
git push origin v0.2.5
```

**Problem: GitHub Actions fails with "Version mismatch"**
```bash
# Check both files have same version
grep "version" src/modelforge/__init__.py pyproject.toml
# Ensure they match, then re-tag after fixing
```

**Problem: Tag already exists**
```bash
# Delete and re-create tag (careful - don't do this for published tags)
git tag -d v0.2.5
git push origin --delete v0.2.5
git tag v0.2.5
git push origin v0.2.5
```

### 🎯 Pre-Commit Checklist (Print This!)

**Before every commit, verify:**
- [ ] `poetry run ruff format .` → "0 files reformatted"
- [ ] `poetry run ruff check .` → "0 errors"
- [ ] `poetry run mypy src/modelforge --ignore-missing-imports` → "Success: no issues found"
- [ ] `poetry run pytest --cov=src/modelforge` → "passed" and ">80% coverage"

### 📋 Build System Evolution
- **From**: Poetry-only with complex CI setup
- **To**: Setuptools-compatible pyproject.toml with pip-friendly dev installation
- **Benefit**: Broader compatibility and simpler CI/CD pipeline

### 🔍 Quality Gates
- **Pre-commit**: Ruff format + check, mypy with lenient config, pytest with coverage
- **CI/CD**: Separate test/lint/security jobs run in parallel
- **Distribution**: Build validation with twine, installation testing

### 🧪 Testing Best Practices
- **Test isolation**: Each test should be independent and not rely on global state
- **Mocking**: Use `unittest.mock` to avoid real API calls in tests
- **Coverage**: Aim for >80% coverage with meaningful test cases
- **Parameter naming**: Tests must match actual library API (e.g., `model` vs `model_name`)

### 🆘 Emergency Debugging Workflow

```bash
# When CI fails and you can't reproduce locally:
# 1. Check exact CI environment
echo "Python: $(python --version)"
echo "Ruff: $(poetry run ruff --version)"
echo "MyPy: $(poetry run mypy --version)"

# 2. Run CI commands in exact order
poetry run ruff format --check .
poetry run ruff check .
poetry run mypy src/modelforge --ignore-missing-imports
poetry run pytest --cov=src/modelforge --cov-report=xml

# 3. If still stuck, create minimal reproduction
# Copy failing test to new file and run:
poetry run pytest tests/debug_test.py -v -s
```

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
