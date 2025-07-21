# Bug Fix: 'modelforge models info' JSON Decode Error - Design

## Technical Analysis

### Current Implementation Issues

1. **Incorrect API Endpoint**: The current implementation in `_fetch_model_info()` constructs a URL like `https://models.dev/models/{provider}/{model}` which doesn't exist in the models.dev API.

2. **API Response Handling**: When the endpoint returns HTML (404 page), the code tries to parse it as JSON without checking the content type or status code.

3. **Provider Name Inconsistency**: The provider name used in the URL may not match the API structure (e.g., `github_copilot` vs `github-copilot`).

4. **No Fallback Logic**: There's no fallback to the main API when the specific endpoint fails.

### Current Code Analysis

```python
def _fetch_model_info(self, cache_path: Path, provider: str, model: str, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch model info from models.dev API."""
    # ... cache logic ...

    url = f"https://models.dev/models/{provider}/{model}"  # ❌ This endpoint doesn't exist
    response = requests.get(url, timeout=10)
    api_response = response.json()  # ❌ This fails with HTML responses

    # ... cache saving ...
    return api_response
```

## Solution Design

### 1. Use Main API Endpoint

Instead of trying to access individual model endpoints, we'll use the main `/api.json` endpoint and extract the specific model data:

```python
def _fetch_model_info(self, cache_path: Path, provider: str, model: str, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch model info from models.dev API."""
    # ... cache logic ...

    # Normalize provider name (replace underscores with hyphens)
    normalized_provider = provider.replace("_", "-")

    # Use the main API endpoint
    url = f"{self.BASE_URL}/api.json"

    try:
        response = self.session.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes

        # Check if response is JSON
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise ValueError(f"Expected JSON response, got {content_type}")

        api_response = response.json()

        # Extract the specific model data
        if normalized_provider not in api_response:
            raise ValueError(f"Provider '{provider}' not found in models.dev API")

        provider_data = api_response[normalized_provider]
        if "models" not in provider_data or not isinstance(provider_data["models"], dict):
            raise ValueError(f"Invalid provider data structure for '{provider}'")

        models = provider_data["models"]
        if model not in models:
            raise ValueError(f"Model '{model}' not found for provider '{provider}'")

        model_info = models[model]

        # Add provider and id fields if not present
        model_info["provider"] = normalized_provider
        model_info["id"] = model

        # Cache the response
        self._save_to_cache(cache_path, model_info)

        return model_info

    except requests.RequestException as e:
        # Handle network errors with cache fallback
        cached_data = self._load_from_cache(cache_path)
        if cached_data and isinstance(cached_data, dict):
            logger.info("Using stale cached model info")
            return cached_data
        raise ValueError(f"Failed to fetch model info: {e}")
    except ValueError as e:
        # Handle parsing/validation errors with cache fallback
        cached_data = self._load_from_cache(cache_path)
        if cached_data and isinstance(cached_data, dict):
            logger.info("Using stale cached model info")
            return cached_data
        # Re-raise the original ValueError without wrapping it
        raise
```

### 2. Provider Name Normalization

To handle provider name inconsistencies, we'll normalize the provider name by replacing underscores with hyphens:

```python
def _normalize_provider_name(self, provider: str) -> str:
    """Normalize provider name for API consistency."""
    return provider.replace("_", "-")
```

### 3. Enhanced Error Handling

We'll add comprehensive error handling with specific error messages and helpful suggestions:

```python
def get_model_info(self, provider: str, model: str, force_refresh: bool = False) -> dict[str, Any]:
    """Get detailed information about a specific model."""
    # Validate provider and model
    if not provider:
        raise ValueError("Provider name is required")
    if not model:
        raise ValueError("Model name is required")

    # Normalize provider name for cache path consistency
    normalized_provider = provider.replace("_", "-")
    cache_path = self._get_cache_path("model_info", normalized_provider, model)

    try:
        return self._fetch_model_info(cache_path, provider, model, force_refresh)
    except ValueError as e:
        # Provide helpful suggestions for common errors
        if "Provider" in str(e) and "not found" in str(e):
            try:
                providers = self.get_providers(force_refresh=False)
                provider_names = [p.get("name", "") for p in providers[:5]]
                suggestions = ", ".join(filter(None, provider_names))
                if suggestions:
                    raise ValueError(f"{e}. Available providers include: {suggestions}") from e
            except ValueError:
                raise  # Re-raise ValueError (including our enhanced one)
            except Exception:
                pass  # Only catch non-ValueError exceptions from get_providers()
        elif "Model" in str(e) and "not found" in str(e):
            try:
                models = self.get_models(provider=normalized_provider, force_refresh=False)
                model_ids = [m.get("id", "") for m in models[:5]]
                suggestions = ", ".join(filter(None, model_ids))
                if suggestions:
                    raise ValueError(f"{e}. Available models include: {suggestions}") from e
            except ValueError:
                raise  # Re-raise ValueError (including our enhanced one)
            except Exception:
                pass  # Only catch non-ValueError exceptions from get_models()
        raise
```

## Implementation Strategy

### Phase 1: Core Fix
1. Update `_fetch_model_info()` to use the main API endpoint
2. Add provider name normalization
3. Add proper error handling for API responses
4. Test with valid provider/model combinations

### Phase 2: Error Handling Enhancement
1. Add validation for provider and model names
2. Add helpful suggestions for invalid providers/models
3. Improve error messages for network issues
4. Test with invalid provider/model combinations

### Phase 3: Cache Compatibility
1. Ensure backward compatibility with existing cache
2. Add cache validation
3. Test cache behavior with new implementation

## Error Handling Design

### API Response Errors
```python
try:
    response = self.session.get(url, timeout=10)
    response.raise_for_status()

    # Check content type
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type.lower():
        raise ValueError(f"Expected JSON response, got {content_type}")

    api_response = response.json()
    # Process response...
except requests.RequestException as e:
    logger.error("Failed to fetch model info: %s", e)
    # Try cache fallback...
    raise ValueError(f"Failed to fetch model info: {e}")
except json.JSONDecodeError as e:
    logger.error("Failed to parse API response: %s", e)
    # Try cache fallback...
    raise ValueError(f"Failed to parse API response: {e}")
```

### Model/Provider Not Found
```python
if normalized_provider not in api_response:
    available_providers = list(api_response.keys())[:5]
    suggestions = ", ".join(available_providers)
    raise ValueError(f"Provider '{provider}' not found. Available providers include: {suggestions}")

if model not in models:
    available_models = list(models.keys())[:5]
    suggestions = ", ".join(available_models)
    raise ValueError(f"Model '{model}' not found for provider '{provider}'. Available models include: {suggestions}")
```

## API Response Structure

The models.dev API returns data in this structure:

```json
{
  "github-copilot": {
    "name": "GitHub Copilot",
    "doc": "GitHub Copilot AI assistant",
    "models": {
      "gpt-4o": {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "attachment": true,
        "reasoning": false,
        "temperature": true,
        "tool_call": true,
        "knowledge": "2023-09",
        "release_date": "2024-05-13",
        "last_updated": "2024-05-13",
        "modalities": {
          "input": ["text", "image"],
          "output": ["text"]
        },
        "open_weights": false,
        "limit": {
          "context": 128000,
          "output": 16384
        }
      }
    }
  }
}
```

Our implementation will:
1. Navigate to `api_response[normalized_provider]["models"][model]`
2. Extract the model data
3. Add `provider` and `id` fields for consistency
4. Cache the extracted model data

## Performance Considerations

- **API Calls**: Still making a single API call, but now to the correct endpoint
- **Response Size**: Main API response is larger (~200KB vs ~5KB), but we only cache the specific model data
- **Cache Efficiency**: Maintains the same cache structure for compatibility
- **Error Handling**: Added validation may slightly increase processing time but improves reliability

## Backward Compatibility

- **Cache Structure**: Maintained existing cache file structure
- **API Interface**: No changes to public method signatures
- **Error Types**: Still raises `ValueError` for consistency with existing error handling
- **CLI Output**: Same JSON output format

## Rollback Strategy

If issues arise:
1. **Quick Fix**: Revert to original implementation but add try/except for JSON parsing
2. **Fallback**: Add a fallback to the main API when the specific endpoint fails
3. **Emergency**: Add a hardcoded response for critical models if API is unreliable
