"""Tests for the ModelForgeRegistry."""

from pytest_mock import MockerFixture

from modelforge.registry import ModelForgeRegistry


# --- Test for Ollama (No Auth) ---
def test_get_llm_ollama_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for retrieving a local Ollama model instance.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_chat_ollama = mocker.patch("modelforge.registry.ChatOllama")

    # Set up the configuration to include an Ollama provider
    mock_config_data = {
        "providers": {
            "local_ollama": {
                "llm_type": "ollama",
                "base_url": "http://localhost:11434",
                "models": {
                    "qwen3:1.7b": {
                        "api_model_name": "qwen3:1.7b",
                    }
                },
            }
        },
        "current_model": {"provider": "local_ollama", "model": "qwen3:1.7b"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act
    llm_instance = registry.get_llm()

    # Assert
    assert llm_instance is not None
    mock_chat_ollama.assert_called_once_with(
        model="qwen3:1.7b",
        base_url="http://localhost:11434",
    )


# --- Test for OpenAI Compatible (API Key Auth) ---
def test_get_llm_openai_compatible_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for retrieving an OpenAI-compatible model instance.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_credentials = mocker.patch("modelforge.registry.auth.get_credentials")
    mock_chat_openai = mocker.patch("modelforge.registry.ChatOpenAI")

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "openai": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "models": {
                    "gpt-4o-mini": {
                        "api_model_name": "gpt-4o-mini",
                    }
                },
            }
        },
        "current_model": {"provider": "openai", "model": "gpt-4o-mini"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Set up the credentials
    mock_get_credentials.return_value = {"api_key": "test-api-key-123"}

    # Create the registry
    registry = ModelForgeRegistry()

    # Act
    llm_instance = registry.get_llm()

    # Assert
    assert llm_instance is not None
    mock_get_credentials.assert_called_once_with("openai", "gpt-4o-mini", verbose=False)
    mock_chat_openai.assert_called_once_with(
        model_name="gpt-4o-mini",
        api_key="test-api-key-123",
        base_url="https://api.openai.com/v1",
    )
