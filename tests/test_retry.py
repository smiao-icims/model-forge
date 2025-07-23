"""Tests for retry mechanism."""

from unittest.mock import patch

import pytest

from modelforge.exceptions import NetworkTimeoutError, RateLimitError
from modelforge.retry import retry_on_error, retry_with_backoff


class TestRetryOnError:
    """Test retry_on_error decorator."""

    def test_successful_on_first_attempt(self):
        """Test that successful calls don't retry."""
        call_count = 0

        @retry_on_error(max_retries=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_network_timeout(self):
        """Test retry on NetworkTimeoutError."""
        call_count = 0

        @retry_on_error(max_retries=2, backoff_factor=0.1)  # Small backoff for testing
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkTimeoutError("API call")
            return "success"

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test that exception is raised when retries are exhausted."""
        call_count = 0

        @retry_on_error(max_retries=2)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise NetworkTimeoutError("API call")

        with patch("time.sleep"):
            with pytest.raises(NetworkTimeoutError):
                always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_no_retry_on_unexpected_exception(self):
        """Test that unexpected exceptions are not retried."""
        call_count = 0

        @retry_on_error(max_retries=3)
        def unexpected_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Unexpected error")

        with pytest.raises(ValueError):
            unexpected_error()

        assert call_count == 1  # No retries

    def test_rate_limit_retry_after(self):
        """Test that rate limit retry_after is honored."""
        sleep_times = []

        @retry_on_error(max_retries=1)
        def rate_limited():
            if not sleep_times:
                raise RateLimitError("API", retry_after=5)
            return "success"

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda x: sleep_times.append(x)
            result = rate_limited()

        assert result == "success"
        assert sleep_times == [5.0]  # Should use retry_after value

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        sleep_times = []
        call_count = 0

        @retry_on_error(max_retries=3, backoff_factor=2.0)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise NetworkTimeoutError("API call")
            return "success"

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda x: sleep_times.append(x)
            result = failing_func()

        assert result == "success"
        assert sleep_times == [1.0, 2.0, 4.0]  # 2^0, 2^1, 2^2

    def test_max_wait_limit(self):
        """Test that wait time is capped by max_wait."""
        sleep_times = []

        @retry_on_error(max_retries=5, backoff_factor=10.0, max_wait=5.0)
        def failing_func():
            if len(sleep_times) < 5:
                raise NetworkTimeoutError("API call")
            return "success"

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda x: sleep_times.append(x)
            result = failing_func()

        assert result == "success"
        assert all(t <= 5.0 for t in sleep_times)

    def test_custom_error_types(self):
        """Test retry with custom error types."""

        class CustomError(Exception):
            pass

        call_count = 0

        @retry_on_error(max_retries=2, errors=(CustomError,), backoff_factor=0.1)
        def custom_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CustomError("Custom error")
            return "success"

        with patch("time.sleep"):
            result = custom_error_func()

        assert result == "success"
        assert call_count == 3

    def test_zero_retries(self):
        """Test with max_retries=0 (no retries)."""

        @retry_on_error(max_retries=0)
        def failing_func():
            raise NetworkTimeoutError("API call")

        with pytest.raises(NetworkTimeoutError):
            failing_func()

    def test_invalid_parameters(self):
        """Test validation of decorator parameters."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):

            @retry_on_error(max_retries=-1)
            def func():
                pass

        with pytest.raises(ValueError, match="backoff_factor must be positive"):

            @retry_on_error(backoff_factor=0)
            def func():
                pass

        with pytest.raises(ValueError, match="max_wait must be positive"):

            @retry_on_error(max_wait=0)
            def func():
                pass

    @patch("modelforge.retry.logger")
    def test_logging(self, mock_logger):
        """Test that retries are logged."""
        call_count = 0

        @retry_on_error(max_retries=1, backoff_factor=0.1)
        def failing_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkTimeoutError("API call")
            return "success"

        with patch("time.sleep"):
            result = failing_once()

        assert result == "success"
        assert mock_logger.warning.called
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "Attempt 1/2 failed" in warning_msg
        assert "Retrying in" in warning_msg

    @patch("modelforge.retry.logger")
    def test_final_failure_logged(self, mock_logger):
        """Test that final failure is logged."""

        @retry_on_error(max_retries=1)
        def always_fails():
            raise NetworkTimeoutError("API call")

        with patch("time.sleep"):
            with pytest.raises(NetworkTimeoutError):
                always_fails()

        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert "All 2 attempts failed" in error_msg

    def test_function_metadata_preserved(self):
        """Test that function metadata is preserved."""

        @retry_on_error()
        def documented_func():
            """This is a documented function."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."


class TestRetryWithBackoff:
    """Test retry_with_backoff function."""

    def test_basic_usage(self):
        """Test basic usage of retry_with_backoff."""
        call_count = 0

        def flaky_func(value):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkTimeoutError("API call")
            return f"success: {value}"

        with patch("time.sleep"):
            result = retry_with_backoff(
                flaky_func, "test", max_retries=2, backoff_factor=0.1
            )

        assert result == "success: test"
        assert call_count == 3

    def test_with_kwargs(self):
        """Test retry_with_backoff with keyword arguments."""

        def func_with_kwargs(a, b=None):
            if b != "expected":
                raise NetworkTimeoutError("API call")
            return f"{a}-{b}"

        with patch("time.sleep"):
            result = retry_with_backoff(
                func_with_kwargs, "test", b="expected", max_retries=1
            )

        assert result == "test-expected"

    def test_custom_parameters(self):
        """Test retry_with_backoff with custom parameters."""
        sleep_times = []

        def failing_func():
            if len(sleep_times) < 2:
                raise RateLimitError("API", retry_after=10)
            return "success"

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda x: sleep_times.append(x)
            result = retry_with_backoff(
                failing_func,
                max_retries=2,
                errors=(RateLimitError,),
            )

        assert result == "success"
        assert sleep_times == [10.0, 10.0]  # Uses retry_after
