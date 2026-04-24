# Building AI Agent Systems — Concepts & Patterns You Need to Know

This document teaches you the foundational concepts for building production-grade AI agent systems, beyond what's specific to this project.

---

## 1. Prompt Engineering Patterns

### 1.1 Chain-of-Thought (CoT)

**What**: Force the LLM to reason step-by-step before giving a final answer.

**Why**: LLMs make fewer mistakes when they "think aloud." A direct "give me a score" prompt produces worse results than "analyze each factor, then derive a score."

**Template**:
```
Analyze the following claim data for [pattern].

Step 1: Identify relevant indicators in the data.
Step 2: Compare each indicator to the benchmark.
Step 3: Assess the severity of each deviation.
Step 4: Calculate a composite score (0-100).
Step 5: List exculpatory factors that reduce suspicion.

Return JSON: {pattern, score, severity, evidence[], reasoning, exculpatory_factors[]}
```

**In our project**: All 4 pattern analyzers use CoT prompts (`*_cot/v1.yaml`).

### 1.2 Few-Shot Learning

**What**: Include 2-3 examples of correct input→output pairs in the prompt.

**Why**: Showing the LLM what "good" output looks like is more effective than describing it.

**Template**:
```
=== EXAMPLE 1 ===
INPUT: Claim CLM-EXAMPLE-001, claimant has 5 prior claims...
OUTPUT: {"score": 85, "severity": "critical", "evidence": [...]}

=== EXAMPLE 2 ===
INPUT: Claim CLM-EXAMPLE-002, claimant has 0 prior claims...
OUTPUT: {"score": 10, "severity": "clean", "evidence": [...]}

=== NOW ANALYZE THIS CLAIM ===
INPUT: {actual_claim_data}
```

**In our project**: `duplicate_similar_cot/v1.yaml` uses few-shot examples.

### 1.3 ReAct (Reasoning + Acting)

**What**: The LLM alternates between THINKING and ACTING (calling tools).

**Why**: Lets the LLM decide what data it needs, rather than front-loading everything.

**Template**:
```
THOUGHT: I need to check the claimant's prior claims to assess fraud risk.
ACTION: lookup_claimant_history(claimant_id="C-4821")
OBSERVATION: {"total_prior_claims": 4, "prior_fraud_flags": 2}

THOUGHT: The claimant has 2 prior fraud flags. Now I need provider data.
ACTION: lookup_provider_network(provider_id="PRV-0093")
OBSERVATION: {"billing_ratio": 2.96, "license_status": "under_investigation"}

THOUGHT: Both the claimant and provider are flagged. I have enough data.
FINAL ANSWER: {"enrichment_status": "complete", ...}
```

**In our project**: `enrichment_react/v1.yaml` uses ReAct for data gathering.

### 1.4 Persona-Based Prompting

**What**: Define WHO the LLM is responding as, tailoring output style.

**In our project**: Kevin (verbose) vs Diana (concise) — same data, different presentation.

---

## 2. Tool Design Patterns

### 2.1 The Tool Interface Pattern
Every tool follows a contract: `name`, `description`, `execute()`.

```python
class BaseTool(ABC):
    @property
    def name(self) -> str: ...          # LLM sees this
    @property
    def description(self) -> str: ...   # LLM reads this to decide when to use the tool
    async def execute(self, **kwargs): ... # Actual logic
    async def run(self, **kwargs): ...    # Wrapper with telemetry
```

**Rule**: The `description` must be written FOR THE LLM. It should clearly explain what the tool does, what inputs it needs, and what it returns — because the LLM uses this text to decide whether to call the tool.

### 2.2 Tool Registry Pattern
Don't hardcode tool references. Use a registry:
```python
registry = ToolRegistry()
registry.register(ToolA())
registry.register(ToolB())
result = await registry.get("tool_a").run(input=data)
```

This enables swapping tools without changing agent code.

### 2.3 Deterministic vs LLM Tools
Not every tool needs an LLM:

| Type | When to Use | Example |
|------|-----------|---------|
| **Deterministic** | Calculations, formatting, data lookup | `calculate_priority_score`, `format_evidence_summary` |
| **LLM-powered** | Reasoning, analysis, generation | `duplicate_similar_analyzer`, `format_investigation_report` |

**Best practice**: Make everything deterministic that CAN be deterministic. Only use the LLM when you need reasoning or natural language generation.

---

## 3. Dependency Injection in AI Systems

### The Problem
```python
# Bad: Agent directly imports and creates its dependencies
class MyAgent:
    def __init__(self):
        self.db = PostgresDatabase("localhost:5432")  # Hardcoded!
        self.llm = GeminiClient("api-key-123")        # Hardcoded!
```

### The Solution
```python
# Good: Dependencies injected from outside
class MyAgent:
    def __init__(self, storage: IStorageRepository, llm_agent: Agent):
        self.storage = storage  # Could be Postgres, MongoDB, or mock
        self.llm = llm_agent    # Could be Gemini, GPT, or mock
```

### Why This Matters for AI
- **Testing**: Inject a mock LLM that returns deterministic responses
- **Cost**: Use a cheap model in dev, expensive model in prod
- **Swapping**: Change from Gemini to GPT-4 by changing one line in the container
- **Multi-environment**: Local mock → staging with real API → production

---

## 4. Parallelism Patterns for AI Pipelines

### 4.1 Fan-Out / Fan-In
Process multiple items concurrently, then aggregate:
```python
# Fan out: N claims processed in parallel
results = await asyncio.gather(*[
    process_claim(claim) for claim in claims
])
# Fan in: aggregate results
summary = aggregate(results)
```

### 4.2 Parallel Tool Execution
When tools are independent, run them simultaneously:
```python
# Bad: Sequential (4x slower)
history = await lookup_history(id)
network = await lookup_network(id)
value = await lookup_value(vin)
policy = await lookup_policy(num)

# Good: Parallel (1x time)
history, network, value, policy = await asyncio.gather(
    lookup_history(id),
    lookup_network(id),
    lookup_value(vin),
    lookup_policy(num),
)
```

### 4.3 Sequential When Necessary
When Tool B depends on Tool A's output:
```python
# Priority score feeds into report generation
priority = await calculate_priority(score)       # Must run first
evidence = await format_evidence(patterns)        # Must run first
report = await generate_report(priority, evidence) # Depends on both
```

---

## 5. Error Handling & Graceful Degradation

### Pattern: Partial Results Over Total Failure
```python
results = await asyncio.gather(
    *[process_claim(c) for c in claims],
    return_exceptions=True  # Don't crash if one claim fails
)

# Separate successes from failures
for result in results:
    if isinstance(result, Exception):
        log_error(result)  # Log but continue
    else:
        successful_results.append(result)
```

### Pattern: Enrichment Fallback
```python
try:
    enriched = await enrich_claim(claim)
except EnrichmentError:
    enriched = {"enrichment_status": "partial", "raw_claim": claim}
    # Continue with partial data — analysis can still run
```

---

## 6. Scoring & Ranking Systems

### Weighted Composite Score
```python
WEIGHTS = {"duplicate": 0.30, "timing": 0.20, "inflated": 0.25, "provider": 0.25}
composite = sum(scores[p] * WEIGHTS[p] for p in WEIGHTS)
```

### Confidence Levels
```python
patterns_flagged = sum(1 for s in scores.values() if s > 40)
if patterns_flagged >= 3: confidence = "high"
elif patterns_flagged >= 2: confidence = "medium"
else: confidence = "low"
```

### Priority Tiers
```python
if composite >= 80: tier = "critical"   # Immediate investigation
elif composite >= 60: tier = "high"     # Investigation recommended
elif composite >= 40: tier = "medium"   # Enhanced monitoring
else: tier = "low"                       # No action needed
```

---

## 7. Versioned Prompt Management

### Why Version Prompts?
Prompts ARE your application logic in an LLM system. Changing a prompt can completely change output quality. You need:
- **Rollback**: If v2 prompt performs worse, revert to v1
- **A/B Testing**: Run v1 and v2 simultaneously, compare results
- **Audit Trail**: Know exactly which prompt generated each result

### Implementation Pattern
```
prompts/
└── my_pattern/
    ├── v1.yaml    # Original
    ├── v2.yaml    # Improved (add few-shot examples)
    └── v3.yaml    # Latest (refined scoring criteria)
```

```python
# Load latest version
prompt = PromptFacade.get_prompt("my_pattern", context)

# Pin specific version for A/B test
prompt_v1 = PromptFacade.get_prompt("my_pattern", context, version="1")
prompt_v2 = PromptFacade.get_prompt("my_pattern", context, version="2")
```

---

## 8. Clean Architecture for AI — Summary Checklist

When building an AI agent system, follow this checklist:

- [ ] **Core**: Domain models in Pydantic, interfaces as ABCs, no framework imports
- [ ] **Application**: Agents own ToolRegistries, use LLMProvider, call PromptFacade
- [ ] **Infrastructure**: One adapter per external system, implements Core interfaces
- [ ] **Presentation**: Thin HTTP layer (A2A servers), web UI, zero business logic
- [ ] **Prompts**: Versioned YAML, loaded via facade, never hardcoded strings
- [ ] **Telemetry**: Every tool/agent/LLM call wrapped in OpenInference spans
- [ ] **DI Container**: Single wiring point, swap any component in one line
- [ ] **Parallelism**: `asyncio.gather` for independent work, sequential for dependencies
- [ ] **Error Handling**: `return_exceptions=True`, partial results over total failure
- [ ] **Testing**: Mock ADK returns deterministic responses from real data
