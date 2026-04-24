"""
Fraud Pattern Analyzer — Pydantic Schemas
==========================================
Strict input/output contracts for all 4 pattern tools and composite output.
Matches spec §15.3 Fraud Analysis Output Schema.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── Per-pattern evidence item ─────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    indicator: str
    value:     str
    benchmark: str = ""
    severity:  str = "minor"   # minor | moderate | major
    source:    str = ""


# ── Single pattern result (output of each CoT tool) ──────────────────────────

class PatternResult(BaseModel):
    pattern:             str
    score:               float = Field(..., ge=0, le=100)
    severity:            str   # clean | minor | notable | significant | critical
    flags:               List[str] = []       # spec §15.3 — human-readable bullet flags
    evidence:            List[EvidenceItem] = []
    reasoning:           str = ""
    exculpatory_factors: List[str] = []


# ── Composite fraud analysis output (spec §15.3) ──────────────────────────────

class FraudAnalysisOutput(BaseModel):
    claim_id:           str
    analysis_timestamp: str = Field(default_factory=_utcnow)
    pattern_results:    Dict[str, PatternResult]
    composite_score:    float = Field(..., ge=0, le=100)
    confidence:         str   # high | medium | low
    priority_tier:      str   # critical | high | medium | low
    patterns_flagged:   int
    classification:     str = "CLEAN"        # FLAGGED | CLEAN
    priority:           str = "P4-Routine"   # P1-Immediate | P2-Urgent | P3-Standard | P4-Routine
    narrative:          str = ""             # CoT coherence summary from composite_score_cot

    # Weights stored for audit / Arize tracing
    weights: Dict[str, float] = {
        "duplicate_similar": 0.30,
        "suspicious_timing":  0.20,
        "inflated_amounts":   0.25,
        "provider_network":   0.25,
    }
