# Config Improvements - Design

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Environment Vars│────▶│  Config Resolver │────▶│ Active Config   │
│ MODELFORGE_*    │     │  (Precedence)    │     │ (Merged)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                        │
         │              ┌─────────┴──────────┐
         └──────────────│   Profile System   │
                        │  - dev/staging/prod│
                        │  - inheritance     │
                        │  - validation      │
                        └────────────────────┘
```

## Design Decisions

### 1. Configuration Structure

#### Enhanced Config Schema
```json
{
  "version": "2.1",
  "profiles": {
    "base": {
      // Shared settings across all profiles
      "telemetry": {
        "show_metrics": true
      }
    },
    "development": {
      "extends": "base",
      "providers": {
        "ollama": {
          "llm_type": "ollama",
          "base_url": "http://localhost:11434"
        }
      },
      "current_model": {
        "provider": "ollama",
        "model": "llama2:7b"
      }
    },
    "production": {
      "extends": "base",
      "providers": {
        "github_copilot": {
          "llm_type": "github_copilot"
        }
      },
      "current_model": {
        "provider": "github_copilot",
        "model": "gpt-4o"
      },
      "telemetry": {
        "show_metrics": false  // Override base
      },
      "hyperparameters": {
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 500
      }
    }
  },
  "active_profile": "development",
  // Direct settings (backward compatible)
  "providers": {},
  "current_model": {}
}
```

### 2. Profile Resolution

#### Profile Resolver Class
```python
class ProfileResolver:
    def __init__(self, config_data: dict):
        self.config_data = config_data
        self.profiles = config_data.get("profiles", {})

    def resolve_profile(self, profile_name: str) -> dict:
        """Resolve a profile with inheritance."""
        if profile_name not in self.profiles:
            raise ConfigurationError(f"Profile '{profile_name}' not found")

        profile = self.profiles[profile_name]

        # Handle inheritance
        if "extends" in profile:
            base = self.resolve_profile(profile["extends"])
            return deep_merge(base, profile)

        return profile

    def get_active_config(self) -> dict:
        """Get the final resolved configuration."""
        # 1. Start with direct settings (backward compat)
        config = {
            "providers": self.config_data.get("providers", {}),
            "current_model": self.config_data.get("current_model"),
            "settings": self.config_data.get("settings", {})
        }

        # 2. Apply active profile if set
        active_profile = self._get_active_profile()
        if active_profile:
            profile_config = self.resolve_profile(active_profile)
            config = deep_merge(config, profile_config)

        # 3. Apply environment overrides
        config = self._apply_env_overrides(config)

        return config

    def _get_active_profile(self) -> str | None:
        """Determine active profile from env or config."""
        # Environment takes precedence
        if env_profile := os.getenv("MODELFORGE_PROFILE"):
            return env_profile

        # Then config file
        return self.config_data.get("active_profile")
```

### 3. Environment Variable System

#### Environment Mapping
```python
ENV_MAPPING = {
    # Direct mappings
    "MODELFORGE_PROFILE": "active_profile",
    "MODELFORGE_PROVIDER": "current_model.provider",
    "MODELFORGE_MODEL": "current_model.model",

    # Settings
    "MODELFORGE_TELEMETRY_ENABLED": "settings.telemetry.show_metrics",
    "MODELFORGE_CACHE_ENABLED": "settings.cache.enabled",

    # Hyperparameters
    "MODELFORGE_TEMPERATURE": "hyperparameters.temperature",
    "MODELFORGE_TOP_P": "hyperparameters.top_p",
    "MODELFORGE_TOP_K": "hyperparameters.top_k",
    "MODELFORGE_MAX_TOKENS": "hyperparameters.max_tokens",
    "MODELFORGE_PRESENCE_PENALTY": "hyperparameters.presence_penalty",
    "MODELFORGE_FREQUENCY_PENALTY": "hyperparameters.frequency_penalty",

    # Provider-specific API keys
    "MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN": "providers.github_copilot.auth_data.access_token",
    "MODELFORGE_OPENAI_API_KEY": "providers.openai.auth_data.api_key",
    "MODELFORGE_ANTHROPIC_API_KEY": "providers.anthropic.auth_data.api_key",
    "MODELFORGE_GOOGLE_API_KEY": "providers.google.auth_data.api_key",
}

def apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides."""
    for env_var, config_path in ENV_MAPPING.items():
        if value := os.getenv(env_var):
            set_nested_value(config, config_path, value)

    # Handle dynamic provider vars
    for key, value in os.environ.items():
        if key.startswith("MODELFORGE_") and "_API_KEY" in key:
            provider = key.replace("MODELFORGE_", "").replace("_API_KEY", "").lower()
            set_nested_value(config, f"providers.{provider}.auth_data.api_key", value)

    return config
```

### 4. CLI Commands

#### Profile Management Commands
```python
@cli.group()
def profile():
    """Manage configuration profiles."""
    pass

@profile.command()
@click.argument("name")
@click.option("--from-current", is_flag=True, help="Initialize from current config")
@click.option("--extends", help="Base profile to extend")
def create(name: str, from_current: bool, extends: str):
    """Create a new profile."""
    # Implementation

@profile.command()
def list():
    """List all profiles."""
    # Show profiles with active marker

@profile.command()
@click.argument("name")
def use(name: str):
    """Switch to a profile."""
    # Update active_profile

@profile.command()
@click.argument("profile1")
@click.argument("profile2")
def diff(profile1: str, profile2: str):
    """Compare two profiles."""
    # Show differences

@profile.command()
@click.argument("name")
@click.option("--output", "-o", type=click.File("w"), default="-")
def export(name: str, output):
    """Export a profile."""
    # Export as JSON

@profile.command()
@click.argument("name")
@click.option("--input", "-i", type=click.File("r"), default="-")
def import_(name: str, input):
    """Import a profile."""
    # Import from JSON

### 5. Hyperparameter Management

#### CLI Commands for Hyperparameters
```python
@cli.group()
def config():
    """Manage configuration and hyperparameters."""
    pass

@config.command()
@click.argument("key")
@click.argument("value")
@click.option("--model", help="Set for specific model")
@click.option("--provider", help="Set for specific provider")
def set(key: str, value: str, model: str, provider: str):
    """Set hyperparameter value."""
    # Validate hyperparameter name and value
    # Update configuration appropriately

@config.command()
@click.argument("key")
@click.option("--model", help="Get for specific model")
def get(key: str, model: str):
    """Get hyperparameter value."""
    # Show current value

@config.command()
def list_hyperparameters():
    """List all available hyperparameters."""
    # Show all supported hyperparameters with descriptions

# Add hyperparameter options to test command
@cli.command()
@click.option("--temperature", type=float, help="Sampling temperature")
@click.option("--top-p", type=float, help="Nucleus sampling parameter")
@click.option("--top-k", type=int, help="Top-k sampling parameter")
@click.option("--max-tokens", type=int, help="Maximum tokens to generate")
def test(temperature, top_p, top_k, max_tokens, ...):
    """Test with hyperparameter overrides."""
    # Apply hyperparameters to the model call
```

#### Hyperparameter Validation
```python
HYPERPARAMETER_SPECS = {
    "temperature": {
        "type": float,
        "min": 0.0,
        "max": 2.0,
        "description": "Controls randomness in output"
    },
    "top_p": {
        "type": float,
        "min": 0.0,
        "max": 1.0,
        "description": "Nucleus sampling threshold"
    },
    "top_k": {
        "type": int,
        "min": 1,
        "max": 1000,
        "description": "Top-k sampling limit"
    },
    "max_tokens": {
        "type": int,
        "min": 1,
        "max": 100000,
        "description": "Maximum tokens to generate"
    },
    "presence_penalty": {
        "type": float,
        "min": -2.0,
        "max": 2.0,
        "description": "Penalty for repeated content"
    },
    "frequency_penalty": {
        "type": float,
        "min": -2.0,
        "max": 2.0,
        "description": "Penalty for frequent tokens"
    }
}

def validate_hyperparameter(name: str, value: any, provider: str = None) -> any:
    """Validate hyperparameter value and convert type."""
    if name not in HYPERPARAMETER_SPECS:
        raise ValidationError(f"Unknown hyperparameter: {name}")

    spec = HYPERPARAMETER_SPECS[name]

    # Type conversion
    try:
        value = spec["type"](value)
    except ValueError:
        raise ValidationError(f"Invalid type for {name}")

    # Range validation
    if "min" in spec and value < spec["min"]:
        raise ValidationError(f"{name} must be >= {spec['min']}")
    if "max" in spec and value > spec["max"]:
        raise ValidationError(f"{name} must be <= {spec['max']}")

    # Provider-specific validation could be added here

    return value
```

### 6. Configuration Loading

#### Updated get_config Function
```python
def get_config() -> tuple[dict[str, Any], str | None]:
    """Get configuration with profile support."""
    # 1. Load raw config files (existing logic)
    global_config, global_path = _load_global_config()
    local_config, local_path = _load_local_config()

    # 2. Merge configs
    if local_config:
        raw_config = deep_merge(global_config, local_config)
        config_path = local_path
    else:
        raw_config = global_config
        config_path = global_path

    # 3. Resolve profiles and environment
    resolver = ProfileResolver(raw_config)
    final_config = resolver.get_active_config()

    return final_config, config_path
```

## Implementation Considerations

### Backward Compatibility
- Existing configs without profiles continue to work
- Direct provider/model settings are preserved
- Gradual migration path provided

### Security
- API keys only via environment variables
- No secrets in profile exports
- Clear precedence for overrides

### Performance
- Profile resolution cached
- Lazy loading of unused profiles
- Minimal overhead for non-profile users

### Error Handling
- Clear errors for missing profiles
- Validation of profile inheritance cycles
- Helpful migration messages
