# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**🚀 ModelForge 1.0.0 - Production Ready with uv Package Manager**

## Quick Start

```bash
# Setup development environment with uv (modern, fast)
./setup.sh

# Quick usage with uv
uv run modelforge config show
uv run modelforge config add --provider openai --model gpt-4o-mini --api-key "YOUR_KEY"
```

## Core Architecture

ModelForge is a Python library for managing LLM providers with three main components:

- **config**: Two-tier configuration system (global `~/.config/model-forge/config.json` and local `./.model-forge/config.json`)
- **auth**: Authentication strategies (API key, OAuth device flow, no-op for local models)
- **registry**: Factory that creates LangChain-compatible LLM instances from configuration

## Distribution Packaging (✅ 1.0.0 Release Ready)

The project has modern, production-ready distribution packaging:

- **pyproject.toml**: PEP 621 compliant configuration with setuptools backend
- **uv.lock**: Reproducible dependency resolution with uv package manager
- **Build system**: Modern uv-based with GitHub Actions automation
- **PyPI**: Published as `model-forge-llm` package
- **CLI**: Entry point `modelforge` command works correctly
- **Testing**: Comprehensive test suite with >90% coverage

Build commands:
```bash
uv run python -m build          # Build wheel and sdist
uv run twine check dist/*       # Validate packages
pip install dist/*.whl          # Test installation
```

## Core Development Workflow

### 🔄 Developer Workflow (uv-based)

**Before every commit, run this exact sequence:**

```bash
# 1. Format code (fixes 90% of issues automatically)
uv run ruff format .

# 2. Check for linting issues
uv run ruff check .

# 3. Type checking (catches subtle bugs)
uv run mypy src/modelforge --ignore-missing-imports

# 4. Run all tests with coverage
uv run pytest --cov=src/modelforge

# 5. If all pass, you're ready to commit!
git add .
git commit -m "your message"
```

**What these tools do:**
- **ruff format**: Auto-fixes code formatting (like Black)
- **ruff check**: Finds code smells and style issues
- **mypy**: Type checking - catches bugs before runtime
- **pytest**: Runs all tests and shows coverage
- **uv**: Modern Python package manager (faster than pip/poetry)

### 🚨 Common Developer Mistakes & Fixes

**Problem: CI fails with "line too long"**
```bash
# Fix: ruff format will auto-wrap lines
uv run ruff format .
```

**Problem: CI fails with "undefined variable"**
```bash
# Fix: mypy catches these - check the error message
uv run mypy src/modelforge --ignore-missing-imports
```

**Problem: Test fails with "assertion error"**
```bash
# Fix: Run tests locally to see detailed failure
uv run pytest tests/test_specific_file.py -v
```

### 🎯 Quick Fix Commands

```bash
# Fix everything in one go
uv run ruff format . && uv run ruff check --fix . && uv run mypy src/modelforge --ignore-missing-imports

# Run specific test file
uv run pytest tests/test_registry.py -v

# See coverage report
uv run pytest --cov=src/modelforge --cov-report=html
open htmlcov/index.html  # View in browser (macOS)
```

### Development Commands

```bash
# Install dependencies and setup (recommended)
./setup.sh

# Or manual setup
uv sync --extra dev
uv run pre-commit install

# Code quality (run these before every commit)
uv run ruff format .
uv run ruff check .
uv run mypy src/modelforge --ignore-missing-imports
uv run pytest --cov=src/modelforge

# CLI usage
uv run modelforge config show
uv run modelforge config add --provider ollama --model qwen3:1.7b
uv run modelforge config use --provider openai --model gpt-4o-mini
uv run modelforge test --prompt "Hello world"
```

## Key Files

- **src/modelforge/registry.py**: Main `ModelForgeRegistry` class - factory for creating LLM instances
- **src/modelforge/config.py**: Configuration loading/saving with global/local precedence
- **src/modelforge/auth.py**: Authentication strategies and credential management
- **src/modelforge/cli.py**: Click-based CLI for configuration management
- **src/modelforge/modelsdev.py**: models.dev API integration with caching
- **src/modelforge/exceptions.py**: Comprehensive exception hierarchy with context and suggestions
- **src/modelforge/error_handler.py**: Error handling decorator with fallback support
- **src/modelforge/retry.py**: Retry mechanism with exponential backoff
- **src/modelforge/validation.py**: Input validation utilities
- **src/modelforge/cli_utils.py**: CLI error formatting and utilities

## Spec-Driven TDD Development 🎯

### **Development Philosophy**
We follow **Specification-Driven Test-Driven Development (TDD)** where:
1. **Specs first**: Write requirements, design, and tasks in `specs/` directory
2. **Tests second**: Write failing tests based on spec requirements
3. **Code third**: Implement code to make tests pass
4. **Refactor fourth**: Improve code while keeping tests green

### **Spec Directory Structure**
```
specs/
├── baseline/                    # Core architecture specs
├── enhancements/               # Feature additions
│   ├── distribution-packaging/ # PyPI packaging (✅ COMPLETED)
│   ├── modelsdev-integration/  # models.dev API (✅ COMPLETED)
│   ├── error-handling-improvements/ # Error handling (✅ IN PROGRESS)
│   └── uv-migration/          # UV package manager
├── security-credentials-refactor/
├── testing-improvements/
└── type-safety-refactor/
```

### **Spec-Driven TDD Workflow**

#### **1. Planning Phase**
```bash
# Create new feature spec
cp -r specs/template specs/features/your-feature-name/

# Edit the three required files:
# - specs/features/your-feature-name/requirements.md
# - specs/features/your-feature-name/design.md
# - specs/features/your-feature-name/tasks.md
```

#### **2. Test-Driven Development**
```bash
# 1. Write failing tests based on spec tasks
touch tests/test_your_feature.py

# 2. Run tests (they should fail)
poetry run pytest tests/test_your_feature.py -v

# 3. Implement minimal code to pass tests
# 4. Refactor while keeping tests green
# 5. Update spec task completion status
```

#### **3. Spec Validation Checklist**
- [ ] **Requirements**: Clear problem statement and acceptance criteria
- [ ] **Design**: Architecture decisions and technical approach
- [ ] **Tasks**: Specific, testable implementation tasks
- [ ] **Tests**: Each task has corresponding test cases
- [ ] **Documentation**: User-facing documentation updated

### **Spec Template Usage**

#### **For New Features**
```bash
# 1. Create new spec directory
mkdir -p specs/features/new-authentication-method

# 2. Copy template
cp specs/template/* specs/features/new-authentication-method/

# 3. Edit files with your feature details
#    - requirements.md: What problem are we solving?
#    - design.md: How will we solve it?
#    - tasks.md: Specific steps to implement
```

#### **Spec Task Completion Format**
When completing tasks, use this format:
```markdown
- [x] **TASK-001**: Create authentication class (✅ AuthProvider implemented)
- [x] **TASK-002**: Add OAuth2 flow (✅ OAuth2DeviceFlow class created)
- [ ] **TASK-003**: Implement token refresh (⏳ pending - see tests/test_auth.py)
```

### **Testing Requirements per Spec**

#### **Minimum Test Coverage**
- **Unit tests**: 90%+ coverage for new features
- **Integration tests**: API endpoints and CLI commands
- **Mock tests**: External dependencies (APIs, file system)
- **Performance tests**: Cache hit rates and API timing

#### **Test Structure**
```python
def test_spec_task_001_basic_functionality():
    """Test TASK-001: Basic functionality requirement"""
    # Given: Setup from spec
    # When: Action from spec
    # Then: Expected result from spec
```

### **Spec Review Process**

#### **Before Implementation**
1. **Peer review**: Spec must be reviewed before coding
2. **Test review**: Test cases must be reviewed before implementation
3. **Design validation**: Architecture decisions validated against requirements

#### **During Implementation**
1. **Daily spec sync**: Update task completion status
2. **Test running**: All tests must pass before moving to next task
3. **Documentation**: Update CLAUDE.md with new patterns

#### **Completion Criteria**
- All spec tasks marked ✅ completed
- All tests passing
- Documentation updated
- Code review approved
- Spec merged to main branch

### **Current Active Specs**

#### **✅ COMPLETED**
- **distribution-packaging**: PyPI distribution (v0.2.4 released)
- **modelsdev-integration**: models.dev API integration

#### **🔄 IN PROGRESS**
- **error-handling-improvements**: Comprehensive error handling (70% complete)
  - ✅ Exception hierarchy with context and suggestions
  - ✅ Error handler decorator with fallback values
  - ✅ Retry mechanism with exponential backoff
  - ✅ Input validation framework
  - ✅ CLI error formatting
  - ✅ Updated config.py, auth.py, registry.py
  - 🔄 Pending: cli.py and modelsdev.py updates

#### **📋 BACKLOG**
- **uv-migration**: Switch to UV package manager
- **security-credentials-refactor**: Enhanced security
- **testing-improvements**: Test suite enhancements
- **type-safety-refactor**: Enhanced type checking

### **Spec Development Commands**

#### **Spec Creation**
```bash
# New feature spec
cp -r specs/template specs/features/my-new-feature

# Edit the three core files
vim specs/features/my-new-feature/requirements.md  # What
vim specs/features/my-new-feature/design.md        # How
vim specs/features/my-new-feature/tasks.md         # Steps
```

#### **Spec Validation**
```bash
# Validate spec completeness
./scripts/validate-spec.sh specs/features/my-new-feature/

# Generate test stubs from spec
./scripts/generate-tests.sh specs/features/my-new-feature/
```

#### **Spec Status**
```bash
# Check spec completion status
find specs -name "tasks.md" -exec grep -l "\[x\]" {} \; | wc -l
echo "$(find specs -name "tasks.md" | wc -l) total specs"
```

### **Best Practices**

#### **Spec Writing**
- **Specific**: Each task should be testable
- **Measurable**: Clear success criteria
- **Achievable**: Realistic scope
- **Relevant**: Aligns with project goals

## Bug Fix Workflow 🐛

### **Structured Bug Fix Process**

We follow a **Specification-Driven Bug Fix** approach that mirrors our feature development workflow:

1. **Investigation & Analysis**: Understand the root cause
2. **Spec Creation**: Document the problem, solution design, and implementation tasks
3. **Test-Driven Fix**: Write tests that demonstrate the fix
4. **Implementation**: Code the solution following the spec
5. **Validation**: Ensure fix works and doesn't break existing functionality

### **Bug Fix Directory Structure**
```
specs/bug-fixes/
├── issue-name/
│   ├── requirements.md    # Problem analysis & requirements
│   ├── design.md         # Technical solution design
│   └── tasks.md          # Implementation tasks
```

### **Step-by-Step Bug Fix Workflow**

#### **Phase 1: Investigation (15-30 minutes)**

```bash
# 1. Reproduce the issue
poetry run modelforge [command that fails]

# 2. Investigate with verbose logging
poetry run modelforge [command] --verbose

# 3. Check relevant test files
poetry run pytest tests/test_[relevant_module].py -v

# 4. Examine the codebase
# Look at the relevant source files to understand current implementation
```

#### **Phase 2: Spec Creation (30-45 minutes)**

```bash
# 1. Create bug fix spec directory
mkdir -p specs/bug-fixes/[issue-name]/

# 2. Create requirements.md
# Document:
# - Problem statement with examples
# - Root cause analysis
# - Expected vs actual behavior
# - Success criteria
```

**requirements.md Template:**
```markdown
# Bug Fix: [Issue Title] - Requirements

## Problem Statement
[Clear description of the issue]

## Root Cause Analysis
[Technical explanation of why the bug occurs]

## Requirements
- **REQ-001**: [Specific requirement to fix the issue]
- **REQ-002**: [Additional requirements]

## Expected Behavior
[What should happen]

## Actual Behavior
[What currently happens]

## Success Criteria
- [ ] Issue is resolved
- [ ] No regressions introduced
- [ ] Tests pass
```

```bash
# 3. Create design.md
# Document:
# - Technical solution approach
# - Code changes needed
# - Testing strategy
# - Backward compatibility considerations
```

**design.md Template:**
```markdown
# Bug Fix: [Issue Title] - Design

## Technical Analysis
[Analysis of the current implementation and issues]

## Solution Design
[How you plan to fix the issue]

## Implementation Strategy
[Step-by-step approach]

## Testing Strategy
[How you'll test the fix]

## Backward Compatibility
[Ensuring no breaking changes]
```

```bash
# 4. Create tasks.md
# Document:
# - Specific implementation tasks
# - Testing tasks
# - Validation tasks
```

**tasks.md Template:**
```markdown
# Bug Fix: [Issue Title] - Tasks

## Implementation Tasks
- [ ] **TASK-001**: [Specific code change]
- [ ] **TASK-002**: [Additional changes]

## Testing Tasks
- [ ] **TASK-003**: [Write/update tests]
- [ ] **TASK-004**: [Integration testing]

## Validation Tasks
- [ ] **TASK-005**: [Manual testing]
- [ ] **TASK-006**: [Regression testing]
```

#### **Phase 3: Test-Driven Fix (30-60 minutes)**

```bash
# 1. Write failing tests that demonstrate the bug
touch tests/test_[bug_fix_name].py

# 2. Write tests that will pass when bug is fixed
poetry run pytest tests/test_[bug_fix_name].py -v
# (These should fail initially)

# 3. Update existing tests if needed
# Ensure existing tests still reflect correct behavior
```

**Test Structure Example:**
```python
def test_bug_fix_specific_scenario():
    """Test that demonstrates the bug is fixed."""
    # Given: Setup that reproduces the bug
    # When: Action that previously failed
    # Then: Expected correct behavior

def test_bug_fix_no_regression():
    """Test that existing functionality still works."""
    # Ensure the fix doesn't break other features
```

#### **Phase 4: Implementation (60-120 minutes)**

```bash
# 1. Implement the fix following the design spec
# Make minimal changes to fix the specific issue

# 2. Run tests frequently during development
poetry run pytest tests/test_[bug_fix_name].py -v

# 3. Update task completion in tasks.md
# Mark tasks as completed: [x] **TASK-001**: Description (✅ completed)
```

#### **Phase 5: Validation (15-30 minutes)**

```bash
# 1. Run full test suite
poetry run pytest --cov=src/modelforge

# 2. Run code quality checks
poetry run ruff format .
poetry run ruff check .
poetry run mypy src/modelforge --ignore-missing-imports

# 3. Manual testing
poetry run modelforge [original failing command]

# 4. Test edge cases and related functionality
```

### **Bug Fix Validation Checklist**

#### **Technical Validation**
- [ ] Original issue is resolved
- [ ] All tests pass (including new tests)
- [ ] Code quality checks pass (ruff, mypy)
- [ ] No performance degradation
- [ ] Backward compatibility maintained

#### **User Experience Validation**
- [ ] CLI commands work as expected
- [ ] Error messages are helpful
- [ ] No new confusing behavior introduced
- [ ] Documentation updated if needed

#### **Regression Testing**
- [ ] Related functionality still works
- [ ] Integration tests pass
- [ ] Manual testing of similar features
- [ ] Edge cases handled properly

### **Bug Fix Example: models-list-empty-descriptions**

**Problem**: `modelforge models list` appeared to show hardcoded data due to empty descriptions.

**Root Cause**: `_parse_model_data()` method wasn't extracting description information from API response.

**Solution**: Enhanced description generation from model metadata.

**Files Changed**:
- `src/modelforge/modelsdev.py`: Added description generation logic
- `tests/test_modelsdev_descriptions.py`: Comprehensive test suite
- Updated existing tests to match new data structure

**Result**: Rich, informative model descriptions showing live API data.

### **Bug Fix Commands Reference**

#### **Investigation**
```bash
# Reproduce issue
poetry run modelforge [failing-command]

# Debug with verbose output
poetry run modelforge [failing-command] --verbose

# Run related tests
poetry run pytest tests/test_[module].py -v
```

#### **Development**
```bash
# Create spec directory
mkdir -p specs/bug-fixes/[issue-name]/

# Run specific tests during development
poetry run pytest tests/test_[bug_fix].py -v

# Check code quality
poetry run ruff format . && poetry run ruff check .
```

#### **Validation**
```bash
# Full test suite
poetry run pytest --cov=src/modelforge

# Manual verification
poetry run modelforge [original-command]

# Performance check (if relevant)
time poetry run modelforge [command]
```

### **Bug Fix Best Practices**

#### **Investigation**
- **Reproduce consistently**: Ensure you can reliably reproduce the issue
- **Understand root cause**: Don't just fix symptoms, understand why it happens
- **Check related code**: Look for similar patterns that might have the same issue
- **Review recent changes**: Check if recent commits introduced the bug

#### **Specification**
- **Be specific**: Clearly define what needs to be fixed
- **Consider edge cases**: Think about boundary conditions and error scenarios
- **Plan for testing**: Design the fix with testability in mind
- **Document assumptions**: Note any assumptions about the current system

#### **Implementation**
- **Minimal changes**: Fix the specific issue without unnecessary refactoring
- **Test-driven**: Write tests first, then implement the fix
- **Incremental progress**: Make small, verifiable changes
- **Update documentation**: Keep specs updated as you implement

#### **Validation**
- **Comprehensive testing**: Test the fix, regressions, and edge cases
- **User perspective**: Verify the fix from a user's point of view
- **Performance impact**: Ensure the fix doesn't degrade performance
- **Long-term maintainability**: Consider how the fix affects future development

### **Common Bug Fix Patterns**

#### **Data Parsing Issues**
- **Problem**: API response structure doesn't match expected format
- **Solution**: Update parsing logic to handle actual API structure
- **Testing**: Mock API responses with real data structure

#### **Empty/Missing Data Display**
- **Problem**: UI shows empty or placeholder data
- **Solution**: Improve data extraction and fallback logic
- **Testing**: Test with various data completeness scenarios

#### **Configuration Issues**
- **Problem**: Settings not loading or applying correctly
- **Solution**: Fix configuration precedence and validation
- **Testing**: Test different configuration scenarios

#### **CLI Command Issues**
- **Problem**: Commands fail or produce unexpected output
- **Solution**: Fix argument parsing and output formatting
- **Testing**: Test CLI commands with various input combinations

### **Bug Fix Documentation**

After completing a bug fix, update:

1. **CLAUDE.md**: Add new patterns or commands if applicable
2. **README.md**: Update if user-facing behavior changed
3. **Spec completion**: Mark all tasks as completed in tasks.md
4. **Code comments**: Reference the bug fix in relevant code sections

### **Emergency Bug Fix Process**

For critical production issues:

1. **Immediate fix**: Create minimal fix without full spec process
2. **Deploy hotfix**: Get the fix to users quickly
3. **Follow-up spec**: Create proper spec documentation after the fact
4. **Comprehensive testing**: Add tests to prevent regression
5. **Root cause analysis**: Understand why the bug wasn't caught earlier
- **Time-bound**: Includes effort estimation

#### **Test Writing**
- **One test per task**: Direct mapping to spec tasks
- **Descriptive names**: Include task number and purpose
- **Arrange-Act-Assert**: Clear test structure
- **Mock external deps**: Use pytest-mock for APIs
- **Parametrize**: Test multiple scenarios

#### **Documentation**
- **Update CLAUDE.md**: Add new patterns and commands
- **Code comments**: Reference spec task numbers
- **README updates**: Document new features
- **Changelog**: Track spec-driven changes

## Error Handling Framework (✅ 70% Complete)

### 🎯 Overview

ModelForge now has a comprehensive error handling framework that provides:
- **Clear, actionable error messages** with context and suggestions
- **Automatic retry** for transient network issues
- **Input validation** before operations
- **Consistent error formatting** across CLI and library

### 🏗️ Architecture

#### Exception Hierarchy
```python
ModelForgeError  # Base exception with context, suggestion, error_code
├── ConfigurationError
│   ├── ConfigurationNotFoundError
│   └── ConfigurationValidationError
├── AuthenticationError
│   ├── InvalidApiKeyError
│   └── TokenExpiredError
├── NetworkError
│   ├── NetworkTimeoutError
│   └── RateLimitError
├── ProviderError
│   ├── ModelNotFoundError
│   └── ProviderNotAvailableError
├── ValidationError
│   ├── InvalidInputError
│   └── FileValidationError
├── JsonError
│   └── JsonDecodeError
└── InternalError
```

#### Key Components

1. **Error Handler Decorator** (`@handle_errors`)
   ```python
   @handle_errors("operation name", fallback_value=None)
   def risky_operation():
       # Automatically catches and converts exceptions
   ```

2. **Retry Mechanism** (`@retry_on_error`)
   ```python
   @retry_on_error(max_retries=3, backoff_factor=2.0)
   def network_operation():
       # Automatically retries on NetworkTimeoutError, RateLimitError
   ```

3. **Input Validation** (`InputValidator`)
   ```python
   # Validates before operations to prevent errors
   provider = InputValidator.validate_provider_name(provider)
   api_key = InputValidator.validate_api_key(api_key, provider)
   ```

4. **CLI Error Formatting** (`ErrorFormatter`)
   ```python
   # Beautiful error display with colors and suggestions
   @handle_cli_errors
   def cli_command(ctx):
       # Errors are automatically formatted for users
   ```

### 📝 Usage Examples

#### Creating Custom Exceptions
```python
raise ConfigurationNotFoundError(
    "openai",
    "gpt-4",
    context="Provider not found in configuration",
    suggestion="Run 'modelforge config add --provider openai'"
)
```

#### Adding Error Handling to Functions
```python
@handle_errors("load configuration", fallback_value={})
def load_config():
    # Exceptions are caught and logged
    # Returns {} on error instead of crashing
```

#### Network Operations with Retry
```python
@handle_errors("API call")
@retry_on_error(max_retries=3)
def call_api():
    # Retries up to 3 times with exponential backoff
    # Honors Retry-After headers for rate limits
```

### 🧪 Testing Error Scenarios

All error handling components have comprehensive tests:
- `tests/test_exceptions.py` - Exception hierarchy tests
- `tests/test_error_handler.py` - Error handler decorator tests
- `tests/test_retry.py` - Retry mechanism tests
- `tests/test_validation.py` - Input validation tests
- `tests/test_cli_utils.py` - CLI formatting tests

### 🔄 Migration Guide

When updating code to use the new error handling:

1. **Replace generic exceptions**:
   ```python
   # Old
   raise ValueError(f"Provider {name} not found")

   # New
   raise ProviderNotAvailableError(
       name,
       "Provider not found in configuration"
   )
   ```

2. **Add error handling decorators**:
   ```python
   # Old
   def risky_operation():
       try:
           # code
       except Exception as e:
           logger.error(f"Error: {e}")
           raise

   # New
   @handle_errors("risky operation")
   def risky_operation():
       # code
   ```

3. **Add input validation**:
   ```python
   # Old
   def add_provider(name, api_key):
       # direct use

   # New
   def add_provider(name, api_key):
       name = InputValidator.validate_provider_name(name)
       api_key = InputValidator.validate_api_key(api_key, name)
       # validated use
   ```

### 📊 Progress Status

- ✅ **Completed**: Exception hierarchy, error handler, retry mechanism, validation, CLI formatting
- ✅ **Updated Modules**: config.py, auth.py, registry.py
- 🔄 **In Progress**: Updating remaining modules (cli.py, modelsdev.py)
- 📋 **Next Steps**: Complete module updates, add telemetry hooks, create error reference docs

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

### Testing Best Practices
- **Parameter naming**: Tests must match actual library API (e.g., `model` vs `model_name`)
- **Mock assertions**: Use exact parameter names from actual constructors
- **Test isolation**: Each test should be independent and not rely on global state
- **Coverage**: Aim for >80% coverage with meaningful test cases
- **Type annotations**: All test methods should have `-> None` return type annotations
- **Mock parameters**: Use `Any` type for mock objects in test signatures

### Test Configuration

The project uses ruff with relaxed rules for test files:

```toml
# pyproject.toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ANN401",  # Allow Any type in tests (common for mocks)
    "S101",    # Allow assert in tests
    "S108",    # Allow hardcoded temp paths in tests
    "PT019",   # Allow pytest fixtures without value
    "PLR2004", # Allow magic value comparison in tests
    "TRY002",  # Allow custom exceptions in tests
    "ARG001",  # Allow unused function arguments (test fixtures)
    "PLR0913", # Allow many arguments in test functions
    "E501",    # Allow longer lines in tests (for assertions)
]
```
