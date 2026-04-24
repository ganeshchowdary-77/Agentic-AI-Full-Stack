"""
Fraud Pipeline Orchestrator — Web Server (Port 8001)
=====================================================
Serves the dashboard UI and exposes the A2A-compatible REST API.
Two endpoints:
  GET  /api/run   — Trigger batch pipeline (reads weekly_auto_claims.json)
  POST /api/chat  — SIU investigator query chat (Tool 5)
  GET  /.well-known/agent.json — A2A agent card discovery
"""

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from src.config.container import Container
from src.infrastructure.telemetry.arize_wrappers import flush_telemetry, span_chain
from src.application.services.siu_query_service import load_profile

app = FastAPI(title="Commercial Auto Fraud Pipeline", version="1.0.0")
container = Container()

HTML = open(os.path.join(os.path.dirname(__file__), "dashboard.html"), encoding="utf-8").read()


# ── A2A Agent Card ────────────────────────────────────────────────────────────

@app.get("/.well-known/agent.json")
def get_agent_card():
    return {
        "name": "fraud_pipeline_orchestrator",
        "description": (
            "Commercial auto insurance fraud detection pipeline orchestrator. "
            "Ingests claim batches, orchestrates dual-level parallel processing "
            "(N claims × 4 fraud patterns), aggregates results ranked by composite "
            "fraud score, and provides a status/query chat for SIU investigators."
        ),
        "url": "http://localhost:8001",
        "version": "1.0.0",
        "capabilities": {"streaming": True, "pushNotifications": False},
        "skills": [
            {
                "id": "batch-fraud-pipeline",
                "name": "Batch Fraud Detection Pipeline",
                "description": (
                    "Processes a batch of 5–50 commercial auto claims through parallel "
                    "enrichment, 4-pattern fraud analysis, composite scoring, and "
                    "investigation report generation. Returns claims ranked by fraud score "
                    "with tier classification (Critical/High/Medium/Low)."
                ),
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
            {
                "id": "siu-query-chat",
                "name": "SIU Investigator Query Chat",
                "description": (
                    "Lightweight chat interface for SIU investigators to check pipeline status, "
                    "query batch results, drill into specific claims, filter by fraud pattern, "
                    "and analyze provider frequency — with responses adapted to investigator "
                    "experience level (Kevin/junior vs Diana/senior)."
                ),
                "inputModes": ["text"],
                "outputModes": ["text"],
            },
        ],
        "tools": [t["name"] for t in container.orchestrator._registry.list_tools()],
    }


# ── Dashboard UI ──────────────────────────────────────────────────────────────

@app.get("/")
async def get_dashboard():
    return HTMLResponse(content=HTML)


# ── Batch Pipeline API ────────────────────────────────────────────────────────

@app.get("/api/run")
async def run_pipeline():
    try:
        path = os.path.join(os.getcwd(), "weekly_auto_claims.json")
        with open(path) as f:
            batch_json = f.read()
        with span_chain("Orchestrator: Batch Pipeline [API Trigger]"):
            payload_str = await container.orchestrator.process_claim_batch(batch_json)
        flush_telemetry()
        return {"payload": payload_str}
    except Exception as e:
        import traceback
        return {
            "payload": json.dumps({
                "summary": f"Failed: {e}\n{traceback.format_exc()}",
                "batch_results": {},
            })
        }


# ── SIU Query Chat API ────────────────────────────────────────────────────────

@app.post("/api/chat")
async def siu_chat(request: Request):
    body    = await request.json()
    query   = body.get("query", "")
    persona = body.get("persona", "kevin")
    profile = load_profile(persona)
    response = await container.orchestrator.handle_siu_query(query, profile)
    flush_telemetry()
    return {"response": response}

