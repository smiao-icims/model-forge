"""Custom exceptions for ModelForge."""


class ModelForgeError(Exception):
    """Base exception class for ModelForge."""


class ConfigurationError(ModelForgeError):
    """Raised when there's an issue with configuration."""


class AuthenticationError(ModelForgeError):
    """Raised when authentication fails."""


class ProviderError(ModelForgeError):
    """Raised when there's an issue with a provider."""


class ModelNotFoundError(ModelForgeError):
    """Raised when a requested model is not found."""


class TokenExpiredError(AuthenticationError):
    """Raised when an authentication token has expired."""


class InvalidProviderError(ProviderError):
    """Raised when an invalid provider is specified."""
