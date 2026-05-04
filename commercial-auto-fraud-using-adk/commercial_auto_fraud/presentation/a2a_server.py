"""
A2A Server Implementation

Exposes ADK agents via FastAPI for inter-agent communication using the A2A protocol.
This module creates separate FastAPI apps for each agent type.
"""

from fastapi import FastAPI
from commercial_auto_fraud.agents.enrichment_agent import enrichment_agent
from commercial_auto_fraud.agents.analyzer_agent import analyzer_agent
from commercial_auto_fraud.agents.report_agent import report_agent
from commercial_auto_fraud.agents.siu_chat_agent import siu_chat_agent

# Create individual FastAPI apps for each agent
enrichment_app = FastAPI(title="Enrichment A2A Agent")
analyzer_app = FastAPI(title="Analyzer A2A Agent")
report_app = FastAPI(title="Report A2A Agent")
siu_app = FastAPI(title="SIU Chat A2A Agent")

@enrichment_app.post("/task")
async def enrichment_task(request: dict):
    """Enrichment agent endpoint."""
    try:
        result = await enrichment_agent.invoke(request)
        return {"status": "success", "output": str(result.output)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@enrichment_app.get("/")
async def enrichment_root():
    return {"agent": "enrichment", "status": "ready"}

@analyzer_app.post("/task")
async def analyzer_task(request: dict):
    """Analyzer agent endpoint."""
    try:
        result = await analyzer_agent.invoke(request)
        return {"status": "success", "output": str(result.output)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@analyzer_app.get("/")
async def analyzer_root():
    return {"agent": "analyzer", "status": "ready"}

@report_app.post("/task")
async def report_task(request: dict):
    """Report agent endpoint."""
    try:
        result = await report_agent.invoke(request)
        return {"status": "success", "output": str(result.output)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@report_app.get("/")
async def report_root():
    return {"agent": "report", "status": "ready"}

@siu_app.post("/task")
async def siu_task(request: dict):
    """SIU chat agent endpoint."""
    try:
        result = await siu_chat_agent.invoke(request)
        return {"status": "success", "output": str(result.output)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@siu_app.get("/")
async def siu_root():
    return {"agent": "siu_chat", "status": "ready"}
