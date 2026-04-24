# Presentation Layer & A2A Protocol — Detailed Documentation

This document explains **why it's called "presentation"**, how the A2A protocol works, the web dashboard, and the SIU query chat.

---

## 1. Why "Presentation" Layer?

In Clean Architecture, "presentation" = **how the system is presented to the outside world**. Think of it as the "face" of the application.

| If your system were a restaurant... | Presentation layer is... |
|------|------|
| The kitchen (cooking) = Application layer | The waitstaff + menu (how food reaches customers) |
| The recipes = Core layer | The dining room, takeout counter, delivery app |
| The oven, fridge = Infrastructure | Different ways to **present** the same food |

In this project, the presentation layer includes:
- **Web Dashboard** (`presentation/web/`) — Browser UI for SIU investigators
- **A2A HTTP Servers** (`presentation/a2a/`) — API endpoints for inter-agent communication
- **A2A HTTP Client** (`presentation/a2a/client.py`) — Outgoing HTTP calls to sub-agents

None of these contain business logic. They are **thin transport boundaries** that serialize/deserialize data and delegate to the Application layer.

---

## 2. A2A Protocol (Agent-to-Agent)

### What is A2A?
A2A is Google's [Agent-to-Agent protocol](https://google.github.io/A2A/) — a standard for AI agents to communicate over HTTP. Each agent is a standalone HTTP service with:
- A **discovery endpoint** (`/.well-known/agent.json`) — describes capabilities
- A **task endpoint** (`/v1/tasks`) — accepts work and returns results

### How Our Agents Communicate

```
┌─────────────────────┐
│  Orchestrator :8001  │
│  (Dashboard + API)   │
└──────┬──┬──┬────────┘
       │  │  │  HTTP POST /v1/tasks
       │  │  │
  ┌────┘  │  └────┐
  ▼       ▼       ▼
:8002   :8003   :8004
Enrich  Analyze  Report
Agent   Agent    Agent
```

Each sub-agent runs on its own port as a FastAPI server started in a daemon thread.

### A2A Message Format
```json
// Request (Orchestrator → Sub-Agent)
{
  "id": "enrich-CLM-2026-001",
  "skill_id": "claim-enrichment",
  "message": {
    "parts": [{"text": "{\"claim_id\": \"CLM-2026-001\", ...}"}]
  }
}

// Response (Sub-Agent → Orchestrator)
{
  "artifacts": [
    {"parts": [{"text": "{\"claim_id\": \"CLM-2026-001\", \"enrichment_status\": \"complete\", ...}"}]}
  ]
}
```

### Agent Discovery Card (`.well-known/agent.json`)
Each agent serves a discovery card describing its capabilities:
```json
{
  "name": "claim_data_enrichment",
  "description": "Enriches raw claims with contextual data...",
  "url": "http://localhost:8002",
  "version": "1.0.0",
  "capabilities": {"streaming": false},
  "skills": [{"id": "claim-enrichment", "name": "Claim Data Enrichment", ...}],
  "tools": [{"name": "lookup_claimant_history", ...}, ...]
}
```

---

## 3. A2A Server Files

### `server_enrichment.py` (Port 8002)
- Creates `FraudEnrichmentAgent` at module level
- `POST /v1/tasks` → extracts claim JSON → delegates to `agent.run(claim)` → returns enriched data
- Extracts W3C `traceparent` header for distributed tracing (so enrichment spans link to Orchestrator trace in Arize)

### `server_analyzer.py` (Port 8003)
- Creates `FraudPatternAnalyzer` at module level
- `POST /v1/tasks` → extracts enriched claim → delegates to `agent.run(enriched_claim)` → returns fraud analysis with 4 pattern scores + composite score

### `server_report.py` (Port 8004)
- Creates `ReportGenerator` at module level
- `POST /v1/tasks` → extracts `{claim_id, fraud_analysis, enriched_data}` → delegates to `agent.run(...)` → returns Markdown report string

### `client.py` — A2A Client (Orchestrator Side)
Three client classes used by the Orchestrator to call sub-agents:

| Client | Target | Method |
|--------|--------|--------|
| `A2AEnrichmentClient` | :8002 | `async enrich(claim) -> dict` |
| `A2AAnalyzerClient` | :8003 | `async analyze(enriched_claim) -> dict` |
| `A2AReportGeneratorClient` | :8004 | `async generate_report(claim_id, fraud_analysis, enriched_data) -> str` |

All clients inject `traceparent` headers via `_inject_trace_headers()` for distributed tracing.

---

## 4. Web Dashboard (`presentation/web/`)

### `app.py` — FastAPI Dashboard Server (Port 8001)

**Routes**:

| Route | Method | What It Does |
|-------|--------|-------------|
| `/` | GET | Serves `dashboard.html` |
| `/api/run` | GET | Triggers the batch pipeline (reads `weekly_auto_claims.json`) |
| `/api/chat` | POST | Handles SIU query chat messages |

### `dashboard.html` — SIU Command Center UI

A single-page application with:

**Left Panel**:
- **KPI Cards** — Total Claims, Critical, High, Medium, Low/Clean counts
- **Top Fraud Pattern** — Most frequently triggered pattern
- **Repeat Providers** — Providers appearing on multiple claims
- **Pipeline Controls** — "Run Weekly Claim Batch" button + status text
- **Claim Cards** — Scrollable list of claim results with score rings, tier chips, pattern bars, and expandable investigation reports

**Right Panel**:
- **Persona Toggle** — Switch between Kevin (Junior Analyst) and Diana (Senior SIU Lead)
- **Chat Interface** — Query results with natural language
- **Quick Action Chips** — "Show results", "Repeat providers", "Network rings", etc.

**Key JavaScript Functions**:
- `runPipeline()` — Calls `/api/run`, updates UI with results
- `buildClaimCard(claim)` — Renders a single claim card with Chart.js score ring
- `sendChat()` — Sends query to `/api/chat`, renders Markdown response
- `updateKPIs(data)` — Updates the top KPI cards from batch results

---

## 5. SIU Query Service (`application/services/siu_query_service.py`)

Handles all query chat logic with persona-adaptive responses.

### Profile-Driven Response Formatting

**Kevin (Junior)**: Verbose narratives, step-by-step explanations, term definitions, evidence walk-throughs, "What This Means" sections.

**Diana (Senior)**: Compact tables, statistical anomalies, high-confidence flags only (filters claims below score 70), provider network focus.

### Key Functions:
- `format_batch_summary(results, profile)` — Different format for Kevin vs Diana
- `format_claim_detail(claim, profile)` — Per-claim drill-down
- `format_pattern_query(results, pattern, profile)` — Filter by specific pattern
- `format_provider_query(results, profile)` — Provider frequency analysis
- `answer_siu_query(query, results, profile)` — Routes query to the right formatter

---

## 6. User Profile Store (`application/services/user_profile_store.py`)

Manages the two SIU personas stored as JSON in `fraud_data_store/user_profiles/`:

### Kevin (Junior Analyst)
```json
{
  "name": "Kevin Torres",
  "role": "Junior SIU Analyst",
  "experience": "junior",
  "response_style": {
    "detail_level": "verbose",
    "include_definitions": true,
    "include_next_steps": true,
    "threshold_filter": 0
  }
}
```

### Diana (Senior SIU Lead)
```json
{
  "name": "Diana Okafor",
  "role": "Senior SIU Lead",
  "experience": "senior",
  "response_style": {
    "detail_level": "concise",
    "include_definitions": false,
    "include_next_steps": false,
    "threshold_filter": 70
  }
}
```
