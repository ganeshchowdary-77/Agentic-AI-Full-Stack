"""
Enrichment Agent — Tool 1: lookup_claimant_history
"""
import json
from src.infrastructure.tools.base_tool import BaseTool


class ClaimantHistoryTool(BaseTool):
    name = "lookup_claimant_history"
    description = (
        "Retrieves the claimant's full claim history from the mock claims database. "
        "Returns: total_prior_claims, prior_claims list (claim_id, loss_date, loss_type, "
        "claimed_amount, outcome, fraud_flag), known_addresses, associated_vehicles, "
        "associated_policies, prior_fraud_flags, claim_frequency_per_year, total_prior_payouts. "
        "Key fraud signal: prior_fraud_flags > 0 or claim_frequency_per_year > 1.5."
    )

    def __init__(self, provider):
        self._provider = provider

    async def execute(self, claimant_id: str) -> dict:
        result = await self._provider.get_claimant_history(claimant_id)
        # Ensure schema-compliant keys
        result.setdefault("claimant_id", claimant_id)
        result.setdefault("total_prior_claims", 0)
        result.setdefault("prior_claims", [])
        result.setdefault("known_addresses", [])
        result.setdefault("associated_vehicles", [])
        result.setdefault("associated_policies", [])
        result.setdefault("prior_fraud_flags", 0)
        result.setdefault("claim_frequency_per_year", 0.0)
        result.setdefault("total_prior_payouts", 0.0)
        return result


