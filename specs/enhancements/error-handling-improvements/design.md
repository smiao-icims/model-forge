# Error Handling Improvements - Design

## Technical Analysis

### Current State Analysis

1. **Exception Usage**:
   - `ConfigurationError` - Used in config.py, auth.py
   - `AuthenticationError` - Used in auth.py
   - `ProviderError` - Used in registry.py
   - `ModelNotFoundError` - Used in registry.py
   - Generic `Exception` - Used throughout CLI

2. **Error Display**:
   - `click.echo(err=True)` - CLI error output
   - `logger.exception()` - Debug logging
   - Raw exception messages - Exposed to users

3. **Error Handling Patterns**:
   - Try/except blocks with generic catches
   - Some custom exceptions with context
   - Limited retry logic (only in GitHub Copilot auth)

## Solution Design

### 1. Exception Hierarchy

```python
# src/modelforge/exceptions.py

class ModelForgeError(Exception):
    """Base exception for all ModelForge errors."""

    def __init__(
        self,
        message: str,
        *,
        context: str | None = None,
        suggestion: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ):
        self.message = message
        self.context = context
        self.suggestion = suggestion
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for structured logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "suggestion": self.suggestion,
            "error_code": self.error_code,
            "details": self.details
        }

# Configuration Errors
class ConfigurationError(ModelForgeError):
    """Base class for configuration-related errors."""
    pass

class ConfigurationNotFoundError(ConfigurationError):
    """Raised when configuration for provider/model is not found."""

    def __init__(self, provider: str, model: str | None = None):
        message = f"No configuration found for provider '{provider}'"
        context = f"Attempting to use model '{model}'" if model else None
        suggestion = f"Run 'modelforge config add --provider {provider}'"
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="CONFIG_NOT_FOUND"
        )

class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass

# Authentication Errors
class AuthenticationError(ModelForgeError):
    """Base class for authentication errors."""
    pass

class InvalidApiKeyError(AuthenticationError):
    """Raised when API key is invalid or expired."""

    def __init__(self, provider: str):
        super().__init__(
            f"Authentication failed for {provider}",
            context="API key is invalid or expired",
            suggestion=f"Update your API key with 'modelforge config add --provider {provider} --api-key NEW_KEY'",
            error_code="INVALID_API_KEY"
        )

# Network Errors
class NetworkError(ModelForgeError):
    """Base class for network-related errors."""
    pass

class NetworkTimeoutError(NetworkError):
    """Raised when network request times out."""
    pass

class RateLimitError(NetworkError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        message = f"Rate limit exceeded for {provider}"
        context = f"Retry after {retry_after} seconds" if retry_after else None
        suggestion = "Wait before retrying or upgrade your plan"
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )

# Provider Errors
class ProviderError(ModelForgeError):
    """Base class for provider-related errors."""
    pass

class ModelNotFoundError(ProviderError):
    """Raised when requested model is not found."""
    pass

# Validation Errors
class ValidationError(ModelForgeError):
    """Base class for validation errors."""
    pass

class InvalidInputError(ValidationError):
    """Raised when user input validation fails."""
    pass
```

### 2. Error Handler Decorator

```python
# src/modelforge/error_handler.py

def handle_errors(operation_name: str, fallback_value: Any = None):
    """Decorator for consistent error handling across operations."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ModelForgeError:
                # Re-raise our custom exceptions as-is
                raise
            except requests.exceptions.Timeout as e:
                raise NetworkTimeoutError(
                    f"Network timeout during {operation_name}",
                    context=str(e),
                    suggestion="Check your internet connection or increase timeout",
                    error_code="NETWORK_TIMEOUT"
                ) from e
            except requests.exceptions.RequestException as e:
                raise NetworkError(
                    f"Network error during {operation_name}",
                    context=str(e),
                    suggestion="Check your internet connection",
                    error_code="NETWORK_ERROR"
                ) from e
            except json.JSONDecodeError as e:
                raise ValidationError(
                    f"Invalid JSON during {operation_name}",
                    context=f"Error at line {e.lineno}, column {e.colno}",
                    suggestion="Check JSON syntax, especially trailing commas",
                    error_code="INVALID_JSON"
                ) from e
            except Exception as e:
                logger.exception(f"Unexpected error in {operation_name}")
                if fallback_value is not None:
                    logger.warning(f"Using fallback value for {operation_name}")
                    return fallback_value
                raise ModelForgeError(
                    f"Unexpected error during {operation_name}",
                    context=str(e),
                    error_code="INTERNAL_ERROR"
                ) from e

        return wrapper
    return decorator
```

### 3. Retry Mechanism

```python
# src/modelforge/retry.py

def retry_on_error(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    errors: tuple[type[Exception], ...] = (NetworkTimeoutError, RateLimitError)
):
    """Decorator for automatic retry with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except errors as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Calculate backoff
                    if isinstance(e, RateLimitError) and e.details.get("retry_after"):
                        wait_time = e.details["retry_after"]
                    else:
                        wait_time = backoff_factor ** attempt

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)

            raise last_exception

        return wrapper
    return decorator
```

### 4. CLI Error Formatter

```python
# src/modelforge/cli_utils.py

class ErrorFormatter:
    """Formats errors for CLI display."""

    def __init__(self, verbose: bool = False, debug: bool = False):
        self.verbose = verbose
        self.debug = debug

    def format_error(self, error: Exception) -> str:
        """Format an exception for CLI display."""
        if isinstance(error, ModelForgeError):
            return self._format_modelforge_error(error)
        else:
            return self._format_generic_error(error)

    def _format_modelforge_error(self, error: ModelForgeError) -> str:
        """Format ModelForgeError with context and suggestions."""
        parts = [click.style(f"❌ Error: {error.message}", fg="red", bold=True)]

        if error.context:
            parts.append(click.style(f"   Context: {error.context}", fg="yellow"))

        if error.suggestion:
            parts.append(click.style(f"   💡 Suggestion: {error.suggestion}", fg="green"))

        if self.verbose and error.error_code:
            parts.append(click.style(f"   Code: {error.error_code}", fg="gray"))

        if self.debug and error.details:
            parts.append(click.style(f"   Details: {error.details}", fg="gray"))

        return "\n".join(parts)

    def _format_generic_error(self, error: Exception) -> str:
        """Format generic exceptions."""
        message = click.style(f"❌ Error: {str(error)}", fg="red", bold=True)

        if self.debug:
            import traceback
            message += "\n\n" + click.style("Traceback:", fg="gray")
            message += "\n" + click.style(traceback.format_exc(), fg="gray")

        return message

# CLI decorator for error handling
def handle_cli_errors(func: Callable) -> Callable:
    """Decorator for consistent CLI error handling."""

    @functools.wraps(func)
    @click.pass_context
    def wrapper(ctx, *args, **kwargs):
        formatter = ErrorFormatter(
            verbose=ctx.obj.get("verbose", False),
            debug=ctx.obj.get("debug", False)
        )

        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            click.echo("\n⚠️  Operation cancelled by user", err=True)
            ctx.exit(130)  # Standard exit code for SIGINT
        except Exception as e:
            error_message = formatter.format_error(e)
            click.echo(error_message, err=True)

            # Log structured error for debugging
            if isinstance(e, ModelForgeError):
                logger.error("CLI error", extra=e.to_dict())
            else:
                logger.exception("Unexpected CLI error")

            ctx.exit(1)

    return wrapper
```

### 5. Input Validation

```python
# src/modelforge/validation.py

class InputValidator:
    """Validates user inputs before processing."""

    @staticmethod
    def validate_provider_name(provider: str) -> str:
        """Validate provider name format."""
        if not provider:
            raise InvalidInputError(
                "Provider name cannot be empty",
                suggestion="Specify a provider like 'openai' or 'ollama'",
                error_code="EMPTY_PROVIDER"
            )

        if not re.match(r"^[a-zA-Z0-9_-]+$", provider):
            raise InvalidInputError(
                f"Invalid provider name: '{provider}'",
                context="Provider names must contain only letters, numbers, hyphens, and underscores",
                suggestion="Use a valid provider name like 'openai' or 'github-copilot'",
                error_code="INVALID_PROVIDER_FORMAT"
            )

        return provider.lower()

    @staticmethod
    def validate_model_name(model: str) -> str:
        """Validate model name format."""
        if not model:
            raise InvalidInputError(
                "Model name cannot be empty",
                suggestion="Specify a model like 'gpt-4' or 'claude-3'",
                error_code="EMPTY_MODEL"
            )

        # Allow more flexible model names
        if len(model) > 100:
            raise InvalidInputError(
                "Model name is too long",
                context=f"Model name has {len(model)} characters (max: 100)",
                suggestion="Use a shorter model name",
                error_code="MODEL_NAME_TOO_LONG"
            )

        return model

    @staticmethod
    def validate_api_key(api_key: str, provider: str) -> str:
        """Validate API key format for known providers."""
        if not api_key:
            raise InvalidInputError(
                f"API key for {provider} cannot be empty",
                suggestion=f"Provide your {provider} API key",
                error_code="EMPTY_API_KEY"
            )

        # Provider-specific validation
        if provider == "openai" and not api_key.startswith("sk-"):
            raise InvalidInputError(
                f"Invalid {provider} API key format",
                context="OpenAI API keys should start with 'sk-'",
                suggestion="Check your API key from OpenAI dashboard",
                error_code="INVALID_API_KEY_FORMAT"
            )

        return api_key
```

## Implementation Strategy

### Phase 1: Foundation (Exception Hierarchy)
1. Create `exceptions.py` with complete hierarchy
2. Create `error_handler.py` with decorator
3. Create `retry.py` with retry mechanism
4. Add comprehensive tests for all exception types

### Phase 2: Module Updates
1. Update `config.py` to use new exceptions
2. Update `auth.py` to use new exceptions
3. Update `registry.py` to use new exceptions
4. Update `modelsdev.py` to use new exceptions
5. Add error handling decorators to all public methods

### Phase 3: CLI Enhancement
1. Create `cli_utils.py` with error formatter
2. Update all CLI commands to use error decorator
3. Add validation to all user inputs
4. Test error display in various scenarios

### Phase 4: Testing & Documentation
1. Add unit tests for all error paths
2. Add integration tests for error scenarios
3. Create error reference documentation
4. Update user documentation with troubleshooting

## Testing Strategy

### Unit Tests
- Test each exception class initialization
- Test exception serialization (to_dict)
- Test error handler decorator with various exceptions
- Test retry mechanism with different scenarios
- Test input validators with edge cases

### Integration Tests
- Test error propagation through layers
- Test CLI error display formatting
- Test retry behavior with real network calls
- Test fallback mechanisms
- Test error logging structure

### Error Scenario Tests
- Missing configuration
- Invalid API keys
- Network timeouts
- Rate limiting
- Malformed JSON
- File permission errors
- Concurrent access issues

## Backward Compatibility

### Approach
1. Keep existing exception classes as subclasses of new hierarchy
2. Maintain existing error messages where possible
3. Add deprecation warnings for old patterns
4. Document migration path for consumers

### Migration Path
```python
# Old code continues to work
try:
    # operation
except ConfigurationError as e:
    # handle error

# New code with enhanced features
try:
    # operation
except ConfigurationNotFoundError as e:
    print(e.suggestion)  # New feature
```

## Performance Considerations

1. **Lazy Loading**: Import exceptions only when needed
2. **Minimal Overhead**: Keep exception creation lightweight
3. **Smart Retries**: Use exponential backoff to avoid hammering APIs
4. **Caching**: Cache validation results where appropriate
5. **Async Support**: Design for future async error handling

## Security Considerations

1. **No Secrets in Errors**: Sanitize API keys and tokens
2. **Limited Context**: Don't expose internal paths in production
3. **Rate Limit Protection**: Prevent error-based DoS
4. **Audit Trail**: Log security-related errors appropriately
