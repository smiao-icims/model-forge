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
- **src/modelforge/modelsdev.py**: models.dev API integration with caching

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
│   ├── uv-migration/          # UV package manager
│   └── error-handling-improvements/
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
- **error-handling-improvements**: Comprehensive error handling (requirements.md ready)

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
