"""
Orchestrator Agent — Tools 2–5
================================
Tools 1 (IngestBatchTool) is in ingest_batch.py.
These 4 thin delegation tools complete the orchestrator's tool registry.

Each inherits BaseTool → automatic Arize TOOL span via run().
"""

import json
from datetime import datetime

from src.infrastructure.tools.base_tool import BaseTool
from src.application.services.siu_query_service import answer_siu_query


class EnrichClaimTool(BaseTool):
    """Tool 2: Delegates enrichment to Claim Data Enrichment Agent (A2A :8002)."""
    name = "enrich_claim"
    description = (
        "Sends a single validated raw claim to the Claim Data Enrichment Agent. "
        "The agent calls 4 tools (claimant history, provider network, vehicle valuation, "
        "policy details) and returns a structured enriched data package."
    )

    def __init__(self, enrichment_client):
        self._client = enrichment_client

    async def execute(self, claim: dict) -> dict:
        enriched = await self._client.enrich(claim)
        enriched.setdefault("enrichment_timestamp", datetime.utcnow().isoformat())
        enriched.setdefault("enrichment_status", "complete")
        return enriched


class AnalyzeFraudPatternsTool(BaseTool):
    """Tool 3: Delegates 4-pattern parallel analysis to Fraud Pattern Analyzer (A2A :8003)."""
    name = "analyze_fraud_patterns"
    description = (
        "Sends an enriched claim to the Fraud Pattern Analyzer Agent. "
        "Runs 4 fraud detection patterns in parallel (Level-2 parallelism): "
        "Duplicate/Similar (30%), Suspicious Timing (20%), "
        "Inflated Amounts (25%), Provider Network (25%). "
        "Returns composite_score, confidence, priority_tier, and full pattern_results."
    )

    def __init__(self, analyzer_client):
        self._client = analyzer_client

    async def execute(self, enriched_claim: dict) -> dict:
        return await self._client.analyze(enriched_claim)


class GenerateReportTool(BaseTool):
    """Tool 4: Delegates report generation to Investigation Report Generator (A2A :8004)."""
    name = "generate_investigation_report"
    description = (
        "Sends fraud analysis results to the Investigation Report Generator Agent. "
        "Called only for claims with composite_score >= 40. "
        "Returns a Markdown-formatted 7-section investigation report."
    )

    def __init__(self, report_client, storage):
        self._client = report_client
        self._storage = storage

    async def execute(self, claim_id: str, fraud_analysis: dict, enriched_data: dict) -> str:
        report = await self._client.generate_report(claim_id, fraud_analysis, enriched_data)
        await self._storage.save_investigation_report(claim_id, {"report": report})
        return report


class QueryResultsTool(BaseTool):
    """Tool 5: SIU investigator query chat — profile-adaptive responses."""
    name = "query_results"
    description = (
        "Searches stored batch results to answer SIU investigator queries. "
        "Supports: pipeline status, batch summary, claim drill-down, "
        "pattern filtering, provider frequency analysis, score explanation. "
        "Response format adapts to user profile: verbose for Kevin (junior), "
        "concise tables for Diana (senior)."
    )

    def __init__(self):
        self._batch_results: dict = {}
        # Live pipeline progress (updated by OrchestratorAgent during batch run)
        self._progress_completed: int = 0
        self._progress_total: int = 0
        self._pipeline_running: bool = False

    def update_progress(self, completed: int, total: int, running: bool = True):
        """Called by OrchestratorAgent as each claim finishes (live status)."""
        self._progress_completed = completed
        self._progress_total = total
        self._pipeline_running = running

    def update_batch_results(self, batch_results: dict):
        """Called by OrchestratorAgent after full pipeline completes."""
        self._batch_results = batch_results
        self._pipeline_running = False
        self._progress_completed = batch_results.get("total_claims", 0)
        self._progress_total = batch_results.get("total_claims", 0)

    async def execute(self, query: str, profile: dict) -> str:
        q = query.lower()
        # Status check works even mid-run
        if any(kw in q for kw in ["status", "progress", "how many", "done", "complete", "running"]):
            if self._pipeline_running:
                remaining = self._progress_total - self._progress_completed
                return (
                    f"⏳ Pipeline in progress: **{self._progress_completed}/{self._progress_total}** "
                    f"claims complete. ~{remaining * 15} seconds remaining."
                )
            elif self._batch_results:
                total = self._batch_results.get("total_claims", 0)
                return f"✅ Pipeline complete. **{total} claims** analyzed. Ask me for a summary or details on any claim."
            else:
                return "⚠️ No pipeline has been started yet. Trigger a batch run to begin."

        if not self._batch_results:
            return (
                "⚠️ No pipeline results available yet. "
                "Run the claim batch first, then ask me your question."
            )
        return answer_siu_query(query, self._batch_results, profile)


