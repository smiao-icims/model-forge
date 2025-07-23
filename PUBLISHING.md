# Publishing ModelForge to PyPI (1.0.0+)

## Automated Release Process (Recommended)

We use GitHub Actions for automated PyPI releases:

1. **Version Bump & Tag**
   ```bash
   # Update version in both files
   vim src/modelforge/__init__.py  # __version__ = "1.0.1"
   vim pyproject.toml             # version = "1.0.1"

   # Commit and tag
   git add src/modelforge/__init__.py pyproject.toml
   git commit -m "chore: bump version to 1.0.1"
   git tag v1.0.1
   git push origin v1.0.1
   ```

2. **GitHub Actions handles the rest**
   - Builds wheel and sdist using setuptools
   - Validates with twine
   - Publishes to PyPI automatically

## Manual Release Process (Backup)

### Prerequisites

1. **Create PyPI accounts:**
   - [PyPI](https://pypi.org/account/register/)
   - [TestPyPI](https://test.pypi.org/account/register/)

2. **Generate API tokens:**
   - Go to Account Settings → API tokens
   - Create tokens for both PyPI and TestPyPI

3. **Install build tools:**
   ```bash
   uv add --dev build twine
   ```

### Release Steps

1. **Build Package**
   ```bash
   # Clean old builds
   rm -rf dist/

   # Build with setuptools (PEP 517)
   uv run python -m build
   ```

2. **Validate Package**
   ```bash
   # Check package integrity
   uv run twine check dist/*

   # Test installation locally
   pip install dist/*.whl
   modelforge --help
   ```

3. **Test on TestPyPI**
   ```bash
   # Upload to TestPyPI first
   uv run twine upload --repository testpypi dist/*

   # Test installation from TestPyPI
   pip install --index-url https://test.pypi.org/simple/ model-forge-llm
   ```

4. **Publish to PyPI**
   ```bash
   # Upload to production PyPI
   uv run twine upload dist/*
   ```

## Version Management

### Version Bumping Rules
- **Patch (1.0.1)**: Bug fixes, documentation updates
- **Minor (1.1.0)**: New features, provider additions
- **Major (2.0.0)**: Breaking changes, architecture changes

### Release Checklist

- [ ] All tests pass: `uv run pytest --cov=src/modelforge`
- [ ] Code quality checks pass: `uv run pre-commit run --all-files`
- [ ] Version updated in both `__init__.py` and `pyproject.toml`
- [ ] Changelog updated (if applicable)
- [ ] Documentation reflects changes
- [ ] Git tag matches version exactly

## Package Information

- **PyPI Name**: `model-forge-llm`
- **Source Package**: `modelforge`
- **Entry Point**: `modelforge` CLI command
- **Python Support**: 3.11+

## Installation After Publishing

```bash
# From PyPI (production)
pip install model-forge-llm

# From TestPyPI (testing)
pip install --index-url https://test.pypi.org/simple/ model-forge-llm

# Verify installation
modelforge --help
```

## Troubleshooting

### Common Issues

1. **Version Already Exists**
   - PyPI versions are immutable
   - Increment version number and retry

2. **Package Name Conflicts**
   - We use `model-forge-llm` on PyPI
   - Source package remains `modelforge`

3. **Build Failures**
   - Ensure `uv sync --extra dev` completes successfully
   - Check `pyproject.toml` syntax with `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"`

4. **GitHub Actions Failures**
   - Check workflow logs in Actions tab
   - Ensure tag format matches exactly: `v1.0.1`
