# Model-Forge Release Strategy

## Version Decision: 2.2.0 (Minor Release)

After careful analysis, these enhancements can be released as **version 2.2.0** (minor release) rather than 3.0.0, maintaining full backward compatibility.

## Rationale for Minor Version

### Why NOT a Breaking Change (3.0.0)

1. **API Compatibility**: The EnhancedLLM wrapper maintains the full BaseChatModel interface
2. **Delegation Pattern**: All existing methods work exactly as before
3. **Opt-out Available**: Users can set `enhanced=False` to get original behavior
4. **Additive Changes**: We're only adding new properties, not modifying existing ones

### Backward Compatibility Guarantees

The implementation will ensure:
- All existing code continues to work without modification
- Type compatibility maintained (EnhancedLLM is-a BaseChatModel)
- Performance impact negligible (<100ms overhead)
- Serialization/deserialization supported

## Release Strategy

### Phase 1: Beta Release (2.2.0-beta.1)
**Timeline**: Week 1-2 after implementation
**Approach**: Conservative defaults

```python
def get_llm(..., enhanced: bool = False):  # Default to False in beta
    """
    Get LLM instance.

    Note: In v2.2.0-beta, enhanced defaults to False for compatibility.
    This will change to True in v2.3.0.
    """
```

**Goals**:
- Early adopter feedback
- Identify edge cases
- Performance validation
- Browser Pilot integration testing

### Phase 2: Stable Release (2.2.0)
**Timeline**: Week 3-4
**Approach**: Feature flag with migration notice

```python
def get_llm(..., enhanced: bool = None):
    """
    Get LLM instance.

    Args:
        enhanced: If True, returns EnhancedLLM with metadata.
                 If False, returns raw LangChain model.
                 If None (default), checks MODELFORGE_ENHANCED env var,
                 defaults to False. Will default to True in v2.3.0.
    """
    if enhanced is None:
        enhanced = os.getenv("MODELFORGE_ENHANCED", "false").lower() == "true"
        if not enhanced:
            warnings.warn(
                "Starting in model-forge v2.3.0, get_llm() will return "
                "EnhancedLLM by default. Set enhanced=False to keep current "
                "behavior or set MODELFORGE_ENHANCED=true to opt-in early.",
                FutureWarning
            )
```

### Phase 3: Default Flip (2.3.0)
**Timeline**: 1-2 months after 2.2.0
**Approach**: Make enhanced behavior default

```python
def get_llm(..., enhanced: bool = True):  # Now defaults to True
    """Enhanced behavior is now default. Set enhanced=False for legacy behavior."""
```

## Implementation Requirements for Compatibility

### 1. Attribute Delegation
```python
class EnhancedLLM(BaseChatModel):
    def __getattr__(self, name):
        """Delegate unknown attributes to wrapped model."""
        return getattr(self._wrapped_llm, name)

    def __setattr__(self, name, value):
        """Handle attribute setting carefully."""
        if name.startswith('_') or name in self._enhanced_attrs:
            super().__setattr__(name, value)
        else:
            setattr(self._wrapped_llm, name, value)
```

### 2. Type Checking Support
```python
class EnhancedLLM(BaseChatModel):
    @property
    def __class__(self):
        """Return wrapped class for isinstance checks."""
        # This is a bit hacky but maintains compatibility
        if hasattr(self, '_isinstance_compat') and self._isinstance_compat:
            return self._wrapped_llm.__class__
        return type(self)
```

### 3. Serialization Support
```python
class EnhancedLLM(BaseChatModel):
    def __getstate__(self):
        """Support pickling."""
        return {
            'wrapped_llm': self._wrapped_llm,
            'metadata': self._metadata,
            'custom_params': self._custom_params
        }

    def __setstate__(self, state):
        """Support unpickling."""
        self._wrapped_llm = state['wrapped_llm']
        self._metadata = state['metadata']
        self._custom_params = state['custom_params']
```

## Migration Guide for Users

### For Existing Users (No Action Required)
```python
# This continues to work exactly as before
llm = registry.get_llm("openai", "gpt-4")
response = llm.invoke("Hello")
```

### For Early Adopters (Opt-in to New Features)
```python
# Option 1: Explicit parameter
llm = registry.get_llm("openai", "gpt-4", enhanced=True)
print(f"Context length: {llm.context_length}")

# Option 2: Environment variable
os.environ["MODELFORGE_ENHANCED"] = "true"
llm = registry.get_llm("openai", "gpt-4")
```

### For Browser Pilot
```python
# Immediate adoption with explicit parameter
llm = registry.get_llm(enhanced=True)
if llm.context_length > 0:
    # Use metadata for intelligent decisions
    max_prompt = int(llm.context_length * 0.8)
```

## Testing Strategy for Compatibility

### 1. Regression Test Suite
- Run ALL existing tests without modification
- Ensure 100% pass rate with enhanced=False
- Ensure 100% pass rate with enhanced=True

### 2. Compatibility Test Suite
```python
def test_isinstance_compatibility():
    """Ensure isinstance checks work."""
    llm = registry.get_llm("openai", "gpt-4", enhanced=True)
    # Should work with proper implementation
    assert isinstance(llm, BaseChatModel)

def test_attribute_access():
    """Ensure provider-specific attributes accessible."""
    llm = registry.get_llm("openai", "gpt-4", enhanced=True)
    # Should delegate to wrapped model
    assert hasattr(llm, 'model_name')

def test_serialization():
    """Ensure pickle/unpickle works."""
    llm = registry.get_llm("openai", "gpt-4", enhanced=True)
    pickled = pickle.dumps(llm)
    unpickled = pickle.loads(pickled)
    assert unpickled.context_length == llm.context_length
```

### 3. Performance Benchmarks
- Measure overhead of wrapper
- Ensure <100ms additional latency
- Monitor memory usage

## Communication Plan

### 1. Pre-Release Announcement
- Blog post explaining new features
- Migration guide
- Beta testing invitation

### 2. Release Notes Template
```markdown
## v2.2.0 - Enhanced Model Metadata and Configuration

### 🎉 New Features
- **Model Metadata**: Access context length, capabilities, and pricing info
- **Parameter Management**: Set and validate model parameters consistently
- **Cost Estimation**: Calculate costs before making API calls
- **Full Backward Compatibility**: All existing code continues to work

### 🔄 Migration
No action required! New features are opt-in via `enhanced=True` parameter.

### 📋 Coming in v2.3.0
Enhanced behavior will become the default. Set `enhanced=False` to maintain current behavior.
```

### 3. Documentation Updates
- Add "What's New in 2.2" section
- Update all examples to show both modes
- Create migration timeline

## Risk Mitigation

### Risk: Hidden Breaking Changes
**Mitigation**:
- Extensive compatibility test suite
- Beta release period
- Conservative default (enhanced=False initially)

### Risk: Performance Regression
**Mitigation**:
- Performance benchmarks in CI/CD
- Caching strategy for metadata
- Lazy loading where possible

### Risk: User Confusion
**Mitigation**:
- Clear documentation
- Helpful warning messages
- Gradual transition period

## Success Criteria

1. **Zero Breaking Changes**: All existing tests pass
2. **Adoption Rate**: >20% opt-in during beta
3. **Performance**: <100ms overhead confirmed
4. **Browser Pilot**: Successfully integrated
5. **User Feedback**: No critical issues in beta

## Timeline Summary

- **Week 1-2**: Implementation + 2.2.0-beta.1
- **Week 3-4**: Beta feedback + 2.2.0 stable
- **Month 2-3**: Monitor adoption + prepare 2.3.0
- **Month 3+**: Release 2.3.0 with enhanced as default

This approach ensures a smooth transition while maintaining the trust of existing users and enabling new capabilities for Browser Pilot.
