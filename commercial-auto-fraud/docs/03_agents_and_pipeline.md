# Agents & Pipeline — Detailed Documentation

This document covers all 4 AI agents, their tools, and how they work together in the pipeline.

---

## 1. Agent Architecture Pattern

Every agent in this system follows the same structural pattern:

```
agent_module/
├── agent.py       # Agent class — owns a ToolRegistry, coordinates tools
├── schemas.py     # Pydantic input/output schemas for validation
└── tools/         # Individual tools (each inherits BaseTool)
    ├── tool_a.py
    ├── tool_b.py
    └── ...
```

**Agent responsibilities**:
- Create an LLM instance via `LLMProvider`
- Register tools in a `ToolRegistry`
- Expose `async run()` as the main entry point
- Coordinate tool execution (parallel or sequential)

**An agent does NOT**:
- Import other agents directly (communicates via A2A HTTP)
- Hardcode LLM model names (uses `LLMProvider`)
- Hardcode prompts (uses `PromptFacade`)

---

## 2. Agent 1: Fraud Pipeline Orchestrator

**File**: `src/application/agents/orchestrator/agent.py`
**Name**: `fraud_pipeline_orchestrator`
**Model**: `gemini-2.5-pro`
**Mode**: Dual — Batch Pipeline (non-conversational) + SIU Query Chat (conversational)

### What It Does
The Orchestrator is the **top-level coordinator**. It doesn't do fraud analysis itself — it delegates to the other 3 agents via A2A HTTP calls and aggregates results.

### Tools (5):

| Tool | File | Type | What It Does |
|------|------|------|-------------|
| `ingest_claim_batch` | `tools/ingest_batch.py` | Deterministic | Validates N claims against Pydantic schemas |
| `enrich_claim` | `tools/pipeline_tools.py` | A2A HTTP | Calls Enrichment Agent on :8002 |
| `analyze_fraud_patterns` | `tools/pipeline_tools.py` | A2A HTTP | Calls Analyzer Agent on :8003 |
| `generate_investigation_report` | `tools/pipeline_tools.py` | A2A HTTP | Calls Report Generator on :8004 |
| `query_results` | `tools/pipeline_tools.py` | In-memory | Answers SIU investigator queries |

### `ingest_claim_batch` — Validation Logic

The `IngestBatchTool` uses an internal `_ClaimValidator` class:

**Required fields**: `claim_id`, `claimant`, `provider`, `vehicle`, `policy_number`, `claimed_amount`, `loss_date`

**Validation rules**:
- `claimed_amount` must be numeric and > 0
- `loss_date` must be YYYY-MM-DD format and not in the future
- `claimant` must have `id` and `name`
- `vehicle` must have `vin`
- `provider` must have `id`

Invalid claims are logged but do NOT block valid claims from processing.

### Pipeline Execution (`process_claim_batch`)

```python
async def process_claim_batch(batch_json_str):
    # 1. Validate batch
    ingestion = await registry.get("ingest_claim_batch").run(batch_json=batch_json_str)

    # 2. Process each valid claim in PARALLEL (Level-1 parallelism)
    tasks = [_process_single_claim(claim) for claim in valid_claims]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Sort by composite score (highest first)
    # 4. Save to storage
    # 5. Return JSON results
```

### Single Claim Pipeline (`_process_single_claim`)

```python
async def _process_single_claim(claim):
    # Step 1: Enrich (HTTP → :8002)
    enriched = await registry.get("enrich_claim").run(claim=claim)

    # Step 2: Analyze 4 patterns (HTTP → :8003, patterns run in parallel inside)
    fraud_analysis = await registry.get("analyze_fraud_patterns").run(enriched_claim=enriched)

    # Step 3: Generate report IF score >= 40 (HTTP → :8004)
    report = None
    if fraud_analysis["composite_score"] >= 40:
        report = await registry.get("generate_investigation_report").run(...)

    return {"claim_id": ..., "enriched": ..., "fraud_analysis": ..., "report": ...}
```

### SIU Query Chat (`handle_query`)

The query tool supports 6 query types, adapting response style based on the user persona (Kevin = verbose, Diana = concise):

| Query Type | Example | Response |
|-----------|---------|----------|
| Pipeline Status | "How many claims processed?" | Progress: "6/8 claims complete" |
| Batch Summary | "Show results" | Tier breakdown, top scores, statistics |
| Claim Drill-Down | "Tell me about CLM-2026-001" | Full detail: score, patterns, evidence |
| Pattern Query | "Which claims had timing flags?" | Filtered claim list |
| Provider Query | "Which providers appear multiple times?" | Provider frequency analysis |
| Explanation | "How is the score calculated?" | Educational explanation |

### Schemas (`orchestrator/schemas.py`)

- `BatchIngestionOutput` — Validation results (valid/invalid claim lists)
- `BatchPipelineOutput` — Final pipeline output (all results + statistics)

---

## 3. Agent 2: Claim Data Enrichment Agent

**File**: `src/application/agents/enrichment/agent.py`
**Name**: `claim_data_enrichment`
**Model**: `gemini-2.5-flash` (speed-critical — runs N times per batch)
**Mode**: Non-conversational, task-based

### What It Does
Takes a raw claim and augments it with contextual data from 4 external data sources (mocked). This is pure **data retrieval** — no fraud scoring happens here.

### Tools (4, all run in PARALLEL):

| Tool | File | Data Retrieved | Fraud Relevance |
|------|------|---------------|----------------|
| `lookup_claimant_history` | `tools/claimant_history.py` | Prior claims, fraud flags, claim frequency | Serial claimants, prior fraud involvement |
| `lookup_provider_network` | `tools/provider_network.py` | Billing ratio, license status, referral rings | Inflated billing, suspicious provider networks |
| `lookup_vehicle_valuation` | `tools/vehicle_valuation.py` | Market value, repair benchmarks, VIN history | Claims exceeding vehicle value |
| `lookup_policy_details` | `tools/policy_details.py` | Inception date, policy changes, lapse history | New-policy fraud, suspicious changes |

### Execution Pattern
```python
async def run(claim: dict) -> dict:
    # All 4 lookups are independent I/O — run concurrently
    (claimant_history, provider_network, vehicle_valuation, policy_details) = \
        await asyncio.gather(
            registry.get("lookup_claimant_history").run(claimant_id=...),
            registry.get("lookup_provider_network").run(provider_id=...),
            registry.get("lookup_vehicle_valuation").run(vin=...),
            registry.get("lookup_policy_details").run(policy_number=...),
        )

    return {
        "claim_id": ...,
        "raw_claim": claim,           # Original claim preserved
        "claimant_history": ...,       # Tool 1 output
        "provider_network": ...,       # Tool 2 output
        "vehicle_valuation": ...,      # Tool 3 output
        "policy_details": ...,         # Tool 4 output
        "enrichment_status": "complete",
    }
```

### Tool Implementation (Example: `ClaimantHistoryTool`)

```python
class ClaimantHistoryTool(BaseTool):
    name = "lookup_claimant_history"
    description = "Retrieves the claimant's full claim history..."

    def __init__(self, provider):       # DI: provider injected, not imported
        self._provider = provider

    async def execute(self, claimant_id):
        result = await self._provider.get_claimant_history(claimant_id)
        result.setdefault("total_prior_claims", 0)  # Schema-safe defaults
        return result
```

All 4 tools follow this exact pattern — delegate to the injected `IEnrichmentProvider`, add safe defaults.

---

## 4. Agent 3: Fraud Pattern Analyzer

**File**: `src/application/agents/analyzer/agent.py`
**Name**: `fraud_pattern_analyzer`
**Model**: `gemini-2.5-pro` (analytical reasoning — needs the strongest model)
**Mode**: Non-conversational, task-based

### What It Does
The analytical core. For each enriched claim, runs 4 independent fraud pattern analyses **in parallel** (Level-2 parallelism), then computes a weighted composite score.

### Tools (4 pattern analyzers, all run in PARALLEL):

| Tool | Pattern | Weight | What It Detects |
|------|---------|--------|----------------|
| `duplicate_similar_analyzer` | Duplicate/Similar Claims | 30% | Same VIN on multiple claims, overlapping dates, matching descriptions |
| `suspicious_timing_analyzer` | Suspicious Timing | 20% | Claim within 30 days of policy inception, weekend staging, post-upgrade claims |
| `inflated_amounts_analyzer` | Inflated Amounts | 25% | Repair > vehicle value, billing > 2x regional benchmark |
| `provider_network_analyzer` | Provider Network | 25% | Provider on >15% of claims, circular referrals, suspended license |

### The BasePatternTool (`tools/base_pattern_tool.py`)

All 4 pattern tools inherit from `BasePatternTool`, which handles the heavy lifting:

```python
class BasePatternTool(BaseTool):
    def __init__(self, agent, pattern_key):
        self._agent = agent          # Shared LLM agent
        self.pattern_key = pattern_key  # e.g., "duplicate_similar"

    async def execute(self, enriched_claim):
        # 1. Extract pattern-specific data slice from enriched claim
        data_slice = _extract_pattern_data(self.pattern_key, enriched_claim)

        # 2. Load versioned CoT prompt from YAML
        prompt = PromptFacade.get_prompt(f"{self.pattern_key}_cot", context={
            "claim_id": ..., "enriched_data": data_slice, ...
        })

        # 3. Send to LLM (mock or real Gemini)
        raw = await self._agent.run(prompt)

        # 4. Parse JSON response → PatternResult
        return self._parse_llm_response(raw, self.pattern_key)
```

#### `_extract_pattern_data()` — Data Flattening

This function takes the nested enriched claim and extracts **only the fields relevant to each pattern**, flattening them into a simple JSON dict:

| Pattern | Fields Extracted |
|---------|-----------------|
| `duplicate_similar` | `claim_id`, `claimant_id`, `vehicle_vin`, `loss_type`, `loss_date`, `total_prior_claims`, `prior_fraud_flags`, `prior_claims[]` |
| `suspicious_timing` | `claim_id`, `loss_date`, `days_since_inception`, `recent_policy_changes[]`, `lapse_history[]` |
| `inflated_amounts` | `claim_id`, `claimed_amount`, `market_value`, `regional_repair_benchmarks`, `billing_ratio` |
| `provider_network` | `claim_id`, `provider_name`, `license_status`, `billing_ratio`, `flagged_claims_count`, `referral_connections[]` |

### Composite Score Calculation

```python
WEIGHTS = {
    "duplicate_similar": 0.30,
    "suspicious_timing": 0.20,
    "inflated_amounts":  0.25,
    "provider_network":  0.25,
}

composite_score = sum(
    result["score"] * WEIGHTS[pattern]
    for pattern, result in pattern_results.items()
)

# Tier assignment:
# Critical: 80-100 | High: 60-79 | Medium: 40-59 | Low: 0-39
```

### Concrete Tool Example (`duplicate_similar.py`)
```python
class DuplicateSimilarTool(BasePatternTool):
    name = "duplicate_similar_analyzer"
    description = "Detects claims identical or suspiciously similar..."

    def __init__(self, agent):
        super().__init__(agent=agent, pattern_key="duplicate_similar")
```

That's it — 4 lines. All logic lives in `BasePatternTool`.

---

## 5. Agent 4: Investigation Report Generator

**File**: `src/application/agents/report_generator/agent.py`
**Name**: `investigation_report_generator`
**Model**: `gemini-2.5-flash` (formatting task — speed over reasoning)
**Mode**: Non-conversational, task-based

### What It Does
Generates a structured 7-section Markdown investigation report for claims scoring ≥ 40. Only called for Medium, High, and Critical tier claims.

### Tools (3, run SEQUENTIALLY — each feeds the next):

| Order | Tool | Type | What It Does |
|-------|------|------|-------------|
| 1st | `calculate_priority_score` | Deterministic | Computes priority rank (P1-Immediate to P4-Monitor) and estimated financial exposure |
| 2nd | `format_evidence_summary` | Deterministic | Builds a Markdown evidence table from all pattern results |
| 3rd | `format_investigation_report` | LLM (Flash) | Sends fraud analysis + evidence table + priority to the LLM to generate the full report |

### Why Sequential (Not Parallel)?
Tools 1 and 2 are **pre-processors** for Tool 3. Their outputs are injected into the LLM prompt so the model doesn't have to re-derive or re-format evidence — it just narrates and structures.

### Report Sections Generated:
1. **Case Header** — Claim ID, claimant, score, tier, confidence
2. **Executive Summary** — 2-3 sentence overview
3. **Pattern Analysis Detail** — Per-pattern sub-score + evidence
4. **Evidence Summary Table** — All evidence items with benchmarks
5. **Recommended Actions** — Specific investigative steps
6. **Risk Factors** — Top indicators ranked by severity
7. **Claimant & Provider Profile** — Background context

### `calculate_priority_score` Logic:
```python
if fraud_score >= 90 and claim_amount >= 50000:  priority = "P1-Immediate"
elif fraud_score >= 75:                           priority = "P1-Immediate"
elif fraud_score >= 60:                           priority = "P2-Urgent"
elif fraud_score >= 40:                           priority = "P3-Standard"
else:                                             priority = "P4-Monitor"

estimated_exposure = claim_amount * (fraud_score / 100)
```

---

## 6. Dual-Level Parallelism

The pipeline uses two levels of `asyncio.gather`:

```
Level 1 (Orchestrator): Process N claims in parallel
├── Claim 1 ──┐
├── Claim 2 ──┤ asyncio.gather (N concurrent claim pipelines)
├── Claim 3 ──┤
└── Claim N ──┘
    │
    └── Per claim:
        Level 2 (Analyzer): 4 patterns in parallel
        ├── Duplicate/Similar ──┐
        ├── Suspicious Timing ──┤ asyncio.gather (4 concurrent analyses)
        ├── Inflated Amounts  ──┤
        └── Provider Network  ──┘
```

For a batch of 12 claims with 4 patterns each, this means up to **48 concurrent operations** instead of 48 sequential ones.
