"""Tests for error handler decorator."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from modelforge.error_handler import handle_errors
from modelforge.exceptions import (
    InternalError,
    JsonDecodeError,
    ModelForgeError,
    NetworkError,
    NetworkTimeoutError,
    RateLimitError,
)


class TestHandleErrors:
    """Test handle_errors decorator."""

    def test_successful_function_call(self):
        """Test that successful calls pass through unchanged."""

        @handle_errors("test operation")
        def successful_func():
            return "success"

        assert successful_func() == "success"

    def test_modelforge_error_passthrough(self):
        """Test that ModelForgeError exceptions pass through."""

        @handle_errors("test operation")
        def failing_func():
            raise ModelForgeError("Custom error")

        with pytest.raises(ModelForgeError) as exc_info:
            failing_func()
        assert str(exc_info.value) == "Custom error"

    def test_timeout_error_handling(self):
        """Test timeout error conversion."""

        @handle_errors("API call")
        def timeout_func():
            error = requests.exceptions.Timeout()
            error.timeout = 30
            raise error

        with pytest.raises(NetworkTimeoutError) as exc_info:
            timeout_func()
        assert exc_info.value.message == "Network timeout during API call"
        assert exc_info.value.error_code == "NETWORK_TIMEOUT"

    def test_timeout_error_with_request(self):
        """Test timeout error with request details."""

        @handle_errors("API call")
        def timeout_func():
            error = requests.exceptions.Timeout()
            error.request = Mock(url="https://api.example.com/endpoint")
            raise error

        with pytest.raises(NetworkTimeoutError) as exc_info:
            timeout_func()
        assert exc_info.value.details["url"] == "https://api.example.com/endpoint"

    def test_rate_limit_error_handling(self):
        """Test rate limit error detection."""

        @handle_errors("API call")
        def rate_limit_func():
            response = Mock()
            response.status_code = 429
            response.headers = {"Retry-After": "60"}
            error = requests.exceptions.HTTPError(response=response)
            raise error

        with pytest.raises(RateLimitError) as exc_info:
            rate_limit_func()
        assert exc_info.value.message == "Rate limit exceeded for API call"
        assert exc_info.value.details["retry_after"] == 60

    def test_rate_limit_without_retry_after(self):
        """Test rate limit error without Retry-After header."""

        @handle_errors("API call")
        def rate_limit_func():
            response = Mock()
            response.status_code = 429
            response.headers = {}
            error = requests.exceptions.HTTPError(response=response)
            raise error

        with pytest.raises(RateLimitError) as exc_info:
            rate_limit_func()
        assert exc_info.value.details["retry_after"] is None

    def test_generic_http_error(self):
        """Test generic HTTP error handling."""

        @handle_errors("API call")
        def http_error_func():
            response = Mock()
            response.status_code = 404
            error = requests.exceptions.HTTPError(response=response)
            raise error

        with pytest.raises(NetworkError) as exc_info:
            http_error_func()
        assert exc_info.value.message == "HTTP error during API call"
        assert exc_info.value.error_code == "HTTP_ERROR"

    def test_connection_error_handling(self):
        """Test connection error handling."""

        @handle_errors("API call")
        def connection_error_func():
            raise requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(NetworkError) as exc_info:
            connection_error_func()
        assert exc_info.value.message == "Connection error during API call"
        assert exc_info.value.error_code == "CONNECTION_ERROR"
        assert "Check your internet connection" in exc_info.value.suggestion

    def test_generic_request_exception(self):
        """Test generic request exception handling."""

        @handle_errors("API call")
        def request_error_func():
            raise requests.exceptions.RequestException("Generic error")

        with pytest.raises(NetworkError) as exc_info:
            request_error_func()
        assert exc_info.value.message == "Network error during API call"
        assert exc_info.value.error_code == "NETWORK_ERROR"

    def test_json_decode_error_handling(self):
        """Test JSON decode error handling."""

        @handle_errors("JSON parsing")
        def json_error_func():
            json.loads("invalid json")

        with pytest.raises(JsonDecodeError) as exc_info:
            json_error_func()
        assert exc_info.value.message == "Invalid JSON in JSON parsing"
        assert exc_info.value.error_code == "JSON_DECODE_ERROR"
        assert exc_info.value.details["line"] == 1

    def test_key_error_handling(self):
        """Test KeyError handling."""

        @handle_errors("dict access")
        def key_error_func():
            d = {}
            return d["missing_key"]

        with pytest.raises(InternalError) as exc_info:
            key_error_func()
        assert exc_info.value.message == "Internal error during dict access"
        assert "KeyError" in exc_info.value.context

    def test_value_error_handling(self):
        """Test ValueError handling."""

        @handle_errors("conversion")
        def value_error_func():
            return int("not a number")

        with pytest.raises(InternalError) as exc_info:
            value_error_func()
        assert exc_info.value.message == "Internal error during conversion"
        assert "ValueError" in exc_info.value.context

    def test_fallback_value_on_error(self):
        """Test fallback value is returned on error."""

        @handle_errors("operation", fallback_value="default")
        def failing_func():
            raise ValueError("Some error")

        result = failing_func()
        assert result == "default"

    def test_fallback_value_on_exception(self):
        """Test fallback value on generic exception."""

        @handle_errors("operation", fallback_value=[])
        def failing_func():
            raise Exception("Unexpected error")

        result = failing_func()
        assert result == []

    def test_no_fallback_on_modelforge_error(self):
        """Test that ModelForgeError is not caught when fallback is set."""

        @handle_errors("operation", fallback_value="default")
        def failing_func():
            raise ModelForgeError("Should not be caught")

        with pytest.raises(ModelForgeError):
            failing_func()

    def test_reraise_as_parameter(self):
        """Test reraise_as parameter converts exceptions."""

        class CustomError(ModelForgeError):
            pass

        @handle_errors("operation", reraise_as=CustomError)
        def timeout_func():
            raise requests.exceptions.Timeout()

        with pytest.raises(CustomError) as exc_info:
            timeout_func()

        # Verify the error contains the right information
        assert exc_info.value.message == "Network timeout during operation"
        assert exc_info.value.error_code == "NETWORK_TIMEOUT"

    def test_function_metadata_preserved(self):
        """Test that function metadata is preserved."""

        @handle_errors("operation")
        def documented_func():
            """This is a documented function."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."

    @patch("modelforge.error_handler.logger")
    def test_logging_on_error(self, mock_logger):
        """Test that errors are logged."""

        @handle_errors("test operation")
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(InternalError):
            error_func()

        mock_logger.exception.assert_called_with(
            "Unexpected ValueError in test operation"
        )

    @patch("modelforge.error_handler.logger")
    def test_logging_with_fallback(self, mock_logger):
        """Test logging when using fallback value."""

        @handle_errors("test operation", fallback_value="fallback")
        def error_func():
            raise ValueError("Test error")

        result = error_func()
        assert result == "fallback"
        mock_logger.warning.assert_called_with(
            "Using fallback value for test operation"
        )
