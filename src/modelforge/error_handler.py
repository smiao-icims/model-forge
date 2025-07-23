"""Error handling decorator for consistent error handling across operations."""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from typing import Any, TypeVar, cast

import requests

from modelforge.exceptions import (
    InternalError,
    JsonDecodeError,
    ModelForgeError,
    NetworkError,
    NetworkTimeoutError,
    RateLimitError,
)
from modelforge.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# HTTP status code constants
HTTP_TOO_MANY_REQUESTS = 429


def _handle_timeout_error(
    e: requests.exceptions.Timeout, operation_name: str
) -> NetworkTimeoutError:
    """Convert timeout exception to NetworkTimeoutError."""
    return NetworkTimeoutError(
        operation_name,
        timeout=getattr(e, "timeout", None),
        url=getattr(e.request, "url", None) if hasattr(e, "request") else None,
    )


def _handle_http_error(
    e: requests.exceptions.HTTPError, operation_name: str
) -> ModelForgeError:
    """Convert HTTP exception to appropriate ModelForgeError."""
    if e.response is not None and e.response.status_code == HTTP_TOO_MANY_REQUESTS:
        retry_after = e.response.headers.get("Retry-After")
        retry_after_int = (
            int(retry_after) if retry_after and retry_after.isdigit() else None
        )
        return RateLimitError(operation_name, retry_after=retry_after_int)

    return NetworkError(
        f"HTTP error during {operation_name}",
        context=str(e),
        suggestion="Check the API endpoint and your credentials",
        error_code="HTTP_ERROR",
    )


def _reraise_with_context(
    error: ModelForgeError,
    reraise_as: type[ModelForgeError],
    original_exception: Exception,
) -> None:
    """Re-raise error with proper context."""
    raise reraise_as(
        error.message,
        context=error.context,
        suggestion=error.suggestion,
        error_code=error.error_code,
        details=error.details,
    ) from original_exception


def _handle_network_error(
    e: requests.exceptions.RequestException, operation_name: str
) -> NetworkError:
    """Convert network exceptions to NetworkError."""
    if isinstance(e, requests.exceptions.ConnectionError):
        return NetworkError(
            f"Connection error during {operation_name}",
            context=str(e),
            suggestion="Check your internet connection",
            error_code="CONNECTION_ERROR",
        )
    return NetworkError(
        f"Network error during {operation_name}",
        context=str(e),
        suggestion="Check your internet connection",
        error_code="NETWORK_ERROR",
    )


def _handle_internal_error(
    e: Exception, operation_name: str, fallback_value: object
) -> object:
    """Handle internal errors with optional fallback."""
    if isinstance(e, KeyError | ValueError | TypeError):
        logger.exception(f"Unexpected {type(e).__name__} in {operation_name}")
    else:
        logger.exception(f"Unexpected error in {operation_name}")

    if fallback_value is not None:
        logger.warning(f"Using fallback value for {operation_name}")
        return fallback_value

    raise InternalError(
        operation_name,
        reason=f"{type(e).__name__}: {str(e)}",
    ) from e


def handle_errors(
    operation_name: str,
    fallback_value: object = None,
    reraise_as: type[ModelForgeError] | None = None,
) -> Callable[[F], F]:
    """Decorator for consistent error handling across operations.

    Args:
        operation_name: Name of the operation for error messages
        fallback_value: Optional value to return on error instead of raising
        reraise_as: Optional exception class to convert all errors to

    Returns:
        Decorated function with error handling
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            try:
                return func(*args, **kwargs)
            except ModelForgeError:
                # Re-raise our custom exceptions as-is unless reraise_as is specified
                if reraise_as:
                    raise
                raise
            except requests.exceptions.Timeout as e:
                timeout_error = _handle_timeout_error(e, operation_name)
                if reraise_as:
                    _reraise_with_context(timeout_error, reraise_as, e)
                raise timeout_error from e
            except requests.exceptions.HTTPError as e:
                http_error = _handle_http_error(e, operation_name)
                if reraise_as:
                    _reraise_with_context(http_error, reraise_as, e)
                raise http_error from e
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
            ) as e:
                network_error = _handle_network_error(e, operation_name)
                if reraise_as:
                    _reraise_with_context(network_error, reraise_as, e)
                raise network_error from e
            except json.JSONDecodeError as e:
                raise JsonDecodeError(
                    operation_name,
                    line=e.lineno,
                    column=e.colno,
                    reason=e.msg,
                ) from e
            except (KeyError, ValueError, TypeError, Exception) as e:
                return _handle_internal_error(e, operation_name, fallback_value)

        return cast(F, wrapper)

    return decorator
