"""ModelForge exception hierarchy for consistent error handling."""

from __future__ import annotations

from typing import Any

# Constants
MAX_DISPLAY_MODELS = 5


class ModelForgeError(Exception):
    """Base exception for all ModelForge errors."""

    def __init__(
        self,
        message: str,
        *,
        context: str | None = None,
        suggestion: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
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
            "details": self.details,
        }


# Configuration Errors
class ConfigurationError(ModelForgeError):
    """Base class for configuration-related errors."""


class ConfigurationNotFoundError(ConfigurationError):
    """Raised when configuration for provider/model is not found."""

    def __init__(self, provider: str, model: str | None = None) -> None:
        message = f"No configuration found for provider '{provider}'"
        context = f"Attempting to use model '{model}'" if model else None
        suggestion = f"Run 'modelforge config add --provider {provider}'"
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="CONFIG_NOT_FOUND",
        )


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""


# Authentication Errors
class AuthenticationError(ModelForgeError):
    """Base class for authentication errors."""


class InvalidApiKeyError(AuthenticationError):
    """Raised when API key is invalid or expired."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Authentication failed for {provider}",
            context="API key is invalid or expired",
            suggestion=(
                f"Update your API key with 'modelforge config add '"
                f"--provider {provider} --api-key NEW_KEY'"
            ),
            error_code="INVALID_API_KEY",
        )


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Authentication token expired for {provider}",
            context="OAuth token needs to be refreshed",
            suggestion=(
                f"Re-authenticate with 'modelforge auth login --provider {provider}'"
            ),
            error_code="TOKEN_EXPIRED",
        )


# Network Errors
class NetworkError(ModelForgeError):
    """Base class for network-related errors."""


class NetworkTimeoutError(NetworkError):
    """Raised when network request times out."""

    def __init__(
        self,
        operation: str,
        timeout: int | None = None,
        url: str | None = None,
    ) -> None:
        message = f"Network timeout during {operation}"
        context = f"Request timed out after {timeout} seconds" if timeout else None
        if url:
            context = f"{context} to {url}" if context else f"Request to {url}"
        super().__init__(
            message,
            context=context,
            suggestion="Check your internet connection or try again later",
            error_code="NETWORK_TIMEOUT",
            details={"timeout": timeout, "url": url},
        )


class RateLimitError(NetworkError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None) -> None:
        message = f"Rate limit exceeded for {provider}"
        context = f"Retry after {retry_after} seconds" if retry_after else None
        suggestion = "Wait before retrying or upgrade your plan"
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


# Provider Errors
class ProviderError(ModelForgeError):
    """Base class for provider-related errors."""


class ModelNotFoundError(ProviderError):
    """Raised when requested model is not found."""

    def __init__(
        self, provider: str, model: str, available_models: list[str] | None = None
    ) -> None:
        message = f"Model '{model}' not found for provider '{provider}'"
        suggestion = (
            f"Use 'modelforge config add --provider {provider} --model MODEL_NAME' "
            f"to add a model"
        )
        if available_models:
            models_list = ", ".join(available_models[:MAX_DISPLAY_MODELS])
            context = f"Available models: {models_list}"
            if len(available_models) > MAX_DISPLAY_MODELS:
                context += f" (and {len(available_models) - MAX_DISPLAY_MODELS} more)"
        else:
            context = None
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="MODEL_NOT_FOUND",
            details={"provider": provider, "model": model},
        )


class ProviderNotAvailableError(ProviderError):
    """Raised when provider is not available or configured."""

    def __init__(self, provider: str, reason: str | None = None) -> None:
        message = f"Provider '{provider}' is not available"
        context = reason
        suggestion = (
            f"Check provider status or run 'modelforge config add "
            f"--provider {provider}'"
        )
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="PROVIDER_NOT_AVAILABLE",
        )


# Validation Errors
class ValidationError(ModelForgeError):
    """Base class for validation errors."""


class InvalidInputError(ValidationError):
    """Raised when user input validation fails."""


class FileValidationError(ValidationError):
    """Raised when file validation fails."""

    def __init__(
        self,
        file_path: str,
        reason: str,
        suggestion: str | None = None,
    ) -> None:
        message = f"File validation failed: {file_path}"
        super().__init__(
            message,
            context=reason,
            suggestion=suggestion,
            error_code="FILE_VALIDATION_ERROR",
            details={"file_path": file_path},
        )


# JSON Errors
class JsonError(ModelForgeError):
    """Base class for JSON-related errors."""


class JsonDecodeError(JsonError):
    """Raised when JSON decoding fails."""

    def __init__(
        self,
        source: str,
        line: int | None = None,
        column: int | None = None,
        reason: str | None = None,
    ) -> None:
        message = f"Invalid JSON in {source}"
        if line and column:
            context: str | None = f"Error at line {line}, column {column}"
        else:
            context = reason
        suggestion = (
            "Check JSON syntax, especially for trailing commas and proper quotes"
        )
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="JSON_DECODE_ERROR",
            details={"line": line, "column": column},
        )


# Internal Errors
class InternalError(ModelForgeError):
    """Raised for unexpected internal errors."""

    def __init__(self, operation: str, reason: str | None = None) -> None:
        message = f"Internal error during {operation}"
        context = reason
        suggestion = "This is likely a bug. Please report it with the error details"
        super().__init__(
            message,
            context=context,
            suggestion=suggestion,
            error_code="INTERNAL_ERROR",
        )
