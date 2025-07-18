# Baseline Technical Design - ModelForge v0.1.0

## Architecture Overview

ModelForge follows a modular architecture with three core components: Configuration Management, Authentication Strategies, and Model Registry. The design emphasizes separation of concerns, extensibility, and security.

## Component Architecture

### 1. Configuration Management (`config.py`)

#### Design Decisions
- **Two-tier configuration**: Global (`~/.config/model-forge/config.json`) and local (`./.model-forge/config.json`) with local precedence
- **JSON format**: Human-readable and easily version-controlled
- **Lazy loading**: Configuration loaded on-demand to minimize startup overhead

#### Configuration Schema
```json
{
  "providers": {
    "provider_name": {
      "llm_type": "ollama|google_genai|openai_compatible|github_copilot",
      "base_url": "optional_base_url",
      "auth_strategy": "api_key|device_flow|local",
      "auth_details": { /* provider-specific auth config */ },
      "auth_data": { /* securely stored credentials */ },
      "models": {
        "model_alias": {
          "api_model_name": "actual_api_model_name"
        }
      }
    }
  },
  "current_model": {
    "provider": "provider_name",
    "model": "model_alias"
  }
}
```

#### Key Patterns
- **Factory pattern**: `get_config()` determines appropriate config file based on precedence rules
- **Error handling**: Graceful handling of missing/invalid JSON with clear error messages

### 2. Authentication Strategies (`auth.py`)

#### Strategy Pattern Implementation
```
AuthStrategy (ABC)
├── ApiKeyAuth
├── DeviceFlowAuth
├── NoAuth
└── Factory: get_auth_strategy()
```

#### Security Design
- **Credential isolation**: Each provider manages its own credential storage
- **Encrypted storage**: Credentials stored within configuration files (user-controlled)
- **No plaintext logging**: Sensitive data never logged
- **Token refresh**: Automatic refresh for OAuth tokens with expiry handling

#### Device Flow Implementation
- **Polling mechanism**: Exponential backoff with configurable intervals
- **User experience**: Clear instructions for browser-based authentication
- **Error resilience**: Handles network failures and user cancellation

### 3. Model Registry (`registry.py`)

#### Factory Pattern
- **Provider mapping**: `llm_type` determines which LangChain class to instantiate
- **Credential injection**: Authentication handled transparently during instantiation
- **Validation**: Comprehensive validation of configuration before instantiation

#### Provider Integration
```python
# Factory mapping
"ollama": ChatOllama
"google_genai": ChatGoogleGenerativeAI
"openai_compatible": ChatOpenAI
"github_copilot": ChatGitHubCopilot (with OpenAI fallback)
```

#### Error Handling Strategy
- **Hierarchical exceptions**: ConfigurationError, ProviderError, ModelNotFoundError
- **Detailed logging**: Debug-level logging for troubleshooting
- **Graceful degradation**: Clear error messages for configuration issues

### 4. Command Line Interface (`cli.py`)

#### Command Structure
```
modelforge
├── config
│   ├── show          # Display current configuration
│   ├── add          # Add new model configuration
│   ├── use          # Set current model
│   ├── remove       # Remove model configuration
│   └── migrate      # Migrate old configuration
├── test             # Test current model
└── status           # Check authentication status
```

#### User Experience Design
- **Interactive prompts**: Secure API key input without echo
- **Progress indicators**: Clear feedback during authentication flows
- **Validation**: Real-time validation of configuration parameters
- **Help system**: Comprehensive `--help` for all commands

## Data Flow

### Model Instantiation Flow
1. **Registry initialization**: Load configuration from appropriate source
2. **Provider resolution**: Determine provider and model from configuration
3. **Authentication**: Retrieve or obtain credentials using appropriate strategy
4. **Validation**: Ensure configuration and credentials are valid
5. **Instantiation**: Create LangChain-compatible LLM instance
6. **Return**: Provide ready-to-use model to caller

### Authentication Flow
1. **Strategy selection**: Based on provider's `auth_strategy`
2. **Credential check**: Attempt to retrieve stored credentials
3. **Authentication**: If needed, trigger authentication flow
4. **Storage**: Securely store obtained credentials
5. **Refresh**: Handle token expiry and refresh as needed

## Extension Points

### Adding New Providers
1. **Configuration schema**: Add provider defaults in `cli.py`
2. **LLM type**: Add new type to `registry.py` factory mapping
3. **Authentication**: Implement new `AuthStrategy` subclass if needed
4. **Testing**: Add comprehensive tests for new provider

### Adding New Authentication Methods
1. **Strategy implementation**: Create new `AuthStrategy` subclass
2. **Integration**: Update `get_auth_strategy()` factory function
3. **Configuration**: Add new strategy to provider configuration
4. **CLI support**: Update CLI commands to handle new strategy

## Security Considerations

### Credential Management
- **Storage location**: User-controlled configuration files
- **Access patterns**: Credentials loaded only when needed
- **Clearing**: Explicit methods to remove stored credentials
- **Validation**: Ensure credentials are valid before use

### Network Security
- **HTTPS enforcement**: All API calls use HTTPS
- **Timeout handling**: Configurable timeouts for all network requests
- **Error handling**: Secure error messages (no credential leakage)

## Performance Characteristics

### Startup Performance
- **Configuration loading**: < 100ms for typical configurations
- **Authentication**: < 2 seconds for cached credentials, < 10 seconds for device flow
- **Model instantiation**: < 5 seconds for most providers

### Memory Usage
- **Lazy loading**: Configuration and credentials loaded on-demand
- **Caching**: Credentials cached in memory after first use
- **Cleanup**: Explicit credential clearing available

## Testing Strategy

### Unit Tests
- **Configuration**: Test all configuration loading and saving scenarios
- **Authentication**: Mock external dependencies for reliable testing
- **Registry**: Test all provider instantiation paths
- **CLI**: Test command-line interface with various inputs

### Integration Tests
- **Provider integration**: Test actual provider APIs (with mock credentials)
- **Configuration migration**: Test migration from old to new format
- **Error scenarios**: Test all error handling paths

### Test Data Management
- **Mock credentials**: Use test credentials that don't expose real secrets
- **Configuration templates**: Reusable configuration for testing
- **Cleanup**: Ensure test data doesn't interfere with production use
