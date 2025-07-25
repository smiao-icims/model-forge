# Contributing to ModelForge

Thank you for your interest in contributing to ModelForge! This guide will help you get started.

## Development Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (modern Python package manager)

### Setup Steps

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/model-forge.git
   cd model-forge
   ```

2. **Set up development environment** (automated)
   ```bash
   ./setup.sh
   ```

   Or manually:
   ```bash
   # Install uv (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies and setup pre-commit
   uv sync --extra dev
   uv run pre-commit install
   ```

3. **Verify setup**
   ```bash
   uv run modelforge --help
   uv run pytest tests/ -v
   ```

## Code Quality

We use several tools to maintain code quality:

- **Ruff**: For linting and formatting
- **MyPy**: For type checking
- **Pytest**: For testing
- **Pre-commit**: For automated checks

### Linting Strategy

We balance code quality with pragmatism. Our linting configuration in `pyproject.toml` enforces critical rules while allowing flexibility for legitimate use cases:

#### Enforced Rules (Critical for code quality)
- **E/F/W**: Basic Python errors and warnings
- **I**: Import sorting
- **N**: Naming conventions
- **UP**: Python version upgrade suggestions
- **B**: Common Python bugs
- **RET**: Return statement issues
- **SIM**: Code simplification

#### Relaxed Rules (Non-critical style preferences)
- **PLR0912/PLR0915**: Complex CLI commands may exceed branch/statement limits
- **ARG002**: Callbacks and overrides often have unused arguments
- **ANN401**: Dynamic Python sometimes needs `Any` type
- **PLC0415**: Conditional imports are sometimes necessary
- **S105**: Test files contain mock tokens/passwords

#### Test-Specific Relaxations
Tests have additional relaxed rules since they follow different patterns:
- Type annotations are optional (focus on test clarity)
- Hardcoded test data is allowed
- Longer lines for complex assertions
- More arguments in test fixtures

### Code Review Guidelines

We maintain comprehensive code review standards:
- **[Detailed Guidelines](CODE_REVIEW_GUIDELINES.md)**: Complete review criteria with examples
- **[LLM Prompt](PROMPT_CODE_REVIEW.md)**: Quick prompt for AI-assisted reviews
- **[Review Example](EXAMPLE_CODE_REVIEW.md)**: Practical example of the review process

### Running Quality Checks

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Type checking
uv run mypy src/modelforge

# Run tests with coverage
uv run pytest --cov=src/modelforge

# Run all checks (recommended before committing)
uv run pre-commit run --all-files
```

### Pre-commit Workflow

Before every commit, run this sequence:
```bash
uv run ruff format .
uv run ruff check .
uv run mypy src/modelforge --ignore-missing-imports
uv run pytest --cov=src/modelforge
```

## Making Changes

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the existing code style
   - Add type hints to all new functions
   - Write/update tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   uv run pytest --cov=src/modelforge
   uv run mypy src/modelforge --ignore-missing-imports
   uv run ruff check .
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

## Commit Messages

We follow conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test changes
- `refactor:` for code refactoring
- `style:` for formatting changes

## Pull Request Process

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request**
   - Provide a clear title and description
   - Link any related issues
   - Ensure all CI checks pass

3. **Review process**
   - Address any feedback from reviewers
   - Update your branch if needed
   - Be patient and responsive

## Adding New Providers

When adding support for a new LLM provider:

1. **Update the CLI** (`src/modelforge/cli.py`)
   - Add provider configuration logic
   - Define the appropriate `llm_type` and `auth_strategy`

2. **Update the Registry** (`src/modelforge/registry.py`)
   - Add LLM initialization logic
   - Handle provider-specific parameters

3. **Add Authentication** (if needed)
   - Extend existing auth strategies or create new ones
   - Ensure secure credential handling

4. **Add Tests**
   - Test configuration
   - Test authentication
   - Test LLM initialization

5. **Update Documentation**
   - Update README with new provider info
   - Add configuration examples

## Testing

- Write unit tests for new functionality
- Ensure good test coverage (aim for >90%)
- Test both success and failure scenarios
- Use mocks appropriately for external dependencies

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all new functions/classes
- Include type hints in all function signatures
- Provide usage examples where appropriate

## Questions?

If you have questions, please:
1. Check existing issues and discussions
2. Create a new issue with the `question` label
3. Be specific about what you're trying to do

Thank you for contributing! 🎉
