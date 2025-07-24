# ModelForge Node.js - Design

## Architecture Overview

Based on the simplified Python v2.0 architecture, the Node.js implementation will mirror the clean, direct approach without unnecessary abstractions.

### File Structure

```
model-forge-js/
├── src/
│   ├── index.ts           # Main exports
│   ├── core.ts            # ModelForge class (~400 lines)
│   ├── config.ts          # Configuration management (~100 lines)
│   ├── auth.ts            # Simple auth handling (~100 lines)
│   ├── telemetry.ts       # Telemetry integration (~200 lines)
│   ├── cli.ts             # CLI commands (~300 lines)
│   └── types.ts           # TypeScript interfaces
├── dist/                  # Compiled JavaScript
├── package.json
├── tsconfig.json
└── README.md
```

Total: ~1,200 lines of TypeScript (smaller than Python due to more concise syntax)

## Core Components

### 1. ModelForge Class (core.ts)

```typescript
import { ChatOpenAI, ChatOllama, ChatGoogleGenerativeAI, ChatAnthropic } from '@langchain/community';
import { BaseLanguageModel } from '@langchain/core';

export class ModelForge {
  private config: Config;
  private auth: Auth;
  private telemetry?: Telemetry;

  constructor(options: ModelForgeOptions = {}) {
    this.config = new Config(options.configScope);
    this.auth = new Auth(this.config);

    if (options.enableTelemetry) {
      this.telemetry = new Telemetry({
        backend: options.telemetryBackend || 'native',
        otelEndpoint: options.otelEndpoint
      });
    }
  }

  async getLLM(provider?: string, model?: string): Promise<BaseLanguageModel> {
    // Direct implementation matching Python v2.0
    const { provider: p, model: m, config } = this.resolveModel(provider, model);

    // Apply telemetry callbacks if enabled
    const callbacks = this.telemetry?.getCallbacks() || [];

    // Direct creation (no factory pattern)
    switch (config.llmType) {
      case 'openai_compatible':
        return new ChatOpenAI({
          modelName: config.apiModelName || m,
          openAIApiKey: await this.auth.getApiKey(p),
          configuration: { baseURL: config.baseUrl },
          callbacks
        });

      case 'ollama':
        return new ChatOllama({
          model: m,
          baseUrl: config.baseUrl || process.env.OLLAMA_HOST,
          callbacks
        });

      case 'google_genai':
        return new ChatGoogleGenerativeAI({
          modelName: config.apiModelName || m,
          apiKey: await this.auth.getApiKey(p),
          callbacks
        });

      // ... other providers

      default:
        throw new Error(`Unsupported LLM type: ${config.llmType}`);
    }
  }

  getTelemetry(): Telemetry | undefined {
    return this.telemetry;
  }
}
```

### 2. Configuration (config.ts)

```typescript
export class Config {
  private scope: 'local' | 'global' | 'auto';
  private configPath: string;

  constructor(scope: 'local' | 'global' | 'auto' = 'auto') {
    this.scope = scope;
    this.configPath = this.getConfigPath();
  }

  read(): ConfigData {
    try {
      return JSON.parse(fs.readFileSync(this.configPath, 'utf8'));
    } catch {
      return { providers: {} };
    }
  }

  write(data: ConfigData): void {
    const dir = path.dirname(this.configPath);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(this.configPath, JSON.stringify(data, null, 2));
  }

  private getConfigPath(): string {
    const home = os.homedir();
    const globalPath = path.join(home, '.config', 'model-forge', 'config.json');
    const localPath = path.join(process.cwd(), '.model-forge', 'config.json');

    switch (this.scope) {
      case 'local': return localPath;
      case 'global': return globalPath;
      case 'auto': return fs.existsSync(localPath) ? localPath : globalPath;
    }
  }
}
```

### 3. Authentication (auth.ts)

```typescript
export class Auth {
  constructor(private config: Config) {}

  async getApiKey(provider: string): Promise<string | undefined> {
    const data = this.config.read();
    const authData = data.providers?.[provider]?.authData;

    return authData?.apiKey || authData?.accessToken;
  }

  async setApiKey(provider: string, apiKey: string): Promise<void> {
    const data = this.config.read();

    if (!data.providers) data.providers = {};
    if (!data.providers[provider]) data.providers[provider] = {};

    data.providers[provider].authData = { apiKey };
    this.config.write(data);
  }

  // GitHub device flow - direct implementation
  async githubDeviceFlow(): Promise<{ accessToken: string }> {
    // Implementation matching Python version
  }
}
```

### 4. Telemetry (telemetry.ts)

```typescript
import { BaseCallbackHandler } from '@langchain/core/callbacks';
import { trace, Span } from '@opentelemetry/api';

export class Telemetry {
  private usageCallback: UsageMetadataCallback;
  private otelCallback?: OTelCallback;
  private costCalculator: CostCalculator;

  constructor(options: TelemetryOptions) {
    this.usageCallback = new UsageMetadataCallback();
    this.costCalculator = new CostCalculator();

    if (options.backend === 'opentelemetry' && options.otelEndpoint) {
      this.otelCallback = new OTelCallback(options.otelEndpoint);
    }
  }

  getCallbacks(): BaseCallbackHandler[] {
    const callbacks = [this.usageCallback];
    if (this.otelCallback) callbacks.push(this.otelCallback);
    return callbacks;
  }

  getUsageSummary(): UsageSummary {
    const usage = this.usageCallback.getMetadata();
    return this.costCalculator.addCosts(usage);
  }
}

class OTelCallback extends BaseCallbackHandler {
  private tracer = trace.getTracer('model-forge');
  private spans = new Map<string, Span>();

  async handleLLMStart(llm: any, prompts: string[], runId: string) {
    const span = this.tracer.startSpan('llm.invoke');
    span.setAttributes({
      'llm.system': 'model-forge',
      'llm.request.model': llm.modelName,
      'llm.request.provider': llm.constructor.name
    });
    this.spans.set(runId, span);
  }

  async handleLLMEnd(output: any, runId: string) {
    const span = this.spans.get(runId);
    if (span && output.llmOutput?.tokenUsage) {
      span.setAttributes({
        'llm.usage.prompt_tokens': output.llmOutput.tokenUsage.promptTokens,
        'llm.usage.completion_tokens': output.llmOutput.tokenUsage.completionTokens,
        'llm.usage.total_tokens': output.llmOutput.tokenUsage.totalTokens
      });
      span.end();
      this.spans.delete(runId);
    }
  }
}
```

### 5. CLI (cli.ts)

```typescript
#!/usr/bin/env node
import { Command } from 'commander';
import { ModelForge } from './core';

const program = new Command();

program
  .name('modelforge')
  .description('ModelForge CLI for managing LLM configurations')
  .version('1.0.0');

// Config commands
const config = program.command('config');

config
  .command('show')
  .description('Show current configuration')
  .action(async () => {
    const forge = new ModelForge();
    const config = forge.getConfig();
    console.log(JSON.stringify(config, null, 2));
  });

config
  .command('add')
  .option('--provider <provider>', 'Provider name')
  .option('--model <model>', 'Model name')
  .option('--api-key <key>', 'API key')
  .action(async (options) => {
    // Implementation matching Python CLI
  });

// Usage commands
const usage = program.command('usage');

usage
  .command('show')
  .description('Show usage statistics')
  .action(async () => {
    const forge = new ModelForge({ enableTelemetry: true });
    const summary = forge.getTelemetry()?.getUsageSummary();
    // Format and display usage
  });

program.parse();
```

## Key Design Decisions

### 1. Direct Pattern Matching
Following Python v2.0's simplification:
- No factory patterns
- No abstract base classes
- Direct switch/case for provider types
- Explicit over implicit

### 2. TypeScript Benefits
```typescript
interface ModelConfig {
  llmType: 'openai_compatible' | 'ollama' | 'google_genai' | 'anthropic';
  apiModelName?: string;
  baseUrl?: string;
}

interface UsageSummary {
  models: Record<string, ModelUsage>;
  totalCost: string;
  totalTokens: number;
}
```

### 3. Async/Await Throughout
- All LLM operations are async
- Consistent with LangChain.js patterns
- Better error handling

### 4. Shared Configuration
- Same JSON format as Python
- Same file locations
- Can read Python configs directly

## Implementation Plan

### Phase 1: Core (Week 1)
1. Set up TypeScript project
2. Implement ModelForge class
3. Basic provider support
4. Unit tests with Vitest

### Phase 2: Config & Auth (Week 2)
1. Configuration management
2. Authentication (API keys only)
3. GitHub device flow
4. CLI scaffold

### Phase 3: Telemetry (Week 3)
1. LangChain.js callbacks
2. OpenTelemetry integration
3. Cost calculation
4. Session management

### Phase 4: Polish (Week 4)
1. Complete CLI commands
2. Documentation
3. npm package setup
4. Cross-platform testing

## Testing Strategy

```typescript
// vitest example
describe('ModelForge', () => {
  it('should create OpenAI instance with telemetry', async () => {
    const forge = new ModelForge({ enableTelemetry: true });
    const llm = await forge.getLLM('openai', 'gpt-4o-mini');

    expect(llm).toBeInstanceOf(ChatOpenAI);
    expect(llm.callbacks).toHaveLength(2); // usage + otel
  });
});
```

## Package Configuration

```json
{
  "name": "model-forge",
  "version": "1.0.0",
  "type": "module",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs"
    }
  },
  "bin": {
    "modelforge": "./dist/cli.js"
  },
  "dependencies": {
    "@langchain/community": "^0.x",
    "@langchain/core": "^0.x",
    "@opentelemetry/api": "^1.x",
    "commander": "^12.x"
  },
  "devDependencies": {
    "@types/node": "^20.x",
    "typescript": "^5.x",
    "vitest": "^1.x"
  }
}
```
