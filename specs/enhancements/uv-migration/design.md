# UV Migration Design - ModelForge v0.4.0

## Architecture Overview

The UV migration will replace Poetry with UV as the primary build and dependency management tool while maintaining full compatibility with the existing codebase and workflow. The design focuses on minimal disruption and maximum performance benefits.

## Migration Strategy

### Phase 1: Assessment & Planning
```
Current State → Assessment → Planning → Gradual Migration → Validation
```

### Phase 2: Parallel Implementation
```
Poetry (existing) ↔ UV (new) → Testing → Validation → Switchover
```

## Technical Design

### Build System Architecture

#### Current (Poetry)
```toml
[tool.poetry]
name = "modelforge"
version = "0.1.0"
description = "..."
```

#### Target (UV)
```toml
[project]
name = "modelforge"
version = "0.1.0"
description = "..."
```

### Configuration Mapping

#### pyproject.toml Updates
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "modelforge"
dynamic = ["version"]
description = "A reusable library for managing LLM providers..."
readme = "README.md"
requires-python = ">=3.11"
license = {file = "LICENSE"}
authors = [
    {name = "Your Name", email = "you@example.com"},
]
keywords = ["llm", "ai", "langchain", "providers"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "click>=8.1.7",
    "requests>=2.32.3",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.3.0",
    "langchain-community>=0.3.0",
    "langchain-google-genai>=2.1.5",
    "langchain-github-copilot>=0.4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.2",
    "pytest-mock>=3.14.0",
    "ruff>=0.7.0",
    "mypy>=1.11.0",
    "pre-commit>=3.8.0",
    "pytest-cov>=5.0.0",
    "types-requests>=2.32.0",
]

[project.scripts]
modelforge = "modelforge.cli:cli"

[project.urls]
Homepage = "https://github.com/your-org/model-forge"
Repository = "https://github.com/your-org/model-forge"
Issues = "https://github.com/your-org/model-forge/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.dynamic]
version = {attr = "modelforge.__version__"}
```

### Command Mapping

| Poetry Command | UV Equivalent | Notes |
|---|---|---|
| `poetry install` | `uv pip install -e .` | Development install |
| `poetry install --dev` | `uv pip install -e ".[dev]"` | With dev dependencies |
| `poetry run pytest` | `uv run pytest` | Run tests |
| `poetry build` | `uv build` | Build package |
| `poetry lock` | `uv pip compile` | Lock dependencies |
| `poetry shell` | `uv venv` + `source .venv/bin/activate` | Virtual environment |

### Development Workflow

#### Local Development
```bash
# Install UV
pip install uv

# Create virtual environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Run CLI
uv run modelforge config show
```

#### CI/CD Updates
```yaml
# GitHub Actions workflow
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4
    - name: Install UV
      uses: astral-sh/setup-uv@v2
    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}
    - name: Install dependencies
      run: uv pip install -e ".[dev]"
    - name: Run tests
      run: uv run pytest --cov=src/modelforge
```

## Migration Process

### Step 1: UV Installation
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### Step 2: Project Initialization
```bash
# Create UV environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"
```

### Step 3: Configuration Validation
```bash
# Test all commands work
uv run pytest
uv run ruff check src/
uv run mypy src/modelforge
uv run modelforge config show
```

### Step 4: Script Updates

#### Updated setup.sh
```bash
#!/bin/bash
# Updated setup.sh for UV

# Check for UV installation
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```

#### Updated modelforge.sh
```bash
#!/bin/bash
# Updated modelforge.sh for UV

# Check for UV installation
if ! command -v uv &> /dev/null; then
    echo "UV not found. Please install UV first."
    exit 1
fi

# Run modelforge with UV
uv run modelforge "$@"
```

## Compatibility Layer

### Poetry Compatibility Script
```python
#!/usr/bin/env python3
# poetry_compat.py - Temporary compatibility layer

import subprocess
import sys
import os

def main():
    """Provide Poetry-like interface for UV."""
    if len(sys.argv) < 2:
        print("Usage: poetry_compat.py [install|run|build]")
        return 1

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "install":
        if "--dev" in args:
            subprocess.run(["uv", "pip", "install", "-e", ".[dev]"])
        else:
            subprocess.run(["uv", "pip", "install", "-e", "."])
    elif command == "run":
        subprocess.run(["uv", "run"] + args)
    elif command == "build":
        subprocess.run(["uv", "build"])
    else:
        print(f"Unknown command: {command}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Performance Considerations

### Speed Improvements
- **Dependency resolution**: 5-10x faster than Poetry
- **Package installation**: 2-3x faster than pip
- **Lock file generation**: Instant with `uv pip compile`
- **Virtual environment creation**: 2-3x faster

### Memory Usage
- **Lower memory footprint**: UV uses less memory for operations
- **Efficient caching**: Better dependency caching strategy
- **Reduced disk usage**: More efficient package storage

## Rollback Strategy

### Immediate Rollback
```bash
# Revert to Poetry if issues arise
git checkout HEAD~1  # Before UV migration
poetry install
```

### Gradual Rollback
```bash
# Keep both systems for transition period
cp pyproject.toml pyproject-poetry.toml
cp pyproject-uv.toml pyproject.toml
```

## Migration Validation

### Validation Checklist
- [ ] All tests pass with UV
- [ ] CLI commands work correctly
- [ ] Package builds successfully
- [ ] CI/CD pipeline passes
- [ ] Documentation updated
- [ ] Team successfully adopts UV

### Performance Benchmarks
```bash
# Benchmark comparison
hyperfine \
  'poetry install --quiet' \
  'uv pip install -e .'

hyperfine \
  'poetry run pytest --quiet' \
  'uv run pytest'
```

## Documentation Updates

### README.md Changes
```markdown
## Installation

### Using UV (Recommended)
```bash
pip install uv
uv pip install modelforge
```

### Using pip
```bash
pip install modelforge
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-org/model-forge.git
cd model-forge

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup development environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```
```

## Risk Mitigation

### Technical Risks
- **Dependency conflicts**: Test with complex dependency trees
- **Platform compatibility**: Test on Windows, macOS, Linux
- **Python version compatibility**: Test across Python 3.11+
- **CI/CD issues**: Test GitHub Actions thoroughly

### Process Risks
- **Team adoption**: Provide training and support
- **Documentation gaps**: Comprehensive migration guide
- **Existing workflows**: Ensure compatibility with existing scripts
- **Rollback capability**: Easy rollback if issues arise

## Future Considerations

### Advanced UV Features
- **UV workspaces**: For monorepo development
- **UV cache**: Global dependency caching
- **UV tools**: Rust-based tools for performance
- **UV publish**: Direct PyPI publishing

### Long-term Benefits
- **Ecosystem integration**: Better integration with Python tooling
- **Performance**: Continued performance improvements
- **Features**: Access to UV's evolving feature set
- **Community**: Growing UV community and ecosystem
