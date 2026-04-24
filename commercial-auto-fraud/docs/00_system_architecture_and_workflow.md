# Commercial Auto Fraud Detection — System Architecture & Workflow

> **Use this document to explain the entire system to anyone** — professors, interviewers, teammates, or stakeholders. Every design decision is justified with a "why."

---

## 1. The Problem We're Solving

Insurance companies lose **$80 billion annually** to fraud. A Special Investigations Unit (SIU) receives hundreds of claims weekly and must decide which ones deserve investigation. Currently:

- Analysts manually review claims one-by-one (slow, inconsistent)
- Rule-based systems generate too many false positives (85%+ noise)
- Cross-claim patterns (same provider on 20 claims) are invisible when reviewing individually
- Junior analysts miss red flags that experienced investigators would catch

### Our Solution
An **AI-powered multi-agent pipeline** that:
1. Takes a batch of insurance claims
2. Enriches each claim with contextual intelligence from external databases
3. Runs 4 independent fraud pattern analyses using LLM-based reasoning
4. Produces a composite fraud score (0-100) with evidence
5. Generates investigation reports for flagged claims
6. Presents results on a dashboard with a natural language query interface

---

## 2. High-Level System Architecture

```
                    ┌──────────────────────────────────────┐
                    │           SIU INVESTIGATOR            │
                    │     (Kevin — Junior Analyst)          │
                    │     (Diana — Senior SIU Lead)         │
                    └──────────────┬───────────────────────┘
                                   │ Browser
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                               │
│                                                                      │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐    │
│  │   Web Dashboard      │    │   A2A Protocol Layer              │    │
│  │   (Port 8001)        │    │                                    │    │
│  │   FastAPI + HTML/JS  │    │  ┌──────────┐ ┌────────┐ ┌──────┐│    │
│  │                      │    │  │Enrichment│ │Analyzer│ │Report││    │
│  │   • Pipeline trigger │    │  │Server    │ │Server  │ │Server││    │
│  │   • Claim cards      │    │  │:8002     │ │:8003   │ │:8004 ││    │
│  │   • SIU query chat   │    │  └──────────┘ └────────┘ └──────┘│    │
│  └─────────────────────┘    └──────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  ORCHESTRATOR AGENT (fraud_pipeline_orchestrator)             │    │
│  │  Model: gemini-2.5-pro | Tools: 5                            │    │
│  │                                                               │    │
│  │  Tool 1: ingest_claim_batch      (validate N claims)         │    │
│  │  Tool 2: enrich_claim            (delegate to Agent 2)       │    │
│  │  Tool 3: analyze_fraud_patterns  (delegate to Agent 3)       │    │
│  │  Tool 4: generate_report         (delegate to Agent 4)       │    │
│  │  Tool 5: query_results           (SIU chat interface)        │    │
│  └──────────────────────┬───────────────────────────────────────┘    │
│                         │ HTTP (A2A Protocol)                        │
│         ┌───────────────┼───────────────┐                            │
│         ▼               ▼               ▼                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ ENRICHMENT  │ │  ANALYZER   │ │   REPORT    │                   │
│  │ AGENT       │ │  AGENT      │ │ GENERATOR   │                   │
│  │ Flash model │ │ Pro model   │ │ Flash model │                   │
│  │ 4 tools     │ │ 4 tools     │ │ 3 tools     │                   │
│  │ (parallel)  │ │ (parallel)  │ │ (sequential)│                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  SERVICES                                                     │    │
│  │  • SIU Query Service (persona-adaptive chat)                  │    │
│  │  • User Profile Store (Kevin/Diana profiles)                  │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                             │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ LLM Provider │ │ Mock APIs    │ │ Local Storage│ │ Telemetry  │ │
│  │ (Agent       │ │ (simulated   │ │ (JSON files) │ │ (Arize AX) │ │
│  │  factory)    │ │  databases)  │ │              │ │            │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐                                  │
│  │ BaseTool     │ │ ToolRegistry │                                  │
│  │ (abstract)   │ │ (DI for      │                                  │
│  │              │ │  tools)      │                                  │
│  └──────────────┘ └──────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     CORE LAYER (innermost — zero dependencies)       │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ Domain Models│ │ Ports        │ │ Exceptions   │                │
│  │ (Pydantic)   │ │ (Interfaces) │ │              │                │
│  │ Claim,       │ │ IEnrichment  │ │ Validation   │                │
│  │ FraudAnalysis│ │ IStorage     │ │ Enrichment   │                │
│  │ PatternResult│ │ Repository   │ │ Timeout      │                │
│  └──────────────┘ └──────────────┘ └──────────────┘                │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     CROSS-CUTTING CONCERNS                           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  PROMPT MANAGER (versioned YAML prompts + PromptFacade)      │    │
│  │  11 templates: 4 CoT analyzers, 1 ReAct enrichment,          │    │
│  │  1 report, 1 orchestrator system, 2 persona, 2 classifiers   │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. End-to-End Workflow

### Phase 1: System Startup

```
python src/main.py
│
├── Thread 1: server_enrichment.py starts on :8002
│   └── Creates FraudEnrichmentAgent (4 lookup tools, Flash model)
│
├── Thread 2: server_analyzer.py starts on :8003
│   └── Creates FraudPatternAnalyzer (4 pattern tools, Pro model)
│
├── Thread 3: server_report.py starts on :8004
│   └── Creates ReportGenerator (3 report tools, Flash model)
│
└── Main Thread: app.py starts on :8001
    └── Container() creates OrchestratorAgent with 3 A2A HTTP clients
```

**Why 4 separate servers?** Each agent is an independent microservice. This means:
- They can be deployed on different machines for scale
- A bug in the report generator doesn't crash the analyzer
- Each can be updated, tested, and monitored independently

### Phase 2: Pipeline Execution

When the investigator clicks **"Run Weekly Claim Batch"**:

```
Step 1: INGEST & VALIDATE
─────────────────────────
Dashboard → GET /api/run → OrchestratorAgent.process_claim_batch()
│
├── Reads weekly_auto_claims.json (12 claims)
└── IngestBatchTool validates each claim:
    ✓ Required fields present (claim_id, claimant, vehicle, provider...)
    ✓ claimed_amount > 0 and numeric
    ✓ loss_date is valid YYYY-MM-DD, not in the future
    ✓ claimant has id + name, vehicle has VIN, provider has id
    │
    Result: 12 valid, 0 invalid

Step 2: PARALLEL CLAIM PROCESSING (12 claims simultaneously)
─────────────────────────────────────────────────────────────
asyncio.gather(*[process_single_claim(claim) for claim in 12_claims])
│
│  For EACH claim (e.g., CLM-2026-001):
│  │
│  ├── Step 2a: ENRICH (HTTP → :8002)
│  │   Orchestrator ──POST──→ Enrichment Agent
│  │   │
│  │   └── 4 tools run IN PARALLEL:
│  │       ├── lookup_claimant_history  → {prior_claims: 4, fraud_flags: 2}
│  │       ├── lookup_provider_network  → {billing_ratio: 2.96, license: "under_investigation"}
│  │       ├── lookup_vehicle_valuation → {market_value: 38500, claimed: 42000}
│  │       └── lookup_policy_details    → {inception: 22 days ago, recent_changes: 1}
│  │
│  │   Result: EnrichedClaimData (raw claim + 4 data sections)
│  │
│  ├── Step 2b: ANALYZE (HTTP → :8003)
│  │   Orchestrator ──POST──→ Analyzer Agent
│  │   │
│  │   └── 4 pattern tools run IN PARALLEL:
│  │       │
│  │       ├── Duplicate/Similar (weight: 30%)
│  │       │   Prompt: "PATTERN: Duplicate Similar\nENRICHED DATA: {...}"
│  │       │   LLM reasons: "4 prior claims, 2 fraud flags → score: 70"
│  │       │
│  │       ├── Suspicious Timing (weight: 20%)
│  │       │   Prompt: "PATTERN: Suspicious Timing\nENRICHED DATA: {...}"
│  │       │   LLM reasons: "22 days since inception, 1 policy change → score: 60"
│  │       │
│  │       ├── Inflated Amounts (weight: 25%)
│  │       │   Prompt: "PATTERN: Inflated Amounts\nENRICHED DATA: {...}"
│  │       │   LLM reasons: "claimed $42K > market $38.5K, billing 2.96x → score: 85"
│  │       │
│  │       └── Provider Network (weight: 25%)
│  │           Prompt: "PATTERN: Provider Network\nENRICHED DATA: {...}"
│  │           LLM reasons: "license under investigation, billing 2.96x → score: 60"
│  │
│  │   Composite Score = 0.30(70) + 0.20(60) + 0.25(85) + 0.25(60)
│  │                   = 21 + 12 + 21.25 + 15 = 69.25 → HIGH tier
│  │
│  └── Step 2c: REPORT (HTTP → :8004, only if score ≥ 40)
│      Orchestrator ──POST──→ Report Generator
│      │
│      └── 3 tools run SEQUENTIALLY:
│          ├── calculate_priority_score → P2-Urgent, exposure: $29,085
│          ├── format_evidence_summary  → Markdown table with all evidence
│          └── format_investigation_report → 7-section Markdown report (LLM)
│
│  Result per claim: {claim_id, enriched, fraud_analysis, report}

Step 3: AGGREGATE & RANK
─────────────────────────
├── Sort all 12 results by composite_score (highest first)
├── Assign tiers: Critical (≥80), High (60-79), Medium (40-59), Low (<40)
├── Save to fraud_data_store/claim_batches/
├── Store results in QueryResultsTool (for SIU chat queries)
└── Return JSON to dashboard
```

### Phase 3: Dashboard Display

```
Dashboard receives results JSON
│
├── Update KPI cards: Total: 12, Critical: 1, High: 4, Medium: 1, Low: 6
├── Show top fraud pattern and repeat providers
├── Render claim cards sorted by score (highest first)
│   Each card: score ring (Chart.js), tier chip, pattern bars, expandable report
└── Chat shows: "Pipeline complete! 12 claims analyzed. Ask me anything."
```

### Phase 4: SIU Query Chat

```
Investigator types: "Tell me about CLM-2026-001"
│
├── POST /api/chat → OrchestratorAgent.handle_query()
├── QueryResultsTool searches stored batch results
├── SIUQueryService formats response based on active persona:
│   │
│   ├── Kevin (Junior): Verbose narrative with definitions, evidence walkthrough,
│   │   "What This Means" explanations, recommended next steps
│   │
│   └── Diana (Senior): Compact table with score, tier, flagged patterns only,
│       statistical anomalies, no explanations for standard terms
│
└── Response rendered as Markdown in chat panel
```

---

## 4. Design Patterns — Why Each One Exists

### 4.1 Clean Architecture (Onion/Hexagonal)

```
WHAT: Organize code in concentric layers — Core → Application → Infrastructure → Presentation
WHY:  So we can change HOW we do things without changing WHAT we do
```

**How to explain it**: "Imagine you're building a calculator. The math formulas (2+2=4) are the CORE — they never change. The button layout (UI) is the PRESENTATION — it could be a physical calculator, a phone app, or a web page. The circuit board (storage, power) is the INFRASTRUCTURE. Clean Architecture says: make the math formulas independent of the button layout. Then you can change the buttons without touching the math."

**In our project**: We can swap the mock database to PostgreSQL by changing ONE line in `container.py`. The fraud analysis logic (Application layer) doesn't know or care how data is stored.

---

### 4.2 Dependency Injection (DI)

```
WHAT: Pass dependencies INTO a class instead of creating them inside
WHY:  So we can swap implementations without changing business logic
```

**How to explain it**: "Instead of a chef buying their own ingredients (hardcoded dependencies), someone hands them ingredients at the door (injection). The chef follows the same recipe regardless of whether the tomatoes are from the garden or the store."

**In our project**:
```python
# BAD: Agent creates its own database connection
class OrchestratorAgent:
    def __init__(self):
        self.storage = PostgresDB("localhost:5432")  # Hardcoded!

# GOOD: Agent receives its storage from outside
class OrchestratorAgent:
    def __init__(self, storage: IStorageRepository):  # Could be anything!
        self.storage = storage
```

The `Container` class (`container.py`) is the single place where all dependencies are wired together.

---

### 4.3 Strategy Pattern

```
WHAT: Define a family of algorithms, encapsulate each one, make them interchangeable
WHY:  So we can swap data sources without changing any business logic
```

**How to explain it**: "A GPS app can use different map providers (Google Maps, Apple Maps, OpenStreetMap). The navigation logic is the same — only the map data source changes. The Strategy Pattern lets you swap the map provider without rewriting the navigation code."

**In our project**: `IEnrichmentProvider` is the strategy interface. `MockEnrichmentProvider` is one strategy. A future `RealSIUDatabaseProvider` would be another. The enrichment agent doesn't care which one it's using.

---

### 4.4 Facade Pattern

```
WHAT: Provide a simplified interface to a complex subsystem
WHY:  So callers don't need to understand YAML loading, version resolution, caching, etc.
```

**How to explain it**: "When you order at a restaurant, you talk to one waiter (facade). Behind the kitchen door, there's a chef, sous chef, dishwasher, and inventory manager. The facade hides all that complexity — you just say 'I want the pasta.'"

**In our project**: `PromptFacade.get_prompt("duplicate_similar_cot", context)` — one line. Behind it: find the YAML directory, resolve the highest version, load the file, parse YAML, extract content, interpolate variables, cache results, log usage for Arize.

---

### 4.5 Factory Pattern (LLMProvider)

```
WHAT: Centralize object creation in one place
WHY:  So every agent gets its LLM the same way, and we can change the LLM config once
```

**How to explain it**: "Instead of every department in a company buying their own computers, there's an IT department (factory) that configures and distributes them. If you need to upgrade all computers to Windows 12, you change the factory — not every department."

**In our project**: `llm_provider.get_agent(name, model, instruction)` creates and caches Agent instances. If we switch from mock Gemini to real Gemini API, we change ONE import in `provider.py`.

---

### 4.6 Singleton Pattern

```
WHAT: Ensure a class has only ONE instance, globally shared
WHY:  Some things should exist only once (configuration, LLM factory, tracer)
```

**In our project**:
- `settings = Settings()` — one config object
- `llm_provider = LLMProvider()` — one LLM factory
- `tracer = setup_telemetry()` — one OpenTelemetry tracer

---

### 4.7 Observer Pattern (Telemetry/Tracing)

```
WHAT: When something happens, notify all interested parties without tight coupling
WHY:  So we can add/remove observability without changing business logic
```

**How to explain it**: "Security cameras in a store. The store operates normally whether cameras are on or off. The cameras observe but don't interfere. If you add more cameras or switch monitoring services, the store doesn't change."

**In our project**: `BaseTool.run()` wraps every tool execution in an Arize span. The tool logic (`execute()`) has zero knowledge of telemetry. If Arize is disabled (no API key), everything works identically — the spans just aren't exported.

---

### 4.8 Template Method Pattern (BasePatternTool)

```
WHAT: Define the skeleton of an algorithm, let subclasses override specific steps
WHY:  So all 4 pattern analyzers follow the same flow without duplicating code
```

**How to explain it**: "A recipe template says: (1) prep ingredients, (2) cook, (3) plate. Each dish overrides the specifics — pasta preps noodles, steak preps meat — but the overall flow is the same."

**In our project**: `BasePatternTool.execute()` defines: extract data → build prompt → call LLM → parse response. Each concrete tool (DuplicateSimilarTool, etc.) only specifies its `pattern_key` — the base class does everything else.

---

### 4.9 Microservices via A2A Protocol

```
WHAT: Split the system into independent services that communicate over HTTP
WHY:  Independent scaling, deployment, testing, and failure isolation
```

**How to explain it**: "A hospital has specialized departments — ER, radiology, surgery. Each department operates independently. The ER doesn't stop working because radiology has a power outage. They communicate by sending patient records between departments."

**In our project**: 4 agents run as 4 FastAPI servers on ports 8001-8004. The Orchestrator sends "patient records" (claims) to specialized "departments" (enrichment, analysis, report generation) via HTTP.

---

### 4.10 Composition Over Inheritance

```
WHAT: Build complex behavior by combining simple objects, not deep inheritance hierarchies
WHY:  More flexible, easier to test, easier to understand
```

**In our project**: `OrchestratorAgent` doesn't inherit from some `BaseAgent`. Instead, it COMPOSES:
- A `ToolRegistry` (has tools)
- An `Agent` via `LLMProvider` (has LLM access)
- A `IStorageRepository` (has persistence)
- 3 A2A clients (has agent communication)

Each component can be swapped independently.

---

## 5. Key Technical Decisions — Explained for Presentations

### "Why 4 agents instead of 1?"
**Answer**: Each agent has a focused job, its own tools, and the right model for its task. The Analyzer uses Pro (needs strong reasoning). The Report Generator uses Flash (just formatting). One monolithic agent would need all tools and the most expensive model for everything.

### "Why A2A HTTP instead of direct function calls?"
**Answer**: Agents run in separate threads/processes. This simulates production where they'd be on different servers. It also enables distributed tracing — we can see the full request flow across agent boundaries in Arize AX.

### "Why mock the LLM?"
**Answer**: Real LLM calls cost money and require network access. The mock returns deterministic, data-driven responses from the actual enriched data — so we can develop, test, and demo without API keys. Switching to real Gemini = change one import line.

### "Why versioned YAML prompts instead of hardcoded strings?"
**Answer**: Prompts are the most frequently iterated part of an LLM application. YAML files can be version-controlled, A/B tested, and audited. The PromptFacade automatically loads the latest version and logs which version was used (for Arize tracing).

### "Why parallel processing?"
**Answer**: 12 claims × 4 patterns = 48 LLM calls. Sequential = 48× latency. With dual-level parallelism (claims + patterns), we get near 1× latency. In production with real LLM APIs, this reduces a 10-minute pipeline to under 1 minute.

### "Why persona-based query chat?"
**Answer**: Kevin (junior, 2 years experience) needs step-by-step explanations and definitions. Diana (senior, 15 years) needs concise tables and statistical anomalies — she already knows what terms mean. Same data, different presentation = better user experience for both.

---

## 6. Technology Stack Summary

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| Language | Python 3.12 | Dominant in AI/ML, async support, Pydantic |
| Web Framework | FastAPI | Async-native, auto-docs, Pydantic integration |
| HTTP Server | Uvicorn | ASGI, handles async concurrently |
| HTTP Client | httpx | Async HTTP client (replaces requests) |
| Validation | Pydantic v2 | Type-safe domain models with auto-serialization |
| LLM | Google Gemini (mock) | ADK-compatible, supports tool calling |
| Telemetry | OpenTelemetry | Vendor-neutral, standard protocol |
| Observability | Arize AX | AI-specific trace visualization |
| Prompt Storage | YAML | Human-readable, version-controllable |
| Data Storage | JSON files | Zero-setup for development |
| Frontend | Vanilla HTML/JS + Chart.js | No build step, deployable anywhere |
| Package Manager | uv | Fast Python package management |
