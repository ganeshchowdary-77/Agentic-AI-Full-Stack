"""
Enrichment Agent — Tool 3: lookup_vehicle_valuation
"""
from src.infrastructure.tools.base_tool import BaseTool


class VehicleValuationTool(BaseTool):
    name = "lookup_vehicle_valuation"
    description = (
        "Retrieves vehicle market value and repair cost benchmarks from mock vehicle DB. "
        "Returns: market_value, salvage_value, total_loss_threshold (70-75% of market value), "
        "regional_repair_benchmarks (minor_collision/major_collision/comprehensive each with "
        "low/median/high), prior_claims_on_vin (claim_id, date, amount), title_history. "
        "Key fraud signal: claimed_amount > market_value, or prior total-loss on same VIN."
    )

    def __init__(self, provider):
        self._provider = provider

    async def execute(self, vin: str, year: int, make: str, model: str) -> dict:
        result = await self._provider.get_vehicle_valuation(vin, year, make, model)
        result.setdefault("vin", vin)
        result.setdefault("year", year)
        result.setdefault("make", make)
        result.setdefault("model", model)
        result.setdefault("market_value", 0.0)
        result.setdefault("salvage_value", 0.0)
        result.setdefault("total_loss_threshold", 0.0)
        result.setdefault("regional_repair_benchmarks", {
            "minor_collision": {"low": 0, "median": 0, "high": 0},
            "major_collision": {"low": 0, "median": 0, "high": 0},
            "comprehensive":   {"low": 0, "median": 0, "high": 0},
        })
        result.setdefault("prior_claims_on_vin", [])
        result.setdefault("title_history", ["clean"])
        return result


