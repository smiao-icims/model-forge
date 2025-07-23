"""Tests for ModelForge exception hierarchy."""

from modelforge.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConfigurationNotFoundError,
    ConfigurationValidationError,
    FileValidationError,
    InternalError,
    InvalidApiKeyError,
    InvalidInputError,
    JsonDecodeError,
    JsonError,
    ModelForgeError,
    ModelNotFoundError,
    NetworkError,
    NetworkTimeoutError,
    ProviderError,
    ProviderNotAvailableError,
    RateLimitError,
    TokenExpiredError,
    ValidationError,
)


class TestModelForgeError:
    """Test base ModelForgeError class."""

    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = ModelForgeError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.context is None
        assert error.suggestion is None
        assert error.error_code is None
        assert error.details == {}

    def test_full_initialization(self):
        """Test exception with all parameters."""
        error = ModelForgeError(
            "Test error",
            context="Test context",
            suggestion="Test suggestion",
            error_code="TEST_ERROR",
            details={"key": "value"},
        )
        assert error.message == "Test error"
        assert error.context == "Test context"
        assert error.suggestion == "Test suggestion"
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}

    def test_to_dict(self):
        """Test converting exception to dictionary."""
        error = ModelForgeError(
            "Test error",
            context="Test context",
            suggestion="Test suggestion",
            error_code="TEST_ERROR",
            details={"key": "value"},
        )
        result = error.to_dict()
        assert result == {
            "error_type": "ModelForgeError",
            "message": "Test error",
            "context": "Test context",
            "suggestion": "Test suggestion",
            "error_code": "TEST_ERROR",
            "details": {"key": "value"},
        }

    def test_inheritance(self):
        """Test that ModelForgeError inherits from Exception."""
        error = ModelForgeError("Test")
        assert isinstance(error, Exception)


class TestConfigurationErrors:
    """Test configuration-related errors."""

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inheritance."""
        error = ConfigurationError("Test")
        assert isinstance(error, ModelForgeError)
        assert isinstance(error, Exception)

    def test_configuration_not_found_error(self):
        """Test ConfigurationNotFoundError."""
        # Without model
        error = ConfigurationNotFoundError("openai")
        assert error.message == "No configuration found for provider 'openai'"
        assert error.context is None
        assert error.suggestion == "Run 'modelforge config add --provider openai'"
        assert error.error_code == "CONFIG_NOT_FOUND"

        # With model
        error = ConfigurationNotFoundError("openai", "gpt-4")
        assert error.message == "No configuration found for provider 'openai'"
        assert error.context == "Attempting to use model 'gpt-4'"
        assert error.suggestion == "Run 'modelforge config add --provider openai'"

    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError."""
        error = ConfigurationValidationError("Invalid config")
        assert isinstance(error, ConfigurationError)
        assert str(error) == "Invalid config"


class TestAuthenticationErrors:
    """Test authentication-related errors."""

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inheritance."""
        error = AuthenticationError("Test")
        assert isinstance(error, ModelForgeError)

    def test_invalid_api_key_error(self):
        """Test InvalidApiKeyError."""
        error = InvalidApiKeyError("openai")
        assert error.message == "Authentication failed for openai"
        assert error.context == "API key is invalid or expired"
        assert (
            error.suggestion
            == "Update your API key with 'modelforge config add '--provider openai --api-key NEW_KEY'"
        )
        assert error.error_code == "INVALID_API_KEY"

    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        error = TokenExpiredError("github")
        assert error.message == "Authentication token expired for github"
        assert error.context == "OAuth token needs to be refreshed"
        assert (
            error.suggestion
            == "Re-authenticate with 'modelforge auth login --provider github'"
        )
        assert error.error_code == "TOKEN_EXPIRED"


class TestNetworkErrors:
    """Test network-related errors."""

    def test_network_error_inheritance(self):
        """Test NetworkError inheritance."""
        error = NetworkError("Test")
        assert isinstance(error, ModelForgeError)

    def test_network_timeout_error_basic(self):
        """Test NetworkTimeoutError basic usage."""
        error = NetworkTimeoutError("API call")
        assert error.message == "Network timeout during API call"
        assert error.context is None
        assert error.suggestion == "Check your internet connection or try again later"
        assert error.error_code == "NETWORK_TIMEOUT"

    def test_network_timeout_error_with_timeout(self):
        """Test NetworkTimeoutError with timeout."""
        error = NetworkTimeoutError("API call", timeout=30)
        assert error.message == "Network timeout during API call"
        assert error.context == "Request timed out after 30 seconds"
        assert error.details == {"timeout": 30, "url": None}

    def test_network_timeout_error_with_url(self):
        """Test NetworkTimeoutError with URL."""
        error = NetworkTimeoutError("API call", url="https://api.example.com")
        assert error.context == "Request to https://api.example.com"

    def test_network_timeout_error_full(self):
        """Test NetworkTimeoutError with all parameters."""
        error = NetworkTimeoutError(
            "API call", timeout=30, url="https://api.example.com"
        )
        assert (
            error.context
            == "Request timed out after 30 seconds to https://api.example.com"
        )
        assert error.details == {"timeout": 30, "url": "https://api.example.com"}

    def test_rate_limit_error_basic(self):
        """Test RateLimitError basic usage."""
        error = RateLimitError("openai")
        assert error.message == "Rate limit exceeded for openai"
        assert error.context is None
        assert error.suggestion == "Wait before retrying or upgrade your plan"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("openai", retry_after=60)
        assert error.message == "Rate limit exceeded for openai"
        assert error.context == "Retry after 60 seconds"
        assert error.details == {"retry_after": 60}


class TestProviderErrors:
    """Test provider-related errors."""

    def test_provider_error_inheritance(self):
        """Test ProviderError inheritance."""
        error = ProviderError("Test")
        assert isinstance(error, ModelForgeError)

    def test_model_not_found_error_basic(self):
        """Test ModelNotFoundError basic usage."""
        error = ModelNotFoundError("openai", "gpt-5")
        assert error.message == "Model 'gpt-5' not found for provider 'openai'"
        assert error.context is None
        assert (
            error.suggestion
            == "Use 'modelforge config add --provider openai --model MODEL_NAME' to add a model"
        )
        assert error.error_code == "MODEL_NOT_FOUND"
        assert error.details == {"provider": "openai", "model": "gpt-5"}

    def test_model_not_found_error_with_available_models(self):
        """Test ModelNotFoundError with available models."""
        models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        error = ModelNotFoundError("openai", "gpt-5", available_models=models)
        assert error.context == "Available models: gpt-3.5-turbo, gpt-4, gpt-4-turbo"

    def test_model_not_found_error_with_many_models(self):
        """Test ModelNotFoundError with many available models."""
        models = [f"model-{i}" for i in range(10)]
        error = ModelNotFoundError("provider", "unknown", available_models=models)
        assert (
            error.context
            == "Available models: model-0, model-1, model-2, model-3, model-4 (and 5 more)"
        )

    def test_provider_not_available_error_basic(self):
        """Test ProviderNotAvailableError basic usage."""
        error = ProviderNotAvailableError("custom-provider")
        assert error.message == "Provider 'custom-provider' is not available"
        assert error.context is None
        assert (
            error.suggestion
            == "Check provider status or run 'modelforge config add --provider custom-provider'"
        )
        assert error.error_code == "PROVIDER_NOT_AVAILABLE"

    def test_provider_not_available_error_with_reason(self):
        """Test ProviderNotAvailableError with reason."""
        error = ProviderNotAvailableError("openai", "Service is down for maintenance")
        assert error.context == "Service is down for maintenance"


class TestValidationErrors:
    """Test validation-related errors."""

    def test_validation_error_inheritance(self):
        """Test ValidationError inheritance."""
        error = ValidationError("Test")
        assert isinstance(error, ModelForgeError)

    def test_invalid_input_error(self):
        """Test InvalidInputError."""
        error = InvalidInputError("Invalid input")
        assert isinstance(error, ValidationError)
        assert str(error) == "Invalid input"

    def test_file_validation_error_basic(self):
        """Test FileValidationError basic usage."""
        error = FileValidationError("/path/to/file", "File not found")
        assert error.message == "File validation failed: /path/to/file"
        assert error.context == "File not found"
        assert error.suggestion is None
        assert error.error_code == "FILE_VALIDATION_ERROR"
        assert error.details == {"file_path": "/path/to/file"}

    def test_file_validation_error_with_suggestion(self):
        """Test FileValidationError with suggestion."""
        error = FileValidationError(
            "/path/to/file",
            "Permission denied",
            suggestion="Check file permissions or run with appropriate privileges",
        )
        assert (
            error.suggestion
            == "Check file permissions or run with appropriate privileges"
        )


class TestJsonErrors:
    """Test JSON-related errors."""

    def test_json_error_inheritance(self):
        """Test JsonError inheritance."""
        error = JsonError("Test")
        assert isinstance(error, ModelForgeError)

    def test_json_decode_error_basic(self):
        """Test JsonDecodeError basic usage."""
        error = JsonDecodeError("config.json")
        assert error.message == "Invalid JSON in config.json"
        assert error.context is None
        assert (
            error.suggestion
            == "Check JSON syntax, especially for trailing commas and proper quotes"
        )
        assert error.error_code == "JSON_DECODE_ERROR"

    def test_json_decode_error_with_position(self):
        """Test JsonDecodeError with line and column."""
        error = JsonDecodeError("config.json", line=5, column=12)
        assert error.context == "Error at line 5, column 12"
        assert error.details == {"line": 5, "column": 12}

    def test_json_decode_error_with_reason(self):
        """Test JsonDecodeError with reason."""
        error = JsonDecodeError("config.json", reason="Unexpected character 'x'")
        assert error.context == "Unexpected character 'x'"


class TestInternalError:
    """Test InternalError."""

    def test_internal_error_basic(self):
        """Test InternalError basic usage."""
        error = InternalError("database operation")
        assert error.message == "Internal error during database operation"
        assert error.context is None
        assert (
            error.suggestion
            == "This is likely a bug. Please report it with the error details"
        )
        assert error.error_code == "INTERNAL_ERROR"

    def test_internal_error_with_reason(self):
        """Test InternalError with reason."""
        error = InternalError("database operation", reason="Connection pool exhausted")
        assert error.context == "Connection pool exhausted"
