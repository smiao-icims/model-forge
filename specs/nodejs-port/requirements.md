# ModelForge Node.js - Requirements

## Context

This specification assumes Python ModelForge v2.0 is completed with:
- Simplified architecture (7 files, ~1,500 lines)
- Native LangChain telemetry integration
- OpenTelemetry support
- Clean, direct implementation patterns

## Problem Statement

Many development teams use both Python and Node.js in their stack:
- Python for data science, ML pipelines, backend services
- Node.js for web applications, APIs, serverless functions

Currently, Node.js developers must either:
- Call Python ModelForge via subprocess (complexity)
- Directly integrate with each LLM provider (duplication)
- Use different tools than their Python teammates (inconsistency)

## Goals

- **Feature parity** with Python ModelForge v2.0
- **Native Node.js/TypeScript** implementation
- **Shared configuration format** with Python version
- **Consistent CLI interface** across languages
- **LangChain.js** compatibility

## Non-Goals

- WebAssembly/shared binary with Python
- Browser support (Node.js only initially)
- Additional features beyond Python v2.0
- Backward compatibility with Python v1.x patterns

## Requirements

### Core Functionality

- **REQ-001**: TypeScript-first implementation with full type safety
- **REQ-002**: Support all providers from Python v2.0 (OpenAI, Anthropic, Google, Ollama, GitHub Copilot)
- **REQ-003**: Compatible configuration JSON format (read/write Python configs)
- **REQ-004**: LangChain.js integration for all LLM operations
- **REQ-005**: Native ESM modules with CommonJS compatibility

### Telemetry & Observability

- **REQ-006**: OpenTelemetry integration matching Python implementation
- **REQ-007**: LangChain.js callback system for token tracking
- **REQ-008**: Cost calculation with shared pricing configuration
- **REQ-009**: Session management compatible with Python telemetry data

### CLI Compatibility

- **REQ-010**: Identical CLI commands using Commander.js
- **REQ-011**: Same output format as Python CLI
- **REQ-012**: Cross-platform support (Windows, macOS, Linux)

### Developer Experience

- **REQ-013**: Simple npm installation: `npm install model-forge`
- **REQ-014**: TypeScript types for all public APIs
- **REQ-015**: Comprehensive JSDoc documentation
- **REQ-016**: Zero dependencies beyond LangChain.js and OpenTelemetry

## Success Criteria

- [ ] Node.js developer can use ModelForge without reading Python docs
- [ ] Configuration files work interchangeably between Python and Node.js
- [ ] Telemetry data can be aggregated across both implementations
- [ ] Performance is comparable to direct LangChain.js usage
- [ ] npm package reaches 1000+ weekly downloads within 3 months

## User Stories

1. **As a full-stack developer**, I want to use the same LLM configuration in my Python backend and Node.js frontend API
2. **As a DevOps engineer**, I want unified telemetry from both Python and Node.js services
3. **As a Node.js developer**, I want TypeScript types for all ModelForge APIs
4. **As a team lead**, I want consistent tooling across our polyglot codebase

## Example Usage

```typescript
import { ModelForge } from 'model-forge';

// Initialize with optional config
const forge = new ModelForge({
  enableTelemetry: true,
  telemetryBackend: 'opentelemetry',
  otelEndpoint: 'http://localhost:4317'
});

// Get LLM instance (uses current selection or specified)
const llm = await forge.getLLM('openai', 'gpt-4o-mini');

// Use with LangChain.js
const response = await llm.invoke('Hello, world!');

// Access telemetry
const usage = await forge.getTelemetry().getUsageSummary();
console.log(`Total cost: $${usage.totalCost}`);

// CLI usage (same as Python)
$ npx modelforge config show
$ npx modelforge config add --provider openai --api-key sk-...
$ npx modelforge test --prompt "Hello"
```

## Technical Decisions

1. **TypeScript over JavaScript** - Type safety and better IDE support
2. **ESM modules** - Modern Node.js standard
3. **Commander.js for CLI** - De facto standard for Node CLIs
4. **Same config paths** - `~/.config/model-forge/` and `./.model-forge/`
5. **Shared pricing config** - JSON file used by both implementations

## Out of Scope

- GraphQL API
- REST API server
- Browser bundle
- Deno support
- React/Vue/Angular components
- Electron app
