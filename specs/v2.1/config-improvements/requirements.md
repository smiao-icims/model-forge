# Config Improvements - Requirements

## Problem Statement

ModelForge's current configuration system has limitations:

1. **Single Environment**: No easy way to switch between dev/staging/prod configurations
2. **Manual Switching**: Users must manually edit configs or use CLI for each change
3. **No Profiles**: Cannot group related settings (e.g., "development" with specific models/providers)
4. **Limited Environment Integration**: Doesn't leverage environment variables effectively

This forces teams to maintain multiple config files or manually switch settings, increasing errors and operational overhead.

## Requirements

### Config Profiles

- **REQ-001**: Support named configuration profiles (dev, staging, prod, custom)
- **REQ-002**: Profile inheritance with override capability
- **REQ-003**: Easy profile switching via CLI and environment variables
- **REQ-004**: Profile validation to ensure completeness
- **REQ-005**: Default profile specification

### Environment-Based Selection

- **REQ-006**: Automatic profile selection based on environment variables
- **REQ-007**: Environment variable override for any config value
- **REQ-008**: Support for secrets via environment variables
- **REQ-009**: Clear precedence rules (env > profile > default)
- **REQ-010**: Environment-specific model selection

### Profile Management

- **REQ-011**: CLI commands to create, list, and delete profiles
- **REQ-012**: Profile export/import functionality
- **REQ-013**: Profile diff command to compare configurations
- **REQ-014**: Team profile sharing capabilities
- **REQ-015**: Profile templates for common scenarios

### Hyperparameter Configuration

- **REQ-016**: Support for model hyperparameters (temperature, top_k, top_p, etc.)
- **REQ-017**: Per-model hyperparameter defaults
- **REQ-018**: Profile-specific hyperparameter overrides
- **REQ-019**: Environment variable support for hyperparameters
- **REQ-020**: Validation of hyperparameter ranges per provider

## User Stories

### Story 1: Development vs Production
```yaml
# config.json
{
  "profiles": {
    "development": {
      "default_provider": "ollama",
      "default_model": "llama2:7b",
      "telemetry": { "show_metrics": true },
      "hyperparameters": {
        "temperature": 0.1,
        "top_p": 0.95
      }
    },
    "production": {
      "default_provider": "github_copilot",
      "default_model": "gpt-4o",
      "telemetry": { "show_metrics": false },
      "retry": { "max_attempts": 5 },
      "hyperparameters": {
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 500
      }
    }
  },
  "active_profile": "development"
}

# Usage
export MODELFORGE_PROFILE=production
modelforge test --prompt "Hello"  # Uses GPT-4
```

### Story 2: Environment Variable Overrides
```bash
# Override specific values
export MODELFORGE_PROVIDER=github_copilot
export MODELFORGE_MODEL=gpt-4o
export MODELFORGE_GITHUB_COPILOT_ACCESS_TOKEN=${SECRET_GITHUB_TOKEN}

# Override hyperparameters
export MODELFORGE_TEMPERATURE=0.7
export MODELFORGE_MAX_TOKENS=1000

# These override any profile settings
modelforge test --prompt "Hello"  # Uses GitHub Copilot with custom hyperparameters
```

### Story 3: Hyperparameter Configuration
```bash
# Set global hyperparameters for all models
modelforge config set temperature 0.7
modelforge config set max_tokens 500

# Model-specific hyperparameters
modelforge config set --model gpt-4o temperature 0.1
modelforge config set --model llama2:7b top_k 40

# Quick override for testing
modelforge test --prompt "Hello" --temperature 0.9 --max-tokens 100
```

### Story 4: Team Profiles
```bash
# Create and share team profile
modelforge profile create team-ml --from-current
modelforge profile export team-ml > team-ml-profile.json

# Team member imports
modelforge profile import team-ml < team-ml-profile.json
modelforge profile use team-ml
```

## Success Criteria

- [ ] Seamless switching between environments
- [ ] Zero code changes needed for different environments
- [ ] Secure handling of secrets via environment
- [ ] Easy team collaboration with shared profiles
- [ ] Backward compatibility with existing configs

## Out of Scope

- Dynamic profile switching at runtime
- Profile versioning/history
- Cloud-based profile storage
- Role-based profile access control
