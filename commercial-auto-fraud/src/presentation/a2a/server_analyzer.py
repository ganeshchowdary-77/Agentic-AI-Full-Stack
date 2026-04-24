"""
Fraud Pattern Analyzer A2A Server — Port 8003
==============================================
Thin HTTP boundary. Responsibilities:
  1. Extract W3C traceparent (distributed tracing from Orchestrator)
  2. Deserialize enriched claim JSON
  3. Wrap in CHAIN span as child of Orchestrator trace
  4. Delegate to FraudPatternAnalyzer (which runs 4 LLM calls in parallel)
  5. Return composite fraud analysis

No fraud logic lives here — this is transport only.
"""

import json
import uvicorn
from fastapi import FastAPI, Request
from opentelemetry import propagate

from src.infrastructure.telemetry.arize_wrappers import tracer
from src.application.agents.analyzer.agent import FraudPatternAnalyzer

app = FastAPI(title="Fraud Pattern Analyzer Agent", version="1.0.0")

# Agent instantiated once — stateless, safe for concurrent requests
_agent = FraudPatternAnalyzer()


@app.get("/.well-known/agent.json")
def get_agent_card():
    return {
        "name": "fraud_pattern_analyzer",
        "description": (
            "Runs 4 parallel fraud detection patterns per claim (Duplicate/Similar Claims, "
            "Suspicious Timing, Inflated Amounts, Provider Network Anomalies) using "
            "Chain-of-Thought reasoning. Produces evidence-based fraud flags, sub-scores, "
            "and a composite fraud score. Task-based, non-conversational."
        ),
        "url": "http://localhost:8003",
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [{
            "id": "fraud-pattern-analysis",
            "name": "Parallel Fraud Pattern Analysis",
            "description": (
                "Analyzes a single enriched commercial auto claim across 4 fraud dimensions "
                "simultaneously: duplicate/similar claims (VIN matching, description similarity, "
                "date overlap), suspicious timing (policy lifecycle proximity, day-of-week anomalies), "
                "inflated amounts (repair vs. market value, medical vs. injury severity), and "
                "provider network anomalies (billing ratios, referral rings, geographic outliers). "
                "Returns sub-scores per pattern, composite weighted score, confidence level, "
                "and evidence lists."
            ),
            "inputModes": ["text"],
            "outputModes": ["text"],
        }],
        "tools": _agent.list_tools(),
        "weights": {
            "duplicate_similar": "30%",
            "suspicious_timing":  "20%",
            "inflated_amounts":   "25%",
            "provider_network":   "25%",
        },
    }


@app.post("/v1/tasks")
async def handle_task(task: dict, request: Request):
    # Distributed trace: extract parent context from Orchestrator
    ctx = propagate.extract(dict(request.headers))

    claim_str    = task["message"]["parts"][0]["text"]
    enriched     = json.loads(claim_str)
    claim_id     = enriched.get("claim_id", "UNKNOWN")

    # CHAIN span as child of Orchestrator's Claim Pipeline span
    with tracer.start_as_current_span(
        f"Fraud Pattern Analyzer [{claim_id}]",
        context=ctx,
    ) as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("agent.name",  _agent.agent_name)
        span.set_attribute("agent.model", _agent.model)
        span.set_attribute("claim.id",    claim_id)
        span.set_attribute("input.value", json.dumps(enriched)[:2000])

        # Runs 4 CoT LLM calls in parallel internally
        fraud_analysis = await _agent.run(enriched)

        span.set_attribute("composite_score",  str(fraud_analysis.get("composite_score", 0)))
        span.set_attribute("priority_tier",    fraud_analysis.get("priority_tier", ""))
        span.set_attribute("confidence",       fraud_analysis.get("confidence", ""))
        span.set_attribute("patterns_flagged", str(fraud_analysis.get("patterns_flagged", 0)))
        span.set_attribute("output.value",     json.dumps(fraud_analysis)[:2000])

    return {"artifacts": [{"parts": [{"text": json.dumps(fraud_analysis)}]}]}


def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8003)

