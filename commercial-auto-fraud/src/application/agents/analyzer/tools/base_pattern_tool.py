"""
Analyzer Tools — Base Pattern Tool
====================================
All 4 CoT pattern tools inherit from BasePatternTool.
Shared logic: prompt loading via PromptFacade, LLM call, JSON parse, schema validation.

Adding a 5th pattern (e.g., Staged Accident) in the future:
  1. Create storage/prompts/staged_accident_cot/v1.yaml
  2. Create tools/staged_accident.py (subclass BasePatternTool)
  3. Register in the agent's ToolRegistry
  Done. Zero changes to agent.py or schemas.py.
"""

import json
import re
from typing import Any, Dict

from src.infrastructure.tools.base_tool import BaseTool
from src.prompt_manager.engine.facade import PromptFacade
from src.application.agents.analyzer.schemas import PatternResult, EvidenceItem


def _extract_pattern_data(pattern_key: str, enriched: dict) -> str:
    """
    Returns a compact, pattern-relevant slice of enriched data.
    Prevents the LLM from being overwhelmed by irrelevant fields.
    """
    raw     = enriched.get("raw_claim", {})
    history = enriched.get("claimant_history", {})
    network = enriched.get("provider_network", {})
    vehicle = enriched.get("vehicle_valuation", {})
    policy  = enriched.get("policy_details", {})

    if pattern_key == "duplicate_similar":
        return json.dumps({
            "claim_id":           enriched.get("claim_id"),
            "claimant_id":        raw.get("claimant", {}).get("id"),
            "vehicle_vin":        raw.get("vehicle", {}).get("vin"),
            "loss_type":          raw.get("loss_type"),
            "loss_date":          raw.get("loss_date"),
            "total_prior_claims": history.get("total_prior_claims", 0),
            "prior_fraud_flags":  history.get("prior_fraud_flags", 0),
            "claim_frequency_per_year": history.get("claim_frequency_per_year", 0),
            "prior_claims":       history.get("prior_claims", []),
            "associated_vehicles": history.get("associated_vehicles", []),
            "prior_claims_on_vin": vehicle.get("prior_claims_on_vin", []),
            "vehicles_on_policy": policy.get("vehicles_on_policy", []),
        }, indent=2)

    elif pattern_key == "suspicious_timing":
        return json.dumps({
            "claim_id":              enriched.get("claim_id"),
            "loss_date":             raw.get("loss_date"),
            "inception_date":        policy.get("inception_date"),
            "expiration_date":       policy.get("expiration_date"),
            "days_since_inception":  policy.get("days_since_inception", 999),
            "days_until_expiration": policy.get("days_until_expiration", 999),
            "policy_status":         policy.get("policy_status"),
            "recent_policy_changes": policy.get("recent_policy_changes", []),
            "lapse_history":         policy.get("lapse_history", []),
            "premium_payment_history": policy.get("premium_payment_history", []),
        }, indent=2)

    elif pattern_key == "inflated_amounts":
        return json.dumps({
            "claim_id":       enriched.get("claim_id"),
            "claimed_amount": raw.get("claimed_amount"),
            "loss_type":      raw.get("loss_type"),
            "market_value":   vehicle.get("market_value"),
            "salvage_value":  vehicle.get("salvage_value"),
            "total_loss_threshold": vehicle.get("total_loss_threshold"),
            "regional_repair_benchmarks": vehicle.get("regional_repair_benchmarks", {}),
            "provider_avg_billing":    network.get("average_billing_amount"),
            "regional_avg_billing":    network.get("regional_average_billing"),
            "billing_ratio":           network.get("billing_ratio"),
        }, indent=2)

    elif pattern_key == "provider_network":
        return json.dumps({
            "claim_id":                   enriched.get("claim_id"),
            "provider_id":                network.get("provider_id"),
            "provider_name":              network.get("provider_name"),
            "license_status":             network.get("license_status"),
            "billing_ratio":              network.get("billing_ratio"),
            "flagged_claims_count":       network.get("flagged_claims_count", 0),
            "total_claims_served":        network.get("total_claims_served", 0),
            "referral_connections":       network.get("referral_connections", []),
            "claims_outside_service_area": network.get("claims_outside_service_area", 0),
            "geographic_service_area":    network.get("geographic_service_area"),
        }, indent=2)

    return json.dumps(enriched, indent=2)


def _parse_llm_response(raw: str, pattern_key: str) -> dict:
    """
    Extracts and validates JSON from LLM output.
    Handles markdown code fences, leading/trailing text.
    Falls back to a safe default if parsing fails.
    """
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()

    # Find the first JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Safe fallback — never crash the pipeline
    return {
        "pattern": pattern_key,
        "score": 0,
        "severity": "clean",
        "evidence": [],
        "reasoning": f"[Parse error] Raw response: {raw[:200]}",
        "exculpatory_factors": [],
    }


class BasePatternTool(BaseTool):
    """
    Abstract base for all 4 fraud pattern CoT tools.
    Subclasses only need to define:
      - name
      - description
      - pattern_key  (matches PromptFacade key and schema key)
    """

    pattern_key: str = ""   # override in subclass

    def __init__(self, llm_agent):
        """
        Args:
            llm_agent: google.adk.Agent instance from LLMProvider
        """
        self._agent = llm_agent

    async def execute(self, enriched_claim: dict) -> dict:
        # Build claim fields — raw_claim may be nested (post-enrichment) or flat (direct call)
        raw_claim = enriched_claim.get("raw_claim", enriched_claim)
        claimant  = raw_claim.get("claimant", {}) if isinstance(raw_claim, dict) else {}
        vehicle   = raw_claim.get("vehicle",  {}) if isinstance(raw_claim, dict) else {}

        # Load versioned CoT prompt — context is a superset of all 4 pattern variable lists
        # so this single call works for every pattern_key (duplicate_similar needs claimant_id + vin)
        prompt = PromptFacade.get_prompt(
            f"{self.pattern_key}_cot",
            context={
                "claim_id":         enriched_claim.get("claim_id", "UNKNOWN"),
                "claimant_name":    claimant.get("name", raw_claim.get("claimant_name", "Unknown")),
                "claimant_id":      claimant.get("id",   raw_claim.get("claimant_id",   "")),
                "vin":              vehicle.get("vin",   raw_claim.get("vin",            "")),
                "loss_date":        raw_claim.get("loss_date", ""),
                "loss_description": raw_claim.get("loss_description", raw_claim.get("description", "")),
                "claimed_amount":   raw_claim.get("claimed_amount", 0),
                "enriched_data":    _extract_pattern_data(self.pattern_key, enriched_claim),
            }
        )

        # LLM call — mock ADK in dev, real Gemini in prod
        raw_response = await self._agent.run(prompt)
        result_dict  = _parse_llm_response(str(raw_response), self.pattern_key)

        # Validate via Pydantic
        try:
            result = PatternResult(**result_dict)
            return result.model_dump()
        except Exception:
            return result_dict


