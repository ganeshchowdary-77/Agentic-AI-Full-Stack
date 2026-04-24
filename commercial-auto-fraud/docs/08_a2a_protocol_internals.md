# A2A Protocol — Complete Internal Mechanics

This document teaches you exactly how A2A (Agent-to-Agent) protocol works, every HTTP header, every JSON field, and how distributed tracing flows across agent boundaries.

---

## 1. A2A Protocol Specification

A2A is Google's open standard for AI agents to discover and communicate with each other over HTTP. Think of it as **REST for AI agents**.

### Core Concepts

| Concept | What It Is | HTTP Equivalent |
|---------|-----------|----------------|
| **Agent Card** | Self-description of an agent | API documentation / OpenAPI spec |
| **Task** | A unit of work sent to an agent | HTTP Request + Response |
| **Skill** | A specific capability an agent offers | An API endpoint |
| **Artifact** | Data produced by a task | Response body |
| **Part** | A piece of content (text, file, etc.) | Content-Type segments |

---

## 2. Agent Discovery — How Agents Find Each Other

### The Agent Card (`/.well-known/agent.json`)

Every A2A agent MUST serve a JSON document at this well-known URL. It's like a business card:

```json
GET http://localhost:8002/.well-known/agent.json

{
  "name": "claim_data_enrichment",
  "description": "Enriches raw claims with contextual data...",
  "url": "http://localhost:8002",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "claim-enrichment",
      "name": "Claim Data Enrichment",
      "description": "Augments a single claim with claimant history...",
      "inputModes": ["text"],
      "outputModes": ["text"]
    }
  ],
  "tools": [
    {"name": "lookup_claimant_history", "description": "..."},
    {"name": "lookup_provider_network", "description": "..."},
    {"name": "lookup_vehicle_valuation", "description": "..."},
    {"name": "lookup_policy_details", "description": "..."}
  ]
}
```

### What Each Field Means

| Field | Purpose | Example |
|-------|---------|---------|
| `name` | Unique agent identifier | `"claim_data_enrichment"` |
| `description` | Human-readable purpose | `"Enriches raw claims..."` |
| `url` | Base URL for sending tasks | `"http://localhost:8002"` |
| `version` | Agent version for compatibility | `"1.0.0"` |
| `capabilities.streaming` | Can it stream responses? | `false` |
| `skills` | List of things this agent can do | Each skill is a distinct capability |
| `tools` | Internal tools the agent uses | Informational — helps the orchestrator understand internals |

### Discovery Flow
```
Orchestrator starts up
  │
  ├── GET http://localhost:8002/.well-known/agent.json
  │   → "Oh, this agent can enrich claims with 4 tools"
  │
  ├── GET http://localhost:8003/.well-known/agent.json
  │   → "This agent can analyze 4 fraud patterns"
  │
  └── GET http://localhost:8004/.well-known/agent.json
      → "This agent generates investigation reports"
```

---

## 3. Task Execution — The Full HTTP Lifecycle

### Step-by-Step: Orchestrator Sends a Claim to Enrichment Agent

#### 3.1 Client Side (Orchestrator)

```python
# src/presentation/a2a/client.py — A2AEnrichmentClient.enrich()

async def enrich(self, claim: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8002/v1/tasks",       # A2A task endpoint
            json={
                "id": "enrich-CLM-2026-001",         # Unique task ID
                "skill_id": "claim-enrichment",       # Which skill to invoke
                "message": {
                    "parts": [
                        {"text": json.dumps(claim)}   # Claim data as JSON string
                    ]
                }
            },
            headers=_inject_trace_headers(),           # W3C traceparent header
            timeout=30.0,
        )
        data = response.json()
        # Extract the enriched claim from the response artifact
        return json.loads(data["artifacts"][0]["parts"][0]["text"])
```

#### 3.2 The HTTP Request (on the wire)

```http
POST /v1/tasks HTTP/1.1
Host: localhost:8002
Content-Type: application/json
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
tracestate:

{
  "id": "enrich-CLM-2026-001",
  "skill_id": "claim-enrichment",
  "message": {
    "parts": [
      {
        "text": "{\"claim_id\":\"CLM-2026-001\",\"claimant\":{\"id\":\"C-4821\",\"name\":\"Marcus Rivera\"},\"vehicle\":{\"vin\":\"1HGCM82633A004352\"},\"claimed_amount\":42000}"
      }
    ]
  }
}
```

#### 3.3 Server Side (Enrichment Agent)

```python
# src/presentation/a2a/server_enrichment.py

@app.post("/v1/tasks")
async def handle_task(task: dict, request: Request):
    # 1. Extract distributed trace context from HTTP headers
    ctx = propagate.extract(dict(request.headers))

    # 2. Parse the claim from the A2A message
    claim_str = task["message"]["parts"][0]["text"]
    claim = json.loads(claim_str)

    # 3. Create a trace span as CHILD of the Orchestrator's span
    with tracer.start_as_current_span("Enrichment Agent", context=ctx):
        # 4. Delegate to the actual agent logic
        enriched = await _agent.run(claim)

    # 5. Return A2A response format
    return {"artifacts": [{"parts": [{"text": json.dumps(enriched)}]}]}
```

#### 3.4 The HTTP Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "artifacts": [
    {
      "parts": [
        {
          "text": "{\"claim_id\":\"CLM-2026-001\",\"raw_claim\":{...},\"claimant_history\":{\"total_prior_claims\":4,\"prior_fraud_flags\":2},\"provider_network\":{\"billing_ratio\":2.96},\"enrichment_status\":\"complete\"}"
        }
      ]
    }
  ]
}
```

---

## 4. Distributed Tracing Across A2A Boundaries

This is the trickiest part. When Agent A calls Agent B over HTTP, how does Agent B's trace link to Agent A's trace?

### The W3C Trace Context Standard

The `traceparent` HTTP header carries trace identity across process boundaries:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              │  │                                │                 │
              │  │                                │                 └─ Flags (01 = sampled)
              │  │                                └─ Parent Span ID (8 bytes hex)
              │  └─ Trace ID (16 bytes hex) ← SAME across all agents
              └─ Version (always 00)
```

### How It Works in Our Code

```
Orchestrator creates a CHAIN span (Trace ID = AAAA)
│
├── Calls enrichment via HTTP
│   Headers: traceparent: 00-AAAA-1111-01
│   │
│   └── Enrichment server extracts headers:
│       ctx = propagate.extract(request.headers)
│       │
│       └── Creates CHILD span with context=ctx
│           This span has Trace ID = AAAA, Parent = 1111
│           → Now linked to Orchestrator's trace!
│
├── Calls analyzer via HTTP
│   Headers: traceparent: 00-AAAA-2222-01
│   │
│   └── Analyzer creates span with Parent = 2222
│       → Also linked to same trace AAAA
│
└── All spans appear in Arize under ONE trace
```

### Client-Side Injection
```python
# src/presentation/a2a/client.py
def _inject_trace_headers() -> dict:
    headers = {}
    propagate.inject(headers)  # Injects traceparent + tracestate
    return headers
```

### Server-Side Extraction
```python
# src/presentation/a2a/server_enrichment.py
ctx = propagate.extract(dict(request.headers))  # Extract parent context
with tracer.start_as_current_span("...", context=ctx):  # Create child span
    ...
```

---

## 5. A2A Message Format — Complete Reference

### Task Request
```json
{
  "id": "string",           // Unique task identifier
  "skill_id": "string",     // Which skill to invoke
  "message": {              // Input data
    "role": "user",          // Optional: "user" or "agent"
    "parts": [               // Content parts (multi-modal support)
      {"text": "string"},    // Text content
      {"file": {"uri": "..."}}  // File content (not used in our project)
    ]
  },
  "metadata": {}             // Optional: extra context
}
```

### Task Response
```json
{
  "id": "string",           // Same task ID
  "status": {               // Task status
    "state": "completed",    // "submitted", "working", "completed", "failed"
    "message": "string"      // Optional status message
  },
  "artifacts": [             // Output data
    {
      "parts": [
        {"text": "string"}   // Result as text (JSON string in our case)
      ]
    }
  ]
}
```

---

## 6. Building A2A Services from Scratch

### Minimal A2A Agent (complete working example)

```python
# my_a2a_agent.py — Complete A2A agent in 40 lines
import json
import uvicorn
from fastapi import FastAPI

app = FastAPI()

# Agent logic
async def analyze(data: dict) -> dict:
    score = 50 if data.get("amount", 0) > 10000 else 10
    return {"claim_id": data["id"], "score": score}

# A2A Discovery
@app.get("/.well-known/agent.json")
def agent_card():
    return {
        "name": "simple_analyzer",
        "description": "Analyzes claims for fraud",
        "url": "http://localhost:9000",
        "version": "1.0.0",
        "capabilities": {"streaming": False},
        "skills": [{"id": "analyze", "name": "Fraud Analysis"}],
    }

# A2A Task Handler
@app.post("/v1/tasks")
async def handle_task(task: dict):
    data = json.loads(task["message"]["parts"][0]["text"])
    result = await analyze(data)
    return {"artifacts": [{"parts": [{"text": json.dumps(result)}]}]}

if __name__ == "__main__":
    uvicorn.run(app, port=9000)
```

### Calling This Agent
```python
import httpx, json

async def call_agent():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:9000/v1/tasks",
            json={
                "id": "task-001",
                "skill_id": "analyze",
                "message": {"parts": [{"text": json.dumps({"id": "CLM-1", "amount": 50000})}]}
            }
        )
        result = json.loads(response.json()["artifacts"][0]["parts"][0]["text"])
        print(result)  # {"claim_id": "CLM-1", "score": 50}
```

---

## 7. A2A vs Other Agent Communication Protocols

| Protocol | Creator | Transport | Discovery | Strengths |
|----------|---------|-----------|-----------|-----------|
| **A2A** | Google | HTTP/REST | Agent cards | Simple, standard HTTP, easy to debug |
| **MCP** (Model Context Protocol) | Anthropic | stdio/SSE | Capability listing | Tool-sharing focused, great for IDEs |
| **AutoGen** | Microsoft | In-process | Code-level | Multi-agent conversations, group chat |
| **LangGraph** | LangChain | In-process | Graph definition | Stateful workflows, complex routing |
| **CrewAI** | CrewAI | In-process | Role definition | Role-based agent teams |

### When to Use A2A
- Agents need to run on **different machines** or **scale independently**
- You want **language-agnostic** communication (any language can implement HTTP)
- You need **distributed tracing** across agent boundaries
- You want agents to be **independently deployable** microservices
