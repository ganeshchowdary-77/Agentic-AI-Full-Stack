# Commercial Auto Fraud Detection Pipeline — Complete Documentation

## Table of Contents
- [01_project_overview.md](./01_project_overview.md) — This file. Architecture, terminology, folder structure
- [02_core_and_infrastructure.md](./02_core_and_infrastructure.md) — Domain models, ports, adapters, tools, telemetry
- [03_agents_and_pipeline.md](./03_agents_and_pipeline.md) — All 4 agents, their tools, and the pipeline flow
- [04_prompt_manager.md](./04_prompt_manager.md) — Prompt versioning, YAML templates, facade pattern
- [05_presentation_layer.md](./05_presentation_layer.md) — A2A servers, web dashboard, SIU query chat
- [06_mock_adk.md](./06_mock_adk.md) — Mock Google ADK, how it simulates LLM responses

---

## 1. What This Project Does

This is an **AI-powered fraud detection pipeline** for commercial auto insurance claims. It takes a batch of insurance claims (JSON), enriches each claim with contextual data, runs 4 parallel fraud pattern analyses using LLM-based Chain-of-Thought reasoning, scores them, and generates investigation reports for an SIU (Special Investigations Unit) team.

### The Pipeline in Plain English
```
Input: 12 insurance claims (JSON file)
  ↓
Step 1: Validate all claims (required fields, data types)
  ↓
Step 2: For EACH claim (in parallel):
  ├── Enrich: Pull claimant history, provider records, vehicle value, policy details
  ├── Analyze: Run 4 fraud patterns simultaneously
  │     ├── Duplicate/Similar Claims  → score 0-100
  │     ├── Suspicious Timing         → score 0-100
  │     ├── Inflated Amounts          → score 0-100
  │     └── Provider Network Anomaly  → score 0-100
  ├── Score: Weighted average = composite fraud score
  └── Report: If score ≥ 40, generate investigation report
  ↓
Output: Ranked list + reports, viewable on web dashboard
```

---

## 2. Architecture: Clean Architecture (Onion/Hexagonal)

This project uses **Clean Architecture** — a software design pattern where code is organized in concentric layers, with the most stable/important code at the center and the most volatile/external code at the edges.

### Why This Matters
The naming conventions (`core`, `application`, `infrastructure`, `presentation`) come directly from Clean Architecture. Here's what each layer means:

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTATION (outermost — how users interact)          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  INFRASTRUCTURE (adapters to external world)     │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  APPLICATION (business logic, agents)    │    │    │
│  │  │  ┌─────────────────────────────┐        │    │    │
│  │  │  │  CORE (domain models, rules) │        │    │    │
│  │  │  └─────────────────────────────┘        │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Layer Definitions

| Layer | Folder | What It Contains | Why It's Named That |
|-------|--------|-----------------|-------------------|
| **Core** | `src/core/` | Domain models (Claim, FraudAnalysis), interfaces (ports), exceptions | The "core" of the business — pure Python, no dependencies on frameworks |
| **Application** | `src/application/` | Agents (Orchestrator, Enrichment, Analyzer, Report Generator), business services | The "application logic" — orchestrates the domain models to solve the fraud detection problem |
| **Infrastructure** | `src/infrastructure/` | LLM provider, mock APIs, file storage, telemetry (Arize), tool framework | "Infrastructure" = external systems. Databases, APIs, file systems — things that could change |
| **Presentation** | `src/presentation/` | Web dashboard (HTML/JS), A2A HTTP servers, FastAPI routes | "Presentation" = how you **present** the system to the outside world. Web UI, HTTP APIs, CLI — all are "presentation" |

### Why "Presentation" and Not "API" or "Web"?
In Clean Architecture, **"presentation"** means the layer that presents your application to the outside world. It includes:
- **Web Dashboard** (`presentation/web/`) — HTML/JS UI for SIU investigators
- **A2A Servers** (`presentation/a2a/`) — HTTP endpoints that expose agents as microservices
- **A2A Client** (`presentation/a2a/client.py`) — HTTP client that calls those microservices

It's called "presentation" because whether you access the system via a web browser, a REST API, a CLI, or a gRPC endpoint — it's all just different ways of "presenting" the same application logic to users.

---

## 3. Complete Folder Structure

```
commercial-auto-fraud/
│
├── .env                          # Environment variables (API keys, ports)
├── pyproject.toml                # Python project config & dependencies
├── requirements.txt              # Pip dependencies (alternative to pyproject.toml)
├── weekly_auto_claims.json       # Default batch of 12 test claims
├── flagged_commercial_claims.json # Alternative batch with different claims
│
├── google/                       # Mock Google ADK package
│   └── adk/
│       └── __init__.py           # Mock Agent class (simulates Gemini LLM)
│
├── fraud_data_store/             # Local file-based "database"
│   ├── claim_batches/            # Saved batch results (JSON)
│   ├── investigation_reports/    # Generated reports per claim (JSON)
│   └── user_profiles/            # Kevin.json, Diana.json (SIU personas)
│
├── src/                          # Main source code
│   ├── main.py                   # Entry point — boots all 4 servers
│   │
│   ├── config/                   # Configuration layer
│   │   ├── settings.py           # Environment config (models, ports, thresholds)
│   │   └── container.py          # Dependency Injection container
│   │
│   ├── core/                     # Layer 1: Domain (innermost, no dependencies)
│   │   ├── models.py             # Pydantic domain models
│   │   ├── exceptions.py         # Custom exception hierarchy
│   │   └── ports/                # Abstract interfaces (contracts)
│   │       ├── data_provider.py  # IEnrichmentProvider interface
│   │       └── repository.py     # IStorageRepository interface
│   │
│   ├── application/              # Layer 2: Business Logic
│   │   ├── agents/               # The 4 AI agents
│   │   │   ├── orchestrator/     # Agent 1: Pipeline coordinator
│   │   │   ├── enrichment/       # Agent 2: Data enrichment
│   │   │   ├── analyzer/         # Agent 3: Fraud pattern analysis
│   │   │   └── report_generator/ # Agent 4: Report generation
│   │   └── services/             # Non-agent business services
│   │       ├── siu_query_service.py   # Query chat logic
│   │       └── user_profile_store.py  # Kevin/Diana profile management
│   │
│   ├── infrastructure/           # Layer 3: External adapters
│   │   ├── llm/
│   │   │   └── provider.py       # LLMProvider singleton (factory for Agent instances)
│   │   ├── adapters/
│   │   │   ├── mock_apis.py      # MockEnrichmentProvider (fake external databases)
│   │   │   └── local_storage.py  # LocalStorageRepository (JSON file storage)
│   │   ├── tools/
│   │   │   ├── base_tool.py      # BaseTool abstract class
│   │   │   └── registry.py       # ToolRegistry (dependency injection for tools)
│   │   └── telemetry/
│   │       └── arize_wrappers.py # OpenTelemetry spans for Arize AX observability
│   │
│   ├── presentation/             # Layer 4: Delivery mechanisms
│   │   ├── a2a/                  # Agent-to-Agent protocol servers
│   │   │   ├── client.py         # HTTP clients (Orchestrator → sub-agents)
│   │   │   ├── server_enrichment.py  # FastAPI server on :8002
│   │   │   ├── server_analyzer.py    # FastAPI server on :8003
│   │   │   └── server_report.py      # FastAPI server on :8004
│   │   └── web/
│   │       ├── app.py            # FastAPI dashboard server on :8001
│   │       └── dashboard.html    # SIU Command Center UI
│   │
│   └── prompt_manager/           # Versioned prompt management system
│       ├── engine/
│       │   └── facade.py         # PromptFacade — single access point for all prompts
│       ├── storage/
│       │   └── prompts/          # 11 YAML prompt templates (versioned)
│       └── templates/            # Python fallback constants
│
├── docs/                         # Documentation
└── tests/                        # Test suite
```

---

## 4. How It All Connects — Startup Flow

When you run `python src/main.py`:

1. **3 daemon threads start** — each runs a FastAPI (uvicorn) server:
   - Thread 1: `server_enrichment.py` → port 8002 (creates `FraudEnrichmentAgent`)
   - Thread 2: `server_analyzer.py` → port 8003 (creates `FraudPatternAnalyzer`)
   - Thread 3: `server_report.py` → port 8004 (creates `ReportGenerator`)

2. **Main thread starts** the Orchestrator dashboard on port 8001:
   - `container.py` creates the DI container → wires all dependencies
   - `OrchestratorAgent` gets 3 A2A HTTP clients (to call :8002, :8003, :8004)
   - `app.py` serves the web dashboard + API endpoints

3. **User triggers pipeline** via the dashboard "Run Weekly Claim Batch" button:
   - Dashboard calls `GET /api/run`
   - Orchestrator reads `weekly_auto_claims.json`
   - For each claim: Orchestrator → HTTP → Enrichment Agent → HTTP → Analyzer Agent → HTTP → Report Generator
   - Results rendered on dashboard

---

## 5. Key Design Patterns Applied

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Dependency Injection** | `container.py`, `ToolRegistry` | Swap implementations without changing business logic |
| **Strategy Pattern** | `IEnrichmentProvider` port | Mock → real API swap by changing one line |
| **Facade Pattern** | `PromptFacade` | Single access point for all prompts across all agents |
| **Tool Pattern (ADK)** | `BaseTool` + `ToolRegistry` | Each agent owns a set of tools, registered at init |
| **A2A Protocol** | `presentation/a2a/` | Agents communicate via HTTP (Google A2A spec) |
| **Observer/Telemetry** | `arize_wrappers.py` | Every span (CHAIN/TOOL/LLM) reported to Arize AX |
| **Chain-of-Thought** | YAML prompts | LLM reasons step-by-step before scoring |
| **ReAct Pattern** | `enrichment_react` prompt | Thought → Action → Observation loop for data gathering |
| **Singleton** | `LLMProvider`, `settings` | One instance shared across the application |
