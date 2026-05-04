"""
Domain Schemas — Commercial Auto Fraud Detection Pipeline

Data contracts for the entire pipeline. All fraud scores use 0-100 scale.
Priority tiers: critical (>=80), high (>=60), medium (>=40), low (<40).
Confidence: high (3+ patterns flagged), medium (2), low (1 or weak evidence).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================
# ENUMS
# ============================================================

class ClaimStatus(str, Enum):
    """Lifecycle states for a claim moving through the pipeline."""
    PENDING = "pending"
    ENRICHING = "enriching"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETE = "complete"
    FAILED = "failed"


class PriorityTier(str, Enum):
    """Fraud priority classification based on composite score."""
    CRITICAL = "critical"   # >= 80
    HIGH = "high"           # >= 60
    MEDIUM = "medium"       # >= 40
    LOW = "low"             # < 40


class ConfidenceLevel(str, Enum):
    """Confidence in fraud assessment based on evidence density."""
    HIGH = "high"       # 3+ patterns flagged (score > 40)
    MEDIUM = "medium"   # 2 patterns flagged
    LOW = "low"         # 1 pattern or weak evidence


class PatternSeverity(str, Enum):
    """Severity classification for individual fraud patterns."""
    CLEAN = "clean"             # 0-20
    MINOR = "minor"             # 21-40
    NOTABLE = "notable"         # 41-60
    SIGNIFICANT = "significant" # 61-80
    CRITICAL = "critical"       # 81-100


# ============================================================
# CLAIM INPUT (Raw from batch JSON)
# ============================================================

class ClaimantInfo(BaseModel):
    """Claimant identity from the raw claim."""
    id: str
    name: str


class ProviderInfo(BaseModel):
    """Provider reference from the raw claim."""
    id: str
    type: str  # repair_shop, medical, attorney, towing


class VehicleInfo(BaseModel):
    """Vehicle details from the raw claim."""
    vin: str
    year: int
    make: str
    model: str


class ClaimInput(BaseModel):
    """A single raw claim as received in the batch JSON."""
    claim_id: str
    claimant: ClaimantInfo
    provider: ProviderInfo
    vehicle: VehicleInfo
    policy_number: str
    claimed_amount: float
    loss_date: str
    loss_type: str
    description: str


# ============================================================
# ENRICHMENT DATA (from 4 external sources)
# ============================================================

class PriorClaim(BaseModel):
    """A single historical claim from claimant records."""
    claim_id: str
    loss_date: str
    loss_type: str
    claimed_amount: float
    outcome: str
    fraud_flag: bool = False


class ClaimantHistory(BaseModel):
    """Claimant history from the claims database."""
    claimant_id: str
    total_prior_claims: int = 0
    prior_claims: List[PriorClaim] = Field(default_factory=list)
    known_addresses: List[str] = Field(default_factory=list)
    associated_vehicles: List[Dict[str, Any]] = Field(default_factory=list)
    associated_policies: List[str] = Field(default_factory=list)
    prior_fraud_flags: int = 0
    claim_frequency_per_year: float = 0.0
    total_prior_payouts: float = 0.0


class ReferralConnection(BaseModel):
    """A referral link between two providers."""
    provider_id: str
    provider_name: str
    shared_claims: int = 0


class ProviderData(BaseModel):
    """Provider information from the provider database."""
    provider_id: str
    provider_name: str = ""
    provider_type: str = ""
    license_status: str = "active"
    total_claims_served: int = 0
    average_billing_amount: float = 0.0
    regional_average_billing: float = 0.0
    billing_ratio: float = 1.0
    referral_connections: List[ReferralConnection] = Field(default_factory=list)
    geographic_service_area: str = ""
    claims_outside_service_area: int = 0
    flagged_claims_count: int = 0
    network_risk: str = "LOW"


class RepairBenchmark(BaseModel):
    """Regional repair cost benchmarks for a damage type."""
    low: float = 0.0
    median: float = 0.0
    high: float = 0.0


class VehicleValuation(BaseModel):
    """Vehicle valuation data including repair benchmarks."""
    vin: str
    year: int = 0
    make: str = ""
    model: str = ""
    market_value: float = 0.0
    salvage_value: float = 0.0
    total_loss_threshold: float = 0.0
    regional_repair_benchmarks: Dict[str, RepairBenchmark] = Field(default_factory=dict)
    prior_claims_on_vin: List[Dict[str, Any]] = Field(default_factory=list)
    title_history: List[str] = Field(default_factory=list)
    prior_total_loss: bool = False


class PolicyChange(BaseModel):
    """A single policy modification event."""
    change_date: str
    change_type: str
    details: str = ""


class PolicyDetails(BaseModel):
    """Policy information from the policy administration system."""
    policy_number: str
    inception_date: str = ""
    expiration_date: str = ""
    days_since_inception: int = 365
    days_until_expiration: int = 365
    coverage_type: str = ""
    coverage_limits: Dict[str, Any] = Field(default_factory=dict)
    premium_amount: float = 0.0
    premium_payment_history: List[Dict[str, Any]] = Field(default_factory=list)
    recent_policy_changes: List[PolicyChange] = Field(default_factory=list)
    vehicles_on_policy: List[Dict[str, Any]] = Field(default_factory=list)
    policy_status: str = "active"
    lapse_history: List[Dict[str, Any]] = Field(default_factory=list)


class EnrichedClaim(BaseModel):
    """A claim augmented with all 4 enrichment data sources."""
    claim_id: str
    raw_claim: ClaimInput
    claimant_history: ClaimantHistory
    provider_data: ProviderData
    vehicle_valuation: VehicleValuation
    policy_details: PolicyDetails
    enrichment_status: str = "complete"
    enrichment_timestamp: str = ""


# ============================================================
# FRAUD PATTERN ANALYSIS (4 patterns, 0-100 scores)
# ============================================================

class EvidenceItem(BaseModel):
    """A single piece of fraud evidence with attribution."""
    indicator: str
    value: str = ""
    benchmark: str = ""
    severity: str = "minor"  # minor, moderate, major
    source: str = ""


class PatternResult(BaseModel):
    """Result from a single fraud pattern analysis."""
    pattern: str
    score: float = 0.0  # 0-100
    severity: PatternSeverity = PatternSeverity.CLEAN
    evidence: List[EvidenceItem] = Field(default_factory=list)
    reasoning: str = ""
    exculpatory_factors: List[str] = Field(default_factory=list)


class CompositeScore(BaseModel):
    """Weighted composite fraud score with full pattern breakdown."""
    claim_id: str
    pattern_results: Dict[str, PatternResult] = Field(default_factory=dict)
    composite_score: float = 0.0  # 0-100
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    priority_tier: PriorityTier = PriorityTier.LOW
    patterns_flagged: int = 0


# ============================================================
# INVESTIGATION REPORT
# ============================================================

class RecommendedAction(BaseModel):
    """A specific investigative action item."""
    action: str
    priority: str = "standard"
    related_pattern: str = ""


class InvestigationReport(BaseModel):
    """Formatted investigation report for SIU case files."""
    claim_id: str
    executive_summary: str = ""
    pattern_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_table: str = ""
    recommended_actions: List[RecommendedAction] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    priority_score: float = 0.0
    priority_rank: str = "P3-Standard"
    estimated_exposure: float = 0.0
    report_markdown: str = ""


# ============================================================
# BATCH RESULTS
# ============================================================

class ClaimResult(BaseModel):
    """Per-claim result summary for batch aggregation."""
    claim_id: str
    claimant_name: str = ""
    claimed_amount: float = 0.0
    composite_score: float = 0.0
    priority_tier: PriorityTier = PriorityTier.LOW
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    patterns_flagged: int = 0
    top_pattern: str = ""
    top_pattern_score: float = 0.0
    has_report: bool = False
    processing_time_ms: float = 0.0


class BatchResult(BaseModel):
    """Aggregated batch processing results."""
    batch_id: str
    batch_name: str = ""
    total_claims: int = 0
    processed_claims: int = 0
    failed_claims: int = 0
    results: List[ClaimResult] = Field(default_factory=list)
    tier_distribution: Dict[str, int] = Field(default_factory=dict)
    top_triggered_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    provider_frequency: Dict[str, int] = Field(default_factory=dict)
    processing_time_ms: float = 0.0
    timestamp: str = ""


# ============================================================
# SCORING UTILITIES
# ============================================================

def classify_severity(score: float) -> PatternSeverity:
    """Classify a 0-100 score into a severity level."""
    if score >= 81:
        return PatternSeverity.CRITICAL
    elif score >= 61:
        return PatternSeverity.SIGNIFICANT
    elif score >= 41:
        return PatternSeverity.NOTABLE
    elif score >= 21:
        return PatternSeverity.MINOR
    else:
        return PatternSeverity.CLEAN


def classify_tier(composite_score: float) -> PriorityTier:
    """Classify a composite score into a priority tier."""
    if composite_score >= 80:
        return PriorityTier.CRITICAL
    elif composite_score >= 60:
        return PriorityTier.HIGH
    elif composite_score >= 40:
        return PriorityTier.MEDIUM
    else:
        return PriorityTier.LOW


def classify_confidence(patterns_flagged: int) -> ConfidenceLevel:
    """Classify confidence based on number of patterns flagged (score > 40)."""
    if patterns_flagged >= 3:
        return ConfidenceLevel.HIGH
    elif patterns_flagged == 2:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


def compute_composite_score(
    duplicate_score: float,
    timing_score: float,
    inflation_score: float,
    provider_score: float,
) -> float:
    """
    Weighted composite fraud score.
    Weights: Duplicate 30%, Timing 20%, Inflation 25%, Provider 25%.
    """
    return round(
        duplicate_score * 0.30
        + timing_score * 0.20
        + inflation_score * 0.25
        + provider_score * 0.25,
        1,
    )
