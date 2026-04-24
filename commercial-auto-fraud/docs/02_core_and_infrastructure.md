# Core & Infrastructure Layer — Detailed Documentation

This document covers the two innermost layers: **Core** (domain models, ports) and **Infrastructure** (adapters, tools, telemetry, LLM provider).

---

## 1. Core Layer (`src/core/`)

The core layer has **zero external dependencies**. It defines what the system IS (domain models) and what it NEEDS (ports/interfaces), but never HOW those needs are fulfilled.

### 1.1 `models.py` — Domain Models (Pydantic)

Every data structure that flows through the pipeline is defined here as a Pydantic `BaseModel`. Pydantic provides automatic validation, serialization, and type safety.

#### Models Defined:

| Model | Fields | Purpose |
|-------|--------|---------|
| `Claimant` | `id`, `name` | Person who filed the claim |
| `Vehicle` | `vin`, `year`, `make`, `model` | Vehicle involved in the loss |
| `Provider` | `id`, `name`, `type` | Repair shop, medical provider, or attorney |
| `Claim` | `claim_id`, `claimant`, `vehicle`, `provider`, `policy_number`, `loss_date`, `report_date`, `claimed_amount`, `loss_description` | A single insurance claim — the primary input |
| `EnrichedClaimData` | `claim_id`, `raw_claim`, `claimant_history`, `provider_network`, `vehicle_valuation`, `policy_details`, `enrichment_status` | Claim + contextual data from 4 enrichment tools |
| `EvidenceItem` | `indicator`, `value`, `benchmark`, `severity`, `source` | One piece of fraud evidence (e.g., "billing_ratio = 2.96x, benchmark < 1.5x") |
| `PatternResult` | `pattern`, `score`, `severity`, `evidence[]`, `reasoning`, `exculpatory_factors[]` | Output of one fraud pattern analysis |
| `FraudAnalysis` | `claim_id`, `pattern_results{}`, `composite_score`, `confidence`, `priority_tier`, `patterns_flagged` | Aggregated result of all 4 pattern analyses |
| `InvestigationReport` | `claim_id`, `report_markdown` | The final Markdown investigation report |
| `UserProfile` | `name`, `role`, `experience_level`, `preferred_detail_level` | SIU investigator profile (Kevin or Diana) |

#### Data Flow Through Models:
```
Claim (raw input)
  → EnrichedClaimData (after enrichment tools)
    → PatternResult × 4 (after each pattern analyzer)
      → FraudAnalysis (composite score + tier)
        → InvestigationReport (if score ≥ 40)
```

### 1.2 `exceptions.py` — Custom Exception Hierarchy

```python
CommercialAutoFraudError           # Base exception (catch-all)
├── ValidationFailedError          # Claim/batch fails validation
├── EnrichmentError                # Mock API lookup fails
└── AnalysisTimeoutError           # Pattern analysis times out
```

Each exception maps to a specific pipeline stage. The orchestrator catches these to implement graceful degradation — if one claim fails enrichment, the rest of the batch continues.

### 1.3 `ports/` — Interfaces (Abstract Base Classes)

Ports define **what the application needs** without specifying **how**. This is the Dependency Inversion Principle (the "D" in SOLID).

#### `data_provider.py` — `IEnrichmentProvider`

```python
class IEnrichmentProvider(ABC):
    async def get_claimant_history(claimant_id: str) -> Dict
    async def get_provider_network(provider_id: str, provider_type: str) -> Dict
    async def get_vehicle_valuation(vin: str, year: int, make: str, model: str) -> Dict
    async def get_policy_details(policy_number: str) -> Dict
```

**Implementation**: `MockEnrichmentProvider` (in `infrastructure/adapters/mock_apis.py`)
**Future**: Could be swapped to real ISO ClaimSearch API, NICB database, etc.

#### `repository.py` — `IStorageRepository`

```python
class IStorageRepository(ABC):
    async def save_batch(batch_id: str, data: Dict) -> None
    async def load_batch(batch_id: str) -> Dict
    async def save_investigation_report(claim_id: str, report_data: Dict) -> None
    async def load_investigation_report(claim_id: str) -> Dict
```

**Implementation**: `LocalStorageRepository` (JSON files in `fraud_data_store/`)
**Future**: Could be swapped to PostgreSQL, MongoDB, S3, etc.

---

## 2. Infrastructure Layer (`src/infrastructure/`)

The infrastructure layer implements the interfaces defined in Core. It handles all external concerns: LLM calls, file storage, mock databases, telemetry.

### 2.1 `llm/provider.py` — LLMProvider (Singleton Factory)

```python
class LLMProvider:
    def get_agent(name, model, instruction) -> Agent
    def list_agents() -> list[str]

llm_provider = LLMProvider()  # Module-level singleton
```

**What it does**: Creates and caches `google.adk.Agent` instances. Every agent in the system gets its LLM through this factory — never by calling `Agent()` directly.

**Why singleton**: Each agent name maps to exactly one Agent instance. The `fraud_pattern_analyzer` agent is created once and shared across all 4 pattern tools (it's stateless).

**How to swap to real Gemini**: Change the import `from google.adk import Agent` to the real Google ADK client. Zero changes needed in any agent module.

### 2.2 `adapters/mock_apis.py` — MockEnrichmentProvider

This is a **30KB file** that simulates 4 external databases. It implements `IEnrichmentProvider` and returns realistic fraud-relevant data based on the claim's claimant ID, provider ID, VIN, and policy number.

**Functions** (each mapped to a claimant/provider/vehicle/policy):
- `get_claimant_history()` — Returns prior claims, fraud flags, claim frequency
- `get_provider_network()` — Returns billing ratio, license status, referral connections
- `get_vehicle_valuation()` — Returns market value, repair benchmarks, VIN history
- `get_policy_details()` — Returns inception date, policy changes, lapse history

**Design**: Uses deterministic hash-based logic to generate consistent data per ID, ensuring the same claim always gets the same enrichment data.

### 2.3 `adapters/local_storage.py` — LocalStorageRepository

```python
class LocalStorageRepository(IStorageRepository):
    async def save_batch(batch_id, data)    # Writes to fraud_data_store/claim_batches/{id}.json
    async def load_batch(batch_id)           # Reads from fraud_data_store/claim_batches/{id}.json
    async def save_investigation_report(claim_id, data)  # fraud_data_store/investigation_reports/{id}.json
    async def load_investigation_report(claim_id)         # fraud_data_store/investigation_reports/{id}.json
```

Simple JSON file persistence. In production, swap this with a database adapter — the application layer won't know or care.

### 2.4 `tools/base_tool.py` — BaseTool (Abstract Tool Interface)

Every tool in the system inherits from `BaseTool`:

```python
class BaseTool(ABC):
    @property
    def name(self) -> str: ...        # Tool identifier (e.g., "lookup_claimant_history")
    @property
    def description(self) -> str: ... # Description shown to the LLM
    async def execute(self, **kwargs): ... # The actual tool logic (override this)
    async def run(self, **kwargs):    # Public entry — wraps execute() in Arize TOOL span
```

**Critical pattern**: Always call `tool.run()`, never `tool.execute()` directly. The `run()` method wraps `execute()` in an OpenTelemetry TOOL span, so every tool invocation appears in the Arize AX trace.

### 2.5 `tools/registry.py` — ToolRegistry (DI for Tools)

```python
class ToolRegistry:
    def register(tool: BaseTool)     # Register by tool.name
    def get(name: str) -> BaseTool   # Retrieve by name (raises KeyError if missing)
    def list_tools() -> list[dict]   # Returns [{name, description}, ...] for agent cards
```

**Pattern**: Each agent creates its own `ToolRegistry` and registers its tools at `__init__` time. The agent never instantiates tools inline — it always goes through the registry.

**Adding a new tool**: (1) Subclass `BaseTool`, (2) `registry.register(YourTool())` in the agent's `__init__`. Done.

### 2.6 `telemetry/arize_wrappers.py` — OpenTelemetry + Arize AX

This module provides **manual OpenInference-compliant span instrumentation**. No auto-instrumentors (FastAPI/HTTPX) — only meaningful agent-level spans.

#### Setup (`setup_telemetry()`)
- Creates a `TracerProvider` with project name `commercial-auto-fraud-pipeline`
- If `ARIZE_SPACE_ID` and `ARIZE_API_KEY` are set in `.env`, exports spans to Arize AX via OTLP
- Returns a module-level `tracer` singleton

#### Span Types (3 context managers):

| Function | Span Kind | When Used |
|----------|-----------|-----------|
| `span_chain(name)` | `CHAIN` | Orchestrator pipeline, claim pipeline, agent-level workflows |
| `span_tool(name)` | `TOOL` | Every `BaseTool.run()` call, A2A server handlers |
| `span_llm(name, model)` | `LLM` | Every `Agent.run(prompt)` call (LLM inference) |

#### Decorators:

| Decorator | What It Does |
|-----------|-------------|
| `@trace_llm_call` | Wraps `Agent.run()` in an LLM span with agent name + model |
| `@trace_agent_step(name, kind)` | Wraps any async method in a CHAIN or TOOL span |

#### Resulting Trace Hierarchy:
```
CHAIN: Orchestrator: Batch Pipeline
  TOOL: ingest_claim_batch
  CHAIN: Claim Pipeline [CLM-2026-001]
    TOOL: Claim Data Enrichment Agent [CLM-2026-001]
      TOOL: Tool: lookup_claimant_history
      TOOL: Tool: lookup_provider_network
      TOOL: Tool: lookup_vehicle_valuation
      TOOL: Tool: lookup_policy_details
    CHAIN: Fraud Pattern Analyzer [CLM-2026-001]
      LLM: duplicate_similar_analyzer.run
      LLM: suspicious_timing_analyzer.run
      LLM: inflated_amounts_analyzer.run
      LLM: provider_network_analyzer.run
    CHAIN: Investigation Report Generator [CLM-2026-001]
      LLM: investigation_report_generator.run
```
