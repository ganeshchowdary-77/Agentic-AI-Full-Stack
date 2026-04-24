"""
Enrichment Agent — Pydantic Schemas
=====================================
Strict input/output contracts for the Claim Data Enrichment Agent.
All data crossing A2A boundaries is validated against these schemas.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Input ─────────────────────────────────────────────────────────────────────

class ClaimantRef(BaseModel):
    id: str
    name: str

class ProviderRef(BaseModel):
    id: str
    type: str = "unknown"

class VehicleRef(BaseModel):
    vin: str
    year: int
    make: str
    model: str

class RawClaimInput(BaseModel):
    claim_id: str
    claimant: ClaimantRef
    provider: ProviderRef
    vehicle: VehicleRef
    policy_number: str
    claimed_amount: float = Field(..., gt=0)
    loss_date: str
    loss_type: str = "major_collision"
    description: str = ""


# ── Output ────────────────────────────────────────────────────────────────────

class PriorClaim(BaseModel):
    claim_id: str
    loss_date: str
    loss_type: str = ""
    claimed_amount: float = 0
    outcome: str = ""
    fraud_flag: bool = False

class ClaimantHistory(BaseModel):
    claimant_id: str
    total_prior_claims: int = 0
    prior_fraud_flags: int = 0
    claim_frequency_per_year: float = 0.0
    total_prior_payouts: float = 0.0
    prior_claims: List[PriorClaim] = []
    associated_vehicles: List[Dict[str, Any]] = []
    known_addresses: List[str] = []

class ReferralConnection(BaseModel):
    provider_id: str
    provider_name: str = ""
    shared_claims: int = 0

class ProviderNetwork(BaseModel):
    provider_id: str
    provider_type: str
    license_status: str = "active"
    total_claims_served: int = 0
    average_billing_amount: float = 0.0
    regional_average_billing: float = 0.0
    billing_ratio: float = 1.0
    flagged_claims_count: int = 0
    referral_connections: List[ReferralConnection] = []
    geographic_service_area: str = ""
    claims_outside_service_area: int = 0
    provider_name: str = ""

class RegionalBenchmarks(BaseModel):
    low: float = 0
    median: float = 0
    high: float = 0

class VehicleValuation(BaseModel):
    vin: str
    year: int
    make: str
    model: str
    market_value: float
    salvage_value: float
    total_loss_threshold: float
    regional_repair_benchmarks: Dict[str, RegionalBenchmarks] = {}
    prior_claims_on_vin: List[Dict[str, Any]] = []
    title_history: List[str] = []

class PolicyChange(BaseModel):
    change_date: str
    change_type: str
    details: str = ""

class PolicyDetails(BaseModel):
    policy_number: str
    inception_date: str = ""
    expiration_date: str = ""
    days_since_inception: int = 999
    days_until_expiration: int = 999
    coverage_type: str = "comprehensive"
    coverage_limits: Dict[str, float] = {}
    premium_amount: float = 0.0
    premium_payment_history: List[Dict[str, Any]] = []
    recent_policy_changes: List[PolicyChange] = []
    vehicles_on_policy: List[Dict[str, Any]] = []
    policy_status: str = "active"
    lapse_history: List[Dict[str, Any]] = []

class EnrichedClaimOutput(BaseModel):
    claim_id: str
    raw_claim: Dict[str, Any]
    claimant_history: ClaimantHistory
    provider_network: ProviderNetwork
    vehicle_valuation: VehicleValuation
    policy_details: PolicyDetails
    enrichment_status: str = "complete"
    enrichment_timestamp: str = ""

