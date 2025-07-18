# Publishing ModelForge to PyPI

## Prerequisites

1. Create accounts:
   - [PyPI](https://pypi.org/account/register/)
   - [TestPyPI](https://test.pypi.org/account/register/)

2. Generate API tokens:
   - Go to Account Settings → API tokens
   - Create tokens for both PyPI and TestPyPI

3. Configure Poetry:
   ```bash
   poetry config pypi-token.pypi YOUR_PYPI_TOKEN
   poetry config pypi-token.testpypi YOUR_TESTPYPI_TOKEN
   ```

## Publishing Commands

### TestPyPI (for testing)
```bash
poetry publish --build --repository testpypi
```

### PyPI (production)
```bash
poetry publish --build
```

## Manual Publishing (if needed)

```bash
# Build package
poetry build

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## Installation After Publishing

```bash
# From PyPI
pip install modelforge

# From TestPyPI
pip install --index-url https://test.pypi.org/simple/ modelforge
```
