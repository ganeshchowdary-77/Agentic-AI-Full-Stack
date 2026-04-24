"""
Orchestrator Agent — Pydantic Schemas
=======================================
Strict input/output contracts for all 5 Orchestrator tools.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Tool 1: ingest_claim_batch ────────────────────────────────────────────────

class InvalidClaim(BaseModel):
    claim_id: str
    errors: List[str]

class BatchIngestionOutput(BaseModel):
    batch_id: str
    batch_name: str
    total_claims: int
    valid_claims: List[Dict[str, Any]]
    invalid_claims: List[InvalidClaim]
    validation_summary: str


# ── Tool 2: enrich_claim ──────────────────────────────────────────────────────

class EnrichClaimOutput(BaseModel):
    claim_id: str
    claimant_history: Dict[str, Any]
    provider_network: Dict[str, Any]
    vehicle_valuation: Dict[str, Any]
    policy_details: Dict[str, Any]
    enrichment_status: str = Field(default="complete",
                                   pattern="^(complete|partial|failed)$")
    enrichment_timestamp: str


# ── Tool 3: analyze_fraud_patterns ───────────────────────────────────────────

class PatternResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    severity: str
    evidence: List[Dict[str, Any]]
    reasoning: str
    exculpatory_factors: List[str] = []

class FraudAnalysisOutput(BaseModel):
    claim_id: str
    pattern_results: Dict[str, PatternResult]
    composite_score: float = Field(..., ge=0, le=100)
    confidence: str = Field(..., pattern="^(high|medium|low)$")
    priority_tier: str = Field(..., pattern="^(critical|high|medium|low)$")
    patterns_flagged: int


# ── Tool 4: generate_investigation_report ─────────────────────────────────────

class ReportOutput(BaseModel):
    claim_id: str
    report_markdown: str
    generated_at: str


# ── Tool 5: query_results ─────────────────────────────────────────────────────

class QueryInput(BaseModel):
    query: str = Field(..., min_length=1)
    persona: str = Field(default="kevin", pattern="^(kevin|diana)$")

class QueryOutput(BaseModel):
    query: str
    persona: str
    response: str


# ── Batch Pipeline Output (full run) ─────────────────────────────────────────

class ClaimPipelineResult(BaseModel):
    claim_id: str
    enriched: Dict[str, Any]
    fraud_analysis: Dict[str, Any]
    report: Optional[str] = None

class BatchPipelineOutput(BaseModel):
    batch_id: str
    batch_name: str
    total_claims: int
    tier_distribution: Dict[str, int]
    top_triggered_patterns: Dict[str, int]
    repeat_providers: Dict[str, int]
    validation_summary: str
    invalid_claims: List[InvalidClaim]
    results: List[ClaimPipelineResult]

