"""
Enrichment Agent — Tool 2: lookup_provider_network
"""
from src.infrastructure.tools.base_tool import BaseTool


class ProviderNetworkTool(BaseTool):
    name = "lookup_provider_network"
    description = (
        "Retrieves provider billing history and network connections from the mock provider DB. "
        "provider_type: 'repair_shop' | 'medical' | 'attorney' | 'towing'. "
        "Returns: provider_name, license_status (active|expired|suspended|under_investigation), "
        "total_claims_served, average_billing_amount, regional_average_billing, "
        "billing_ratio (provider_avg / regional_avg), referral_connections, "
        "geographic_service_area, claims_outside_service_area, flagged_claims_count. "
        "Key fraud signal: billing_ratio > 2.0 or license_status != 'active'."
    )

    def __init__(self, provider):
        self._provider = provider

    async def execute(self, provider_id: str, provider_type: str) -> dict:
        result = await self._provider.get_provider_network(provider_id, provider_type)
        result.setdefault("provider_id", provider_id)
        result.setdefault("provider_type", provider_type)
        result.setdefault("provider_name", "Unknown Provider")
        result.setdefault("license_status", "active")
        result.setdefault("total_claims_served", 0)
        result.setdefault("average_billing_amount", 0.0)
        result.setdefault("regional_average_billing", 0.0)
        result.setdefault("billing_ratio", 1.0)
        result.setdefault("referral_connections", [])
        result.setdefault("geographic_service_area", "unknown")
        result.setdefault("claims_outside_service_area", 0)
        result.setdefault("flagged_claims_count", 0)
        return result


