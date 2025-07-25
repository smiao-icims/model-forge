"""Input validation utilities for ModelForge."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from modelforge.exceptions import FileValidationError, InvalidInputError


class InputValidator:
    """Validates user inputs before processing."""

    # Common patterns for validation
    PROVIDER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
    MODEL_NAME_MAX_LENGTH = 100
    URL_SCHEMES = {"http", "https"}
    MAX_DISPLAY_CHOICES = 5

    # Known provider API key patterns
    API_KEY_PATTERNS = {
        "openai": re.compile(r"^sk-[a-zA-Z0-9]{48}$"),
        "anthropic": re.compile(r"^sk-ant-[a-zA-Z0-9-]{50,}$"),
    }

    @classmethod
    def validate_provider_name(cls: type[InputValidator], provider: str | None) -> str:
        """Validate provider name format.

        Args:
            provider: Provider name to validate

        Returns:
            Normalized provider name (lowercase)

        Raises:
            InvalidInputError: If provider name is invalid
        """
        if not provider:
            raise InvalidInputError(
                "Provider name cannot be empty",
                suggestion="Specify a provider like 'openai' or 'ollama'",
                error_code="EMPTY_PROVIDER",
            )

        provider = provider.strip()

        if not cls.PROVIDER_NAME_PATTERN.match(provider):
            raise InvalidInputError(
                f"Invalid provider name: '{provider}'",
                context=(
                    "Provider names must contain only letters, numbers, hyphens, "
                    "and underscores"
                ),
                suggestion=(
                    "Use a valid provider name like 'openai' or 'github-copilot'"
                ),
                error_code="INVALID_PROVIDER_FORMAT",
            )

        # Normalize provider name (convert hyphens to underscores for consistency)
        # This allows both github-copilot and github_copilot to work
        return provider.lower().replace("-", "_")

    @classmethod
    def validate_model_name(cls: type[InputValidator], model: str | None) -> str:
        """Validate model name format.

        Args:
            model: Model name to validate

        Returns:
            Cleaned model name

        Raises:
            InvalidInputError: If model name is invalid
        """
        if not model:
            raise InvalidInputError(
                "Model name cannot be empty",
                suggestion="Specify a model like 'gpt-4' or 'claude-3'",
                error_code="EMPTY_MODEL",
            )

        model = model.strip()

        if len(model) > cls.MODEL_NAME_MAX_LENGTH:
            raise InvalidInputError(
                "Model name is too long",
                context=(
                    f"Model name has {len(model)} characters "
                    f"(max: {cls.MODEL_NAME_MAX_LENGTH})"
                ),
                suggestion="Use a shorter model name",
                error_code="MODEL_NAME_TOO_LONG",
            )

        # Model names can be more flexible, ensure they're not empty
        if not model:
            raise InvalidInputError(
                "Model name cannot be just whitespace",
                suggestion="Specify a valid model name",
                error_code="INVALID_MODEL_NAME",
            )

        return model

    @classmethod
    def validate_api_key(
        cls: type[InputValidator], api_key: str | None, provider: str
    ) -> str:
        """Validate API key format for known providers.

        Args:
            api_key: API key to validate
            provider: Provider name for provider-specific validation

        Returns:
            API key (unchanged)

        Raises:
            InvalidInputError: If API key is invalid
        """
        if not api_key:
            raise InvalidInputError(
                f"API key for {provider} cannot be empty",
                suggestion=f"Provide your {provider} API key",
                error_code="EMPTY_API_KEY",
            )

        api_key = api_key.strip()

        if not api_key:
            raise InvalidInputError(
                f"API key for {provider} cannot be just whitespace",
                suggestion=f"Provide a valid {provider} API key",
                error_code="INVALID_API_KEY",
            )

        # Provider-specific validation
        provider_lower = provider.lower()
        if provider_lower in cls.API_KEY_PATTERNS:
            pattern = cls.API_KEY_PATTERNS[provider_lower]
            if not pattern.match(api_key):
                if provider_lower == "openai":
                    suggestion = (
                        "OpenAI API keys should start with 'sk-' "
                        "and be 51 characters long"
                    )
                elif provider_lower == "anthropic":
                    suggestion = "Anthropic API keys should start with 'sk-ant-'"
                else:
                    suggestion = f"Check your API key format for {provider}"

                raise InvalidInputError(
                    f"Invalid {provider} API key format",
                    context=(
                        f"The provided API key doesn't match the expected format "
                        f"for {provider}"
                    ),
                    suggestion=suggestion,
                    error_code="INVALID_API_KEY_FORMAT",
                )

        return api_key

    @classmethod
    def validate_file_path(
        cls: type[InputValidator],
        file_path: str | None,
        must_exist: bool = False,
        must_be_writable: bool = False,
    ) -> Path:
        """Validate file path.

        Args:
            file_path: File path to validate
            must_exist: Whether the file must already exist
            must_be_writable: Whether the file/directory must be writable

        Returns:
            Path object for the validated path

        Raises:
            FileValidationError: If file path is invalid
        """
        if not file_path:
            raise FileValidationError(
                "empty path",
                "File path cannot be empty",
                suggestion="Provide a valid file path",
            )

        try:
            path = Path(file_path).expanduser().resolve()
        except Exception as e:
            raise FileValidationError(
                file_path,
                f"Invalid file path: {e}",
                suggestion="Check the file path syntax",
            ) from e

        if must_exist and not path.exists():
            raise FileValidationError(
                str(path),
                "File or directory does not exist",
                suggestion=f"Create the file or check the path: {path}",
            )

        if must_be_writable:
            # Check if we can write to the file or its parent directory
            check_path = path if path.exists() else path.parent
            if not os.access(check_path, os.W_OK):
                raise FileValidationError(
                    str(path),
                    "No write permission",
                    suggestion="Check file permissions or choose a different location",
                )

        return path

    @classmethod
    def validate_url(
        cls: type[InputValidator], url: str | None, require_https: bool = True
    ) -> str:
        """Validate URL format.

        Args:
            url: URL to validate
            require_https: Whether to require HTTPS scheme

        Returns:
            Validated URL

        Raises:
            InvalidInputError: If URL is invalid
        """
        if not url:
            raise InvalidInputError(
                "URL cannot be empty",
                suggestion="Provide a valid URL",
                error_code="EMPTY_URL",
            )

        url = url.strip()

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise InvalidInputError(
                f"Invalid URL: '{url}'",
                context=str(e),
                suggestion="Check the URL format",
                error_code="INVALID_URL_FORMAT",
            ) from e

        if not parsed.scheme:
            raise InvalidInputError(
                f"URL missing scheme: '{url}'",
                context="URLs must start with http:// or https://",
                suggestion=f"Try: https://{url}",
                error_code="URL_MISSING_SCHEME",
            )

        if parsed.scheme not in cls.URL_SCHEMES:
            raise InvalidInputError(
                f"Invalid URL scheme: '{parsed.scheme}'",
                context=f"Supported schemes: {', '.join(cls.URL_SCHEMES)}",
                suggestion="Use http:// or https://",
                error_code="INVALID_URL_SCHEME",
            )

        if require_https and parsed.scheme != "https":
            raise InvalidInputError(
                "URL must use HTTPS",
                context=f"Current scheme: {parsed.scheme}",
                suggestion=f"Use: {url.replace('http://', 'https://', 1)}",
                error_code="HTTPS_REQUIRED",
            )

        if not parsed.netloc:
            raise InvalidInputError(
                "URL missing domain",
                context=f"Invalid URL: '{url}'",
                suggestion="Include the domain name in the URL",
                error_code="URL_MISSING_DOMAIN",
            )

        return url

    @classmethod
    def validate_positive_integer(
        cls: type[InputValidator],
        value: int | str | None,
        name: str,
        min_value: int = 1,
        max_value: int | None = None,
    ) -> int:
        """Validate positive integer value.

        Args:
            value: Value to validate (can be string)
            name: Name of the parameter for error messages
            min_value: Minimum allowed value (default: 1)
            max_value: Maximum allowed value (optional)

        Returns:
            Validated integer

        Raises:
            InvalidInputError: If value is invalid
        """
        if value is None:
            raise InvalidInputError(
                f"{name} cannot be None",
                suggestion=f"Provide a positive integer for {name}",
                error_code="NULL_VALUE",
            )

        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise InvalidInputError(
                f"Invalid {name}: '{value}'",
                context=f"{name} must be an integer",
                suggestion=f"Provide a valid integer for {name}",
                error_code="INVALID_INTEGER",
            ) from None

        if int_value < min_value:
            raise InvalidInputError(
                f"{name} must be at least {min_value}",
                context=f"Current value: {int_value}",
                suggestion=f"Use a value >= {min_value}",
                error_code="VALUE_TOO_SMALL",
            )

        if max_value is not None and int_value > max_value:
            raise InvalidInputError(
                f"{name} must be at most {max_value}",
                context=f"Current value: {int_value}",
                suggestion=f"Use a value <= {max_value}",
                error_code="VALUE_TOO_LARGE",
            )

        return int_value

    @classmethod
    def validate_choice(
        cls: type[InputValidator],
        value: str | None,
        choices: list[str] | set[str],
        name: str,
        case_sensitive: bool = False,
    ) -> str:
        """Validate that value is one of the allowed choices.

        Args:
            value: Value to validate
            choices: Allowed choices
            name: Parameter name for error messages
            case_sensitive: Whether comparison is case-sensitive

        Returns:
            Validated value (normalized if case-insensitive)

        Raises:
            InvalidInputError: If value is not in choices
        """
        if not value:
            raise InvalidInputError(
                f"{name} cannot be empty",
                suggestion=f"Choose one of: {', '.join(sorted(choices))}",
                error_code="EMPTY_CHOICE",
            )

        if not case_sensitive:
            # Normalize for comparison
            value_lower = value.lower()
            choices_map = {choice.lower(): choice for choice in choices}
            if value_lower in choices_map:
                return choices_map[value_lower]
        elif value in choices:
            return value

        # Value not in choices
        sorted_choices = sorted(choices)
        if len(sorted_choices) <= cls.MAX_DISPLAY_CHOICES:
            choices_str = ", ".join(sorted_choices)
        else:
            choices_str = (
                ", ".join(sorted_choices[: cls.MAX_DISPLAY_CHOICES])
                + f" (and {len(sorted_choices) - cls.MAX_DISPLAY_CHOICES} more)"
            )

        raise InvalidInputError(
            f"Invalid {name}: '{value}'",
            context=f"Allowed values: {choices_str}",
            suggestion="Choose one of the valid options",
            error_code="INVALID_CHOICE",
        )
