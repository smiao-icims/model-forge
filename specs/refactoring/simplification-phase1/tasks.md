# ModelForge Simplification Refactoring - Tasks

## Implementation Tasks

### Phase 1: Core Simplification (Registry & Validation)

- [ ] **TASK-001**: Create new `core.py` file with simplified `ModelForge` class
- [ ] **TASK-002**: Migrate `get_llm()` method without factory pattern
- [ ] **TASK-003**: Implement direct LLM creation for each provider type
- [ ] **TASK-004**: Inline validation logic at API boundaries only
- [ ] **TASK-005**: Remove `_create_*_llm` methods in favor of direct creation
- [ ] **TASK-006**: Update imports in `__init__.py` to expose new API
- [ ] **TASK-007**: Write tests for new simplified core module

### Phase 2: Error Handling Simplification

- [ ] **TASK-008**: Remove `@handle_errors` decorator usage from all files
- [ ] **TASK-009**: Replace decorator error handling with explicit try/except where needed
- [ ] **TASK-010**: Remove `error_handler.py` file
- [ ] **TASK-011**: Simplify `@retry_on_error` to a simple retry function
- [ ] **TASK-012**: Move retry logic inline where actually needed (network calls)
- [ ] **TASK-013**: Remove `retry.py` file
- [ ] **TASK-014**: Update all error messages to be clear without decorator context

### Phase 3: Authentication Simplification

- [ ] **TASK-015**: Create simplified `Auth` class without ABC pattern
- [ ] **TASK-016**: Implement `get_api_key()` method for all providers
- [ ] **TASK-017**: Implement `set_api_key()` method for storing credentials
- [ ] **TASK-018**: Migrate GitHub device flow to direct implementation
- [ ] **TASK-019**: Remove `AuthStrategy` ABC and all subclasses
- [ ] **TASK-020**: Consolidate auth logic into ~100 lines
- [ ] **TASK-021**: Update all auth calls in CLI and core

### Phase 4: Configuration Simplification

- [ ] **TASK-022**: Create simplified `Config` class with explicit scope
- [ ] **TASK-023**: Remove complex precedence logic
- [ ] **TASK-024**: Implement `get()` and `save()` with explicit scope
- [ ] **TASK-025**: Remove configuration merging logic
- [ ] **TASK-026**: Update CLI to use explicit scope flags
- [ ] **TASK-027**: Migrate existing configs to new structure
- [ ] **TASK-028**: Remove old config helper functions

### Phase 5: Validation Consolidation

- [ ] **TASK-029**: Move all validation to `core.py` entry points
- [ ] **TASK-030**: Remove validation from internal methods
- [ ] **TASK-031**: Delete `validation.py` file
- [ ] **TASK-032**: Ensure validation happens once per operation
- [ ] **TASK-033**: Update error messages for validation failures

### Phase 6: CLI Consolidation

- [ ] **TASK-034**: Merge `cli_utils.py` into `cli.py`
- [ ] **TASK-035**: Simplify error formatting without special handlers
- [ ] **TASK-036**: Remove `@handle_cli_errors` decorator
- [ ] **TASK-037**: Use standard Click error handling
- [ ] **TASK-038**: Ensure all CLI commands work identically

### Phase 7: Logging Simplification

- [ ] **TASK-039**: Remove `logging_config.py` file
- [ ] **TASK-040**: Add simple logging setup to `__init__.py`
- [ ] **TASK-041**: Use standard Python logging without custom configuration
- [ ] **TASK-042**: Update all logger imports

### Phase 8: Final Cleanup

- [ ] **TASK-043**: Update all imports throughout the codebase
- [ ] **TASK-044**: Remove deleted files from git
- [ ] **TASK-045**: Update `pyproject.toml` if needed
- [ ] **TASK-046**: Run full test suite
- [ ] **TASK-047**: Update code coverage
- [ ] **TASK-048**: Fix any failing tests

## Testing Tasks

- [ ] **TASK-049**: Ensure all existing unit tests pass
- [ ] **TASK-050**: Ensure all existing integration tests pass
- [ ] **TASK-051**: Test backward compatibility of public APIs
- [ ] **TASK-052**: Test CLI commands produce identical output
- [ ] **TASK-053**: Test configuration migration
- [ ] **TASK-054**: Performance comparison (should be same or better)

## Documentation Tasks

- [ ] **TASK-055**: Update README with new architecture
- [ ] **TASK-056**: Update CLAUDE.md with simplified patterns
- [ ] **TASK-057**: Update inline docstrings
- [ ] **TASK-058**: Create migration guide for developers
- [ ] **TASK-059**: Update API documentation

## Validation Tasks

- [ ] **TASK-060**: Code review for simplicity
- [ ] **TASK-061**: Cyclomatic complexity analysis
- [ ] **TASK-062**: Lines of code comparison
- [ ] **TASK-063**: New developer onboarding test
- [ ] **TASK-064**: Ensure no functionality is lost

## Rollback Plan

- [ ] **TASK-065**: Create git branch for each phase
- [ ] **TASK-066**: Tag stable version before refactoring
- [ ] **TASK-067**: Document rollback procedure
- [ ] **TASK-068**: Test rollback procedure

## Success Metrics

- [ ] **METRIC-001**: Achieve 40% reduction in lines of code
- [ ] **METRIC-002**: Reduce from 12 files to 7 files
- [ ] **METRIC-003**: Average cyclomatic complexity < 5
- [ ] **METRIC-004**: All tests pass without modification
- [ ] **METRIC-005**: Zero breaking changes to public API
