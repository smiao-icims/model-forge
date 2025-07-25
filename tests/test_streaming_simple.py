"""Simplified tests for streaming authentication support."""

from unittest.mock import Mock, patch

from modelforge.auth import ApiKeyAuth
from modelforge.streaming import StreamingAuthHandler, StreamWrapper


class TestStreamingAuthBasics:
    """Basic tests for streaming auth functionality."""

    def test_handler_initialization(self) -> None:
        """Test basic handler creation."""
        auth_strategy = Mock()
        handler = StreamingAuthHandler("test_provider", auth_strategy)

        assert handler.provider_name == "test_provider"
        assert handler.auth_strategy == auth_strategy
        assert handler.token_refresh_threshold == 300
        assert handler.check_interval == 60

    def test_non_oauth_skip(self) -> None:
        """Test that non-OAuth providers are skipped."""
        # Use actual ApiKeyAuth which is not DeviceFlowAuth
        auth_strategy = ApiKeyAuth("test_provider")
        handler = StreamingAuthHandler("test_provider", auth_strategy)

        # Should return early without error
        handler.check_token_validity()

    def test_wrapper_initialization(self) -> None:
        """Test stream wrapper creation."""
        llm = Mock()

        # Without provider info
        wrapper = StreamWrapper(llm)
        assert wrapper.llm == llm
        assert wrapper.provider_name is None
        assert len(wrapper.callbacks) == 0

        # With provider info
        provider_data = {"auth_strategy": "api_key"}
        wrapper = StreamWrapper(llm, "openai", provider_data)
        assert wrapper.provider_name == "openai"
        # Should have auth handler callback
        assert len(wrapper.callbacks) == 1
        assert isinstance(wrapper.callbacks[0], StreamingAuthHandler)


class TestStreamingIntegration:
    """Integration tests with async streaming."""

    def test_basic_streaming(self) -> None:
        """Test basic streaming without auth issues."""
        # Create a simple mock LLM
        mock_llm = Mock()

        async def mock_astream(prompt, callbacks=None):  # type: ignore[no-untyped-def]
            """Yield some test chunks."""
            for chunk in ["Hello", " ", "world"]:
                yield Mock(content=chunk)

        mock_llm.astream = mock_astream

        # Create wrapper without auth
        wrapper = StreamWrapper(mock_llm)

        # Test that stream method exists and returns an async iterator
        stream_iter = wrapper.stream("test prompt", buffer_size=2)
        assert hasattr(stream_iter, "__aiter__")

    def test_streaming_with_env_auth(self) -> None:
        """Test streaming with environment variable authentication."""
        # Create mock LLM
        mock_llm = Mock()

        async def mock_astream(prompt, callbacks=None):  # type: ignore[no-untyped-def]
            """Yield test chunks."""
            for chunk in ["Response", " ", "text"]:
                yield Mock(content=chunk)

        mock_llm.astream = mock_astream

        # Set environment variable
        with patch.dict("os.environ", {"MODELFORGE_OPENAI_API_KEY": "test-key"}):
            # Create wrapper with provider info
            provider_data = {"auth_strategy": "api_key"}
            wrapper = StreamWrapper(mock_llm, "openai", provider_data)

            # Verify auth handler was added
            assert len(wrapper.callbacks) == 1
            assert isinstance(wrapper.callbacks[0], StreamingAuthHandler)

            # Test that stream method returns async iterator
            stream_iter = wrapper.stream("test", buffer_size=10)
            assert hasattr(stream_iter, "__aiter__")
