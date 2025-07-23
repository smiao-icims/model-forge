"""Tests for input validation."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from modelforge.exceptions import FileValidationError, InvalidInputError
from modelforge.validation import InputValidator


class TestProviderNameValidation:
    """Test provider name validation."""

    def test_valid_provider_names(self) -> None:
        """Test valid provider names."""
        assert InputValidator.validate_provider_name("openai") == "openai"
        assert InputValidator.validate_provider_name("OpenAI") == "openai"  # Lowercase
        assert (
            InputValidator.validate_provider_name("github-copilot") == "github-copilot"
        )
        assert InputValidator.validate_provider_name("ollama_local") == "ollama_local"
        assert InputValidator.validate_provider_name("provider123") == "provider123"

    def test_empty_provider_name(self) -> None:
        """Test empty provider name."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_provider_name("")
        assert exc_info.value.error_code == "EMPTY_PROVIDER"
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(InvalidInputError):
            InputValidator.validate_provider_name(None)

    def test_invalid_provider_names(self) -> None:
        """Test invalid provider names."""
        invalid_names = [
            "provider with spaces",
            "provider@example",
            "provider.com",
            "provider/test",
            "provider\\test",
            "provider:8080",
        ]
        for name in invalid_names:
            with pytest.raises(InvalidInputError) as exc_info:
                InputValidator.validate_provider_name(name)
            assert exc_info.value.error_code == "INVALID_PROVIDER_FORMAT"
            assert (
                "letters, numbers, hyphens, and underscores" in exc_info.value.context
            )

    def test_provider_name_whitespace_handling(self) -> None:
        """Test whitespace handling in provider names."""
        assert InputValidator.validate_provider_name("  openai  ") == "openai"
        assert InputValidator.validate_provider_name("\topenai\n") == "openai"


class TestModelNameValidation:
    """Test model name validation."""

    def test_valid_model_names(self) -> None:
        """Test valid model names."""
        assert InputValidator.validate_model_name("gpt-4") == "gpt-4"
        assert InputValidator.validate_model_name("claude-3-opus") == "claude-3-opus"
        assert InputValidator.validate_model_name("llama2:7b-chat") == "llama2:7b-chat"
        assert (
            InputValidator.validate_model_name("model.with.dots") == "model.with.dots"
        )
        assert (
            InputValidator.validate_model_name("Model With Spaces")
            == "Model With Spaces"
        )

    def test_empty_model_name(self) -> None:
        """Test empty model name."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_model_name("")
        assert exc_info.value.error_code == "EMPTY_MODEL"

        with pytest.raises(InvalidInputError):
            InputValidator.validate_model_name(None)

    def test_whitespace_only_model_name(self) -> None:
        """Test whitespace-only model name."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_model_name("   ")
        assert exc_info.value.error_code == "INVALID_MODEL_NAME"

    def test_model_name_too_long(self) -> None:
        """Test model name length limit."""
        long_name = "a" * 101
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_model_name(long_name)
        assert exc_info.value.error_code == "MODEL_NAME_TOO_LONG"
        assert "101 characters" in exc_info.value.context

    def test_model_name_whitespace_handling(self) -> None:
        """Test whitespace handling in model names."""
        assert InputValidator.validate_model_name("  gpt-4  ") == "gpt-4"


class TestApiKeyValidation:
    """Test API key validation."""

    def test_empty_api_key(self) -> None:
        """Test empty API key."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_api_key("", "openai")
        assert exc_info.value.error_code == "EMPTY_API_KEY"

        with pytest.raises(InvalidInputError):
            InputValidator.validate_api_key(None, "openai")

    def test_whitespace_only_api_key(self) -> None:
        """Test whitespace-only API key."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_api_key("   ", "openai")
        assert exc_info.value.error_code == "INVALID_API_KEY"

    def test_valid_openai_api_key(self) -> None:
        """Test valid OpenAI API key format."""
        valid_key = "sk-" + "a" * 48
        assert InputValidator.validate_api_key(valid_key, "openai") == valid_key

    def test_invalid_openai_api_key(self) -> None:
        """Test invalid OpenAI API key format."""
        invalid_keys = [
            "not-starting-with-sk",
            "sk-tooshort",
            "sk-" + "a" * 47,  # Too short
            "sk-" + "a" * 49,  # Too long
            "SK-" + "a" * 48,  # Wrong case
        ]
        for key in invalid_keys:
            with pytest.raises(InvalidInputError) as exc_info:
                InputValidator.validate_api_key(key, "openai")
            assert exc_info.value.error_code == "INVALID_API_KEY_FORMAT"
            assert "sk-" in exc_info.value.suggestion
            assert "51 characters" in exc_info.value.suggestion

    def test_valid_anthropic_api_key(self) -> None:
        """Test valid Anthropic API key format."""
        valid_key = "sk-ant-" + "a" * 50
        assert InputValidator.validate_api_key(valid_key, "anthropic") == valid_key

    def test_invalid_anthropic_api_key(self) -> None:
        """Test invalid Anthropic API key format."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_api_key("sk-" + "a" * 50, "anthropic")
        assert exc_info.value.error_code == "INVALID_API_KEY_FORMAT"
        assert "sk-ant-" in exc_info.value.suggestion

    def test_unknown_provider_api_key(self) -> None:
        """Test API key for unknown provider (no specific validation)."""
        any_key = "any-random-api-key-12345"
        assert InputValidator.validate_api_key(any_key, "custom-provider") == any_key

    def test_api_key_whitespace_handling(self) -> None:
        """Test whitespace handling in API keys."""
        valid_key = "sk-" + "a" * 48
        assert (
            InputValidator.validate_api_key(f"  {valid_key}  ", "openai") == valid_key
        )


class TestFilePathValidation:
    """Test file path validation."""

    def test_empty_file_path(self) -> None:
        """Test empty file path."""
        with pytest.raises(FileValidationError) as exc_info:
            InputValidator.validate_file_path("")
        assert "empty path" in exc_info.value.message

        with pytest.raises(FileValidationError):
            InputValidator.validate_file_path(None)

    @patch("pathlib.Path.exists")
    def test_valid_file_path(self, mock_exists: Any) -> None:
        """Test valid file path."""
        mock_exists.return_value = True
        result = InputValidator.validate_file_path("/tmp/test.txt")
        assert isinstance(result, Path)
        assert str(result).endswith("test.txt")

    def test_expanduser(self) -> None:
        """Test tilde expansion."""
        with (
            patch("pathlib.Path.expanduser") as mock_expand,
            patch("pathlib.Path.exists"),
        ):
            mock_expand.return_value = Path("/home/user/file.txt")
            InputValidator.validate_file_path("~/file.txt")
            mock_expand.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_must_exist_validation(self, mock_exists: Any) -> None:
        """Test must_exist validation."""
        mock_exists.return_value = False
        with pytest.raises(FileValidationError) as exc_info:
            InputValidator.validate_file_path("/tmp/nonexistent.txt", must_exist=True)
        assert "does not exist" in exc_info.value.context

        mock_exists.return_value = True
        result = InputValidator.validate_file_path("/tmp/exists.txt", must_exist=True)
        assert isinstance(result, Path)

    @patch("os.access")
    @patch("pathlib.Path.exists")
    def test_must_be_writable_validation(
        self, mock_exists: Any, mock_access: Any
    ) -> None:
        """Test must_be_writable validation."""
        mock_exists.return_value = True
        mock_access.return_value = False

        with pytest.raises(FileValidationError) as exc_info:
            InputValidator.validate_file_path(
                "/tmp/readonly.txt", must_be_writable=True
            )
        assert "No write permission" in exc_info.value.context

        mock_access.return_value = True
        result = InputValidator.validate_file_path(
            "/tmp/writable.txt", must_be_writable=True
        )
        assert isinstance(result, Path)


class TestUrlValidation:
    """Test URL validation."""

    def test_empty_url(self) -> None:
        """Test empty URL."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_url("")
        assert exc_info.value.error_code == "EMPTY_URL"

        with pytest.raises(InvalidInputError):
            InputValidator.validate_url(None)

    def test_valid_urls(self) -> None:
        """Test valid URLs."""
        assert (
            InputValidator.validate_url("https://api.example.com")
            == "https://api.example.com"
        )
        assert (
            InputValidator.validate_url("https://api.example.com/v1/models")
            == "https://api.example.com/v1/models"
        )
        assert (
            InputValidator.validate_url("http://localhost:8080", require_https=False)
            == "http://localhost:8080"
        )

    def test_missing_scheme(self) -> None:
        """Test URL without scheme."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_url("api.example.com")
        assert exc_info.value.error_code == "URL_MISSING_SCHEME"
        assert "https://api.example.com" in exc_info.value.suggestion

    def test_invalid_scheme(self) -> None:
        """Test URL with invalid scheme."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_url("ftp://example.com")
        assert exc_info.value.error_code == "INVALID_URL_SCHEME"

    def test_https_required(self) -> None:
        """Test HTTPS requirement."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_url("http://api.example.com", require_https=True)
        assert exc_info.value.error_code == "HTTPS_REQUIRED"
        assert "https://api.example.com" in exc_info.value.suggestion

    def test_missing_domain(self) -> None:
        """Test URL without domain."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_url("https://")
        assert exc_info.value.error_code == "URL_MISSING_DOMAIN"

    def test_url_whitespace_handling(self) -> None:
        """Test whitespace handling in URLs."""
        assert (
            InputValidator.validate_url("  https://api.example.com  ")
            == "https://api.example.com"
        )


class TestPositiveIntegerValidation:
    """Test positive integer validation."""

    def test_valid_integers(self) -> None:
        """Test valid positive integers."""
        assert InputValidator.validate_positive_integer(5, "count") == 5
        assert InputValidator.validate_positive_integer("10", "limit") == 10
        assert (
            InputValidator.validate_positive_integer(1, "min_value", min_value=1) == 1
        )

    def test_none_value(self) -> None:
        """Test None value."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_positive_integer(None, "count")
        assert exc_info.value.error_code == "NULL_VALUE"

    def test_invalid_integer(self) -> None:
        """Test invalid integer values."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_positive_integer("not a number", "count")
        assert exc_info.value.error_code == "INVALID_INTEGER"

        with pytest.raises(InvalidInputError):
            InputValidator.validate_positive_integer("12.5", "count")

    def test_min_value_validation(self) -> None:
        """Test minimum value validation."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_positive_integer(0, "count", min_value=1)
        assert exc_info.value.error_code == "VALUE_TOO_SMALL"
        assert "at least 1" in str(exc_info.value)

    def test_max_value_validation(self) -> None:
        """Test maximum value validation."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_positive_integer(101, "percentage", max_value=100)
        assert exc_info.value.error_code == "VALUE_TOO_LARGE"
        assert "at most 100" in str(exc_info.value)

    def test_custom_range(self) -> None:
        """Test custom min/max range."""
        assert (
            InputValidator.validate_positive_integer(
                50, "value", min_value=10, max_value=100
            )
            == 50
        )


class TestChoiceValidation:
    """Test choice validation."""

    def test_valid_choices(self) -> None:
        """Test valid choices."""
        choices = ["red", "green", "blue"]
        assert InputValidator.validate_choice("red", choices, "color") == "red"
        assert InputValidator.validate_choice("green", choices, "color") == "green"

    def test_case_insensitive_choices(self) -> None:
        """Test case-insensitive choice matching."""
        choices = ["Red", "Green", "Blue"]
        assert (
            InputValidator.validate_choice(
                "red", choices, "color", case_sensitive=False
            )
            == "Red"
        )
        assert (
            InputValidator.validate_choice(
                "GREEN", choices, "color", case_sensitive=False
            )
            == "Green"
        )

    def test_case_sensitive_choices(self) -> None:
        """Test case-sensitive choice matching."""
        choices = ["Red", "Green", "Blue"]
        with pytest.raises(InvalidInputError):
            InputValidator.validate_choice("red", choices, "color", case_sensitive=True)

    def test_empty_choice(self) -> None:
        """Test empty choice."""
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_choice("", ["a", "b"], "option")
        assert exc_info.value.error_code == "EMPTY_CHOICE"

    def test_invalid_choice(self) -> None:
        """Test invalid choice."""
        choices = ["red", "green", "blue"]
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_choice("yellow", choices, "color")
        assert exc_info.value.error_code == "INVALID_CHOICE"
        assert "blue, green, red" in exc_info.value.context  # Sorted alphabetically

    def test_many_choices(self) -> None:
        """Test error message with many choices."""
        choices = [f"option{i}" for i in range(10)]
        with pytest.raises(InvalidInputError) as exc_info:
            InputValidator.validate_choice("invalid", choices, "option")
        assert "(and 5 more)" in exc_info.value.context
