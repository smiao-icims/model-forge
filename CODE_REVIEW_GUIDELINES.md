# ModelForge Code Quality & Review Guidelines

## LLM Instructions for Code Review

You are a senior Python developer conducting a code review for the ModelForge project - a library for managing LLM providers, authentication, and model selection. Apply these guidelines consistently to maintain code quality and project standards.

## 📋 **Core Review Criteria**

> **⚠️ PREREQUISITE**: All unit tests must pass before code review begins. Run `poetry run pytest tests/ -v` to verify.

### 1. **Code Style & Formatting**

**MUST CHECK:**
- [ ] Code follows Ruff formatting (88 char line length)
- [ ] Imports are organized (stdlib → third-party → local)
- [ ] No trailing whitespace or unnecessary blank lines
- [ ] Consistent quote usage (double quotes preferred)
- [ ] Variable names are descriptive and follow snake_case
- [ ] Class names follow PascalCase
- [ ] Constants are UPPER_CASE

**EXAMPLES:**
```python
# ✅ GOOD
from typing import Dict, Any, Optional
import json
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from . import config, auth
from .exceptions import AuthenticationError

# ❌ BAD
from .exceptions import AuthenticationError
from . import config, auth
import json
from pathlib import Path
from typing import Dict,Any,Optional
from langchain_core.language_models.chat_models import BaseChatModel
```

### 2. **Type Safety**

**MUST CHECK:**
- [ ] All function signatures have type hints
- [ ] Return types are explicitly annotated
- [ ] Complex types use proper imports from `typing`
- [ ] Optional parameters are properly annotated
- [ ] No use of `Any` without justification

**EXAMPLES:**
```python
# ✅ GOOD
def get_config() -> Tuple[Dict[str, Any], Path]:
    """Loads model configuration with local-over-global precedence."""

def set_current_model(provider: str, model: str, local: bool = False) -> bool:
    """Sets the currently active model in the configuration."""

# ❌ BAD
def get_config():
    """Loads model configuration with local-over-global precedence."""

def set_current_model(provider, model, local=False):
    """Sets the currently active model in the configuration."""
```

### 3. **Error Handling & Exceptions**

**MUST CHECK:**
- [ ] Use custom exceptions from `exceptions.py` instead of generic ones
- [ ] No bare `except:` clauses
- [ ] Exceptions include meaningful error messages
- [ ] Use logging instead of print statements for errors
- [ ] Proper exception chaining with `raise ... from ...`

**EXAMPLES:**
```python
# ✅ GOOD
from .exceptions import ConfigurationError, AuthenticationError
from .logging_config import get_logger

logger = get_logger(__name__)

try:
    with open(config_path, "r") as f:
        return json.load(f), config_path
except FileNotFoundError as e:
    logger.error("Configuration file not found: %s", config_path)
    raise ConfigurationError(f"Config file not found: {config_path}") from e
except json.JSONDecodeError as e:
    logger.error("Invalid JSON in config file: %s", config_path)
    raise ConfigurationError(f"Invalid JSON in config: {config_path}") from e

# ❌ BAD
try:
    with open(config_path, "r") as f:
        return json.load(f), config_path
except:
    print(f"Error: Could not read config file at {config_path}")
    return {}, config_path
```

### 4. **Logging & Output**

**MUST CHECK:**
- [ ] Use logging instead of print statements
- [ ] Log levels are appropriate (DEBUG, INFO, WARNING, ERROR)
- [ ] Sensitive information is not logged
- [ ] User-facing messages are clear and actionable
- [ ] Debug information uses proper logger

**EXAMPLES:**
```python
# ✅ GOOD
from .logging_config import get_logger

logger = get_logger(__name__)

def authenticate(self) -> Dict[str, Any]:
    logger.info("Starting authentication for provider: %s", self.provider_name)
    try:
        # ... authentication logic
        logger.debug("Authentication successful")
        return {"api_key": api_key}
    except Exception as e:
        logger.error("Authentication failed: %s", str(e))
        raise AuthenticationError("Authentication failed") from e

# ❌ BAD
def authenticate(self) -> Dict[str, Any]:
    print(f"Please enter the API key for {self.provider_name}:")
    try:
        # ... authentication logic
        print("API key stored successfully.")
        return {"api_key": api_key}
    except Exception as e:
        print(f"Error: {e}")
        return None
```

### 5. **Function Design & Architecture**

**MUST CHECK:**
- [ ] Functions have single responsibility
- [ ] Functions are not longer than 30 lines (prefer 15-20)
- [ ] No deep nesting (max 3 levels)
- [ ] Parameters have default values where appropriate
- [ ] Return values are consistent and documented

**EXAMPLES:**
```python
# ✅ GOOD - Single responsibility, clear purpose
def _validate_provider_config(provider_data: Dict[str, Any], provider_name: str) -> None:
    """Validate provider configuration data."""
    if not provider_data:
        raise ConfigurationError(f"Provider '{provider_name}' not found")

    required_fields = ["llm_type", "auth_strategy"]
    for field in required_fields:
        if field not in provider_data:
            raise ConfigurationError(f"Missing required field '{field}' for provider '{provider_name}'")

def get_llm(self, provider_name: Optional[str] = None, model_alias: Optional[str] = None) -> Optional[BaseChatModel]:
    """Retrieve and initialize a LangChain chat model."""
    provider_name, model_alias = self._resolve_model_params(provider_name, model_alias)
    provider_data = self._get_provider_data(provider_name)
    self._validate_provider_config(provider_data, provider_name)
    return self._create_llm_instance(provider_data, provider_name, model_alias)

# ❌ BAD - Too long, multiple responsibilities
def get_llm(self, provider_name: Optional[str] = None, model_alias: Optional[str] = None) -> Optional[BaseChatModel]:
    if not provider_name or not model_alias:
        current_model = config.get_current_model()
        if not current_model:
            print("Error: No model selected...")
            return None
        provider_name = current_model.get("provider")
        model_alias = current_model.get("model")

    provider_data = self._config.get("providers", {}).get(provider_name)
    if not provider_data:
        print(f"Error: Provider '{provider_name}' not found...")
        return None
    # ... 50+ more lines of mixed logic
```

### 6. **Documentation & Comments**

**MUST CHECK:**
- [ ] All public functions have comprehensive docstrings
- [ ] Docstrings follow Google/NumPy style
- [ ] Complex logic has explanatory comments
- [ ] No commented-out code (use git instead)
- [ ] Type information is included in docstrings when helpful

**EXAMPLES:**
```python
# ✅ GOOD
def get_credentials(provider_name: str, model_alias: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored credentials for a given provider.

    Reads the configuration, determines the appropriate auth strategy,
    and returns the credentials if available.

    Args:
        provider_name: The name of the provider (e.g., 'openai', 'github_copilot').
        model_alias: The alias of the model (used for context in error messages).
        verbose: If True, print debug information during credential retrieval.

    Returns:
        A dictionary containing credentials (e.g., {'api_key': '...'}) or None
        if credentials are not found or authentication fails.

    Raises:
        AuthenticationError: If the authentication strategy is invalid or fails.
        ConfigurationError: If the provider configuration is missing or invalid.
    """

# ❌ BAD
def get_credentials(provider_name: str, model_alias: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    # Gets credentials
    pass
```

### 7. **Security Considerations**

**MUST CHECK:**
- [ ] No hardcoded secrets or API keys
- [ ] Sensitive data uses secure storage (configuration files)
- [ ] Input validation for user-provided data
- [ ] No logging of sensitive information
- [ ] Proper handling of authentication tokens

**EXAMPLES:**
```python
# ✅ GOOD
def store_api_key(self, api_key: str) -> None:
    """Store API key securely in configuration file."""
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")

    # Validate API key format (example for OpenAI)
    if not api_key.startswith(('sk-', 'sk-proj-')):
        raise ValueError("Invalid API key format")

    self._save_auth_data({"api_key": api_key})
    logger.info("API key stored successfully for provider: %s", self.provider_name)

# ❌ BAD
def store_api_key(self, api_key: str) -> None:
    """Store API key."""
    logger.info("Storing API key: %s", api_key)  # SECURITY ISSUE!
    self._save_auth_data({"api_key": api_key})
```

### 8. **Testing Considerations**

**MUST CHECK:**
- [ ] **All unit tests pass** (no failing tests allowed)
- [ ] Code is testable (no hard dependencies on external services)
- [ ] Functions can be easily mocked
- [ ] Side effects are minimized
- [ ] New functionality includes corresponding tests
- [ ] Edge cases are considered
- [ ] Tests run successfully in CI/CD pipeline

**EXAMPLES:**
```python
# ✅ GOOD - Testable design
class ApiKeyAuth(AuthStrategy):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def _get_auth_data(self) -> Dict[str, Any]:
        """Wrapper for config access to enable testing."""
        return get_config()[0].get("providers", {}).get(self.provider_name, {}).get("auth_data", {})

# ❌ BAD - Hard to test
class ApiKeyAuth(AuthStrategy):
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        # Direct config call - hard to mock in tests
        config_data, _ = get_config()
        auth_data = config_data.get("providers", {}).get(self.provider_name, {}).get("auth_data", {})
        return auth_data if auth_data else None
```

### **Test Execution Requirements**

**MANDATORY BEFORE CODE REVIEW:**
```bash
# All tests must pass before submitting for review
poetry run pytest tests/ -v

# Expected output should show all tests passing:
# ============ 19 passed in 3.10s ============

# If any tests fail, they must be fixed before merge
```

**MUST VERIFY:**
- [ ] `poetry run pytest tests/ -v` shows all tests passing
- [ ] No test files are skipped or ignored
- [ ] New functionality includes corresponding test coverage
- [ ] Tests run in clean environment (no external dependencies)

## 🧹 **Linter Error Clearance Checklist**

### **📋 Pre-Review Requirements**
Before any code review, **ALL** linter errors must be resolved. This section provides a systematic approach to clearing linter issues.

### **🔍 Step 1: Automated Fixes**
```bash
# Apply all auto-fixable rules
poetry run ruff check --fix .

# Apply unsafe fixes (be careful, review changes)
poetry run ruff check --fix --unsafe-fixes .

# Format code with Black/Ruff
poetry run ruff format .
```

### **📊 Progress Tracking**
**Progress Made:** 600+ errors → 104 errors (83% improvement) ✅

**✅ COMPLETED:**
- Type annotations (ANN001, ANN201, ANN202, ANN204)
- Import organization (I001)
- Trailing whitespace (W291, W293)
- Basic formatting issues

**🚧 REMAINING (104 errors):**
- Line length violations (E501): ~25 errors
- Exception handling (TRY003, TRY301, TRY401): ~40 errors
- Path operations (PTH123): 2 errors
- Security issues (S110, S311, S113): 4 errors
- Code complexity (PLR0912, PLR0913, PLR0915): 4 errors
- Other misc issues: ~29 errors

### **🎯 Step 2: Systematic Error Resolution**

#### **📏 Line Length Violations (E501)**
**What to Fix:**
- Lines longer than 88 characters
- Common causes: Long strings, method calls, complex expressions

**How to Fix:**
```python
# ❌ Too long
really_long_message = f"This is a very long message that contains {variable_name} and {another_variable} and exceeds the line limit"

# ✅ Fixed with parentheses
really_long_message = (
    f"This is a very long message that contains {variable_name} "
    f"and {another_variable} and exceeds the line limit"
)

# ❌ Long method call
result = some_object.very_long_method_name(argument1, argument2, argument3, argument4)

# ✅ Fixed with line breaks
result = some_object.very_long_method_name(
    argument1, argument2, argument3, argument4
)
```

#### **⚠️ Exception Handling (TRY003, TRY301, TRY401)**
**What to Fix:**
- TRY003: Long exception messages outside exception class
- TRY301: Abstract raise to inner function
- TRY401: Redundant str(e) in logging.exception

**How to Fix:**
```python
# ❌ TRY003: Long message in raise
raise ConfigurationError(f"Very long error message with {variable}")

# ✅ Fixed: Move to exception class or shorten
class ConfigurationError(Exception):
    @classmethod
    def provider_not_found(cls, provider: str) -> "ConfigurationError":
        return cls(f"Provider '{provider}' not found")

raise ConfigurationError.provider_not_found(provider_name)

# ❌ TRY401: Redundant str(e)
logger.exception("Error occurred: %s", str(e))

# ✅ Fixed: Remove str(e)
logger.exception("Error occurred")
```

#### **📁 Path Operations (PTH123)**
**What to Fix:**
- Replace `open()` with `Path.open()`

**How to Fix:**
```python
# ❌ Old style
with open(config_path, "w") as f:
    json.dump(data, f)

# ✅ Modern pathlib
with config_path.open("w") as f:
    json.dump(data, f)
```

#### **🔒 Security Issues (S110, S311, S113)**
**What to Fix:**
- S110: try-except-pass without logging
- S311: Insecure random for crypto
- S113: Missing request timeouts

**How to Fix:**
```python
# ❌ S110: Silent exception
try:
    risky_operation()
except Exception:
    pass

# ✅ Fixed: Log the exception
try:
    risky_operation()
except Exception:
    logger.debug("Optional operation failed, continuing")

# ❌ S311: Insecure random
delay = random.uniform(0, 1)

# ✅ Fixed: Use secrets for crypto, random for non-crypto
delay = random.uniform(0, 1)  # OK for backoff delays

# ❌ S113: No timeout
response = requests.post(url, data=data)

# ✅ Fixed: Add timeout
response = requests.post(url, data=data, timeout=30)
```

#### **🏗️ Code Complexity (PLR0912, PLR0913, PLR0915)**
**What to Fix:**
- PLR0912: Too many branches (>12)
- PLR0913: Too many arguments (>5)
- PLR0915: Too many statements (>50)

**How to Fix:**
```python
# ❌ PLR0913: Too many arguments
def complex_function(a, b, c, d, e, f, g):
    pass

# ✅ Fixed: Use dataclass or config object
@dataclass
class Config:
    a: str
    b: str
    c: str
    # ... etc

def simplified_function(config: Config):
    pass
```

### **🔄 Step 3: Final Verification**
```bash
# Check remaining errors
poetry run ruff check .

# Run tests to ensure no regressions
poetry run pytest

# Verify pre-commit passes
poetry run pre-commit run --all-files
```

### **📝 Step 4: Commit Clean Code**
```bash
git add .
git commit -m "fix: Clear all remaining linter errors

✅ Fixed line length violations (E501)
✅ Improved exception handling patterns
✅ Updated path operations to use pathlib
✅ Added security improvements
✅ Reduced code complexity

All 19 tests passing. Code ready for review."
```

### **📝 Code Review Notes**
When reviewing code with linter errors:

**❌ Reject immediately if:**
- Any linter errors remain unfixed
- `poetry run ruff check .` shows non-zero errors
- Type checking fails with `mypy .`

**✅ Accept only when:**
- All automated fixes have been applied
- Manual fixes follow this checklist
- All tests still pass after fixes
- Code maintainability is preserved or improved

**🔄 Iterative Process:**
1. Run automated fixes first
2. Address type annotations systematically
3. Fix line length and formatting
4. Resolve exception handling patterns
5. Address security and complexity issues
6. Verify all tests still pass
7. Commit with descriptive message

## 🏗️ **Architecture Patterns to Enforce**

### 1. **Strategy Pattern for Authentication**
- Each auth method should inherit from `AuthStrategy`
- New auth methods should be added to `AUTH_STRATEGY_MAP`
- Auth strategies should be stateless where possible

### 2. **Configuration Management**
- Use the two-tier system (global/local)
- Always use `get_config()` to read configuration
- Validate configuration before use

### 3. **Factory Pattern for LLM Creation**
- `ModelForgeRegistry` acts as the factory
- Provider-specific logic should be contained
- LLM instances should be ready-to-use upon creation

## 🚨 **Common Anti-Patterns to Flag**

### 1. **Print Statement Usage**
```python
# ❌ REJECT THIS
print("Error: Something went wrong")

# ✅ REQUIRE THIS
logger.error("Something went wrong: %s", error_details)
```

### 2. **Generic Exception Handling**
```python
# ❌ REJECT THIS
try:
    risky_operation()
except Exception:
    return None

# ✅ REQUIRE THIS
try:
    risky_operation()
except SpecificError as e:
    logger.error("Operation failed: %s", str(e))
    raise ConfigurationError("Operation failed") from e
```

### 3. **Long Parameter Lists**
```python
# ❌ REJECT THIS (>5 parameters)
def create_provider(name, type, url, key, secret, timeout, retries, debug):
    pass

# ✅ REQUIRE THIS
@dataclass
class ProviderConfig:
    name: str
    type: str
    url: str
    key: str
    secret: str
    timeout: int = 30
    retries: int = 3
    debug: bool = False

def create_provider(config: ProviderConfig):
    pass
```

## 📊 **Review Checklist Template**

For each code review, verify:

```markdown
## Code Quality Review

### ✅ Style & Formatting
- [ ] Code follows Ruff formatting standards
- [ ] Imports are properly organized
- [ ] Variable names are descriptive

### ✅ Type Safety
- [ ] All functions have type hints
- [ ] Return types are annotated
- [ ] No unjustified use of `Any`

### ✅ Error Handling
- [ ] Custom exceptions used appropriately
- [ ] No bare except clauses
- [ ] Proper logging instead of print statements

### ✅ Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Sensitive data handled securely

### ✅ Architecture
- [ ] Follows established patterns
- [ ] Single responsibility principle
- [ ] Functions are appropriately sized

### ✅ Documentation
- [ ] Comprehensive docstrings
- [ ] Complex logic is commented
- [ ] Public API is documented

### ✅ Testing
- [ ] **All unit tests pass**
- [ ] Code is testable
- [ ] Dependencies can be mocked
- [ ] Edge cases considered
- [ ] New tests added for new functionality
```

## 🎯 **Priority Levels for Review Comments**

### 🔴 **CRITICAL** (Must fix before merge)
- **Failing unit tests** (all tests must pass)
- Security vulnerabilities
- Broken functionality
- Missing type hints on public APIs
- Use of print statements instead of logging

### 🟡 **IMPORTANT** (Should fix)
- Poor error handling
- Missing documentation
- Code style violations
- Performance concerns

### 🔵 **SUGGESTION** (Nice to have)
- Alternative implementations
- Code optimization opportunities
- Additional test cases
- Documentation improvements

## 🚀 **Review Response Format**

Structure feedback as:

```markdown
## Code Review Feedback

### 🔴 Critical Issues
- **Tests**: `tests/test_auth.py::test_api_key_auth_authenticate`
  **Issue**: Unit test failing due to missing mock
  **Fix**: Add proper mocking for keyring.set_password in test setup

- **File**: `src/modelforge/auth.py`, Line 45
  **Issue**: Using print statement instead of logging
  **Fix**: Replace with `logger.error("Authentication failed: %s", str(e))`

### 🟡 Important Issues
- **File**: `src/modelforge/registry.py`, Line 23
  **Issue**: Missing type hints
  **Fix**: Add return type annotation `-> Optional[BaseChatModel]`

### 🔵 Suggestions
- Consider extracting validation logic into separate function
- Could benefit from additional error handling for edge case X

### ✅ Positive Feedback
- Excellent use of Strategy pattern
- Clear and comprehensive docstrings
- Good separation of concerns
```

Use these guidelines consistently to maintain ModelForge's code quality and help developers learn Python best practices.
