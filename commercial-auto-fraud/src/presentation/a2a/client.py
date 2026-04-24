"""
A2A Client — with manual W3C Trace Context Propagation
--------------------------------------------------------
The Orchestrator lives in one process; the sub-agents in separate threads.
We manually inject the `traceparent` header on every outgoing HTTP call so
that sub-agent spans are linked to the parent Orchestrator span in Arize.
"""

import httpx
import json
from opentelemetry import propagate, trace


def _inject_trace_headers() -> dict:
    """Return W3C traceparent/tracestate headers for the current span context."""
    headers = {}
    propagate.inject(headers)
    return headers


class A2AEnrichmentClient:
    def __init__(self, url: str = "http://localhost:8002"):
        self.url = url

    async def enrich(self, claim: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/v1/tasks",
                json={
                    "id": f"enrich-{claim['claim_id']}",
                    "skill_id": "claim-enrichment",
                    "message": {"parts": [{"text": json.dumps(claim)}]},
                },
                headers=_inject_trace_headers(),
                timeout=30.0,
            )
            data = response.json()
            return json.loads(data["artifacts"][0]["parts"][0]["text"])


class A2AAnalyzerClient:
    def __init__(self, url: str = "http://localhost:8003"):
        self.url = url

    async def analyze(self, enriched_claim: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/v1/tasks",
                json={
                    "id": f"analyze-{enriched_claim['claim_id']}",
                    "skill_id": "fraud-pattern-analysis",
                    "message": {"parts": [{"text": json.dumps(enriched_claim)}]},
                },
                headers=_inject_trace_headers(),
                timeout=60.0,
            )
            data = response.json()
            return json.loads(data["artifacts"][0]["parts"][0]["text"])


class A2AReportGeneratorClient:
    def __init__(self, url: str = "http://localhost:8004"):
        self.url = url

    async def generate_report(self, claim_id: str, fraud_analysis: dict, enriched_data: dict) -> str:
        async with httpx.AsyncClient() as client:
            payload = {
                "claim_id": claim_id,
                "fraud_analysis": fraud_analysis,
                "enriched_data": enriched_data,
            }
            response = await client.post(
                f"{self.url}/v1/tasks",
                json={
                    "id": f"report-{claim_id}",
                    "skill_id": "investigation-report",
                    "message": {"parts": [{"text": json.dumps(payload)}]},
                },
                headers=_inject_trace_headers(),
                timeout=60.0,
            )
            data = response.json()
            return data["artifacts"][0]["parts"][0]["text"]

