"""
Enrichment Tools — 4-source data gathering for claim enrichment.
Each tool calls MockEnrichmentProvider and returns structured data
for the Claim Data Enrichment Agent (Gemini Flash).
"""

from typing import Dict, Any
from google.adk.tools import ToolContext
from ..infrastructure.mock_providers import provider


async def lookup_claimant_history(claimant_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves the claimant's history from the mock claims database.
    Returns prior claims count, fraud flags, claim frequency, prior payouts,
    known addresses, associated vehicles, and associated policies.
    """
    data = await provider.get_claimant_history(claimant_id)
    return data


async def lookup_provider_network(provider_id: str, provider_type: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves provider information from the mock provider database.
    Returns billing ratio, flagged claims count, network risk level,
    license status, referral connections, and geographic service area.
    """
    data = await provider.get_provider_network(provider_id, provider_type)
    return data


async def lookup_vehicle_valuation(vin: str, year: int, make: str, model: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves vehicle valuation data from the mock vehicle database.
    Returns market value, salvage value, total loss threshold,
    regional repair benchmarks, prior claims on VIN, and title history.
    """
    data = await provider.get_vehicle_valuation(vin, year, make, model)
    return data


async def lookup_policy_details(policy_number: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves policy information from the mock policy administration system.
    Returns inception date, days since inception, coverage type, premium,
    recent policy changes, and policy status.
    """
    data = await provider.get_policy_details(policy_number)
    return data
