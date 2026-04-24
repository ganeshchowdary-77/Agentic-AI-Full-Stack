"""
Investigation Report Generator — Pydantic Schemas
===================================================
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Tool 3: calculate_priority_score ─────────────────────────────────────────

class PriorityScore(BaseModel):
    priority_score:     float
    priority_rank:      str   # P1-Immediate | P2-Urgent | P3-Standard | P4-Monitor
    reasoning:          str
    estimated_exposure: float  # claim_amount * (fraud_score / 100)


# ── Tool 2: format_evidence_summary input ─────────────────────────────────────

class EvidenceFlag(BaseModel):
    indicator: str
    value:     str = ""
    benchmark: str = ""
    severity:  str = "minor"
    source:    str = ""
    pattern:   str = ""   # which fraud pattern produced this


# ── Tool 1 / Full report output ────────────────────────────────────────────────

class ReportInput(BaseModel):
    claim_id:       str
    fraud_analysis: Dict[str, Any]
    enriched_data:  Dict[str, Any]


class ReportOutput(BaseModel):
    claim_id:       str
    report_markdown: str
    priority:       PriorityScore
    generated_at:   str
    word_count:     int = 0

