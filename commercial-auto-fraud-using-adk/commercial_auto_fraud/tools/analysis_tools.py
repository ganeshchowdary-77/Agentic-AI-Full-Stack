"""
Analysis Tools — 4 deterministic fraud pattern detection tools.
Each tool computes a 0-100 fraud sub-score with evidence items.
The LLM synthesizes reasoning; these tools provide the raw signal.
"""

import json
from typing import Dict, Any
from google.adk.tools import ToolContext
from ..infrastructure.mock_providers import provider, REPAIR_BENCHMARKS


async def analyze_duplicate_pattern(claim_data_json: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Detects duplicate/similar claim patterns by checking claimant prior claims,
    same VIN across claims, same provider frequency, and prior fraud flags.
    Returns a score (0-100) with evidence items.
    """
    claim = json.loads(claim_data_json) if isinstance(claim_data_json, str) else claim_data_json
    claimant_id = claim.get("claimant", {}).get("id", "")
    vin = claim.get("vehicle", {}).get("vin", "")
    provider_id = claim.get("provider", {}).get("id", "")

    history = await provider.get_claimant_history(claimant_id)
    score = 0.0
    evidence = []

    # Prior fraud flags (major signal)
    fraud_flags = history.get("prior_fraud_flags", 0)
    if fraud_flags > 0:
        points = min(fraud_flags * 20, 40)
        score += points
        evidence.append({"indicator": "Prior fraud flags on claimant", "value": str(fraud_flags), "benchmark": "0", "severity": "major", "source": "claimant_history"})

    # High claim frequency
    freq = history.get("claim_frequency_per_year", 0)
    if freq >= 2.0:
        points = min((freq - 1.0) * 15, 25)
        score += points
        evidence.append({"indicator": "High claim frequency", "value": f"{freq:.1f} claims/year", "benchmark": "< 1.0 claims/year", "severity": "moderate", "source": "claimant_history"})

    # Same VIN with prior claims
    prior_claims = history.get("prior_claims", [])
    same_vin_claims = [c for c in history.get("associated_vehicles", []) if c.get("vin") == vin]
    if len(prior_claims) >= 3:
        score += 15
        evidence.append({"indicator": "Multiple prior claims by same claimant", "value": str(len(prior_claims)), "benchmark": "< 2 typical", "severity": "moderate", "source": "claimant_history"})

    # Multiple policies (potential double-dipping)
    policies = history.get("associated_policies", [])
    if len(policies) >= 2:
        score += 10
        evidence.append({"indicator": "Claimant holds multiple policies", "value": str(len(policies)), "benchmark": "1 policy typical", "severity": "minor", "source": "claimant_history"})

    # High prior payouts
    payouts = history.get("total_prior_payouts", 0)
    if payouts > 50000:
        score += 10
        evidence.append({"indicator": "High cumulative prior payouts", "value": f"${payouts:,.0f}", "benchmark": "< $25,000", "severity": "moderate", "source": "claimant_history"})

    return {"pattern": "duplicate_similar", "score": min(round(score, 1), 100), "evidence": evidence}


async def analyze_timing_pattern(claim_data_json: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Detects suspicious timing patterns by checking policy inception proximity,
    recent coverage changes, and timing of loss relative to policy lifecycle.
    Returns a score (0-100) with evidence items.
    """
    claim = json.loads(claim_data_json) if isinstance(claim_data_json, str) else claim_data_json
    policy_number = claim.get("policy_number", "")

    policy = await provider.get_policy_details(policy_number)
    score = 0.0
    evidence = []

    # Days since inception (new policy + claim = suspicious)
    days = policy.get("days_since_inception", 365)
    if days <= 7:
        score += 40
        evidence.append({"indicator": "Claim filed within 7 days of policy inception", "value": f"{days} days", "benchmark": "> 90 days typical", "severity": "major", "source": "policy_details"})
    elif days <= 30:
        score += 25
        evidence.append({"indicator": "Claim filed within 30 days of policy inception", "value": f"{days} days", "benchmark": "> 90 days typical", "severity": "moderate", "source": "policy_details"})

    # Recent policy changes (coverage upgrades before loss)
    changes = policy.get("recent_policy_changes", [])
    for change in changes:
        change_type = change.get("change_type", "")
        if "coverage" in change_type.lower() or "increased" in change_type.lower():
            score += 30
            evidence.append({"indicator": "Recent coverage upgrade before loss", "value": change.get("details", change_type), "benchmark": "No changes expected near loss date", "severity": "major", "source": "policy_details"})
        elif "added" in change_type.lower():
            score += 10
            evidence.append({"indicator": "Recent policy modification", "value": change.get("details", change_type), "benchmark": "Stable policy expected", "severity": "minor", "source": "policy_details"})

    # Policy status anomalies
    status = policy.get("policy_status", "active")
    if status in ("reinstated", "lapsed"):
        score += 15
        evidence.append({"indicator": f"Policy status: {status}", "value": status, "benchmark": "active", "severity": "moderate", "source": "policy_details"})

    return {"pattern": "suspicious_timing", "score": min(round(score, 1), 100), "evidence": evidence}


async def analyze_inflation_pattern(claim_data_json: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Detects inflated claim amounts by comparing claimed amount to vehicle
    market value and regional repair benchmarks.
    Returns a score (0-100) with evidence items.
    """
    claim = json.loads(claim_data_json) if isinstance(claim_data_json, str) else claim_data_json
    vin = claim.get("vehicle", {}).get("vin", "")
    year = claim.get("vehicle", {}).get("year", 2020)
    make = claim.get("vehicle", {}).get("make", "")
    model = claim.get("vehicle", {}).get("model", "")
    claimed = claim.get("claimed_amount", 0)
    loss_type = claim.get("loss_type", "minor_collision")

    vehicle = await provider.get_vehicle_valuation(vin, year, make, model)
    score = 0.0
    evidence = []
    market_value = vehicle.get("market_value", 25000)

    # Claimed amount vs market value ratio
    if market_value > 0 and claimed > 0:
        ratio = claimed / market_value
        if ratio > 1.3:
            points = min((ratio - 1.0) * 60, 50)
            score += points
            evidence.append({"indicator": "Claimed amount exceeds vehicle market value", "value": f"${claimed:,.0f} (ratio: {ratio:.2f}x)", "benchmark": f"Market value: ${market_value:,.0f}", "severity": "major", "source": "vehicle_valuation"})
        elif ratio > 1.0:
            score += 15
            evidence.append({"indicator": "Claimed amount near vehicle market value", "value": f"${claimed:,.0f} (ratio: {ratio:.2f}x)", "benchmark": f"Market value: ${market_value:,.0f}", "severity": "moderate", "source": "vehicle_valuation"})

    # Claimed amount vs regional repair benchmarks
    benchmarks = REPAIR_BENCHMARKS.get(loss_type, {})
    if benchmarks:
        median = benchmarks.get("median", 0)
        high = benchmarks.get("high", 0)
        if median > 0 and claimed > high:
            ratio_bench = claimed / median
            score += min((ratio_bench - 1.0) * 20, 30)
            evidence.append({"indicator": "Claimed amount exceeds regional high benchmark", "value": f"${claimed:,.0f}", "benchmark": f"Regional median: ${median:,.0f}, high: ${high:,.0f}", "severity": "major", "source": "repair_benchmarks"})
        elif median > 0 and claimed > median * 1.3:
            score += 15
            evidence.append({"indicator": "Claimed amount above regional median", "value": f"${claimed:,.0f}", "benchmark": f"Regional median: ${median:,.0f}", "severity": "moderate", "source": "repair_benchmarks"})

    # Prior total loss on vehicle
    if vehicle.get("prior_total_loss", False):
        score += 15
        evidence.append({"indicator": "Vehicle has prior total loss history", "value": "Yes", "benchmark": "No prior total loss", "severity": "moderate", "source": "vehicle_valuation"})

    # Rebuilt title
    titles = vehicle.get("title_history", [])
    if "rebuilt" in titles or "salvage" in titles:
        score += 10
        evidence.append({"indicator": "Vehicle has salvage/rebuilt title", "value": ", ".join(titles), "benchmark": "Clean title", "severity": "minor", "source": "vehicle_valuation"})

    return {"pattern": "inflated_amounts", "score": min(round(score, 1), 100), "evidence": evidence}


async def analyze_provider_network(claim_data_json: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Detects provider network anomalies including high billing ratios,
    excessive flagged claims, referral ring patterns, and license issues.
    Returns a score (0-100) with evidence items.
    """
    claim = json.loads(claim_data_json) if isinstance(claim_data_json, str) else claim_data_json
    provider_id = claim.get("provider", {}).get("id", "")
    provider_type = claim.get("provider", {}).get("type", "repair_shop")

    prov_data = await provider.get_provider_network(provider_id, provider_type)
    score = 0.0
    evidence = []

    # Network risk level
    risk = prov_data.get("network_risk", "LOW")
    if risk == "CRITICAL":
        score += 40
        evidence.append({"indicator": "Provider network risk: CRITICAL", "value": risk, "benchmark": "LOW", "severity": "major", "source": "provider_network"})
    elif risk == "HIGH":
        score += 30
        evidence.append({"indicator": "Provider network risk: HIGH", "value": risk, "benchmark": "LOW", "severity": "major", "source": "provider_network"})
    elif risk == "MEDIUM":
        score += 15
        evidence.append({"indicator": "Provider network risk: MEDIUM", "value": risk, "benchmark": "LOW", "severity": "moderate", "source": "provider_network"})

    # Billing ratio
    billing_ratio = prov_data.get("billing_ratio", 1.0)
    if billing_ratio > 2.0:
        score += 25
        evidence.append({"indicator": "Provider billing significantly above regional average", "value": f"{billing_ratio:.2f}x regional avg", "benchmark": "1.0x (at regional average)", "severity": "major", "source": "provider_network"})
    elif billing_ratio > 1.5:
        score += 10
        evidence.append({"indicator": "Provider billing above regional average", "value": f"{billing_ratio:.2f}x regional avg", "benchmark": "1.0x", "severity": "moderate", "source": "provider_network"})

    # Flagged claims count
    flagged = prov_data.get("flagged_claims_count", 0)
    if flagged > 20:
        score += 20
        evidence.append({"indicator": "Provider has high flagged claims count", "value": str(flagged), "benchmark": "< 5", "severity": "major", "source": "provider_network"})
    elif flagged > 5:
        score += 10
        evidence.append({"indicator": "Provider has elevated flagged claims", "value": str(flagged), "benchmark": "< 5", "severity": "moderate", "source": "provider_network"})

    # License status
    license_status = prov_data.get("license_status", "active")
    if license_status != "active":
        score += 15
        evidence.append({"indicator": f"Provider license status: {license_status}", "value": license_status, "benchmark": "active", "severity": "major", "source": "provider_network"})

    # Referral connections (ring indicator)
    referrals = prov_data.get("referral_connections", [])
    if referrals:
        for ref in referrals:
            if ref.get("shared_claims", 0) > 10:
                score += 10
                evidence.append({"indicator": f"Referral ring with {ref['provider_name']}", "value": f"{ref['shared_claims']} shared claims", "benchmark": "< 3 shared claims", "severity": "major", "source": "provider_network"})

    return {"pattern": "provider_network", "score": min(round(score, 1), 100), "evidence": evidence}
