"""
Enrichment Agent — Tool 4: lookup_policy_details
"""
from src.infrastructure.tools.base_tool import BaseTool


class PolicyDetailsTool(BaseTool):
    name = "lookup_policy_details"
    description = (
        "Retrieves policy details, coverage, and recent changes from mock policy admin system. "
        "Returns: inception_date, expiration_date, days_since_inception, days_until_expiration, "
        "coverage_type, coverage_limits, premium_amount, premium_payment_history, "
        "recent_policy_changes (change_date, change_type, details), vehicles_on_policy, "
        "policy_status (active|lapsed|cancelled|reinstated), lapse_history. "
        "Key fraud signals: days_since_inception < 30, coverage upgraded within 72h of loss, "
        "lapse history with recent reinstatement."
    )

    def __init__(self, provider):
        self._provider = provider

    async def execute(self, policy_number: str) -> dict:
        result = await self._provider.get_policy_details(policy_number)
        result.setdefault("policy_number", policy_number)
        result.setdefault("inception_date", "")
        result.setdefault("expiration_date", "")
        result.setdefault("days_since_inception", 999)
        result.setdefault("days_until_expiration", 999)
        result.setdefault("coverage_type", "comprehensive")
        result.setdefault("coverage_limits", {})
        result.setdefault("premium_amount", 0.0)
        result.setdefault("premium_payment_history", [])
        result.setdefault("recent_policy_changes", [])
        result.setdefault("vehicles_on_policy", [])
        result.setdefault("policy_status", "active")
        result.setdefault("lapse_history", [])
        return result


