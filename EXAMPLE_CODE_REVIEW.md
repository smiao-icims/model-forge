# Example: Using the LLM Code Review Prompt

This example shows how to use the `PROMPT_CODE_REVIEW.md` prompt effectively.

## Step 1: Copy the Prompt

Copy the entire content from `PROMPT_CODE_REVIEW.md` and paste it as your initial message to the LLM.

## Step 2: Add Your Code

Then add your code with context. Here's an example:

---

**Your message to LLM:**

```
[PASTE THE ENTIRE PROMPT_CODE_REVIEW.md CONTENT HERE]

---

Please review this code that I'm adding to the ModelForge project:

**File**: `src/modelforge/providers.py` (new file)
**Purpose**: Add support for Anthropic Claude provider

```python
import requests
import json

def add_anthropic_provider(api_key, model_name):
    # Configure Anthropic provider
    if not api_key:
        print("Error: API key required")
        return
    
    config = {
        "llm_type": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "auth_strategy": "api_key"
    }
    
    try:
        # Test the API key
        response = requests.post(
            config["base_url"] + "/messages", 
            headers={"x-api-key": api_key},
            json={"model": model_name, "messages": [{"role": "user", "content": "test"}]}
        )
        if response.status_code == 200:
            print("API key validated successfully")
            return config
        else:
            print("Invalid API key")
            return None
    except:
        print("Connection failed")
        return None
```
```

## Step 3: Expected LLM Response

The LLM should respond with structured feedback like this:

---

## Code Review Feedback

### 🔴 Critical Issues

- **File**: `src/modelforge/providers.py`, Line 3
  **Issue**: Missing type hints on function signature
  **Fix**: `def add_anthropic_provider(api_key: str, model_name: str) -> Optional[Dict[str, Any]]:`

- **File**: `src/modelforge/providers.py`, Lines 6, 15, 18, 23
  **Issue**: Using print statements instead of logging
  **Fix**: Import and use logger: `from .logging_config import get_logger; logger = get_logger(__name__)`

- **File**: `src/modelforge/providers.py`, Line 22
  **Issue**: Bare except clause
  **Fix**: `except requests.RequestException as e:` and proper error handling

- **File**: `src/modelforge/providers.py`, Line 5
  **Issue**: No input validation for sensitive data
  **Fix**: Add validation: `if not api_key or not api_key.strip():`

### 🟡 Important Issues

- **File**: `src/modelforge/providers.py`, Line 1-2
  **Issue**: Missing imports for typing and proper exception handling
  **Fix**: Add `from typing import Optional, Dict, Any` and custom exceptions

- **File**: `src/modelforge/providers.py`, Line 7-11
  **Issue**: Should follow the established configuration pattern used by other providers
  **Fix**: Use the existing config system instead of creating config directly

- **File**: `src/modelforge/providers.py`, Line 14-21
  **Issue**: API validation logic should be in the auth module, not here
  **Fix**: Move validation to appropriate auth strategy class

### 🔵 Suggestions

- Consider using the existing CLI pattern in `cli.py` for adding providers
- The function name suggests it adds to config, but it only creates config - clarify purpose
- Consider extracting API endpoint construction to a constant
- Add comprehensive docstring following project standards

### ✅ Positive Feedback

- Good use of HTTPS endpoint
- Reasonable error checking approach
- Clear configuration structure matches other providers

## Improved Version

Here's how this code should look following ModelForge standards:

```python
from typing import Optional, Dict, Any
import requests

from .exceptions import ProviderError, AuthenticationError
from .logging_config import get_logger

logger = get_logger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"

def validate_anthropic_credentials(api_key: str, model_name: str) -> bool:
    """
    Validate Anthropic API credentials.
    
    Args:
        api_key: The Anthropic API key to validate
        model_name: The model name to test with
        
    Returns:
        True if credentials are valid, False otherwise
        
    Raises:
        AuthenticationError: If validation fails due to invalid credentials
        ProviderError: If validation fails due to service issues
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    
    if not model_name or not model_name.strip():
        raise ValueError("Model name cannot be empty")
    
    try:
        response = requests.post(
            f"{ANTHROPIC_API_BASE}/messages",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={
                "model": model_name,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "test"}]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("Anthropic API key validated successfully")
            return True
        elif response.status_code == 401:
            logger.error("Invalid Anthropic API key")
            raise AuthenticationError("Invalid API key")
        else:
            logger.error("Anthropic API validation failed: %s", response.status_code)
            raise ProviderError(f"API validation failed: {response.status_code}")
            
    except requests.Timeout as e:
        logger.error("Anthropic API timeout: %s", str(e))
        raise ProviderError("API request timeout") from e
    except requests.RequestException as e:
        logger.error("Anthropic API request failed: %s", str(e))
        raise ProviderError("API request failed") from e
```

---

## Key Benefits of This Approach

1. **Consistent Quality**: Every review follows the same standards
2. **Educational**: Developers learn best practices through detailed feedback
3. **Actionable**: Specific fixes with file/line references
4. **Prioritized**: Critical issues flagged for immediate attention
5. **Positive Reinforcement**: Acknowledges good practices

## Tips for Better Reviews

1. **Be Specific**: Always include file names and line numbers
2. **Provide Context**: Explain why something is a problem
3. **Show Examples**: Include corrected code when helpful
4. **Stay Constructive**: Balance criticism with positive feedback
5. **Focus on Learning**: Help developers understand the 'why' behind standards 