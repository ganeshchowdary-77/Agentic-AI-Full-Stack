from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class Claimant(BaseModel):
    id: str
    name: str

class Vehicle(BaseModel):
    vin: str
    year: int
    make: str
    model: str

class Provider(BaseModel):
    id: str
    name: str
    type: str

class Claim(BaseModel):
    claim_id: str
    claimant: Claimant
    vehicle: Vehicle
    provider: Provider
    policy_number: str
    loss_date: str
    report_date: str
    claimed_amount: float
    loss_description: str

class EnrichedClaimData(BaseModel):
    claim_id: str
    raw_claim: Claim
    claimant_history: Dict[str, Any]
    provider_network: Dict[str, Any]
    vehicle_valuation: Dict[str, Any]
    policy_details: Dict[str, Any]
    enrichment_status: str

class EvidenceItem(BaseModel):
    indicator: str
    value: str
    benchmark: str
    severity: str
    source: str

class PatternResult(BaseModel):
    pattern: str
    score: float
    severity: str
    evidence: List[EvidenceItem]
    reasoning: str
    exculpatory_factors: List[str]

class FraudAnalysis(BaseModel):
    claim_id: str
    pattern_results: Dict[str, PatternResult]
    composite_score: float
    confidence: str
    priority_tier: str
    patterns_flagged: int

class InvestigationReport(BaseModel):
    claim_id: str
    report_markdown: str

class UserProfile(BaseModel):
    name: str
    role: str
    experience_level: str
    preferred_detail_level: str

