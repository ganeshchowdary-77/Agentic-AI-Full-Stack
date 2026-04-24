"""
Investigation Report Generator A2A Server — Port 8004
======================================================
Thin HTTP boundary. Responsibilities:
  1. Extract W3C traceparent (distributed tracing from Orchestrator)
  2. Deserialize fraud analysis + enriched claim JSON
  3. Wrap in CHAIN span as child of Orchestrator trace
  4. Delegate to ReportGenerator (Tools 2 & 3 deterministic, Tool 1 Flash LLM)
  5. Return Markdown report string

No report logic lives here — this is transport only.
"""

import json
import uvicorn
from fastapi import FastAPI, Request
from opentelemetry import propagate

from src.infrastructure.telemetry.arize_wrappers import tracer
from src.application.agents.report_generator.agent import ReportGenerator

app = FastAPI(title="Investigation Report Generator Agent", version="1.0.0")

_agent = ReportGenerator()


@app.get("/.well-known/agent.json")
def get_agent_card():
    return {
        "name": "investigation_report_generator",
        "description": (
            "Generates formatted investigation reports with evidence summaries, "
            "recommended actions, and priority classification for commercial auto "
            "insurance fraud claims. Task-based, non-conversational."
        ),
        "url": "http://localhost:8004",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [{
            "id": "investigation-report",
            "name": "Fraud Investigation Report Generation",
            "description": (
                "Produces a structured investigation report for a single claim: "
                "case header, executive summary, per-pattern analysis detail, "
                "consolidated evidence table, recommended investigative actions, "
                "risk factor ranking, and claimant/provider profile. "
                "Output in Markdown format suitable for SIU case files."
            ),
            "inputModes": ["text"],
            "outputModes": ["text"],
        }],
        "tools": _agent.list_tools(),
        "score_threshold": 40,
    }


@app.post("/v1/tasks")
async def handle_task(task: dict, request: Request):
    ctx = propagate.extract(dict(request.headers))

    payload_str = task["message"]["parts"][0]["text"]
    payload     = json.loads(payload_str)
    claim_id    = payload.get("claim_id", "UNKNOWN")
    fraud_score = payload.get("fraud_analysis", {}).get("composite_score", 0)

    with tracer.start_as_current_span(
        f"Investigation Report Generator [{claim_id}]",
        context=ctx,
    ) as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("agent.name",   _agent.agent_name)
        span.set_attribute("agent.model",  _agent.model)
        span.set_attribute("claim.id",     claim_id)
        span.set_attribute("fraud_score",  str(fraud_score))

        report = await _agent.run(
            claim_id=payload["claim_id"],
            fraud_analysis=payload["fraud_analysis"],
            enriched_data=payload["enriched_data"],
        )

        span.set_attribute("report_length", str(len(report)))
        span.set_attribute("output.value",  report[:2000])

    return {"artifacts": [{"parts": [{"text": report}]}]}


def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8004)

