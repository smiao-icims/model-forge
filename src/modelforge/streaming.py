"""Streaming support for ModelForge with authentication handling."""

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLLM

from .auth import DeviceFlowAuth, get_auth_strategy, get_credentials
from .exceptions import AuthenticationError, NetworkError
from .logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)


class StreamingAuthHandler(BaseCallbackHandler):
    """Callback handler that monitors streaming for auth issues."""

    def __init__(
        self,
        provider_name: str,
        auth_strategy: Any,
        token_refresh_threshold: int = 300,  # 5 minutes
    ) -> None:
        """Initialize the streaming auth handler.

        Args:
            provider_name: Name of the provider
            auth_strategy: Authentication strategy instance
            token_refresh_threshold: Seconds before expiry to trigger refresh
        """
        self.provider_name = provider_name
        self.auth_strategy = auth_strategy
        self.token_refresh_threshold = token_refresh_threshold
        self.last_check = datetime.now(UTC)
        self.check_interval = 60  # Check every minute during streaming

    def check_token_validity(self) -> None:
        """Check if token needs refresh during streaming."""
        # Only check if we're using OAuth (DeviceFlowAuth)
        if not isinstance(self.auth_strategy, DeviceFlowAuth):
            return

        # Rate limit checks to avoid overhead
        now = datetime.now(UTC)
        if (now - self.last_check).total_seconds() < self.check_interval:
            return

        self.last_check = now

        # Get current token info
        if hasattr(self.auth_strategy, "get_token_info"):
            token_info = self.auth_strategy.get_token_info()
        else:
            return

        if not token_info:
            return

        # Check if token is close to expiry
        expires_at_str = token_info.get("expires_at")
        if not expires_at_str:
            return

        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            time_until_expiry = (expires_at - now).total_seconds()

            if time_until_expiry <= self.token_refresh_threshold:
                logger.info(
                    "Token for %s expires in %d seconds, refreshing during stream",
                    self.provider_name,
                    time_until_expiry,
                )
                # Attempt refresh in background
                asyncio.create_task(self._background_refresh())
        except Exception as e:
            logger.warning("Error checking token validity: %s", e)

    async def _background_refresh(self) -> None:
        """Refresh token in background without interrupting stream."""
        try:
            refreshed = self.auth_strategy._refresh_token()
            if refreshed:
                logger.info(
                    "Successfully refreshed token for %s during streaming",
                    self.provider_name,
                )
            else:
                logger.warning(
                    "Failed to refresh token for %s during streaming",
                    self.provider_name,
                )
        except Exception:
            logger.exception("Error refreshing token during streaming")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when a new token is generated during streaming."""
        # Check auth validity periodically
        self.check_token_validity()


class StreamWrapper:
    """Wrapper for streaming LLM responses with auth support."""

    def __init__(
        self,
        llm: BaseLLM,
        provider_name: str | None = None,
        provider_data: dict[str, Any] | None = None,
        callbacks: list[BaseCallbackHandler] | None = None,
    ) -> None:
        """Initialize the stream wrapper.

        Args:
            llm: The LangChain LLM instance
            provider_name: Name of the provider (for auth handling)
            provider_data: Provider configuration data
            callbacks: Additional callbacks to use
        """
        self.llm = llm
        self.provider_name = provider_name
        self.provider_data = provider_data
        self.callbacks = callbacks or []

        # Add auth handler if we have provider info
        if provider_name and provider_data:
            try:
                auth_strategy = get_auth_strategy(provider_name, provider_data)
                auth_handler = StreamingAuthHandler(provider_name, auth_strategy)
                self.callbacks.append(auth_handler)
            except Exception as e:
                logger.warning("Could not add auth handler for streaming: %s", e)

    async def stream(
        self,
        prompt: str,
        *,
        timeout: float = 300.0,
        on_progress: Callable[[int], None] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        buffer_size: int = 10,
        retry_on_auth_error: bool = True,
    ) -> AsyncIterator[str]:
        """Stream LLM response with auth handling.

        Args:
            prompt: The prompt to send
            timeout: Timeout in seconds
            on_progress: Callback for progress updates (token count)
            on_chunk: Callback for each chunk
            buffer_size: Number of chunks to buffer before yielding
            retry_on_auth_error: Whether to retry on auth errors

        Yields:
            Buffered response chunks

        Raises:
            AuthenticationError: If authentication fails
            NetworkError: If network or timeout issues occur
        """
        buffer: list[str] = []
        total_tokens = 0
        retry_count = 0
        max_retries = 1 if retry_on_auth_error else 0

        while retry_count <= max_retries:
            try:
                # Create timeout task
                timeout_task = asyncio.create_task(asyncio.sleep(timeout))

                # Start streaming
                stream_iter = self.llm.astream(prompt, callbacks=self.callbacks)

                async for chunk in stream_iter:
                    # Check if we've timed out
                    if timeout_task.done():
                        raise TimeoutError

                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                    buffer.append(content)

                    # Rough token estimation (4 chars per token)
                    total_tokens += len(content) // 4

                    if on_chunk:
                        on_chunk(content)

                    if on_progress and total_tokens % 10 == 0:
                        on_progress(total_tokens)

                    if len(buffer) >= buffer_size:
                        yield "".join(buffer)
                        buffer = []

                # Cancel timeout if streaming completed
                timeout_task.cancel()

                # Yield remaining buffer
                if buffer:
                    yield "".join(buffer)

                # Success, exit retry loop
                break

            except TimeoutError as timeout_err:
                raise NetworkError(
                    f"Stream timeout after {timeout}s",
                    context="Response took too long",
                    suggestion=(
                        f"Increase timeout beyond {timeout}s or use a simpler prompt"
                    ),
                    error_code="STREAM_TIMEOUT",
                ) from timeout_err

            except Exception as e:
                # Check if it's an auth error
                error_str = str(e).lower()
                if any(
                    term in error_str
                    for term in ["401", "unauthorized", "authentication", "token"]
                ):
                    retry_count += 1
                    if (
                        retry_count <= max_retries
                        and self.provider_name
                        and self.provider_data
                    ):
                        logger.warning(
                            "Authentication error during streaming, "
                            "attempting to re-authenticate"
                        )
                        try:
                            # Try to get fresh credentials
                            creds = get_credentials(
                                self.provider_name,
                                "",  # model_alias not needed for auth
                                self.provider_data,
                            )
                            if creds:
                                logger.info(
                                    "Re-authentication successful, retrying stream"
                                )
                                continue
                        except Exception:
                            logger.exception("Re-authentication failed")

                    raise AuthenticationError(
                        "Authentication failed during streaming",
                        context=str(e),
                        suggestion="Check your credentials or re-authenticate",
                        error_code="STREAM_AUTH_ERROR",
                    ) from e
                else:
                    # Not an auth error, re-raise
                    raise


async def stream(
    llm: BaseLLM,
    prompt: str,
    provider_name: str | None = None,
    provider_data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> AsyncIterator[str]:
    """Convenience function for streaming with auth support.

    Args:
        llm: The LangChain LLM instance
        prompt: The prompt to send
        provider_name: Name of the provider (for auth handling)
        provider_data: Provider configuration data
        **kwargs: Additional arguments passed to StreamWrapper.stream()

    Yields:
        Response chunks
    """
    wrapper = StreamWrapper(llm, provider_name, provider_data)
    async for chunk in wrapper.stream(prompt, **kwargs):
        yield chunk


async def stream_to_file(
    llm: BaseLLM,
    prompt: str,
    filepath: "Path",
    provider_name: str | None = None,
    provider_data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> None:
    """Stream response directly to file with auth support.

    Args:
        llm: The LangChain LLM instance
        prompt: The prompt to send
        filepath: Path to write the response to
        provider_name: Name of the provider (for auth handling)
        provider_data: Provider configuration data
        **kwargs: Additional arguments passed to stream()
    """
    try:
        import aiofiles  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "aiofiles is required for async file operations. "
            "Install with: pip install aiofiles"
        ) from e

    async with aiofiles.open(filepath, "w") as f:
        async for chunk in stream(llm, prompt, provider_name, provider_data, **kwargs):
            await f.write(chunk)
