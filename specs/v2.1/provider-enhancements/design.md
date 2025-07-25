# Provider Enhancements - Design

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   User Code     │────▶│  Enhanced API    │────▶│ Provider-Specific│
│                 │     │  - stream()      │     │ Optimizations   │
│                 │     │  - batch()       │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                        ┌───────┴────────┐
                        │ Retry Manager  │
                        │ (Per Provider) │
                        └────────────────┘
```

## Design Decisions

### 1. Streaming Support

#### Stream Wrapper Class
```python
class StreamWrapper:
    def __init__(self, llm: BaseLLM, callbacks: list = None):
        self.llm = llm
        self.callbacks = callbacks or []

    async def stream(
        self,
        prompt: str,
        *,
        timeout: float = 300.0,
        on_progress: Callable[[int], None] = None,
        on_chunk: Callable[[str], None] = None,
        buffer_size: int = 10
    ) -> AsyncIterator[str]:
        """Stream with automatic buffering and callbacks."""
        buffer = []
        total_tokens = 0

        try:
            async for chunk in self.llm.astream(prompt, callbacks=self.callbacks):
                content = chunk.content
                buffer.append(content)
                total_tokens += estimate_tokens(content)

                if on_chunk:
                    on_chunk(content)

                if on_progress and total_tokens % 10 == 0:
                    on_progress(total_tokens)

                if len(buffer) >= buffer_size:
                    yield "".join(buffer)
                    buffer = []

            # Yield remaining buffer
            if buffer:
                yield "".join(buffer)

        except asyncio.TimeoutError:
            raise NetworkTimeoutError(
                timeout,
                context="Stream timeout",
                suggestion=f"Increase timeout beyond {timeout}s"
            )
```

#### Convenience Functions
```python
# In modelforge/streaming.py
def stream(llm: BaseLLM, prompt: str, **kwargs) -> AsyncIterator[str]:
    """Convenience function for streaming."""
    wrapper = StreamWrapper(llm)
    return wrapper.stream(prompt, **kwargs)

def stream_to_file(llm: BaseLLM, prompt: str, filepath: Path, **kwargs):
    """Stream response directly to file."""
    async def write_stream():
        async with aiofiles.open(filepath, 'w') as f:
            async for chunk in stream(llm, prompt, **kwargs):
                await f.write(chunk)
    return write_stream()
```

### 2. Provider-Specific Retry Configuration

#### Enhanced Retry Decorator
```python
class ProviderRetryConfig:
    def __init__(self, provider_config: dict):
        self.max_retries = provider_config.get("max_attempts", 3)
        self.backoff_factor = provider_config.get("backoff_factor", 2.0)
        self.max_wait = provider_config.get("max_wait", 60)
        self.respect_retry_after = provider_config.get("respect_retry_after", True)

        # Provider-specific rate limits
        self.rate_limits = provider_config.get("rate_limit", {})
        self.request_counter = RequestCounter(self.rate_limits)

@dataclass
class RequestCounter:
    """Track requests for rate limiting."""
    requests_per_minute: int
    tokens_per_minute: int

    def check_limits(self, tokens: int) -> float:
        """Return wait time if rate limited, 0 otherwise."""
        # Implementation here
```

#### Registry Integration
```python
class ModelForgeRegistry:
    def __init__(self, verbose: bool = False, enable_optimizations: bool = False):
        self.retry_configs = self._load_retry_configs()

    def get_llm(self, ...) -> BaseLLM:
        llm = self._create_llm_instance(...)

        # Wrap with provider-specific retry
        if provider_name in self.retry_configs:
            llm = RetryWrapper(llm, self.retry_configs[provider_name])

        return llm
```

### 3. Provider-Specific Optimizations

#### Optimization Strategies

```python
class ProviderOptimizer(ABC):
    @abstractmethod
    def optimize_prompt(self, prompt: str) -> str:
        pass

    @abstractmethod
    def optimize_config(self, config: dict) -> dict:
        pass

class OpenAIOptimizer(ProviderOptimizer):
    def optimize_config(self, config: dict) -> dict:
        # Enable seed for reproducibility
        config.setdefault("seed", 42)
        # Use JSON mode where appropriate
        if "json" in config.get("response_format", ""):
            config["response_format"] = {"type": "json_object"}
        return config

class AnthropicOptimizer(ProviderOptimizer):
    def optimize_prompt(self, prompt: str) -> str:
        # Structure for cache hits
        # Put static content first, dynamic last
        if "<<STATIC>>" in prompt and "<<DYNAMIC>>" in prompt:
            static, dynamic = prompt.split("<<DYNAMIC>>")
            # Ensure static part is >1024 chars for caching
            return f"{static}\n\n{dynamic}"
        return prompt

class BatchProcessor:
    """Handle batch operations efficiently."""

    async def batch_invoke(
        self,
        llm: BaseLLM,
        prompts: list[str],
        *,
        max_concurrent: int = 5,
        use_batch_api: bool = True
    ) -> list[str]:
        if isinstance(llm, ChatOpenAI) and use_batch_api:
            # Use OpenAI batch API for 50% discount
            return await self._openai_batch_api(llm, prompts)
        else:
            # Concurrent processing with rate limiting
            return await self._concurrent_invoke(llm, prompts, max_concurrent)
```

## Implementation Approach

### Phase 1: Streaming Support
1. Implement StreamWrapper class
2. Add convenience functions
3. Create streaming examples
4. Test with all providers

### Phase 2: Retry Configuration
1. Extend configuration schema
2. Implement ProviderRetryConfig
3. Create RetryWrapper
4. Add rate limiting

### Phase 3: Provider Optimizations
1. Create optimizer base class
2. Implement provider-specific optimizers
3. Add batch processing
4. Document optimization strategies

## Configuration Schema

```yaml
providers:
  openai:
    # Standard config...
    retry:
      max_attempts: 5
      backoff_factor: 2.0
      max_wait: 60
      respect_retry_after: true
    rate_limit:
      requests_per_minute: 3500
      tokens_per_minute: 90000
    optimizations:
      enable_batch_api: true
      enable_seed: true
      json_mode_auto: true

  anthropic:
    # Standard config...
    retry:
      max_attempts: 3
      backoff_factor: 1.5
    optimizations:
      cache_prompt_structure: true
      min_cache_length: 1024
```

## Error Handling

- Stream interruptions: Clean up resources, call callbacks
- Rate limit errors: Return clear wait times
- Optimization failures: Fall back to standard behavior
