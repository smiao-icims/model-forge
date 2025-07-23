"""Retry mechanism for automatic retry with exponential backoff."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from modelforge.exceptions import NetworkTimeoutError, RateLimitError
from modelforge.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_error(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    errors: tuple[type[Exception], ...] = (NetworkTimeoutError, RateLimitError),
    max_wait: float = 60.0,
) -> Callable[[F], F]:
    """Decorator for automatic retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        errors: Tuple of exception types to retry on
            (default: NetworkTimeoutError, RateLimitError)
        max_wait: Maximum wait time between retries in seconds (default: 60.0)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_error(max_retries=3)
        def api_call():
            return requests.get("https://api.example.com")
    """
    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")
    if backoff_factor <= 0:
        raise ValueError("backoff_factor must be positive")
    if max_wait <= 0:
        raise ValueError("max_wait must be positive")

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except errors as e:
                    last_exception = e

                    if attempt == max_retries:
                        # This was the last attempt
                        break

                    # Calculate backoff time
                    if isinstance(e, RateLimitError) and e.details.get("retry_after"):
                        # Honor rate limit retry-after header
                        wait_time = float(e.details["retry_after"])
                    else:
                        # Exponential backoff
                        wait_time = min(backoff_factor**attempt, max_wait)

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {wait_time:.1f} seconds..."
                    )

                    time.sleep(wait_time)
                except Exception:
                    # Don't retry on unexpected exceptions
                    raise

            # All retries exhausted
            if last_exception:
                logger.error(f"All {max_retries + 1} attempts failed. Giving up.")
                raise last_exception

            # This should never happen, but just in case
            raise RuntimeError("Retry logic completed without result or exception")

        return cast(F, wrapper)

    return decorator


def retry_with_backoff(
    func: Callable[..., object],
    *args: object,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    errors: tuple[type[Exception], ...] = (NetworkTimeoutError, RateLimitError),
    max_wait: float = 60.0,
    **kwargs: object,
) -> object:
    """Function-based retry with exponential backoff.

    This is a functional alternative to the decorator for cases where
    you need to retry a function call dynamically.

    Args:
        func: Function to call with retry
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        errors: Tuple of exception types to retry on
        max_wait: Maximum wait time between retries
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail

    Example:
        result = retry_with_backoff(
            requests.get, "https://api.example.com", max_retries=5
        )
    """
    decorated = retry_on_error(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        errors=errors,
        max_wait=max_wait,
    )(func)
    return decorated(*args, **kwargs)
