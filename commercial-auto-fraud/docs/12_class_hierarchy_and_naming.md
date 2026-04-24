# Class Hierarchy & Naming Conventions — Complete Reference

This document maps every class in the project, explains WHY it's named that way, lists every method, and shows the inheritance/composition relationships.

---

## 1. Complete Class Hierarchy Diagram

```
ABC (Python Abstract Base Class)
│
├── IEnrichmentProvider (src/core/ports/data_provider.py)
│   │  WHY: "I" prefix = Interface. "Enrichment" = what it does. "Provider" = it provides data.
│   │  It's a PORT — defines WHAT data we need, not HOW to get it.
│   │
│   └── MockEnrichmentProvider (src/infrastructure/adapters/mock_apis.py)
│       WHY: "Mock" = fake implementation for development. Implements the interface with hardcoded data.
│       In production, you'd create "RealEnrichmentProvider" that calls actual SIU databases.
│
├── IStorageRepository (src/core/ports/repository.py)
│   │  WHY: "I" prefix = Interface. "Storage" = what it manages. "Repository" = design pattern name
│   │  (Repository Pattern = abstracts data persistence behind a clean interface).
│   │
│   └── LocalStorageRepository (src/infrastructure/adapters/local_storage.py)
│       WHY: "Local" = stores on local filesystem. "Storage" = what it does. "Repository" = pattern.
│       In production, you'd create "PostgresRepository" or "S3Repository".
│
├── BaseTool (src/infrastructure/tools/base_tool.py)
│   │  WHY: "Base" = abstract base class, not used directly. "Tool" = ADK concept — a function
│   │  an agent can call. Every tool in the system inherits this.
│   │
│   ├── [Enrichment Tools]
│   │   ├── ClaimantHistoryTool    WHY: Looks up claimant's history
│   │   ├── ProviderNetworkTool    WHY: Looks up provider's network data
│   │   ├── VehicleValuationTool   WHY: Looks up vehicle's market value
│   │   └── PolicyDetailsTool      WHY: Looks up policy inception/changes
│   │
│   ├── BasePatternTool (src/application/agents/analyzer/tools/base_pattern_tool.py)
│   │   │  WHY: "Base" = abstract, shared logic for all pattern analyzers.
│   │   │  "Pattern" = fraud detection pattern. Adds prompt-building + LLM-calling logic.
│   │   │
│   │   ├── DuplicateSimilarTool   WHY: Detects duplicate/similar claims
│   │   ├── SuspiciousTimingTool   WHY: Detects suspicious timing patterns
│   │   ├── InflatedAmountsTool    WHY: Detects inflated claim amounts
│   │   └── ProviderNetworkTool    WHY: Detects provider network anomalies
│   │       (Note: same name as enrichment tool but DIFFERENT class in different package)
│   │
│   ├── [Orchestrator Tools]
│   │   ├── IngestBatchTool        WHY: Ingests and validates a batch of claims
│   │   ├── EnrichClaimTool        WHY: Delegates enrichment to A2A agent
│   │   ├── AnalyzeFraudPatternsTool  WHY: Delegates analysis to A2A agent
│   │   ├── GenerateReportTool     WHY: Delegates report generation to A2A agent
│   │   └── QueryResultsTool       WHY: Handles SIU investigator queries
│   │
│   └── [Report Tools]
│       ├── CalculatePriorityTool  WHY: Calculates priority rank (P1-P4)
│       ├── FormatEvidenceTool     WHY: Formats evidence into Markdown table
│       └── FormatReportTool       WHY: Uses LLM to generate full Markdown report
│
├── BaseModel (Pydantic)
│   ├── Claimant                   WHY: Person who files an insurance claim
│   ├── Vehicle                    WHY: The vehicle involved in the loss
│   ├── Provider                   WHY: Repair shop / medical facility / attorney
│   ├── Claim                      WHY: A single insurance claim (the primary input)
│   ├── EnrichedClaimData          WHY: Claim + contextual data from enrichment
│   ├── EvidenceItem               WHY: One piece of fraud evidence
│   ├── PatternResult              WHY: Result of one pattern analysis
│   ├── FraudAnalysis              WHY: Combined result of all 4 patterns
│   ├── InvestigationReport        WHY: The final Markdown report
│   ├── UserProfile                WHY: SIU investigator profile (Kevin/Diana)
│   ├── BatchIngestionOutput       WHY: Output of batch validation step
│   ├── BatchPipelineOutput        WHY: Output of full pipeline run
│   └── ReportOutput               WHY: Output schema for report generator
│
└── Exception
    └── CommercialAutoFraudError   WHY: Base exception for this application
        ├── ValidationFailedError  WHY: Claim/batch validation failed
        ├── EnrichmentError        WHY: External data lookup failed
        └── AnalysisTimeoutError   WHY: Pattern analysis timed out

[Non-inheriting classes]
├── Agent (google/adk/__init__.py)        WHY: ADK concept — an AI agent with name, model, tools
├── LLMProvider (infrastructure/llm/)     WHY: Factory that creates/caches Agent instances
├── ToolRegistry (infrastructure/tools/)  WHY: DI container specifically for tools
├── PromptFacade (prompt_manager/engine/) WHY: Facade pattern — single access point for all prompts
├── Settings (config/settings.py)         WHY: Environment configuration values
├── Container (config/container.py)       WHY: DI container — wires all dependencies together
├── OrchestratorAgent                     WHY: Top-level pipeline coordinator
├── FraudEnrichmentAgent                  WHY: Data enrichment specialist
├── FraudPatternAnalyzer                  WHY: Fraud detection analyst
└── ReportGenerator                       WHY: Investigation report writer
```

---

## 2. Naming Convention Rules

### Rule 1: "I" Prefix = Interface (Abstract Contract)
```
IEnrichmentProvider  → "I want someone to provide enrichment data"
IStorageRepository   → "I want someone to handle storage"
```
WHY: The "I" prefix (from C#/Java tradition) immediately tells you "this is an interface, not a concrete class." You can't instantiate it — someone must implement it.

### Rule 2: "Base" Prefix = Abstract Base Class
```
BaseTool         → Shared logic for ALL tools (name, description, run/execute)
BasePatternTool  → Shared logic for pattern analyzer tools specifically
```
WHY: "Base" means "inherit from me." It contains shared logic that concrete classes extend.

### Rule 3: "Mock" Prefix = Fake Implementation
```
MockEnrichmentProvider → Fake external databases (returns hardcoded data)
```
WHY: "Mock" tells developers this is NOT the real implementation. It exists for development/testing.

### Rule 4: Agent Names = Their Job Title
```
FraudEnrichmentAgent     → "I enrich claims with fraud-relevant data"
FraudPatternAnalyzer     → "I analyze claims for fraud patterns"
ReportGenerator          → "I generate investigation reports"
OrchestratorAgent        → "I orchestrate the entire pipeline"
```

### Rule 5: Tool Names = Verb + Noun (What They Do)
```
lookup_claimant_history        → Looks up claimant history
lookup_provider_network        → Looks up provider network data
analyze_fraud_patterns         → Analyzes fraud patterns
calculate_priority_score       → Calculates priority score
format_evidence_summary        → Formats evidence into a summary
format_investigation_report    → Formats the investigation report
ingest_claim_batch             → Ingests a claim batch
generate_investigation_report  → Generates an investigation report
query_results                  → Queries stored results
```
WHY: Tool names are shown TO THE LLM. The LLM reads the name + description to decide which tool to call. Clear verb+noun names help the LLM make correct decisions.

### Rule 6: Service/Utility Names = What Domain They Serve
```
SIUQueryService      → Serves the SIU (Special Investigations Unit) query chat
UserProfileStore     → Stores and retrieves user profiles
```

---

## 3. Every Class — Every Method

### 3.1 Core Layer

#### `IEnrichmentProvider` — Port (Interface)
```python
class IEnrichmentProvider(ABC):
    # WHY 4 methods: Each maps to one external database system
    async def get_claimant_history(claimant_id) -> Dict     # ISO ClaimSearch / NICB
    async def get_provider_network(provider_id, type) -> Dict  # Provider licensing DB
    async def get_vehicle_valuation(vin, year, make, model) -> Dict  # KBB/NADA valuation
    async def get_policy_details(policy_number) -> Dict     # Policy admin system
```

#### `IStorageRepository` — Port (Interface)
```python
class IStorageRepository(ABC):
    # WHY 4 methods: CRUD for the two main data types we persist
    async def save_batch(batch_id, data) -> None            # Save pipeline results
    async def load_batch(batch_id) -> Dict                  # Load pipeline results
    async def save_investigation_report(claim_id, data) -> None  # Save one report
    async def load_investigation_report(claim_id) -> Dict   # Load one report
```

---

### 3.2 Infrastructure Layer

#### `BaseTool` — Abstract Tool Interface
```python
class BaseTool(ABC):
    @property name -> str           # Tool identifier (LLM sees this)
    @property description -> str    # Tool purpose (LLM reads this to decide usage)
    async def execute(**kwargs)     # Override this — your tool logic goes here
    async def run(**kwargs)         # Public API — wraps execute() in Arize TOOL span
    # WHY run() vs execute(): run() adds observability. Always call run(), never execute().
```

#### `BasePatternTool(BaseTool)` — Shared Pattern Analyzer Logic
```python
class BasePatternTool(BaseTool):
    def __init__(agent, pattern_key)  # agent=shared LLM, pattern_key="duplicate_similar"
    async def execute(enriched_claim) # Builds prompt → calls LLM → parses JSON response

    # Private helpers:
    _extract_pattern_data(key, enriched)  # Flattens enriched data into pattern-specific slice
    _parse_llm_response(raw, pattern)     # Parses LLM JSON into PatternResult dict
    # WHY separate: Each pattern needs different fields from the enriched data.
    # _extract_pattern_data selects ONLY relevant fields so the LLM prompt stays focused.
```

#### `ToolRegistry` — DI Container for Tools
```python
class ToolRegistry:
    def register(tool: BaseTool)     # Add tool by its .name property
    def get(name: str) -> BaseTool   # Retrieve tool (KeyError if not found)
    def list_tools() -> list[dict]   # [{name, description}] for agent cards
    def __len__() -> int             # Number of registered tools
    # WHY registry and not a dict: Provides logging on register, error messages on missing tools,
    # and a clean list_tools() for A2A agent cards.
```

#### `LLMProvider` — Singleton Factory
```python
class LLMProvider:
    def __init__()                   # Creates empty cache
    def get_agent(name, model, instruction) -> Agent  # Create or return cached Agent
    def list_agents() -> list[str]   # All agent names created so far
    # WHY singleton: The fraud_pattern_analyzer Agent is created ONCE and shared by 4 tools.
    # If each tool created its own Agent, we'd waste memory and lose caching benefits.

llm_provider = LLMProvider()  # Module-level singleton — import this everywhere
```

#### `MockEnrichmentProvider(IEnrichmentProvider)` — Fake External Databases
```python
class MockEnrichmentProvider:
    # Implements all 4 interface methods with deterministic mock data
    async def get_claimant_history(claimant_id)  # Returns prior claims, fraud flags
    async def get_provider_network(provider_id, type)  # Returns billing ratio, license
    async def get_vehicle_valuation(vin, year, make, model)  # Returns market value
    async def get_policy_details(policy_number)  # Returns inception date, changes
    # WHY 30KB file: Each method has realistic data mapped to specific claimant/provider IDs
    # from the test claims. This ensures consistent, reproducible test results.
```

#### `LocalStorageRepository(IStorageRepository)` — JSON File Storage
```python
class LocalStorageRepository:
    async def save_batch(batch_id, data)    # json.dump to fraud_data_store/claim_batches/
    async def load_batch(batch_id)           # json.load from fraud_data_store/claim_batches/
    async def save_investigation_report(claim_id, data)  # json.dump to investigation_reports/
    async def load_investigation_report(claim_id)         # json.load from investigation_reports/
    # WHY JSON files: Simplest possible persistence. No database setup needed for development.
    # Swap to PostgresRepository for production — change ONE line in container.py.
```

---

### 3.3 Application Layer — Agents

#### `OrchestratorAgent` — Pipeline Coordinator
```python
class OrchestratorAgent:
    agent_name = "fraud_pipeline_orchestrator"
    model = "gemini-2.5-pro"

    def __init__(enrichment_client, analyzer_client, report_client, storage)
        # WHY DI: Clients and storage injected so we can swap mock ↔ real
        # Creates: LLM agent via llm_provider, ToolRegistry with 5 tools

    async def process_claim_batch(batch_json_str) -> str
        # MODE 1: Non-conversational batch pipeline
        # WHY this method: Entry point for the pipeline button on the dashboard
        # Steps: validate → enrich each claim → analyze → generate reports → rank → save

    async def _process_single_claim(claim) -> dict
        # Private: Processes one claim through enrich → analyze → report
        # WHY private: Called N times in parallel by process_claim_batch()

    async def handle_query(query, persona) -> str
        # MODE 2: Conversational SIU query chat
        # WHY separate mode: Investigators need to ask questions AFTER the pipeline runs

    # WHY "Orchestrator": It doesn't do any analysis itself — it coordinates other agents.
    # Like a conductor who doesn't play instruments but coordinates the orchestra.
```

#### `FraudEnrichmentAgent` — Data Researcher
```python
class FraudEnrichmentAgent:
    agent_name = "claim_data_enrichment"
    model = "gemini-2.5-flash"  # WHY Flash: Data lookup is I/O-bound, not reasoning-heavy

    def __init__(data_provider)
        # WHY DI: data_provider implements IEnrichmentProvider (mock or real)
        # Creates: ToolRegistry with 4 lookup tools

    def list_tools() -> list[dict]
        # WHY: A2A agent card needs to list available tools

    async def run(claim: dict) -> dict
        # Runs all 4 lookup tools in PARALLEL via asyncio.gather
        # WHY parallel: All 4 lookups are independent I/O. No ordering dependency.
        # Returns: enriched claim with raw_claim + 4 data sections

    # WHY "Enrichment": It ENRICHES raw claims with additional context data.
    # A raw claim says "Marcus Rivera filed $42K claim." After enrichment:
    # "Marcus has 4 prior claims, 2 fraud flags, uses a provider under investigation..."
```

#### `FraudPatternAnalyzer` — Detective
```python
class FraudPatternAnalyzer:
    agent_name = "fraud_pattern_analyzer"
    model = "gemini-2.5-pro"  # WHY Pro: Pattern analysis needs strong reasoning

    def __init__()
        # Creates ONE shared LLM agent, registers 4 pattern tools
        # WHY shared agent: All 4 tools use the same model. Agent is stateless.

    def list_tools() -> list[dict]

    async def run(enriched_claim: dict) -> dict
        # Runs 4 patterns in PARALLEL, computes weighted composite score
        # Returns: {pattern_results, composite_score, priority_tier, confidence}

    # WHY "Analyzer" not "Detector": It ANALYZES evidence and produces nuanced scores,
    # not binary detect/don't-detect. A score of 45 vs 85 carries different meaning.
```

#### `ReportGenerator` — Writer
```python
class ReportGenerator:
    agent_name = "investigation_report_generator"
    model = "gemini-2.5-flash"  # WHY Flash: Report formatting, not analytical reasoning

    def __init__()
        # Creates ToolRegistry with 3 tools (2 deterministic + 1 LLM)

    def list_tools() -> list[dict]

    async def run(claim_id, fraud_analysis, enriched_data) -> str
        # Runs 3 tools SEQUENTIALLY:
        #   1. calculate_priority_score (deterministic)
        #   2. format_evidence_summary  (deterministic)
        #   3. format_investigation_report (LLM)
        # WHY sequential: Tool 3 needs output from Tools 1 and 2

    # WHY "Generator" not "Writer": It GENERATES structured output from data,
    # not creative writing. The report format is deterministic — only narrative varies.
```

---

### 3.4 Presentation Layer

#### `A2AEnrichmentClient` — HTTP Client
```python
class A2AEnrichmentClient:
    def __init__(url="http://localhost:8002")
    async def enrich(claim: dict) -> dict
        # Sends A2A task to enrichment server, returns enriched claim
        # Injects traceparent header for distributed tracing
    # WHY separate class: Encapsulates HTTP transport. If we switch to gRPC, only this changes.
```

#### `A2AAnalyzerClient` — HTTP Client
```python
class A2AAnalyzerClient:
    def __init__(url="http://localhost:8003")
    async def analyze(enriched_claim: dict) -> dict
```

#### `A2AReportGeneratorClient` — HTTP Client
```python
class A2AReportGeneratorClient:
    def __init__(url="http://localhost:8004")
    async def generate_report(claim_id, fraud_analysis, enriched_data) -> str
```

---

### 3.5 Configuration

#### `Settings` — Environment Config
```python
class Settings:
    default_model: str           # Which LLM model to use by default
    orchestrator_model: str      # Model for orchestrator agent
    enrichment_model: str        # Model for enrichment agent
    analyzer_model: str          # Model for analyzer agent
    report_model: str            # Model for report generator
    gemini_api_key: str          # Gemini API key (empty = use mock)
    arize_space_id: str          # Arize workspace ID
    arize_api_key: str           # Arize API key
    orchestrator_port: int       # Port 8001
    enrichment_port: int         # Port 8002
    analyzer_port: int           # Port 8003
    report_port: int             # Port 8004
    report_score_threshold: float  # Minimum score to generate report (40.0)
    high_tier_threshold: float   # High tier boundary (60.0)
    critical_tier_threshold: float  # Critical tier boundary (80.0)

settings = Settings()  # Module-level singleton
# WHY class not dict: Type hints, IDE autocomplete, validation
```

#### `Container` — Dependency Injection Wiring
```python
class Container:
    def __init__():
        self.storage = LocalStorageRepository()       # Could be PostgresRepository
        self.data_provider = MockEnrichmentProvider()  # Could be RealEnrichmentProvider
        self.enrichment_client = A2AEnrichmentClient()
        self.analyzer_client = A2AAnalyzerClient()
        self.report_client = A2AReportGeneratorClient()
        self.orchestrator = OrchestratorAgent(...)     # Everything injected here

    # WHY Container: ONE place where all dependencies are wired.
    # To change ANY component, you change ONE line here. No other file changes.
    # This is the Composition Root pattern from DI literature.
```

---

### 3.6 Prompt Manager

#### `PromptFacade` — Facade Pattern
```python
class PromptFacade:
    @classmethod get_prompt(template_name, context, version) -> str
        # Load YAML → fallback to Python → format with context variables
        # WHY classmethod: No instance needed. Stateless utility.

    @classmethod get_last_usage() -> dict
        # Returns {template, version, timestamp} for Arize span attributes

    @classmethod get_usage_log() -> list
        # Full audit trail of all prompt usages in this session

    @classmethod list_prompts() -> list[str]
        # All registered prompt keys

    @classmethod get_version_info(template_name) -> dict
        # YAML metadata (version, description, agent, model)

    # WHY "Facade": Facade pattern = one simple interface hiding complex internals.
    # Behind PromptFacade: YAML loading, version resolution, caching, fallback logic,
    # variable interpolation, usage logging. Callers just call get_prompt().
```

---

## 4. Composition Relationships (Who Uses Whom)

```
Container
├── creates → LocalStorageRepository
├── creates → MockEnrichmentProvider
├── creates → A2AEnrichmentClient
├── creates → A2AAnalyzerClient
├── creates → A2AReportGeneratorClient
└── creates → OrchestratorAgent
                ├── uses → LLMProvider.get_agent()
                ├── owns → ToolRegistry
                │           ├── IngestBatchTool
                │           ├── EnrichClaimTool ──uses──→ A2AEnrichmentClient
                │           ├── AnalyzeFraudPatternsTool ──uses──→ A2AAnalyzerClient
                │           ├── GenerateReportTool ──uses──→ A2AReportGeneratorClient
                │           └── QueryResultsTool
                └── uses → PromptFacade

FraudEnrichmentAgent (created by server_enrichment.py)
├── uses → LLMProvider.get_agent()
├── owns → ToolRegistry
│           ├── ClaimantHistoryTool ──uses──→ IEnrichmentProvider
│           ├── ProviderNetworkTool ──uses──→ IEnrichmentProvider
│           ├── VehicleValuationTool ──uses──→ IEnrichmentProvider
│           └── PolicyDetailsTool ──uses──→ IEnrichmentProvider
└── uses → PromptFacade

FraudPatternAnalyzer (created by server_analyzer.py)
├── uses → LLMProvider.get_agent() → creates ONE shared Agent
├── owns → ToolRegistry
│           ├── DuplicateSimilarTool ──uses──→ shared Agent
│           ├── SuspiciousTimingTool ──uses──→ shared Agent
│           ├── InflatedAmountsTool ──uses──→ shared Agent
│           └── ProviderNetworkTool ──uses──→ shared Agent
└── uses → PromptFacade

ReportGenerator (created by server_report.py)
├── uses → LLMProvider.get_agent()
├── owns → ToolRegistry
│           ├── CalculatePriorityTool (no LLM)
│           ├── FormatEvidenceTool (no LLM)
│           └── FormatReportTool ──uses──→ Agent
└── uses → PromptFacade
```
