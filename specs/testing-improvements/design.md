# Testing Improvements - Design

## Architecture Overview

### Test Structure
```
tests/
├── conftest.py              # Global fixtures and configuration
├── fixtures/               # Reusable test data and fixtures
│   ├── __init__.py
│   ├── config_fixtures.py  # Configuration test fixtures
│   ├── api_fixtures.py     # API response fixtures
│   ├── auth_fixtures.py    # Authentication fixtures
│   └── mock_data.py        # Centralized mock data
├── unit/                   # Unit tests
│   ├── test_config.py
│   ├── test_registry.py
│   ├── test_auth.py
│   ├── test_modelsdev.py
│   └── test_cli.py
├── integration/            # Integration tests
│   ├── test_cli_commands.py
│   └── test_end_to_end.py
└── utils/                  # Test utilities
    ├── __init__.py
    ├── factories.py        # Test data factories
    ├── mocks.py           # Mock objects and helpers
    └── assertions.py      # Custom assertions
```

## Core Test Fixtures

### Configuration Fixtures (`conftest.py`)
```python
import pytest
from pathlib import Path
from typing import Dict, Any, Generator
import tempfile
import json

@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Provide temporary configuration directory."""
    config_dir = tmp_path / ".config" / "model-forge"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

@pytest.fixture
def global_config_file(tmp_config_dir: Path) -> Path:
    """Provide temporary global configuration file."""
    return tmp_config_dir / "config.json"

@pytest.fixture
def local_config_file(tmp_path: Path) -> Path:
    """Provide temporary local configuration file."""
    config_dir = tmp_path / ".model-forge"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"

@pytest.fixture
def clean_env(monkeypatch) -> None:
    """Clean environment variables for testing."""
    monkeypatch.delenv("MODEL_FORGE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
```

### Type-Safe Test Fixtures (`fixtures/config_fixtures.py`)
```python
import pytest
from typing import Dict, Any
from pathlib import Path
import json

class ConfigFactory:
    """Factory for creating test configurations."""

    @staticmethod
    def create_minimal_config() -> Dict[str, Any]:
        """Create minimal valid configuration."""
        return {
            "providers": {
                "openai": {
                    "llm_type": "openai_compatible",
                    "base_url": "https://api.openai.com/v1",
                    "models": {
                        "gpt-4o-mini": {
                            "api_model_name": "gpt-4o-mini"
                        }
                    }
                }
            }
        }

    @staticmethod
    def create_full_config() -> Dict[str, Any]:
        """Create comprehensive configuration with all providers."""
        return {
            "providers": {
                "openai": {
                    "llm_type": "openai_compatible",
                    "base_url": "https://api.openai.com/v1",
                    "models": {
                        "gpt-4o-mini": {
                            "api_model_name": "gpt-4o-mini",
                            "max_tokens": 16384,
                            "temperature": 0.7,
                            "top_p": 0.9
                        }
                    }
                },
                "ollama": {
                    "llm_type": "ollama",
                    "base_url": "http://localhost:11434",
                    "models": {
                        "qwen3:1.7b": {
                            "api_model_name": "qwen3:1.7b"
                        }
                    }
                },
                "github_copilot": {
                    "llm_type": "github_copilot",
                    "models": {
                        "claude-3.7-sonnet": {
                            "api_model_name": "claude-3.7-sonnet"
                        }
                    }
                }
            },
            "current_model": {
                "provider": "openai",
                "model": "gpt-4o-mini"
            }
        }

@pytest.fixture
def minimal_config() -> Dict[str, Any]:
    """Provide minimal test configuration."""
    return ConfigFactory.create_minimal_config()

@pytest.fixture
def full_config() -> Dict[str, Any]:
    """Provide comprehensive test configuration."""
    return ConfigFactory.create_full_config()

@pytest.fixture
def write_config_file():
    """Factory fixture for writing configuration files."""
    def _write_config(file_path: Path, config_data: Dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    return _write_config
```

### API Response Fixtures (`fixtures/api_fixtures.py`)
```python
import pytest
from typing import Dict, Any, List
import json

class ApiResponseFactory:
    """Factory for creating mock API responses."""

    @staticmethod
    def create_providers_response() -> Dict[str, Any]:
        """Create mock providers response."""
        return {
            "success": True,
            "message": "Providers retrieved successfully",
            "data": {
                "openai": {
                    "name": "openai",
                    "display_name": "OpenAI",
                    "description": "OpenAI GPT models",
                    "auth_types": ["api_key"],
                    "base_urls": ["https://api.openai.com/v1"],
                    "documentation_url": "https://platform.openai.com/docs"
                },
                "ollama": {
                    "name": "ollama",
                    "display_name": "Ollama",
                    "description": "Local LLM models",
                    "auth_types": ["none"],
                    "base_urls": ["http://localhost:11434"],
                    "documentation_url": "https://ollama.ai"
                }
            }
        }

    @staticmethod
    def create_models_response() -> Dict[str, Any]:
        """Create mock models response."""
        return {
            "success": True,
            "message": "Models retrieved successfully",
            "data": {
                "gpt-4o-mini": {
                    "id": "gpt-4o-mini",
                    "provider": "openai",
                    "display_name": "GPT-4o Mini",
                    "description": "Fast and cost-effective GPT model",
                    "capabilities": ["chat", "completion"],
                    "context_length": 128000,
                    "max_tokens": 16384,
                    "pricing": {
                        "input_per_1k": 0.00015,
                        "output_per_1k": 0.0006
                    }
                },
                "qwen3:1.7b": {
                    "id": "qwen3:1.7b",
                    "provider": "ollama",
                    "display_name": "Qwen3 1.7B",
                    "description": "Small efficient local model",
                    "capabilities": ["chat", "completion"],
                    "context_length": 32768,
                    "max_tokens": 32768,
                    "pricing": None
                }
            }
        }

@pytest.fixture
def mock_providers_response() -> Dict[str, Any]:
    """Provide mock providers response."""
    return ApiResponseFactory.create_providers_response()

@pytest.fixture
def mock_models_response() -> Dict[str, Any]:
    """Provide mock models response."""
    return ApiResponseFactory.create_models_response()

@pytest.fixture
def mock_requests(mocker, mock_providers_response, mock_models_response):
    """Mock requests for API testing."""
    mock_session = mocker.patch('requests.Session')
    mock_instance = mock_session.return_value

    def mock_get(url):
        response = mocker.Mock()
        if '/providers' in url:
            response.json.return_value = mock_providers_response
        elif '/models' in url:
            response.json.return_value = mock_models_response
        else:
            response.json.return_value = {"success": False, "message": "Not found"}
        response.raise_for_status.return_value = None
        return response

    mock_instance.get.side_effect = mock_get
    return mock_instance
```

### Authentication Fixtures (`fixtures/auth_fixtures.py`)
```python
import pytest
from typing import Dict, Any

class AuthFixtureFactory:
    """Factory for creating authentication test fixtures."""

    @staticmethod
    def create_api_key_credentials() -> Dict[str, str]:
        """Create API key credentials."""
        return {"api_key": "test-api-key-12345"}

    @staticmethod
    def create_device_flow_credentials() -> Dict[str, Any]:
        """Create device flow credentials."""
        return {
            "access_token": "test-access-token",
            "expires_at": 1234567890,
            "token_type": "Bearer"
        }

@pytest.fixture
def mock_keyring(mocker):
    """Mock keyring for credential testing."""
    mock_keyring = mocker.patch('keyring.get_password')
    mock_keyring.set_password = mocker.Mock()
    mock_keyring.delete_password = mocker.Mock()
    return mock_keyring

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    def set_env_var(key: str, value: str) -> None:
        monkeypatch.setenv(key, value)
    return set_env_var
```

## Test Utilities (`utils/factories.py`)
```python
import uuid
from typing import Dict, Any
from datetime import datetime

class ModelFactory:
    """Factory for generating test models."""

    @staticmethod
    def create_openai_model(
        model_id: str = "gpt-4o-mini",
        api_model_name: str = "gpt-4o-mini",
        **kwargs
    ) -> Dict[str, Any]:
        """Create OpenAI model configuration."""
        return {
            "id": model_id,
            "provider": "openai",
            "display_name": f"OpenAI {model_id}",
            "description": f"Test {model_id} model",
            "capabilities": ["chat", "completion"],
            "context_length": kwargs.get("context_length", 128000),
            "max_tokens": kwargs.get("max_tokens", 16384),
            "pricing": {
                "input_per_1k": kwargs.get("input_price", 0.00015),
                "output_per_1k": kwargs.get("output_price", 0.0006)
            }
        }

    @staticmethod
    def create_ollama_model(
        model_id: str = "qwen3:1.7b",
        **kwargs
    ) -> Dict[str, Any]:
        """Create Ollama model configuration."""
        return {
            "id": model_id,
            "provider": "ollama",
            "display_name": f"Ollama {model_id}",
            "description": f"Test {model_id} local model",
            "capabilities": ["chat", "completion"],
            "context_length": kwargs.get("context_length", 32768),
            "max_tokens": kwargs.get("max_tokens", 32768),
            "pricing": None
        }

class ProviderFactory:
    """Factory for generating test providers."""

    @staticmethod
    def create_openai_provider(**kwargs) -> Dict[str, Any]:
        """Create OpenAI provider configuration."""
        return {
            "name": "openai",
            "display_name": "OpenAI",
            "description": "OpenAI GPT models",
            "auth_types": ["api_key"],
            "base_urls": ["https://api.openai.com/v1"],
            **kwargs
        }
```

## Mock Objects (`utils/mocks.py`)
```python
import pytest
from typing import Any, Dict, Optional
from unittest.mock import Mock

class MockLangChainModel:
    """Mock LangChain model for testing."""

    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self.responses = responses or {}
        self.invoked = []

    def invoke(self, messages: Any) -> Any:
        """Mock invoke method."""
        self.invoked.append(messages)
        return self.responses.get("invoke", {"content": "Mock response"})

class MockAuthStrategy:
    """Mock authentication strategy."""

    def __init__(self, provider_name: str, credentials: Optional[Dict[str, Any]] = None):
        self.provider_name = provider_name
        self.credentials = credentials or {}
        self.authenticate_calls = []

    def authenticate(self) -> Optional[Dict[str, Any]]:
        """Mock authenticate method."""
        self.authenticate_calls.append(True)
        return self.credentials

@pytest.fixture
def mock_langchain_model():
    """Provide mock LangChain model."""
    return MockLangChainModel()

@pytest.fixture
def mock_registry():
    """Provide mock registry."""
    registry = Mock()
    registry.get_llm.return_value = MockLangChainModel()
    return registry
```

## Test Organization

### Unit Tests (`unit/test_config.py`)
```python
import pytest
from pathlib import Path
from modelforge import config

class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_load_config_from_global_file(
        self,
        global_config_file: Path,
        write_config_file,
        minimal_config
    ):
        """Test loading configuration from global file."""
        write_config_file(global_config_file, minimal_config)

        loaded_config, config_path = config.get_config_from_path(global_config_file)

        assert loaded_config == minimal_config
        assert config_path == global_config_file

    def test_load_config_with_local_override(
        self,
        global_config_file: Path,
        local_config_file: Path,
        write_config_file,
        minimal_config,
        full_config
    ):
        """Test configuration loading with local override."""
        write_config_file(global_config_file, minimal_config)
        write_config_file(local_config_file, full_config)

        config_data, _ = config.get_config(use_local=True)

        # Local config should take precedence
        assert "ollama" in config_data["providers"]
        assert config_data["current_model"]["provider"] == "openai"
```

### Integration Tests (`integration/test_cli_commands.py`)
```python
import pytest
from click.testing import CliRunner
from modelforge.cli import cli

class TestCLICommands:
    """Test CLI commands with proper mocking."""

    def test_config_show_command(
        self,
        runner: CliRunner,
        local_config_file: Path,
        write_config_file,
        full_config
    ):
        """Test config show command."""
        write_config_file(local_config_file, full_config)

        result = runner.invoke(cli, ['config', 'show'])

        assert result.exit_code == 0
        assert "openai" in result.output
        assert "gpt-4o-mini" in result.output
```

## Test Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --cov=src/modelforge
    --cov-report=term-missing
    --cov-report=html
    --cov-branch
    --cov-fail-under=90
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    cli: marks tests as CLI tests
```

### Pre-commit Hook
```yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: pytest tests/unit -v
      language: system
      pass_filenames: false
      always_run: true
```

## Performance Optimization

### Test Execution Strategy
- **Parallel Execution**: Use pytest-xdist for parallel test execution
- **Selective Testing**: Use markers to run specific test categories
- **Caching**: Cache expensive setup operations (mock API responses)
- **Isolation**: Ensure tests don't interfere with each other

### Test Data Management
- **Lazy Loading**: Load test data only when needed
- **Reusable Objects**: Create reusable mock objects
- **Memory Management**: Clean up large test objects
- **Disk Usage**: Use temporary directories for file operations

## CI/CD Integration

### GitHub Actions Workflow
```yaml
- name: Run Tests
  run: |
    pytest tests/ -v --cov=src/modelforge --cov-report=xml

- name: Run Type Tests
  run: |
    pytest tests/unit/test_types.py -v

- name: Run Integration Tests
  run: |
    pytest tests/integration/ -v --tb=short
```

This comprehensive testing framework provides:
- Type-safe test fixtures
- Reusable test data factories
- Proper test isolation
- Clear test organization
- Comprehensive coverage
- CI/CD integration
- Performance optimization
