# Testing Enhancements - Design

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Test Commands  │────▶│  Test Orchestrator│────▶│  Result Analyzer│
│  - compare      │     │  - Multi-model   │     │  - Statistics   │
│  - benchmark    │     │  - Concurrent    │     │  - Visualization│
│  - cost analyze │     │  - Metrics       │     │  - Export       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                    ┌───────────┴────────────┐
                    │   Testing Framework    │
                    │  - Comparison Engine   │
                    │  - Benchmark Runner    │
                    │  - Cost Calculator     │
                    └────────────────────────┘
```

## Design Decisions

### 1. Model Comparison System

#### Comparison Engine
```python
@dataclass
class ComparisonResult:
    model_id: str
    provider: str
    model: str
    response: str
    metrics: dict[str, Any]
    error: str | None = None

class ModelComparator:
    def __init__(self, registry: ModelForgeRegistry):
        self.registry = registry

    async def compare(
        self,
        models: list[str],  # Format: "provider/model"
        prompt: str,
        **kwargs
    ) -> list[ComparisonResult]:
        """Compare responses from multiple models."""
        tasks = []

        for model_spec in models:
            provider, model = model_spec.split("/")
            task = self._test_model(provider, model, prompt, **kwargs)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_results(results)

    async def _test_model(
        self,
        provider: str,
        model: str,
        prompt: str,
        **kwargs
    ) -> ComparisonResult:
        """Test a single model."""
        start_time = time.time()

        try:
            # Get model with telemetry
            telemetry = TelemetryCallback(provider, model)
            llm = self.registry.get_llm(provider, model, callbacks=[telemetry])

            # Invoke model
            response = await llm.ainvoke(prompt)

            # Collect metrics
            metrics = {
                "latency": time.time() - start_time,
                "tokens": telemetry.metrics.token_usage.total_tokens,
                "cost": telemetry.metrics.estimated_cost,
                "prompt_tokens": telemetry.metrics.token_usage.prompt_tokens,
                "completion_tokens": telemetry.metrics.token_usage.completion_tokens,
            }

            return ComparisonResult(
                model_id=f"{provider}/{model}",
                provider=provider,
                model=model,
                response=response.content,
                metrics=metrics
            )

        except Exception as e:
            return ComparisonResult(
                model_id=f"{provider}/{model}",
                provider=provider,
                model=model,
                response="",
                metrics={},
                error=str(e)
            )
```

#### Comparison Formatter
```python
class ComparisonFormatter:
    def format_table(self, results: list[ComparisonResult]) -> str:
        """Format comparison results as table."""
        # Use rich or tabulate for nice output

    def format_json(self, results: list[ComparisonResult]) -> str:
        """Format as JSON for export."""

    def format_markdown(self, results: list[ComparisonResult]) -> str:
        """Format as markdown for reports."""
```

### 2. Performance Benchmarking

#### Benchmark Runner
```python
@dataclass
class BenchmarkConfig:
    provider: str
    model: str
    prompts: list[str]
    concurrent_requests: int = 1
    duration: float | None = None
    max_requests: int | None = None
    warmup_requests: int = 5

@dataclass
class BenchmarkResult:
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    latencies: list[float]
    tokens_per_second: float
    total_cost: float
    errors: list[str]

    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests

    def percentile(self, p: float) -> float:
        """Calculate latency percentile."""
        return np.percentile(self.latencies, p)

class BenchmarkRunner:
    def __init__(self, registry: ModelForgeRegistry):
        self.registry = registry

    async def run_benchmark(
        self,
        config: BenchmarkConfig
    ) -> BenchmarkResult:
        """Run performance benchmark."""
        # Warmup phase
        await self._warmup(config)

        # Main benchmark
        start_time = time.time()
        results = []

        async with asyncio.Semaphore(config.concurrent_requests):
            while self._should_continue(start_time, results, config):
                result = await self._benchmark_request(config)
                results.append(result)

        return self._analyze_results(results, time.time() - start_time)

    async def _benchmark_request(self, config: BenchmarkConfig):
        """Execute single benchmark request."""
        prompt = random.choice(config.prompts)
        start = time.time()

        try:
            telemetry = TelemetryCallback(config.provider, config.model)
            llm = self.registry.get_llm(
                config.provider,
                config.model,
                callbacks=[telemetry]
            )

            response = await llm.ainvoke(prompt)

            return {
                "success": True,
                "latency": time.time() - start,
                "tokens": telemetry.metrics.token_usage.total_tokens,
                "cost": telemetry.metrics.estimated_cost,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "latency": time.time() - start,
                "tokens": 0,
                "cost": 0,
                "error": str(e)
            }
```

### 3. Cost Analysis

#### Cost Analyzer
```python
@dataclass
class CostScenario:
    name: str
    prompts_per_day: int
    avg_prompt_tokens: int
    avg_completion_tokens: int
    days: int = 30

class CostAnalyzer:
    def __init__(self, models_dev: ModelsDev):
        self.models_dev = models_dev

    def analyze_scenario(
        self,
        scenario: CostScenario,
        providers: list[str]
    ) -> dict[str, float]:
        """Calculate costs for a scenario across providers."""
        costs = {}

        for provider in providers:
            models = self.models_dev.get_models(provider)

            for model in models:
                pricing = model.get("pricing", {})
                if not pricing:
                    continue

                # Calculate daily cost
                daily_cost = self._calculate_cost(
                    scenario.prompts_per_day,
                    scenario.avg_prompt_tokens,
                    scenario.avg_completion_tokens,
                    pricing
                )

                # Project to full period
                total_cost = daily_cost * scenario.days
                costs[f"{provider}/{model['name']}"] = total_cost

        return costs

    def recommend_model(
        self,
        scenarios: list[CostScenario],
        constraints: dict = None
    ) -> dict:
        """Recommend best model based on cost and constraints."""
        # Analyze all scenarios
        all_costs = {}
        for scenario in scenarios:
            costs = self.analyze_scenario(scenario, self._get_all_providers())
            all_costs[scenario.name] = costs

        # Apply constraints (latency, quality scores, etc.)
        if constraints:
            all_costs = self._apply_constraints(all_costs, constraints)

        # Find best overall
        return self._find_optimal_model(all_costs)
```

### 4. CLI Integration

#### Enhanced Test Command
```python
@cli.command()
@click.option("--compare", help="Compare multiple models (comma-separated)")
@click.option("--benchmark", is_flag=True, help="Run performance benchmark")
@click.option("--cost-analyze", is_flag=True, help="Analyze costs")
@click.option("--export", type=click.Choice(["json", "csv", "markdown"]))
def test(compare, benchmark, cost_analyze, export, ...):
    """Enhanced testing capabilities."""

    if compare:
        # Model comparison mode
        models = compare.split(",")
        comparator = ModelComparator(registry)
        results = asyncio.run(comparator.compare(models, prompt))

        if export:
            export_results(results, export)
        else:
            display_comparison(results)

    elif benchmark:
        # Benchmark mode
        runner = BenchmarkRunner(registry)
        config = BenchmarkConfig(...)
        results = asyncio.run(runner.run_benchmark(config))
        display_benchmark_results(results)

    elif cost_analyze:
        # Cost analysis mode
        analyzer = CostAnalyzer(models_dev)
        scenarios = load_scenarios()
        recommendations = analyzer.recommend_model(scenarios)
        display_cost_analysis(recommendations)
```

## Implementation Considerations

### Performance
- Async/concurrent execution for comparisons
- Connection pooling for benchmarks
- Result caching for cost analysis
- Streaming for large result sets

### Accuracy
- Proper statistical analysis
- Outlier detection
- Confidence intervals
- Repeated measurements

### Usability
- Progress indicators
- Clear error messages
- Export formats
- Visualization options

### Extensibility
- Plugin system for custom metrics
- Custom evaluation functions
- External result processors
- Integration with monitoring tools
