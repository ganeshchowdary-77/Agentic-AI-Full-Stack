"""
Web API Server
Exposes the main entry point for the fraud pipeline, batch submission, 
and SIU chat.
"""

import json
import asyncio
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from ..agents.orchestrator_workflow import orchestrator
from ..agents.siu_chat_agent import siu_chat_agent

app = FastAPI(title="Commercial Auto Fraud SIU Dashboard")

# Store batch results in memory (in production, use Redis or a database)
batch_results_store = {}

@app.post("/api/fraud-detection/batch")
async def submit_batch(request: Request):
    """Accepts a batch of claims and triggers the pipeline."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    
    batch_id = body.get("batch_id", "unknown")
    
    # Run the orchestrator and wait for completion
    try:
        batch_result = await orchestrator.process_batch(body)
        
        # Store the result
        batch_results_store[batch_id] = batch_result.model_dump()
        
        return JSONResponse({
            "status": "complete",
            "batch_id": batch_id,
            "summary": {
                "total_claims": batch_result.total_claims,
                "processed_claims": batch_result.processed_claims,
                "failed_claims": batch_result.failed_claims,
                "tier_distribution": batch_result.tier_distribution,
                "processing_time_ms": batch_result.processing_time_ms
            }
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "batch_id": batch_id,
            "error": str(e)
        }, status_code=500)

@app.get("/api/batch/{batch_id}/results")
async def batch_results(batch_id: str):
    """Get final aggregated results."""
    if batch_id in batch_results_store:
        return JSONResponse(batch_results_store[batch_id])
    return JSONResponse({"error": "Batch not found"}, status_code=404)

@app.get("/api/batch/{batch_id}/claims/{claim_id}")
async def claim_detail(batch_id: str, claim_id: str):
    """Get detailed results for a specific claim."""
    if batch_id not in batch_results_store:
        return JSONResponse({"error": "Batch not found"}, status_code=404)
    
    batch_data = batch_results_store[batch_id]
    for result in batch_data.get("results", []):
        if result["claim_id"] == claim_id:
            return JSONResponse(result)
    
    return JSONResponse({"error": "Claim not found"}, status_code=404)

@app.post("/api/siu/chat")
async def siu_chat(request: Request):
    """SIU Chat interface for querying results."""
    body = await request.json()
    query = body.get("query", "")
    batch_id = body.get("batch_id", "")
    
    # Include batch context if available
    context = ""
    if batch_id and batch_id in batch_results_store:
        context = f"\n\nBatch Context:\n{json.dumps(batch_results_store[batch_id], indent=2)}"
    
    prompt = f"Query: {query}{context}"
    
    try:
        resp = await siu_chat_agent.invoke(prompt)
        return JSONResponse({"response": str(resp.output)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_ui():
    """Serves the premium dashboard UI."""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Error: Dashboard HTML not found</h1>", status_code=404)

@app.get("/")
async def root():
    """Root endpoint redirects to dashboard."""
    return HTMLResponse('<html><body><script>window.location.href="/dashboard";</script></body></html>')
