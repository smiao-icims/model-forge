# Distribution Packaging Design - ModelForge v0.2.6

## Architecture Overview

The distribution packaging will transform ModelForge from a development-focused project to a production-ready Python package available via PyPI. The design focuses on minimal disruption to existing development workflow while enabling broader adoption.

## Package Structure

### Build System Migration
```
Current: Poetry (pyproject.toml)
Target: Standard setuptools with pyproject.toml
```

**Rationale**: While Poetry is excellent for development, standard setuptools provides broader compatibility with PyPI tooling and ensures the package can be installed in any Python environment.

### Package Layout
```
modelforge/
├── pyproject.toml          # Updated for distribution
├── src/modelforge/         # Source code (unchanged)
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/               # Usage examples
├── scripts/                # Build and release scripts
└── .github/workflows/      # CI/CD for releases
```

### Key Configuration Changes

#### pyproject.toml Updates
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "modelforge"
version = "0.2.6"
description = "A reusable library for managing LLM providers, authentication, and model selection"
readme = "README.md"
requires-python = ">=3.11"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
keywords = ["llm", "ai", "langchain", "openai", "ollama", "providers"]

[project.urls]
Homepage = "https://github.com/your-org/model-forge"
Repository = "https://github.com/your-org/model-forge"
Documentation = "https://model-forge.readthedocs.io"
Issues = "https://github.com/your-org/model-forge/issues"

[project.scripts]
modelforge = "modelforge.cli:cli"
```

## Release Pipeline Design

### GitHub Actions Workflow
```
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12"]

  release:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### Version Management
- **Strategy**: Semantic versioning (SemVer 2.0)
- **Automation**: `python-semantic-release` for version bumping
- **Trigger**: Tag-based releases for stability
- **Pre-releases**: Alpha/beta/rc for testing

### Quality Gates
1. **Test Suite**: All tests pass across Python versions and platforms
2. **Type Checking**: mypy clean
3. **Linting**: ruff clean
4. **Security**: bandit scan
5. **Installation**: Fresh install test in clean environment

## Package Contents

### Core Package
- Source code under `src/modelforge/`
- CLI entry point: `modelforge.cli:cli`
- All runtime dependencies included
- No development dependencies in wheel

### Documentation
- API documentation via Sphinx
- README.md with installation and usage
- CHANGELOG.md with release history
- Examples directory with common use cases

### Metadata
- **Classifiers**: Comprehensive PyPI classifiers
- **Keywords**: SEO-optimized keywords
- **URLs**: Homepage, repository, documentation
- **License**: MIT license clearly stated

## Distribution Strategy

### Release Types
1. **Stable releases** (`v1.2.3`): Full releases with changelog
2. **Pre-releases** (`v1.2.3b1`): Beta testing
3. **Development releases** (`v1.2.3.dev1`): Continuous integration

### Distribution Channels
1. **PyPI**: Primary distribution
2. **TestPyPI**: Pre-release validation
3. **GitHub Releases**: Source distributions and release notes
4. **Docker Hub**: Container images (future enhancement)

### Installation Verification
```bash
# Test installation in clean environment
docker run --rm python:3.11 pip install modelforge
modelforge --help

# Verify CLI functionality
modelforge config show
```

## Security Considerations

### Package Security
- **Dependency scanning**: Check for known vulnerabilities
- **License compliance**: Verify all dependencies have compatible licenses
- **Supply chain**: Use trusted build environments
- **Signing**: Sign releases with GPG (optional)

### Content Security
- **No secrets**: Ensure no API keys or tokens in package
- **Clean build**: Exclude `.env`, `.git`, development files
- **Metadata validation**: Verify package metadata accuracy

## Migration Strategy

### For Existing Users
1. **Development**: Continue using Poetry for development
2. **Installation**: New users install via pip
3. **Existing users**: Can continue using poetry install
4. **Documentation**: Clear migration guide in README

### CI/CD Changes
- **Build system**: Switch from Poetry build to setuptools
- **Testing**: Test pip installation in CI
- **Release**: Automated PyPI publishing
- **Documentation**: Auto-generate API docs

## Success Metrics

- **Installation success rate**: >99% in clean environments
- **Package size**: <5MB wheel
- **Release frequency**: Monthly stable releases
- **User adoption**: PyPI download statistics
- **Issue resolution**: <24h for critical installation issues

## Future Considerations

### Advanced Features
- **Plugin system**: Allow third-party provider plugins
- **Configuration templates**: Provide common setup templates
- **Binary distributions**: Platform-specific wheels for faster installation
- **Container images**: Docker images for easy deployment

### Maintenance
- **Automated testing**: Daily installation tests
- **Security monitoring**: Automated vulnerability scanning
- **Compatibility testing**: New Python version testing
- **Performance regression**: Installation time monitoring
