"""
Claim Data Enrichment A2A Server — Port 8002
=============================================
Thin HTTP boundary layer. Responsibilities:
  1. Extract W3C traceparent from incoming headers (distributed tracing)
  2. Deserialize the raw claim JSON
  3. Delegate to FraudEnrichmentAgent (src/application/agents/enrichment/agent.py)
  4. Wrap the agent.run() call in a named TOOL span as child of Orchestrator trace
  5. Return the enriched claim package

Nothing fraud-related lives here — this is transport only.
"""

import json
import uvicorn
from fastapi import FastAPI, Request
from opentelemetry import propagate

from src.infrastructure.telemetry.arize_wrappers import tracer
from src.infrastructure.adapters.mock_apis import MockEnrichmentProvider
from src.application.agents.enrichment.agent import FraudEnrichmentAgent

app = FastAPI(title="Claim Data Enrichment Agent", version="1.0.0")

# Agent instantiated once — shared across all requests (stateless)
_provider = MockEnrichmentProvider()
_agent    = FraudEnrichmentAgent(data_provider=_provider)


@app.get("/.well-known/agent.json")
def get_agent_card():
    return {
        "name": "claim_data_enrichment",
        "description": (
            "Enriches raw commercial auto insurance claims with contextual data: "
            "claimant history, provider network information, vehicle valuation, "
            "and policy details. Task-based, non-conversational."
        ),
        "url": "http://localhost:8002",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [{
            "id": "claim-enrichment",
            "name": "Claim Data Enrichment",
            "description": (
                "Augments a single commercial auto claim with claimant history "
                "(prior claims, fraud flags, associated vehicles), provider network info "
                "(billing patterns, referral connections, license status), "
                "vehicle valuation (market value, repair benchmarks), "
                "and policy details (inception date, recent changes, premium history). "
                "Returns a structured enriched data package."
            ),
            "inputModes": ["text"],
            "outputModes": ["text"],
        }],
        "tools": _agent.list_tools(),
    }


@app.post("/v1/tasks")
async def handle_task(task: dict, request: Request):
    # ── Distributed trace: extract parent context from Orchestrator ─────────
    ctx = propagate.extract(dict(request.headers))

    claim_str = task["message"]["parts"][0]["text"]
    claim     = json.loads(claim_str)
    claim_id  = claim.get("claim_id", "UNKNOWN")

    # ── Create named TOOL span as child of Orchestrator's Claim Pipeline span
    with tracer.start_as_current_span(
        f"Claim Data Enrichment Agent [{claim_id}]",
        context=ctx,
    ) as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        span.set_attribute("agent.name",  _agent.agent_name)
        span.set_attribute("agent.model", _agent.model)
        span.set_attribute("claim.id",    claim_id)
        span.set_attribute("input.value", json.dumps(claim)[:2000])

        # Delegate to the agent (which runs 4 tools in parallel internally)
        enriched = await _agent.run(claim)

        span.set_attribute("enrichment_status", enriched.get("enrichment_status", "unknown"))
        span.set_attribute("output.value", json.dumps(enriched)[:2000])

    return {"artifacts": [{"parts": [{"text": json.dumps(enriched)}]}]}


def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8002)

