# Bug Fix: 'modelforge models info' JSON Decode Error - Requirements

## Problem Statement
The `modelforge models info --provider github_copilot --model gpt-4o` command fails with a JSON decode error because it's trying to fetch model information from a non-existent API endpoint that returns HTML instead of JSON.

## Root Cause Analysis
1. **Incorrect API Endpoint**: The `_fetch_model_info()` method constructs URLs like `https://models.dev/models/{provider}/{model}` which don't exist
2. **API Structure Misunderstanding**: The models.dev API only has one endpoint (`/api.json`) that contains all data
3. **No Fallback Logic**: When the endpoint returns HTML (404 page), the code tries to parse it as JSON, causing the decode error
4. **Provider Name Mismatch**: The provider name used in URL construction may not match the API structure

## Error Details
```
Traceback (most recent call last):
  File "requests/models.py", line 976, in json
    return complexjson.loads(self.text, **kwargs)
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## Requirements

### 1. Fix API Endpoint Usage
- **REQ-001**: Use the main `/api.json` endpoint to get model information
- **REQ-002**: Extract specific model data from the full API response
- **REQ-003**: Handle cases where the model doesn't exist in the API response
- **REQ-004**: Maintain backward compatibility with existing cache structure

### 2. Improve Error Handling
- **REQ-005**: Add proper error handling for non-JSON responses
- **REQ-006**: Provide meaningful error messages when model is not found
- **REQ-007**: Add validation for provider and model names
- **REQ-008**: Handle network errors gracefully

### 3. Provider Name Consistency
- **REQ-009**: Ensure provider names are consistent between list and info commands
- **REQ-010**: Handle provider name variations (github_copilot vs github-copilot)
- **REQ-011**: Validate provider exists before attempting to get model info
- **REQ-012**: Provide helpful suggestions when provider/model not found

### 4. API Response Validation
- **REQ-013**: Validate API response is JSON before parsing
- **REQ-014**: Check response status codes properly
- **REQ-015**: Handle empty or malformed responses
- **REQ-016**: Add logging for debugging API issues

## Expected Behavior

### Before (Broken)
```bash
$ modelforge models info --provider github_copilot --model gpt-4o
❌ Error getting model info: Expecting value: line 1 column 1 (char 0)
```

### After (Fixed)
```bash
$ modelforge models info --provider github_copilot --model gpt-4o
{
  "id": "gpt-4o",
  "name": "GPT-4o",
  "provider": "github-copilot",
  "attachment": true,
  "reasoning": false,
  "temperature": true,
  "tool_call": true,
  "knowledge": "2023-09",
  "release_date": "2024-05-13",
  "modalities": {
    "input": ["text", "image"],
    "output": ["text"]
  },
  "limit": {
    "context": 128000,
    "output": 16384
  }
}
```

## API Structure Analysis

The models.dev API structure is:
```json
{
  "github-copilot": {
    "models": {
      "gpt-4o": {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "attachment": true,
        "reasoning": false,
        "knowledge": "2023-09",
        "release_date": "2024-05-13",
        "limit": {"context": 128000, "output": 16384}
      }
    }
  }
}
```

## Success Criteria
- [ ] `modelforge models info` command works for all providers
- [ ] Proper JSON response returned with model details
- [ ] Helpful error messages when model/provider not found
- [ ] No breaking changes to existing functionality
- [ ] Proper error handling for network issues
- [ ] Cache system works correctly with new implementation

## Testing Requirements
- [ ] Test with valid provider/model combinations
- [ ] Test with invalid provider names
- [ ] Test with invalid model names
- [ ] Test with network failures
- [ ] Test cache behavior
- [ ] Test JSON output format

## Non-Requirements
- This fix does NOT change the CLI interface
- This fix does NOT modify the cache structure significantly
- This fix does NOT affect other model commands (list, search)
- This fix does NOT require additional API endpoints
