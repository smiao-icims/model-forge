# models.dev Integration Design - ModelForge v0.3.0

## Architecture Overview

The models.dev integration will transform ModelForge from a manually configured library to an intelligent, data-driven system that leverages the open-source models.dev inventory for provider and model discovery, validation, and configuration.

## Integration Architecture

### Core Components

#### 1. models.dev Client (`modelsdev_client.py`)
```python
class ModelsDevClient:
    """HTTP client for models.dev API with caching and retry logic."""

    def __init__(self, cache_ttl: int = 86400, timeout: int = 30):
        self.base_url = "https://api.models.dev/v1"
        self.cache = ModelsDevCache()
        self.timeout = timeout
        self.session = self._create_session()
```

#### 2. Cache System (`modelsdev_cache.py`)
```python
class ModelsDevCache:
    """Intelligent caching system for models.dev data."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or get_cache_dir()
        self.compressor = gzip
        self.serializer = json
```

#### 3. Data Models (`modelsdev_models.py`)
```python
@dataclass
class ProviderInfo:
    name: str
    display_name: str
    auth_type: str  # "api_key", "oauth", "none"
    base_url: str
    configuration_template: dict[str, Any]

@dataclass
class ModelInfo:
    provider: str
    name: str
    display_name: str
    description: str
    capabilities: list[str]
    pricing: dict[str, float] | None
    context_window: int | None
    max_tokens: int | None
```

### Data Flow Architecture

#### Discovery Flow
```
User CLI → ModelsDevClient → Cache Check → models.dev API → Cache → Display
```

#### Configuration Flow
```
User Request → ModelsDevClient → Provider Template → Configuration Validation → Save Config
```

## Cache Strategy

### Cache Structure
```
~/.cache/model-forge/modelsdev/
├── providers/
│   ├── providers.json.gz          # All providers
│   └── providers-{hash}.json.gz   # Provider-specific
├── models/
│   ├── models.json.gz            # All models
│   ├── {provider}/models.json.gz # Provider-specific
│   └── {provider}/{model}.json.gz # Model-specific
└── metadata.json                 # Cache metadata
```

### Cache Management
- **TTL Strategy**:
  - Providers: 7 days (stable)
  - Models: 24 hours (frequent updates)
  - Individual models: 24 hours
- **Cleanup**: LRU eviction with 50MB limit
- **Compression**: Gzip with ~80% size reduction
- **Validation**: Checksum verification on load

### Cache API
```python
class ModelsDevCache:
    def get_providers(self) -> list[ProviderInfo] | None
    def get_models(self, provider: str | None = None) -> list[ModelInfo] | None
    def get_model_details(self, provider: str, model: str) -> ModelInfo | None
    def refresh(self, force: bool = False) -> None
    def clear(self) -> None
```

## CLI Enhancement Design

### New Commands

#### `modelforge discover`
```bash
# Interactive model discovery
$ modelforge discover
ℹ️ Fetching models from models.dev...

Available Providers:
1. OpenAI
2. Anthropic
3. Google
4. Ollama

Select provider [1-4]: 1

Available Models:
1. gpt-4o (latest, $0.06/1K tokens)
2. gpt-4o-mini (cost-effective, $0.006/1K tokens)
3. gpt-3.5-turbo (legacy, $0.0015/1K tokens)

Select model: 2

✅ Added 'gpt-4o-mini' from OpenAI to your configuration
```

#### `modelforge search`
```bash
# Search with filters
$ modelforge search --provider openai --capability "vision"
$ modelforge search --max-price 0.01 --min-context 4000
$ modelforge search "code generation"
```

#### `modelforge info`
```bash
# Detailed model information
$ modelforge info openai gpt-4o-mini

Provider: OpenAI
Model: gpt-4o-mini
Description: GPT-4o Mini - cost-effective GPT-4 variant
Pricing: $0.006 input / $0.018 output per 1K tokens
Context Window: 128,000 tokens
Capabilities: text, vision, function_calling
Status: Active
```

## Configuration Integration

### Auto-configuration Templates
```python
class AutoConfigurator:
    def generate_provider_config(self, provider: str) -> dict[str, Any]:
        """Generate provider configuration from models.dev template."""

    def suggest_models(self, use_case: str, constraints: dict) -> list[ModelInfo]:
        """Suggest optimal models based on criteria."""

    def validate_existing_config(self, config: dict) -> list[str]:
        """Validate existing configuration against models.dev."""
```

### Configuration Enhancement
```python
# Enhanced config add with models.dev integration
@config_group.command(name="add-auto")
@click.option("--provider", help="Provider name")
@click.option("--use-case", help="Primary use case")
@click.option("--budget", type=float, help="Maximum cost per 1K tokens")
def add_auto_model(provider: str, use_case: str, budget: float):
    """Add model using models.dev recommendations."""
```

## API Integration Design

### HTTP Client Configuration
```python
class ModelsDevClient:
    RETRY_CONFIG = {
        'total': 3,
        'backoff_factor': 1,
        'status_forcelist': [429, 500, 502, 503, 504]
    }

    TIMEOUT_CONFIG = {
        'connect': 5,
        'read': 30
    }
```

### Rate Limiting
- **Respect API limits**: Automatic backoff on 429 responses
- **Conditional requests**: Use ETags for efficient updates
- **Batch operations**: Minimize API calls through intelligent caching

### Error Handling
```python
class ModelsDevError(Exception):
    """Base exception for models.dev integration."""

class ModelsDevAPIError(ModelsDevError):
    """API communication errors."""

class ModelsDevCacheError(ModelsDevError):
    """Cache-related errors."""
```

## Data Synchronization

### Background Updates
- **Trigger**: Every 24 hours or on user request
- **Strategy**: Incremental updates with ETags
- **Conflict resolution**: Merge changes, highlight conflicts
- **Rollback**: Cache versioning for safe updates

### Real-time Validation
- **Model existence**: Check if model still exists
- **Provider status**: Verify provider is active
- **Pricing updates**: Alert users to pricing changes
- **Deprecation warnings**: Notify about deprecated models

## Offline Mode Design

### Graceful Degradation
```python
class OfflineAdapter:
    def __init__(self, cache: ModelsDevCache):
        self.cache = cache

    def get_available_data(self) -> dict[str, Any]:
        """Return cached data with staleness indicators."""

    def is_data_fresh(self) -> bool:
        """Check if cached data is reasonably fresh."""
```

### User Experience
- **Clear indicators**: Show when using cached vs fresh data
- **Refresh capability**: Manual refresh option always available
- **Staleness warnings**: Alert when data is >7 days old
- **Fallback guidance**: Clear instructions when API unavailable

## Performance Optimization

### Lazy Loading
- **On-demand**: Load provider/model data only when needed
- **Incremental**: Load subsets of data for specific queries
- **Background**: Preload common data during idle time

### Memory Management
- **Streaming**: Stream large datasets instead of loading entirely
- **Compression**: Gzip compression reduces memory usage by ~80%
- **Cleanup**: Automatic cleanup of expired cache entries

## Security Considerations

### API Security
- **HTTPS enforcement**: All API calls use HTTPS
- **Certificate validation**: Proper SSL certificate verification
- **Input sanitization**: Sanitize all user input used in API calls
- **No sensitive data**: Cache contains only public models.dev data

### Cache Security
- **Secure storage**: Cache files with appropriate permissions
- **No secrets**: Ensure no API keys or user data in cache
- **Validation**: Validate all cached data before use

## Extension Points

### Custom Providers
- **Hybrid approach**: Use models.dev + custom provider definitions
- **Override capability**: Allow local overrides of models.dev data
- **Validation**: Ensure custom providers don't conflict with models.dev

### Future Enhancements
- **Real-time updates**: Webhook support for model changes
- **User preferences**: Personalized model recommendations
- **Usage analytics**: Opt-in usage tracking for better recommendations

## Testing Strategy

### Mock Implementation
```python
class MockModelsDevClient(ModelsDevClient):
    """Mock client for testing without network calls."""

    def __init__(self, fixtures_dir: Path):
        self.fixtures = self._load_fixtures(fixtures_dir)
```

### Test Coverage
- **API integration**: Test all API endpoints
- **Cache behavior**: Test cache lifecycle
- **Error handling**: Test all error scenarios
- **Offline mode**: Test graceful degradation
- **CLI commands**: Test new CLI functionality

## Migration Strategy

### Backward Compatibility
- **Existing configs**: Continue to work unchanged
- **Manual overrides**: Allow manual configuration alongside models.dev
- **Gradual adoption**: Users can choose to use models.dev features
- **Clear documentation**: Migration guide for existing users

### Rollback Plan
- **Feature flag**: Enable/disable models.dev integration
- **Manual fallback**: Always allow manual configuration
- **Cache reset**: Clear cache if corruption detected
- **API switch**: Fallback to manual mode on API failures
