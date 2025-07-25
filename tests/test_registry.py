"""Tests for the ModelForgeRegistry."""

import pytest
from pytest_mock import MockerFixture

from modelforge.exceptions import (
    ConfigurationError,
    InvalidApiKeyError,
    ModelNotFoundError,
    ProviderError,
    ProviderNotAvailableError,
)
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
        callbacks=None,
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
    mock_get_credentials.assert_called_once_with(
        "openai",
        "gpt-4o-mini",
        {
            "llm_type": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "models": {
                "gpt-4o-mini": {
                    "api_model_name": "gpt-4o-mini",
                }
            },
        },
        verbose=False,
    )
    mock_chat_openai.assert_called_once_with(
        model="gpt-4o-mini",
        api_key="test-api-key-123",
        base_url="https://api.openai.com/v1",
        callbacks=None,
    )


# --- Test for GitHub Copilot ---
def test_get_llm_github_copilot_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for retrieving a GitHub Copilot model instance.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_credentials = mocker.patch("modelforge.registry.auth.get_credentials")
    mock_chat_github_copilot = mocker.patch("modelforge.registry.ChatGitHubCopilot")
    mocker.patch("modelforge.registry.GITHUB_COPILOT_AVAILABLE", True)

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "github_copilot": {
                "llm_type": "github_copilot",
                "models": {
                    "gpt-4o": {
                        "api_model_name": "gpt-4o",
                    }
                },
            }
        },
        "current_model": {"provider": "github_copilot", "model": "gpt-4o"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Set up the credentials
    mock_get_credentials.return_value = {"access_token": "test-github-token-123"}

    # Create the registry
    registry = ModelForgeRegistry()

    # Act
    llm_instance = registry.get_llm()

    # Assert
    assert llm_instance is not None
    mock_get_credentials.assert_called_once()
    mock_chat_github_copilot.assert_called_once_with(
        api_key="test-github-token-123",
        model="gpt-4o",
        callbacks=None,
    )


def test_get_llm_github_copilot_not_available(mocker: MockerFixture) -> None:
    """
    Tests when GitHub Copilot library is not installed.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mocker.patch("modelforge.registry.GITHUB_COPILOT_AVAILABLE", False)

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "github_copilot": {
                "llm_type": "github_copilot",
                "models": {"gpt-4o": {}},
            }
        },
        "current_model": {"provider": "github_copilot", "model": "gpt-4o"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ProviderNotAvailableError) as exc_info:
        registry.get_llm()

    assert exc_info.value.context == "GitHub Copilot libraries not installed"


def test_get_llm_github_copilot_no_token(mocker: MockerFixture) -> None:
    """
    Tests when GitHub Copilot credentials are missing.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_credentials = mocker.patch("modelforge.registry.auth.get_credentials")
    mocker.patch("modelforge.registry.GITHUB_COPILOT_AVAILABLE", True)

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "github_copilot": {
                "llm_type": "github_copilot",
                "models": {"gpt-4o": {}},
            }
        },
        "current_model": {"provider": "github_copilot", "model": "gpt-4o"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # No credentials returned
    mock_get_credentials.return_value = None

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(InvalidApiKeyError) as exc_info:
        registry.get_llm()

    assert "github_copilot" in str(exc_info.value)


# --- Test for Google Generative AI ---
def test_get_llm_google_genai_success(mocker: MockerFixture) -> None:
    """
    Tests the happy path for retrieving a Google Generative AI model instance.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_credentials = mocker.patch("modelforge.registry.auth.get_credentials")
    mock_chat_google = mocker.patch("modelforge.registry.ChatGoogleGenerativeAI")

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "google": {
                "llm_type": "google_genai",
                "models": {
                    "gemini-pro": {
                        "api_model_name": "gemini-1.5-pro",
                    }
                },
            }
        },
        "current_model": {"provider": "google", "model": "gemini-pro"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Set up the credentials
    mock_get_credentials.return_value = {"api_key": "test-google-api-key-123"}

    # Create the registry
    registry = ModelForgeRegistry()

    # Act
    llm_instance = registry.get_llm()

    # Assert
    assert llm_instance is not None
    mock_get_credentials.assert_called_once()
    mock_chat_google.assert_called_once_with(
        model="gemini-1.5-pro",
        google_api_key="test-google-api-key-123",
        callbacks=None,
    )


def test_get_llm_google_genai_no_credentials(mocker: MockerFixture) -> None:
    """
    Tests when Google Generative AI credentials are missing.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_credentials = mocker.patch("modelforge.registry.auth.get_credentials")

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "google": {
                "llm_type": "google_genai",
                "models": {"gemini-pro": {}},
            }
        },
        "current_model": {"provider": "google", "model": "gemini-pro"},
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # No credentials returned
    mock_get_credentials.return_value = None

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(InvalidApiKeyError) as exc_info:
        registry.get_llm()

    assert "google" in str(exc_info.value)


# --- Test Error Cases ---
def test_get_llm_no_model_selected(mocker: MockerFixture) -> None:
    """
    Tests when no model is selected and no provider/model specified.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_current_model = mocker.patch(
        "modelforge.registry.config.get_current_model"
    )

    # Empty configuration
    mock_config_data = {"providers": {}}
    mock_get_config.return_value = (mock_config_data, "/path/to/config")
    mock_get_current_model.return_value = None

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ConfigurationError) as exc_info:
        registry.get_llm()

    assert "No model selected" in str(exc_info.value)
    assert "modelforge config use" in str(exc_info.value.suggestion)


def test_get_llm_provider_not_found(mocker: MockerFixture) -> None:
    """
    Tests when specified provider is not in configuration.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")

    # Configuration with different providers
    mock_config_data = {
        "providers": {
            "openai": {"llm_type": "openai_compatible", "models": {}},
            "ollama": {"llm_type": "ollama", "models": {}},
        }
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ProviderNotAvailableError) as exc_info:
        registry.get_llm("anthropic", "claude-3")

    assert "anthropic" in str(exc_info.value)
    assert "Available: openai, ollama" in exc_info.value.context


def test_get_llm_model_not_found(mocker: MockerFixture) -> None:
    """
    Tests when specified model is not found for provider.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")

    # Configuration with provider but different models
    mock_config_data = {
        "providers": {
            "openai": {
                "llm_type": "openai_compatible",
                "models": {
                    "gpt-3.5-turbo": {},
                    "gpt-4": {},
                },
            }
        }
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ModelNotFoundError) as exc_info:
        registry.get_llm("openai", "gpt-4o-mini")

    assert "gpt-4o-mini" in str(exc_info.value)
    assert "openai" in str(exc_info.value)


def test_get_llm_missing_llm_type(mocker: MockerFixture) -> None:
    """
    Tests when provider configuration is missing llm_type.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")

    # Configuration missing llm_type
    mock_config_data = {
        "providers": {
            "custom": {
                # Missing llm_type
                "models": {"model1": {}}
            }
        }
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ConfigurationError) as exc_info:
        registry.get_llm("custom", "model1")

    assert "no 'llm_type' configured" in str(exc_info.value)


def test_get_llm_unsupported_llm_type(mocker: MockerFixture) -> None:
    """
    Tests when provider has unsupported llm_type.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")

    # Configuration with unknown llm_type
    mock_config_data = {
        "providers": {"custom": {"llm_type": "unknown_type", "models": {"model1": {}}}}
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ProviderError) as exc_info:
        registry.get_llm("custom", "model1")

    assert "Unsupported llm_type 'unknown_type'" in str(exc_info.value)
    assert (
        "ollama, google_genai, openai_compatible, github_copilot"
        in exc_info.value.suggestion
    )


def test_get_llm_ollama_missing_base_url(mocker: MockerFixture) -> None:
    """
    Tests when Ollama provider is missing base_url and OLLAMA_HOST env var.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mocker.patch("os.getenv", return_value=None)  # No OLLAMA_HOST

    # Configuration without base_url
    mock_config_data = {
        "providers": {
            "ollama": {
                "llm_type": "ollama",
                # Missing base_url
                "models": {"llama2": {}},
            }
        }
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")

    # Create the registry
    registry = ModelForgeRegistry()

    # Act & Assert
    with pytest.raises(ConfigurationError) as exc_info:
        registry.get_llm("ollama", "llama2")

    assert "Ollama base URL not configured" in str(exc_info.value)
    assert "OLLAMA_HOST" in exc_info.value.context


def test_get_llm_with_verbose_logging(mocker: MockerFixture) -> None:
    """
    Tests verbose logging in registry.
    """
    # Mock dependencies
    mock_get_config = mocker.patch("modelforge.registry.config.get_config")
    mock_get_credentials = mocker.patch("modelforge.registry.auth.get_credentials")
    mocker.patch("modelforge.registry.ChatOpenAI")  # Mock but don't assign (not used)
    mock_logger = mocker.patch("modelforge.registry.logger")

    # Set up the configuration
    mock_config_data = {
        "providers": {
            "openai": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "models": {"gpt-4": {}},
            }
        }
    }
    mock_get_config.return_value = (mock_config_data, "/path/to/config")
    mock_get_credentials.return_value = {"api_key": "test-key"}

    # Create the registry with verbose=True
    registry = ModelForgeRegistry(verbose=True)

    # Act
    registry.get_llm("openai", "gpt-4")

    # Assert verbose logging was called
    assert mock_logger.debug.called
    debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
    assert any("Creating ChatOpenAI instance with:" in call for call in debug_calls)
