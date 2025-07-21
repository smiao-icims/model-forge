# Type Safety Refactor - Design

## Architecture Overview

### Type Definition Strategy
- Use `TypedDict` for JSON-like configuration structures
- Use `@dataclass` for runtime objects with validation
- Use `Protocol` for interface definitions
- Use `Literal` for string constants and enums
- Use `NotRequired` for optional fields in TypedDict

### Type Definition Files
```
src/modelforge/types/
├── __init__.py          # Type exports
├── config.py           # Configuration types
├── models.py           # Model and provider types
├── credentials.py      # Authentication types
├── api.py             # API response types
└── exceptions.py      # Exception types
```

## Core Type Definitions

### Configuration Types (`types/config.py`)
```python
from typing import TypedDict, NotRequired, Literal
from typing_extensions import TypeAlias

# Provider type literals
ProviderType: TypeAlias = Literal[
    "ollama",
    "google_genai",
    "openai_compatible",
    "github_copilot"
]

class ModelConfig(TypedDict):
    """Configuration for a specific model."""
    api_model_name: str
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]
    top_p: NotRequired[float]
    top_k: NotRequired[int]
    frequency_penalty: NotRequired[float]
    presence_penalty: NotRequired[float]
    stop_sequences: NotRequired[list[str]]

class ProviderConfig(TypedDict):
    """Configuration for a provider."""
    llm_type: ProviderType
    base_url: NotRequired[str]
    models: dict[str, ModelConfig]
    auth_config: NotRequired[dict[str, str]]

class GlobalConfig(TypedDict):
    """Root configuration structure."""
    providers: dict[str, ProviderConfig]
    current_model: NotRequired[dict[str, str]]
    version: NotRequired[str]
```

### Model Types (`types/models.py`)
```python
from typing import TypedDict, NotRequired, Literal
from datetime import datetime

ModelCapability: TypeAlias = Literal[
    "chat",
    "completion",
    "vision",
    "audio",
    "code",
    "reasoning"
]

class ModelsDevProvider(TypedDict):
    """Provider information from models.dev API."""
    name: str
    display_name: str
    description: str
    auth_types: list[str]
    base_urls: list[str]
    documentation_url: NotRequired[str]
    supported_regions: NotRequired[list[str]]

class ModelsDevModel(TypedDict):
    """Model information from models.dev API."""
    id: str
    provider: str
    display_name: str
    description: str
    capabilities: list[ModelCapability]
    context_length: NotRequired[int]
    max_tokens: NotRequired[int]
    pricing: NotRequired[dict[str, float]]
    rate_limits: NotRequired[dict[str, int]]
    regions: NotRequired[list[str]]
    last_updated: NotRequired[str]

class CachedData(TypedDict):
    """Structure for cached API data."""
    data: list[dict[str, Any]]
    timestamp: float
    expiry: float
```

### Credential Types (`types/credentials.py`)
```python
from typing import TypedDict, Literal, Union
from datetime import datetime

AuthType: TypeAlias = Literal["api_key", "device_flow", "oauth", "none"]

class ApiKeyCredentials(TypedDict):
    """API key based credentials."""
    type: Literal["api_key"]
    api_key: str

class DeviceFlowCredentials(TypedDict):
    """Device flow OAuth credentials."""
    type: Literal["device_flow"]
    access_token: str
    refresh_token: NotRequired[str]
    expires_at: int
    token_type: str
    scope: NotRequired[str]

class OAuthCredentials(TypedDict):
    """Standard OAuth credentials."""
    type: Literal["oauth"]
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str
    scope: str

class NoCredentials(TypedDict):
    """No authentication required."""
    type: Literal["none"]

Credentials = Union[ApiKeyCredentials, DeviceFlowCredentials, OAuthCredentials, NoCredentials]
```

### API Response Types (`types/api.py`)
```python
from typing import TypedDict, NotRequired
from .models import ModelsDevProvider, ModelsDevModel

class ApiResponse(TypedDict):
    """Base API response structure."""
    success: bool
    message: str
    data: dict[str, Any] | None
    error: NotRequired[str]

class ProvidersResponse(ApiResponse):
    """Response from /providers endpoint."""
    data: dict[str, ModelsDevProvider] | None

class ModelsResponse(ApiResponse):
    """Response from /models endpoint."""
    data: dict[str, ModelsDevModel] | None

class ModelInfoResponse(ApiResponse):
    """Response from /models/{id} endpoint."""
    data: ModelsDevModel | None
```

### Exception Types (`types/exceptions.py`)
```python
from typing import TypedDict

class ErrorDetails(TypedDict):
    """Structured error information."""
    code: str
    message: str
    details: dict[str, Any]
    provider: str | None
    model: str | None
```

## Runtime Validation

### Configuration Validator
```python
from typing import Any
from jsonschema import validate, ValidationError

class ConfigValidator:
    """Runtime validation for configuration objects."""

    _config_schema = {
        "type": "object",
        "properties": {
            "providers": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "llm_type": {
                            "type": "string",
                            "enum": ["ollama", "google_genai", "openai_compatible", "github_copilot"]
                        },
                        "base_url": {"type": "string"},
                        "models": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "api_model_name": {"type": "string"},
                                    "max_tokens": {"type": "integer", "minimum": 1},
                                    "temperature": {"type": "number", "minimum": 0, "maximum": 2},
                                    "top_p": {"type": "number", "minimum": 0, "maximum": 1}
                                },
                                "required": ["api_model_name"]
                            }
                        }
                    },
                    "required": ["llm_type", "models"]
                }
            },
            "current_model": {
                "type": "object",
                "properties": {
                    "provider": {"type": "string"},
                    "model": {"type": "string"}
                },
                "required": ["provider", "model"]
            }
        },
        "required": ["providers"]
    }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> GlobalConfig:
        """Validate and return typed configuration."""
        try:
            validate(instance=config, schema=cls._config_schema)
            return config  # type: ignore
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration: {e.message}")
```

### API Response Validator
```python
import requests
from typing import Any

class ApiResponseValidator:
    """Runtime validation for API responses."""

    @staticmethod
    def validate_providers_response(data: dict[str, Any]) -> ProvidersResponse:
        """Validate providers response."""
        if not isinstance(data, dict):
            raise ValidationError("Invalid response format")

        if "success" not in data or not data["success"]:
            raise ValidationError(f"API error: {data.get('message', 'Unknown error')}")

        return data  # type: ignore

    @staticmethod
    def validate_models_response(data: dict[str, Any]) -> ModelsResponse:
        """Validate models response."""
        if not isinstance(data, dict):
            raise ValidationError("Invalid response format")

        if "success" not in data or not data["success"]:
            raise ValidationError(f"API error: {data.get('message', 'Unknown error')}")

        return data  # type: ignore
```

## Integration with Existing Code

### Updated Registry with Type Safety
```python
from typing import cast
from modelforge.types.config import GlobalConfig, ProviderConfig, ModelConfig

class ModelForgeRegistry:
    """Type-safe registry implementation."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._config = self._load_typed_config()

    def _load_typed_config(self) -> GlobalConfig:
        """Load and validate configuration."""
        config_data, _ = config.get_config()
        return ConfigValidator.validate_config(config_data)

    def _get_model_config(
        self, provider_name: str | None, model_alias: str | None
    ) -> tuple[str, str, ProviderConfig, ModelConfig]:
        """Type-safe model configuration retrieval."""
        resolved_provider, resolved_model = self._resolve_model_selection(
            provider_name, model_alias
        )

        provider_config = cast(ProviderConfig, self._config["providers"][resolved_provider])
        model_config = cast(ModelConfig, provider_config["models"][resolved_model])

        return resolved_provider, resolved_model, provider_config, model_config
```

### Updated ModelsDev Client
```python
from typing import cast
from modelforge.types.models import ModelsDevProvider, ModelsDevModel

class ModelsDevClient:
    """Type-safe models.dev client."""

    def get_providers(self, force_refresh: bool = False) -> list[ModelsDevProvider]:
        """Get providers with type safety."""
        cache_key = "providers"

        if not force_refresh and self._is_cache_valid(cache_key, self.provider_cache_ttl):
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cast(list[ModelsDevProvider], cached_data["data"])

        try:
            response = self.session.get(f"{self.base_url}/providers")
            response.raise_for_status()

            data = response.json()
            validated_response = ApiResponseValidator.validate_providers_response(data)
            providers = list(validated_response["data"].values()) if validated_response["data"] else []

            self._save_to_cache(cache_key, providers)
            return providers

        except requests.exceptions.RequestException as e:
            return self._handle_api_error(cache_key, e)
```

## Mypy Configuration

### Strict Mode Configuration
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
show_error_codes = true

[[tool.mypy.overrides]]
module = [
    "jsonschema.*",
    "keyring.*",
    "cryptography.*"
]
ignore_missing_imports = true
```

## Testing Strategy

### Type-Safe Test Fixtures
```python
import pytest
from typing import Dict, Any
from modelforge.types.config import GlobalConfig, ProviderConfig

@pytest.fixture
def sample_config() -> GlobalConfig:
    """Provide type-safe test configuration."""
    return {
        "providers": {
            "openai": {
                "llm_type": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "models": {
                    "gpt-4o-mini": {
                        "api_model_name": "gpt-4o-mini",
                        "max_tokens": 16384,
                        "temperature": 0.7
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
def mock_providers_response() -> dict[str, Any]:
    """Provide type-safe mock API response."""
    return {
        "success": True,
        "message": "Providers retrieved successfully",
        "data": {
            "openai": {
                "name": "openai",
                "display_name": "OpenAI",
                "description": "OpenAI GPT models",
                "auth_types": ["api_key"],
                "base_urls": ["https://api.openai.com/v1"]
            }
        }
    }
```

## Migration Plan

### Phase 1: Type Definitions
1. Create `modelforge/types/` directory structure
2. Define all TypedDict structures
3. Update imports throughout codebase

### Phase 2: Runtime Validation
1. Add jsonschema for runtime validation
2. Create validator classes
3. Update error handling

### Phase 3: Strict Mypy
1. Enable strict mypy mode
2. Fix all type errors
3. Add type checking to CI

### Phase 4: Testing
1. Update test fixtures with proper types
2. Add type validation tests
3. Update documentation with type examples
